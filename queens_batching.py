"""Matched 17-queen prefix corpus: natural recursion versus upfront batching."""
import argparse
import json
from pathlib import Path
import random
import re
import statistics
import time

from bend_bench.core import append, environment, exclusive, execute, hash_file, load_config, provenance, write_json

ROOT = Path(__file__).resolve().parent
VARIANTS = ['published-batch', 'recursive', 'recursive-batch']


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected one source anchor: {old}')
    return text.replace(old, new)


def sources(config, n, limit):
    if not 5 <= n <= 17 or not 1 <= limit <= n**4:
        raise ValueError('Expected N=5..17 and a nonempty prefix range')
    depth = (n**4-1).bit_length()
    full = (1 << n)-1
    folder = Path(config['bend']['path']) / 'bench/runtime/queens'
    base = (folder / 'main.bend').read_text().split('def main()')[0]
    extra = (ROOT / 'src/bend_bench/assets/ports/queens-prefix.bend').read_text()
    start = base.index('      +cc =', base.index('def pfx.s3'))
    end = base.index('\ndef pfx.s2', start)
    forked = base[:start] + '      leaf(nn2, full, c4, l4, r4)\n\n' + base[end:]
    batch = f'batch!({depth}n, 0, {(1 << depth)-1}, {n}, {full}, {limit})'
    natural = f'prefix!({n*n}n, 4n, {n}, {limit}, {full}, 0, 0, 0, {full}, 0, False{{}})'
    bend = {}
    for variant in VARIANTS:
        body = base if variant == 'published-batch' else forked
        # Bend resolves definitions in source order. The new leaf calls need
        # smerge and the recursive helpers before the published prefix decoder.
        merge = body[body.index('def smerge('):body.index('def batch(')]
        body = body.replace(merge, '')
        index = body.index('def pfx.s3(')
        body = body[:index] + merge + extra + '\n' + body[index:]
        call = natural if variant == 'recursive' else batch
        bend[variant] = body + f'\ndef main() -> IO(Unit):\n  emit.stats({call})\n'
    cpp = (folder / 'main.c').read_text()
    for name, value in [('DEPTH', depth), ('SIZE', n), ('LIMIT', limit)]:
        cpp, matches = re.subn(rf'#define {name} \d+u', f'#define {name} {value}u', cpp)
        if matches != 1:
            raise ValueError('C source constants changed')
    cpp = replace_once(cpp, 'static uint32_t run(', 'static Stats run(')
    cpp = replace_once(cpp, '  return (sols * 2654435761u) ^ nodes;', '  return (Stats){sols, nodes};')
    cpp = replace_once(cpp, '  printf("%u\\n", run(SIZE, LIMIT));',
                       '  Stats s = run(SIZE, LIMIT);\n  printf("%u %u\\n", s.sols, s.nodes);')
    omp = replace_once(cpp, '  for (uint32_t i = 0u;',
                       '  #pragma omp parallel for schedule(dynamic,16) reduction(+:sols,nodes)\n  for (uint32_t i = 0u;')
    return bend, cpp, omp


def build(config, folder, n, limit):
    folder.mkdir(parents=True)
    bend, cpp, omp = sources(config, n, limit)
    commands = []
    tools = config['tools']
    flags = ['-O3', '-march=native', '-ffp-contract=off']
    for variant, source in bend.items():
        path = folder / f'{variant}.bend'
        path.write_text(source)
        cfile = folder / f'{variant}.c'
        commands += [[tools['bun'], Path(config['bend']['path']) / 'bend2/main.ts', path, '-o', cfile],
                     [tools['cc'], '-std=c11', *flags, cfile, '-lpthread', '-lm', '-o', folder / variant]]
    for name, text in [('serial', cpp), ('openmp', omp)]:
        path = folder / f'{name}.c'
        path.write_text(text)
        commands.append([tools['cxx'], '-x', 'c++', '-std=c++17', *flags,
                         *(['-fopenmp'] if name == 'openmp' else []), path, '-o', folder / name])
    for command in commands:
        result = execute(command)
        append(folder / 'build.jsonl', result)
        if result['returncode'] or result['timeout']:
            raise RuntimeError(f'Build failed: {folder}; {result["stderr"]}')
    libraries = {}
    for name in [*VARIANTS, 'serial', 'openmp']:
        linked = execute(['ldd', folder / name])
        for path in re.findall(r'(/[^\s()]+)', linked['stdout']):
            if Path(path).is_file():
                libraries[path] = hash_file(path)
    write_json(folder / 'artifacts.json', dict(files={p.name: hash_file(p) for p in folder.iterdir() if p.is_file()}, libraries=libraries))


def command(config, folder, name, threads):
    argv = ['taskset', '-c', ','.join(map(str, config['cpus'][:threads])), folder / name]
    if name in VARIANTS:
        argv += ['--gpu', 'off', '--threads', threads]
    env = {**environment(), 'OMP_NUM_THREADS': str(threads), 'OMP_DYNAMIC': 'false',
           'OMP_PROC_BIND': 'true', 'OMP_PLACES': 'threads', 'OMP_STACKSIZE': '64M'}
    return argv, env


