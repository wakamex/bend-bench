"""Finite resident-process MNK throughput diagnostic, preserving all evidence."""
import json
import argparse
import os
from pathlib import Path
import selectors
import statistics
import subprocess
import time
import random
import threading
import copy
from itertools import product

from bend_bench.core import append, environment, exclusive, execute, hash_file, load_config, provenance, write_json
from bend_bench.gpu_activity import Monitor, process_identity
from bend_bench.suites import plan, stage
from bend_bench.applications import lines

ROOT = Path(__file__).resolve().parent


def bend_resident(source, depth, total=12, corpus_size=16):
    mask = corpus_size - 1
    source = source.replace('answer(position(i))', f'answer(position(U32.and(U32.add(i, offset), {mask})))')
    source = source.replace('def batch(+d: Nat, +i: U32)', 'def batch(+d: Nat, +i: U32, +offset: U32)')
    source = source.replace('batch(p, U32.shl(i)) batch(p, U32.inc(U32.shl(i)))',
                            'batch(p, U32.shl(i), offset) batch(p, U32.inc(U32.shl(i)), offset)')
    source = source[:source.index('def main()')]
    return source + f'''def emit(a: Answers, start: Nat) -> IO(Unit):
  do IO<Unit>:
    end : Nat <- IO.now()
    Unit <- IO.print(output(a, "END"))
    done : Nat <- IO.now()
    IO.print_err("PHASE_MS " ++ Nat.show(start) ++ " " ++ Nat.show(end) ++ " " ++ Nat.show(done))

def repeat(+n: Nat) -> IO(Unit):
  match n:
    case 0n: IO.pure(Unit, Unit{{}})
    case 1n+p:
      do IO<Unit>:
        start : Nat <- IO.now()
        Unit <- emit(batch!({depth}n, 0, U32.and(U32.add(U32.from_nat(p), {(12-total) & mask}), {mask})), start)
        repeat(p)

def main() -> IO(Unit):
  do IO<Unit>:
    Unit <- IO.print("READY")
    repeat({total}n)
'''


