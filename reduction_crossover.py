"""Finite, correctness-gated search for a single-job Bend/CUB crossover."""
import argparse
import json
from pathlib import Path
import random
import re
import statistics
import time

from bend_bench.core import append, correct, environment, exclusive, execute, hash_file, load_config, provenance, write_json
from bend_bench.suites import plan, stage
from validate_applications import wait_idle

ROOT = Path(__file__).resolve().parent
MAX_COUNT = 1 << 30


def source(count):
    if not 1 <= count <= 1 << 31:
        raise ValueError('count must be between 1 and 2^31')
    base = (ROOT / 'src/bend_bench/assets/gpu/reduce.bend').read_text()
    # Build the prefix from unchanged power-of-two reductions. Only the
    # incomplete right edge differs from the original balanced reduction.
    if count & (count - 1) == 0:
        return base.replace('sum!(18n, 0)', f'sum!({count.bit_length()-1}n, 0)')
    prefix = base[:base.index('def main()')]
    n, start, index = count, 0, 0
    definitions = []
    while n:
        depth = n.bit_length() - 1
        width = 1 << depth
        call = f'sum({depth}n, {start // width})'
        definition = f'def chunk{index}() -> U32:\n'
        if n == width:
            definition += f'  {call}\n\n'
        else:
            definition += f'  a b = {call} chunk{index+1}()\n  U32.add(a, b)\n\n'
        definitions.append(definition)
        n, start, index = n-width, start+width, index+1
    return prefix + ''.join(reversed(definitions)) + 'def main() -> IO(Unit):\n  IO.print(U32.show(chunk0!()))\n'


def pins(config):
    files = [Path(__file__), ROOT / 'validate_applications.py']
    files += sorted((ROOT / 'src').rglob('*.py'))
    files += sorted((ROOT / 'src/bend_bench/assets').rglob('*'))
    return dict(provenance=provenance(config), files={str(p): hash_file(p) for p in files if p.is_file()})


def recipes(config, folder, count, cpu=False):
    local = {**config, 'gpu_depths': [23]}
    stage(local, folder)
    bend = folder / 'ports/cub-reduce-23.bend'
    bend.write_text(source(count))
    cuda = folder / 'gpu/cub.cu'
    text = cuda.read_text()
    old = '''unsigned depth=unsigned(atoi(argv[2]));
  if(depth>26 || (!sorting && strcmp(argv[1],"reduce"))) return 2;
  uint32_t n=1u<<depth;'''
    if text.count(old) != 1:
        raise ValueError('CUB adapter changed')
    cuda.write_text(text.replace(old, '''unsigned depth=0;
  unsigned long requested=strtoul(argv[2],nullptr,10);
  if(strcmp(argv[1],"reduce") || requested<1 || requested>(1ul<<31)) return 2;
  uint32_t n=uint32_t(requested);'''))
    # Independent scalar oracle, no large input allocation. The CUDA and Bend
    # sides still generate exactly these values inside their reductions.
    reference = folder / 'gpu/reference.cpp'
    reference.write_text('''#include <cstdint>
#include <cstdio>
int main() {
  uint32_t sum=0;
  for (uint32_t i=0; i<''' + str(count) + '''u; ++i) {
    uint32_t x=(i+1u)*2654435761u;
    x ^= x<<13; x ^= x>>17; x ^= x<<5;
    sum += x;
  }
  printf("%u\\n",sum);
}
''')
    builds, cases = plan(local, folder)
    builds = [c for c in builds if not any('cub-sort-' in str(v) for v in c)]
    cases = [c for c in cases if c['workload'] == 'reduce-23' and c['implementation'] != 'serial-cpp']
    for case in cases:
        if case['implementation'] == 'cub-cuda':
            case['command'][-1] = str(count)
    if cpu:
        import copy
        # Explicit wide item counts avoid offset overflow above INT_MAX.
        cuda.write_text(cuda.read_text().replace('keys,sum,n)', 'keys,sum,uint64_t(n))'))
        reference_case = cases[0]
        cpu_source = folder / 'gpu/reduction_cpu.cpp'
        cpu_source.write_text((ROOT / 'src/bend_bench/assets/gpu/reduction_cpu.cpp').read_text())
        for implementation, threads in [('bend-1', 1), ('bend-16', 16), ('serial-cpp', 1), ('openmp-16', 16)]:
            case = copy.deepcopy(reference_case)
            case.update(implementation=implementation, threads=threads, unsupported=None)
            case.pop('check_args', None)
            binary = folder / 'build' / implementation
            args = [str(count)]
            if implementation.startswith('bend-'):
                binary = folder / 'build/cub-reduce-23'
                args = ['--gpu', 'off', '--threads', str(threads)]
            else:
                flags = ['-fopenmp'] if threads == 16 else []
                builds.append([config['tools']['cxx'], '-std=c++17', '-O3', '-march=native',
                               '-ffp-contract=off', *flags, str(cpu_source), '-o', str(binary)])
            case['command'] = ['taskset', '-c', ','.join(map(str, config['cpus'][:threads])), str(binary), *args]
            case['env'].update(OMP_NUM_THREADS=str(threads), OMP_DYNAMIC='false')
            cases.append(case)
    return builds, cases