def pins(config):
    return dict(provenance=provenance(config), runner=hash_file(Path(__file__)))


def report(out, timings, expected):
    lines = ['# Matched 17×17 N-Queens batching', '',
             f'Each implementation searches the same legal four-row prefixes with base-17 IDs below 11,730. Every run must return the exact solution and below-prefix node counts: `{expected}`. The two recursive variants share the same inner search; their difference is recursive prefix discovery versus the published balanced, permuted prefix batch. The published variant is an anchor with a different, accumulator-based inner search.', '',
             '| Implementation | 1 CPU thread seconds | 16 CPU threads seconds | CPU speedup |', '|---|---:|---:|---:|']
    for name in [*VARIANTS, 'openmp', 'serial']:
        values = [timings.get(f'{name}/{threads}', []) for threads in (1, 16)]
        medians = [statistics.median(v) if len(v) == 10 else None for v in values]
        cells = [f'{v:.6f}' if v is not None else '' for v in medians]
        speedup = f'{medians[0]/medians[1]:.2f}×' if all(medians) else ''
        lines.append(f'| {name} | {cells[0]} | {cells[1]} | {speedup} |')
    lines += ['', 'Complete-program times include startup and printing the two counters. Each cell requires ten checked measurements after two warmups; order is shuffled within each repetition. Counters use wrapping U32 arithmetic. Small-board tests independently verify counts with a board-based reference. The full-size serial reference must reproduce the published checksum 2063750025. Prefix-construction work differs by design; both recursive variants count the same search nodes below those prefixes. This is a CPU experiment, not a GPU measurement.', '']
    (out / 'report.md').write_text('\n'.join(lines))


def run(request):
    saved = json.loads(request.read_text())
    config, out = saved['config'], request.parent
    if (out / 'started.json').exists() or pins(config) != saved['pins']:
        raise RuntimeError('Request already started or queued inputs changed')
    with exclusive(config):
        write_json(out / 'started.json', dict(status='running'))
        deadline = time.monotonic() + 7200
        build(config, out / 'work', 17, 11730)
        argv, env = command(config, out / 'work', 'serial', 1)
        oracle = execute(argv, env=env)
        write_json(out / 'oracle.json', oracle)
        if oracle['returncode'] or oracle['timeout'] or not re.fullmatch(r'\d+ \d+\s*', oracle['stdout']):
            raise RuntimeError('Oracle failed')
        expected = oracle['stdout'].strip()
        sols, nodes = map(int, expected.split())
        if (((sols*2654435761) & 0xffffffff) ^ nodes) != 2063750025:
            raise RuntimeError('Reference differs from published checksum')
        cases = [(name, threads) for name in [*VARIANTS, 'openmp'] for threads in (1, 16)] + [('serial', 1)]
        timings = {f'{name}/{threads}': [] for name, threads in cases}
        rng = random.Random(17)
        for phase, reps in [('check', 1), ('warmup', 2), ('measure', 10)]:
            for rep in range(reps):
                order = cases.copy()
                rng.shuffle(order)
                for name, threads in order:
                    if time.monotonic() > deadline:
                        raise TimeoutError('Two-hour experiment budget exhausted')
                    argv, env = command(config, out / 'work', name, threads)
                    result = execute(argv, env=env, measured=True)
                    passed = not (result['returncode'] or result['timeout']) and result['stdout'].strip() == expected
                    key = f'{name}/{threads}'
                    append(out / 'samples.jsonl', dict(case=key, phase=phase, rep=rep, correct=passed, **result))
                    print(phase, key, rep, result['end_to_end_seconds'], passed, flush=True)
                    if not passed:
                        raise RuntimeError(f'Correctness gate failed: {key}')
                    if phase == 'measure':
                        timings[key].append(result['end_to_end_seconds'])
                report(out, timings, expected)
        if pins(config) != saved['pins']:
            raise RuntimeError('Inputs changed during run')
    write_json(out / 'summary.json', dict(expected=expected, medians={key: statistics.median(v) for key, v in timings.items()}))
    write_json(out / 'completed.json', dict(report=str(out / 'report.md')))
    print('COMPLETE', out / 'report.md', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--enqueue', action='store_true')
    args = parser.parse_args()
    request = args.request.resolve()
    if args.enqueue:
        config = load_config(ROOT / 'nqueens.toml')
        config.update(label='matched-queens-batching', threads=[1, 16])
        config['blocked_services'] += ['bend-bench-summation-scaling.service', 'bend-bench-validation.service']
        request.parent.mkdir(parents=True, exist_ok=False)
        write_json(request, dict(config=config, pins=pins(config), size=17, limit=11730))
    else:
        try:
            run(request)
        except Exception as error:
            write_json(request.parent / 'failed.json', dict(error=repr(error)))
            raise


if __name__ == '__main__':
    main()
