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
from itertools import product

from bend_bench.core import append, environment, exclusive, execute, hash_file, load_config, provenance, write_json
from bend_bench.gpu_activity import Monitor, process_identity
from bend_bench.suites import plan, stage

ROOT = Path(__file__).resolve().parent


def bend_resident(source, depth, total=12):
    source = source.replace('answer(position(i))', 'answer(position(U32.and(U32.add(i, offset), 15)))')
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
        Unit <- emit(batch!({depth}n, 0, U32.and(U32.add(U32.from_nat(p), {(12-total) & 15}), 15)), start)
        repeat(p)

def main() -> IO(Unit):
  do IO<Unit>:
    Unit <- IO.print("READY")
    repeat({total}n)
'''


def cpp_resident(source, count, total=12):
    source = '#include <vector>\n' + source
    source = source[:source.index('int main()')]
    source = source.replace('int position = blockIdx.x, move = threadIdx.x;',
                            'int position = blockIdx.x, move = threadIdx.x; int input = (position + offset) & 15;')
    source = source.replace('__global__ void children(int *out)', '__global__ void children(int *out, int offset)')
    source = source.replace('positions[position]', 'positions[input]')
    source = source.replace('int position = threadIdx.x, best = -1;',
                            f'int position = blockIdx.x * blockDim.x + threadIdx.x, best = -1; if (position >= {count}) return;')
    return source + f'''
int main() {{
  constexpr int count = {count};
  std::vector<int> out(count);
#ifdef __CUDACC__
  int *d, *scores;
  CUDA(cudaDeviceSetLimit(cudaLimitStackSize, 32768));
  CUDA(cudaMalloc(&d, count * sizeof(int)));
  CUDA(cudaMalloc(&scores, count * 32 * sizeof(int)));
#endif
  puts("READY"); fflush(stdout);
  for (int rep = 0; rep < {total}; ++rep) {{
    int offset = (11 - rep) & 15;
    auto start = std::chrono::steady_clock::now();
#ifdef __CUDACC__
    children<<<count, 32>>>(scores, offset);
    CUDA(cudaGetLastError());
    combine<<<(count + 127) / 128, 128>>>(scores, d);
    CUDA(cudaGetLastError());
    CUDA(cudaMemcpy(out.data(), d, count * sizeof(int), cudaMemcpyDeviceToHost));
#else
#pragma omp parallel for schedule(dynamic, 1)
    for (int i = 0; i < count; ++i)
      out[i] = 1 + solve(positions[(i + offset) & 15][0], positions[(i + offset) & 15][1], empty, -2, 2);
#endif
    auto searched = std::chrono::steady_clock::now();
    for (int value : out) printf("%d\\n", value);
    puts("END"); fflush(stdout);
    auto done = std::chrono::steady_clock::now();
    fprintf(stderr, "PHASE_NS %lld %lld %lld\\n",
      (long long)std::chrono::duration_cast<std::chrono::nanoseconds>(start.time_since_epoch()).count(),
      (long long)std::chrono::duration_cast<std::chrono::nanoseconds>(searched.time_since_epoch()).count(),
      (long long)std::chrono::duration_cast<std::chrono::nanoseconds>(done.time_since_epoch()).count());
  }}
#ifdef __CUDACC__
  CUDA(cudaFree(d)); CUDA(cudaFree(scores));
#endif
}}
'''


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
                        mismatches += line != str(expected[(values + 11 - rep) & 15]).encode()
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
    args = parser.parse_args()
    config = load_config(ROOT / 'applications-mnk.toml')
    config.update(mnk_games=[[5, 5, 4, 8]], threads=[1, 16])
    config['blocked_services'].append('bend-bench-applications.service')
    out = ROOT / 'runs' / time.strftime('mnk-sustained-%Y%m%d-%H%M%S')
    out.mkdir()
    write_json(out / 'provenance.json', dict(harness=provenance(config), script_sha256=hash_file(__file__), arguments=vars(args), shuffle_seed=20260918))
    from validate_applications import wait_idle
    wait_idle(config, out)
    report = ['# Resident-process endgame throughput', '',
              'Repeated fixed corpus of 16 positions, two warmup batches per process. Latency includes answer formatting, pipe delivery and host observation; it is not kernel time. Full-process throughput counts all completed batches including warmups and includes startup and shutdown.', '',
              '| Positions per batch | Measured batches | Implementation | Mean delivered batch ms | Positions/second excluding warmups | Positions/second full process | Startup to READY ms |',
              '|---|---:|---|---:|---:|---:|---:|']
    with exclusive(config):
        for depth, measured in product(args.depths, args.batches):
            count = 1 << depth
            total = measured + 2
            work = out / f'{count}-batches-{measured}'
            work.mkdir()
            (work / 'build').mkdir()
            stage(config, work)
            name = 'mnk-5-5-4-8'
            source = work / 'ports' / (name + '.bend')
            source.write_text(bend_resident(source.read_text(), depth, total))
            cpp = work / 'gpu/mnk.cpp'
            cpp.write_text(cpp_resident(cpp.read_text(), count, total))
            builds, cases = plan(config, work)
            for command in builds:
                result = execute(command, timeout=180)
                append(work / 'build.jsonl', result)
                if result['returncode']:
                    raise RuntimeError(f'Build failed: {work}')
            write_json(work / 'hashes.json', {str(p.relative_to(work)): hash_file(p) for p in work.rglob('*') if p.is_file()})
            expected = json.loads(source.with_suffix('.json').read_text())
            selected = []
            for case in cases:
                if args.multicore_only and case['implementation'] == 'bend' and case['threads'] == 1:
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
                report.append(f"| {count} | {measured} | {folder.name} | {latency * 1000:.3f} | {count / latency:.1f} | {result['positions_per_second_including_startup']:.1f} | {result['startup_seconds'] * 1000:.3f} |")
                (out / 'report.md').write_text('\n'.join(report) + '\n')
                print(report[-1], flush=True)
    write_json(out / 'completed.json', dict(report=str(out / 'report.md')))
    print('COMPLETE', out, flush=True)


if __name__ == '__main__':
    main()