def build(config, folder, count, cpu=False):
    builds, cases = recipes(config, folder, count, cpu=cpu)
    for command in builds:
        result = execute(command, timeout=180)
        append(folder / 'build.jsonl', result)
        if result['returncode'] or result['timeout']:
            raise RuntimeError(f'Build failed: {folder}')
    oracle = execute([folder / 'build/cub-reference'], timeout=180)
    write_json(folder / 'oracle.json', oracle)
    if oracle['returncode'] or not re.fullmatch(r'\d+\s*', oracle['stdout']):
        raise RuntimeError('Oracle failed')
    for case in cases:
        case['expected_regex'] = oracle['stdout'].strip()
        case['id'] = f'reduce-{count}/{case["implementation"]}'
        case['contract'].update(size=count, expected=int(oracle['stdout']))
    artifacts = {str(p.relative_to(folder)): hash_file(p) for p in folder.rglob('*')
                 if p.is_file() and 'upstream' not in p.parts}
    libraries = {}
    for file in (folder / 'build').iterdir():
        if file.is_file() and file.read_bytes()[:4] == b'\x7fELF':
            result = execute(['ldd', file])
            for path in re.findall(r'(/[^\s()]+)', result['stdout']):
                if Path(path).is_file():
                    libraries[path] = hash_file(path)
    write_json(folder / 'prepared.json', dict(count=count, builds=builds, cases=cases, artifacts=artifacts, libraries=libraries))
    return cases


def measure(config, out, count, cpu=False, keep=None):
    folder = out / str(count)
    folder.mkdir()
    cases = build(config, folder, count, cpu=cpu)
    if keep:
        cases = [c for c in cases if c['implementation'] in keep]
    samples = {c['implementation']: [] for c in cases}
    rng = random.Random(count)
    for phase, repetitions in [('check', 1), ('warmup', 2), ('measure', 10)]:
        for rep in range(repetitions):
            order = list(cases)
            rng.shuffle(order)
            for case in order:
                result = execute(case['command'], env={**environment(), **case['env']},
                                 timeout=180, measured=True, gpu_policy=config)
                passed = correct(case, result)
                append(folder / 'samples.jsonl', dict(phase=phase, rep=rep, case=case['id'], correct=passed, **result))
                if not passed:
                    raise RuntimeError(f'Correctness/activity gate failed: {folder}')
                if phase == 'measure':
                    samples[case['implementation']].append(result['end_to_end_seconds'])
                if cpu:
                    print(phase, count, case['implementation'], rep, result['end_to_end_seconds'], flush=True)
    medians = {k: statistics.median(v) for k, v in samples.items()}
    result = dict(count=count, medians=medians)
    if {'cub-cuda', 'bend-cuda'} <= medians.keys():
        result['cub_wins'] = medians['cub-cuda'] < medians['bend-cuda']
    write_json(folder / 'summary.json', result)
    append(out / 'summary.jsonl', result)
    print('RESULT', json.dumps(result), flush=True)
    return result