def cpp_resident(source, count, total=12, corpus_size=16):
    mask = corpus_size - 1
    source = '#include <vector>\n#include <string>\n' + source
    source = source[:source.index('int main()')]
    source = source.replace('int position = blockIdx.x, move = threadIdx.x;',
                            f'int position = blockIdx.x, move = threadIdx.x; int input = (position + offset) & {mask};')
    source = source.replace('__global__ void children(int *out)', '__global__ void children(int *out, int offset)')
    source = source.replace('positions[position]', 'positions[input]')
    source = source.replace('int position = threadIdx.x, best = -1;',
                            f'int position = blockIdx.x * blockDim.x + threadIdx.x, best = -1; if (position >= {count}) return;')
    source = source.replace('empty - 1, -2, 2)', 'empty - 1, -SEARCH_BOUND, SEARCH_BOUND)')
    source = '#ifndef OMP_CHUNK\n#define OMP_CHUNK 1\n#endif\n#ifndef SEARCH_BOUND\n#define SEARCH_BOUND 2\n#endif\n' + source
    return source + f'''
#ifdef __CUDACC__
__global__ void whole_positions(int *out, int offset) {{
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= {count}) return;
  int input = (i + offset) & {mask};
  out[i] = 1 + solve(positions[input][0], positions[input][1], empty, -SEARCH_BOUND, SEARCH_BOUND);
}}
#endif
int main() {{
  constexpr int count = {count};
  std::vector<int> out(count);
#ifdef BULK_OUTPUT
  // Override the observer's legacy line buffering before any stdout operation.
  if (setvbuf(stdout, nullptr, _IOFBF, 65536)) return 3;
  std::string text;
  text.reserve(count * 2 + 4);
#endif
#ifdef __CUDACC__
  int *d, *scores;
  CUDA(cudaDeviceSetLimit(cudaLimitStackSize, 32768));
  CUDA(cudaMalloc(&d, count * sizeof(int)));
#ifndef WHOLE_POSITION
  CUDA(cudaMalloc(&scores, count * 32 * sizeof(int)));
#endif
#endif
  puts("READY"); fflush(stdout);
  for (int rep = 0; rep < {total}; ++rep) {{
    int offset = (11 - rep) & {mask};
    auto start = std::chrono::steady_clock::now();
#ifdef __CUDACC__
#ifdef WHOLE_POSITION
    whole_positions<<<(count + 127) / 128, 128>>>(d, offset);
#else
    children<<<count, 32>>>(scores, offset);
    CUDA(cudaGetLastError());
    combine<<<(count + 127) / 128, 128>>>(scores, d);
#endif
    CUDA(cudaGetLastError());
    CUDA(cudaMemcpy(out.data(), d, count * sizeof(int), cudaMemcpyDeviceToHost));
#else
#pragma omp parallel for schedule(dynamic, OMP_CHUNK)
    for (int i = 0; i < count; ++i)
      out[i] = 1 + solve(positions[(i + offset) & {mask}][0], positions[(i + offset) & {mask}][1], empty, -SEARCH_BOUND, SEARCH_BOUND);
#endif
    auto searched = std::chrono::steady_clock::now();
#ifdef BULK_OUTPUT
    text.clear();
    for (int value : out) {{
      if (value < 0 || value > 2) return 4;
      text.push_back('0' + value);
      text.push_back('\\n');
    }}
    text += "END\\n";
    if (fwrite(text.data(), 1, text.size(), stdout) != text.size()) return 5;
    if (fflush(stdout)) return 5;
#else
    for (int value : out) printf("%d\\n", value);
    puts("END"); fflush(stdout);
#endif
    auto done = std::chrono::steady_clock::now();
    fprintf(stderr, "PHASE_NS %lld %lld %lld\\n",
      (long long)std::chrono::duration_cast<std::chrono::nanoseconds>(start.time_since_epoch()).count(),
      (long long)std::chrono::duration_cast<std::chrono::nanoseconds>(searched.time_since_epoch()).count(),
      (long long)std::chrono::duration_cast<std::chrono::nanoseconds>(done.time_since_epoch()).count());
  }}
#ifdef __CUDACC__
  CUDA(cudaFree(d));
#ifndef WHOLE_POSITION
  CUDA(cudaFree(scores));
#endif
#endif
}}
'''


def control_variants(builds, cases):
    """Retain the original controls and vary bounds, then GPU decomposition."""
    for case in list(cases):
        impl = case['implementation']
        if impl not in ('local-alpha-beta-cuda', 'local-alpha-beta-openmp'):
            continue
        executable = case['command'][3]
        build = next(b for b in builds if '-o' in b and b[b.index('-o') + 1] == executable)
        variants = [('tight', ['-DSEARCH_BOUND=1'])]
        if impl.endswith('cuda'):
            variants.append(('position-tight', ['-DSEARCH_BOUND=1', '-DWHOLE_POSITION=1']))
        for label, flags in variants:
            target = executable + '-' + label
            if any('-o' in b and b[b.index('-o') + 1] == target for b in builds):
                continue  # CPU thread-count cases share one binary.
            command = list(build)
            command[command.index('-o') + 1] = target
            builds.append([*command, *flags])
        for label, _ in variants:
            variant = copy.deepcopy(case)
            variant['implementation'] = impl.replace('-cuda', f'-{label}-cuda') if impl.endswith('cuda') else impl + '-' + label
            variant['id'] += '-' + label
            variant['command'][3] = executable + '-' + label
            cases.append(variant)


def derived_variants(builds, cases, label, flag, required):
    """Give a one-factor control a distinct binary and result identity."""
    for case in list(cases):
        if required not in case['implementation']:
            continue
        executable = case['command'][3]
        target = executable + '-' + label
        build = next(b for b in builds if '-o' in b and b[b.index('-o') + 1] == executable)
        if not any('-o' in b and b[b.index('-o') + 1] == target for b in builds):
            command = list(build)
            command[command.index('-o') + 1] = target
            builds.append([*command, flag])
        variant = copy.deepcopy(case)
        impl = case['implementation']
        variant['implementation'] = impl.replace('-cuda', f'-{label}-cuda') if impl.endswith('cuda') else impl + '-' + label
        variant['id'] += '-' + label
        variant['command'][3] = target
        cases.append(variant)