def search(evaluate, maximum=MAX_COUNT, refinements=4):
    points = []
    lower = None
    count = 1 << 23
    while count <= maximum:
        point = evaluate(count)
        points.append(point)
        if point['cub_wins']:
            break
        lower = count
        count *= 2
    else:
        return points, None
    if lower is None:
        return points, [None, count]
    upper = count
    for _ in range(refinements):
        middle = (lower + upper) // 2
        point = evaluate(middle)
        points.append(point)
        if point['cub_wins']:
            upper = middle
        else:
            lower = middle
    return points, [lower, upper]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--enqueue', action='store_true')
    args = parser.parse_args()
    config = load_config(ROOT / 'gpu-primitives.toml')
    config['label'] = 'single-job-reduction-crossover'
    config['gpu_resident'] = {'cgroup': '/user.slice/user-1000.slice/user@1000.service/app.slice/transcribe-worker.service'}
    config['blocked_services'] += ['bend-bench-applications.service', 'bend-bench-gpu.service']
    out = args.request.resolve().parent
    if args.enqueue:
        out.mkdir(parents=True, exist_ok=False)
        write_json(args.request, dict(config=config, pins=pins(config), maximum=MAX_COUNT, refinements=4))
        return
    saved = json.loads(args.request.read_text())
    if (out / 'started.json').exists():
        raise RuntimeError('Request already started; preserve its evidence and enqueue a new request')
    config = saved['config']
    if pins(config) != saved['pins']:
        raise RuntimeError('Queued inputs changed; requeue explicitly')
    wait_idle(config, out)
    with exclusive(config):
        if pins(config) != saved['pins']:
            raise RuntimeError('Queued inputs changed during wait')
        write_json(out / 'started.json', {'status': 'running'})
        deadline = time.monotonic() + 3600
        def evaluate(count):
            if time.monotonic() > deadline:
                raise TimeoutError('One-hour measurement budget exhausted')
            return measure(config, out, count)
        points, bracket = search(evaluate, saved['maximum'], saved['refinements'])
        if pins(config) != saved['pins']:
            raise RuntimeError('Inputs changed during measurements')
    lines = ['# Single-job summation crossover', '',
             'Complete-program medians include startup, generation, summation and output. Each point has an independent scalar correctness check, two warmups and ten measured executions per implementation in shuffled order. Existing worker-canary exemptions apply; other GPU activity fails the run.', '',
             '| Generated integers | Bend GPU seconds | CUB seconds | Bend/CUB time ratio |', '|---|---:|---:|---:|']
    for p in sorted(points, key=lambda p: p['count']):
        b, c = p['medians']['bend-cuda'], p['medians']['cub-cuda']
        lines.append(f'| {p["count"]:,} | {b:.6f} | {c:.6f} | {b/c:.3f} |')
    lines += ['', f'Measured crossover bracket: {bracket}. A null bracket means no crossover was found within the size cap. A null lower bound means CUB already won at the starting size. This is a local bracket, not proof of a universal or monotonic threshold.', '',
              'Power-of-two points retain the original Bend reduction. Intermediate points join unchanged power-of-two reductions into a prefix of the same generated sequence. These intermediate points have unequal top-level branches. All original source copies, generated adapters, build commands, artifact hashes and failed samples are retained.', '']
    (out / 'report.md').write_text('\n'.join(lines))
    write_json(out / 'completed.json', dict(bracket=bracket, report=str(out / 'report.md')))
    print('COMPLETE', out / 'report.md', flush=True)


if __name__ == '__main__':
    main()