def bulk_variants(builds, cases):
    derived_variants(builds, cases, 'bulk', '-DBULK_OUTPUT=1', 'tight')


def literal_win_check(source, m=5, n=5, k=4):
    start = source.index('SEARCH bool won(')
    end = source.index('SEARCH int solve(', start)
    masks = [sum(1 << i for i in line) for line in lines(m, n, k)]
    # The Bend generator prepends each mask to its expression.
    expression = ' || '.join(f'((board & {mask}u) == {mask}u)' for mask in reversed(masks))
    replacement = f'#ifdef LITERAL_WIN\nSEARCH bool won(uint32_t board) {{ return {expression}; }}\n#else\n'
    return source[:start] + replacement + source[start:end] + '#endif\n' + source[end:]


def chunked_bend_output(source):
    helpers = '''def chunk_text(a: Answers) -> String:
  match a:
    case Answer{v}: U32.show(v)
    case Both{a, b}: output(a, chunk_text(b))

def print_chunks(+depth: Nat, a: Answers) -> IO(Unit):
  match depth:
    case 0n: IO.print(chunk_text(a))
    case 1n+p:
      match a:
        case Answer{v}: IO.print(U32.show(v))
        case Both{a, b}:
          do IO<Unit>:
            Unit <- print_chunks(p, a)
            print_chunks(p, b)

'''
    old = '    Unit <- IO.print(output(a, "END"))'
    if source.count(old) != 1:
        raise ValueError('Resident Bend output template changed')
    return source.replace('def emit(', helpers + 'def emit(', 1).replace(old, '    Unit <- print_chunks(7n, a)\n    Unit <- IO.print("END")')


def bend_output_variants(builds, cases, source, work):
    target_source = source.with_name(source.stem + '-chunks.bend')
    target_source.write_text(chunked_bend_output(source.read_text()))
    base = str(work / 'build' / source.stem)
    mapping = {str(source): str(target_source), base: base + '-chunks',
               base + '.c': base + '-chunks.c', base + '-cuda': base + '-chunks-cuda'}
    for command in list(builds):
        if any(arg in mapping for arg in command):
            builds.append([mapping.get(arg, arg) for arg in command])
    for case in list(cases):
        if not case['implementation'].startswith('bend'):
            continue
        variant = copy.deepcopy(case)
        variant['implementation'] = 'bend-chunks-cuda' if case['implementation'].endswith('cuda') else 'bend-chunks'
        variant['id'] += '-chunks'
        variant['command'][3] = mapping[case['command'][3]]
        cases.append(variant)


class Telemetry:
    """Low-frequency hardware observations, kept outside benchmark stdout."""
    def __init__(self, folder):
        self.folder = folder
        self.stop = threading.Event()
        self.pid = None
        self.gpu_file = (folder / 'gpu-telemetry.csv').open('w')
        self.gpu = subprocess.Popen(['nvidia-smi', '--query-gpu=timestamp,temperature.gpu,power.draw,clocks.sm,clocks.mem,utilization.gpu,memory.used',
                                     '--format=csv', '--loop-ms=1000'], stdout=self.gpu_file, stderr=subprocess.STDOUT)
        self.thread = threading.Thread(target=self.sample, daemon=True)
        self.thread.start()

    def sample(self):
        while not self.stop.is_set():
            record = dict(monotonic=time.monotonic(), cpu_stat=Path('/proc/stat').read_text(),
                          load=os.getloadavg(), observer_stat=Path('/proc/self/stat').read_text())
            if self.pid:
                try:
                    record['process_stat'] = Path(f'/proc/{self.pid}/stat').read_text()
                    record['process_status'] = Path(f'/proc/{self.pid}/status').read_text()
                except FileNotFoundError:
                    pass
            append(self.folder / 'host-telemetry.jsonl', record)
            self.stop.wait(1)

    def close(self):
        self.stop.set()
        self.thread.join()
        self.gpu.terminate()
        self.gpu.wait(timeout=10)
        self.gpu_file.close()


def resident(command, folder, config, expected, count, gpu, total=12, telemetry=False):
    """Timestamp batch boundaries before parsing; retain complete output and activity."""
    started = time.monotonic()
    result = dict(command=list(map(str, command)), batches=[], correct=False)
    monitor = Monitor(config) if gpu else None
    hardware = Telemetry(folder) if telemetry else None
    proc = None
    try:
        with (folder / 'stderr.txt').open('w') as err, (folder / 'stdout.txt').open('wb') as raw:
            started = time.monotonic()
            proc = subprocess.Popen(['stdbuf', '-oL', *map(str, command)], stdout=subprocess.PIPE,
                                    stderr=err, env={**environment(), 'OMP_NUM_THREADS': '16',
                                    'OMP_PROC_BIND': 'true', 'OMP_PLACES': 'threads'}, start_new_session=True)
            if hardware:
                hardware.pid = proc.pid
            if monitor:
                monitor.activity.known_benchmarks = {proc.pid: process_identity(proc.pid)['start_ticks']}
                monitor.start(proc.pid)
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ)
            pending = b''
            values = 0
            mismatches = 0
            previous = None
            deadline = started + 300
            while time.monotonic() < deadline:
                if not selector.select(1):
                    continue
                chunk = os.read(proc.stdout.fileno(), 65536)
                if not chunk:
                    break
                raw.write(chunk)
                pending += chunk
                lines = pending.split(b'\n')
                pending = lines.pop()
                for line in lines:
                    if line == b'READY':
                        previous = time.monotonic()
                        result['startup_seconds'] = previous - started
                    elif line == b'END':
                        now = time.monotonic()
                        if previous is None:
                            raise ValueError('Missing READY')
                        result['batches'].append(dict(seconds=now - previous, elapsed_seconds=now - started, answers=values,
                                                      mismatches=mismatches, correct=values == count and mismatches == 0))
                        previous, values, mismatches = now, 0, 0
                    else:
                        rep = len(result['batches'])
                        mismatches += line != str(expected[(values + 11 - rep) % len(expected)]).encode()
                        values += 1
            selector.close()
            if proc.poll() is None:
                proc.wait(timeout=max(0.1, deadline - time.monotonic()))
            result['returncode'] = proc.returncode
            result['correct'] = proc.returncode == 0 and len(result['batches']) == total and not pending and not values
            for batch in result['batches']:
                result['correct'] &= batch['correct']
    except Exception as error:
        result['error'] = repr(error)
    finally:
        if proc and proc.poll() is None:
            import signal
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        result['process_seconds'] = time.monotonic() - started
        elapsed = 0
        for index, batch in enumerate(result['batches']):
            batch['cumulative_positions_per_second_including_startup'] = (index + 1) * count / batch['elapsed_seconds']
            if index >= 2:
                elapsed += batch['seconds']
                batch['cumulative_measured_positions_per_second'] = (index - 1) * count / elapsed
        result['total_batches'] = total
        result['positions_per_second_including_startup'] = total * count / result['process_seconds']
        if proc and proc.stdout:
            proc.stdout.close()
        if monitor:
            result['gpu_activity'] = monitor.finish()
            result['correct'] &= not result['gpu_activity']['errors']
        if hardware:
            hardware.close()
        phases = []
        for line in (folder / 'stderr.txt').read_text().splitlines():
            if line.startswith(('PHASE_MS ', 'PHASE_NS ')):
                kind, start, end, done = line.split()
                scale = 1000 if kind == 'PHASE_MS' else 1e9
                phases.append(dict(search_seconds=(int(end)-int(start))/scale,
                                   output_seconds=(int(done)-int(end))/scale))
        result['phases'] = phases
        if phases:
            result['correct'] &= len(phases) == total and all(p['search_seconds'] >= 0 and p['output_seconds'] >= 0 for p in phases)
        write_json(folder / 'result.json', result)
    if not result['correct']:
        raise RuntimeError(f'Resident correctness/activity gate failed: {folder}')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--depths', type=int, nargs='+', choices=range(4, 23), default=[4, 8, 12, 16])
    parser.add_argument('--gpu-only', action='store_true', help='Measure only the two GPU implementations')
    parser.add_argument('--batches', type=int, nargs='+', choices=(10, 30, 100), default=[10], help='Measured batches after two warmups')
    parser.add_argument('--repeats', type=int, choices=range(1, 6), default=1, help='Independent process repetitions in shuffled order')
    parser.add_argument('--telemetry', action='store_true')
    parser.add_argument('--multicore-only', action='store_true', help='Omit Bend one-thread measurements')
    parser.add_argument('--corpus-sizes', type=int, nargs='+', choices=(16, 64, 256, 1024), default=[16])
    parser.add_argument('--control-variants', action='store_true', help='Add tight-bound CPU/root-CUDA and whole-position CUDA controls')
    parser.add_argument('--bulk-variants', action='store_true', help='Compare per-answer and bulk output on tight-bound controls')
    parser.add_argument('--literal-win-variants', action='store_true', help='Add literal-mask win checks to bulk-output controls')
    parser.add_argument('--scheduling-output-variants', action='store_true', help='Compare OpenMP chunks 1/16/64/256 and chunked Bend output')
    args = parser.parse_args()
    if min(1 << d for d in args.depths) < max(args.corpus_sizes):
        parser.error('Every batch must cover the complete corpus')
    config = load_config(ROOT / 'applications-mnk.toml')
    config.update(mnk_games=[[5, 5, 4, 8]], threads=[1, 16])
    config['blocked_services'].append('bend-bench-applications.service')
    out = ROOT / 'runs' / time.strftime('mnk-sustained-%Y%m%d-%H%M%S')
    out.mkdir()
    write_json(out / 'provenance.json', dict(harness=provenance(config), script_sha256=hash_file(__file__), arguments=vars(args), shuffle_seed=20260918))
    from validate_applications import wait_idle
    wait_idle(config, out)
    report = ['# Resident-process endgame throughput', '',
              'Deterministic distinct legal positions, independently solved by the tuple-board oracle. Larger corpora preserve the original prefix. Two warmup batches per process. Latency includes answer formatting, pipe delivery and host observation; it is not kernel time. Full-process throughput counts all completed batches including warmups and includes startup and shutdown.', '',
              '| Distinct positions | Positions per batch | Measured batches | Implementation | Mean delivered batch ms | Positions/second excluding warmups | Positions/second full process | Startup to READY ms | Mean search-to-host ms | Mean output ms |',
              '|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|']
    with exclusive(config):
        for corpus_size, depth, measured in product(args.corpus_sizes, args.depths, args.batches):
            count = 1 << depth
            total = measured + 2
            work = out / f'corpus-{corpus_size}-{count}-batches-{measured}'
            work.mkdir()
            (work / 'build').mkdir()
            stage(config, work, mnk_count=corpus_size)
            name = 'mnk-5-5-4-8'
            source = work / 'ports' / (name + '.bend')
            source.write_text(bend_resident(source.read_text(), depth, total, corpus_size))
            cpp = work / 'gpu/mnk.cpp'
            cpp_source = cpp_resident(cpp.read_text(), count, total, corpus_size)
            if args.literal_win_variants:
                cpp_source = literal_win_check(cpp_source)
            cpp.write_text(cpp_source)
            builds, cases = plan(config, work)
            if args.control_variants or args.bulk_variants or args.literal_win_variants or args.scheduling_output_variants:
                control_variants(builds, cases)
            if args.bulk_variants or args.literal_win_variants or args.scheduling_output_variants:
                bulk_variants(builds, cases)
            if args.literal_win_variants:
                derived_variants(builds, cases, 'literal', '-DLITERAL_WIN=1', 'bulk')
            if args.scheduling_output_variants:
                for chunk in (16, 64, 256):
                    # Exact base selection avoids deriving variants of variants.
                    selected_cases = [c for c in cases if c['implementation'] == 'local-alpha-beta-openmp-tight-bulk']
                    derived_variants(builds, selected_cases, f'chunk{chunk}', f'-DOMP_CHUNK={chunk}', 'bulk')
                    cases.extend(c for c in selected_cases if f'chunk{chunk}' in c['implementation'])
                bend_output_variants(builds, cases, source, work)
            for case in cases:
                case['contract'] = {**case['contract'], 'positions': count, 'distinct_positions': corpus_size,
                                    'measured_batches': measured, 'warmup_batches': 2,
                                    'implementation_variant': case['implementation'],
                                    'output_policy': 'Bend subtree chunks, split depth 7' if 'bend-chunks' in case['implementation'] else
                                        'Bend string' if case['implementation'].startswith('bend') else
                                        ('bulk text' if 'bulk' in case['implementation'] else 'line-flushed printf'),
                                    'win_check': 'literal expressions' if case['implementation'].startswith('bend') or
                                        'literal' in case['implementation'] else 'mask array loop'}
            write_json(work / 'experiment.json', dict(corpus_size=corpus_size, positions_per_batch=count,
                       bounds='Original controls [-2,2]; tight controls [-1,1]; Bend [0,2]',
                       move_order='ascending empty square index', builds=builds, cases=cases))
            for command in builds:
                result = execute(command, timeout=180)
                append(work / 'build.jsonl', result)
                if result['returncode']:
                    raise RuntimeError(f'Build failed: {work}')
            write_json(work / 'hashes.json', {str(p.relative_to(work)): hash_file(p) for p in work.rglob('*') if p.is_file()})
            expected = json.loads(source.with_suffix('.json').read_text())
            write_json(work / 'corpus-summary.json', dict(distinct_positions=len(expected),
                       outcomes={label: expected.count(value) for value, label in enumerate(('loss', 'draw', 'win'))},
                       corpus_sha256=hash_file(source.with_suffix('.corpus.json'))))
            selected = []
            for case in cases:
                if args.scheduling_output_variants and not (
                    case['implementation'].startswith('bend') or
                    case['implementation'] == 'local-alpha-beta-openmp-tight-bulk' or
                    case['implementation'].startswith('local-alpha-beta-openmp-tight-bulk-chunk')
                ):
                    continue
                if args.multicore_only and case['implementation'].startswith('bend') and not case['implementation'].endswith('cuda') and case['threads'] == 1:
                    continue
                if args.gpu_only and not case['implementation'].endswith('cuda'):
                    continue
                if case['implementation'] != 'bend' and case['threads'] == 1 and not case['implementation'].endswith('cuda'):
                    continue
                selected.append(case)
            schedule = [(case, repetition) for repetition in range(args.repeats) for case in selected]
            if args.repeats > 1:
                random.Random(20260918).shuffle(schedule)
            write_json(work / 'schedule.json', [dict(case=c['id'], repetition=r) for c,r in schedule])
            for case, repetition in schedule:
                folder = work / f"{case['implementation']}-{case['threads']}-run{repetition}"
                folder.mkdir()
                result = resident(case['command'], folder, config, expected, count, case['implementation'].endswith('cuda'), total, args.telemetry)
                if len(result['phases']) != total:
                    raise RuntimeError(f'Missing phase measurements: {folder}')
                latency = statistics.mean(b['seconds'] for b in result['batches'][2:])
                search_ms = statistics.mean(p['search_seconds'] for p in result['phases'][2:]) * 1000
                output_ms = statistics.mean(p['output_seconds'] for p in result['phases'][2:]) * 1000
                report.append(f"| {corpus_size} | {count} | {measured} | {folder.name} | {latency * 1000:.3f} | {count / latency:.1f} | {result['positions_per_second_including_startup']:.1f} | {result['startup_seconds'] * 1000:.3f} | {search_ms:.3f} | {output_ms:.3f} |")
                (out / 'report.md').write_text('\n'.join(report) + '\n')
                print(report[-1], flush=True)
    write_json(out / 'completed.json', dict(report=str(out / 'report.md')))
    print('COMPLETE', out, flush=True)


if __name__ == '__main__':
    main()
