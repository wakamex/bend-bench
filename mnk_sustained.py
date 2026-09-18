"""Finite resident-process MNK throughput diagnostic, preserving all evidence."""
import json
import argparse
import os
from pathlib import Path
import selectors
import statistics
import subprocess
import time

from bend_bench.core import append, environment, exclusive, execute, hash_file, load_config, provenance, write_json
from bend_bench.gpu_activity import Monitor, process_identity
from bend_bench.suites import plan, stage

ROOT = Path(__file__).resolve().parent


def bend_resident(source, depth):
    source = source.replace('answer(position(i))', 'answer(position(U32.and(U32.add(i, offset), 15)))')
    source = source.replace('def batch(+d: Nat, +i: U32)', 'def batch(+d: Nat, +i: U32, +offset: U32)')
    source = source.replace('batch(p, U32.shl(i)) batch(p, U32.inc(U32.shl(i)))',
                            'batch(p, U32.shl(i), offset) batch(p, U32.inc(U32.shl(i)), offset)')
    source = source[:source.index('def main()')]
    return source + f'''def repeat(+n: Nat) -> IO(Unit):
  match n:
    case 0n: IO.pure(Unit, Unit{{}})
    case 1n+p:
      do IO<Unit>:
        Unit <- IO.print(output(batch!({depth}n, 0, U32.from_nat(p)), "END"))
        repeat(p)

def main() -> IO(Unit):
  do IO<Unit>:
    Unit <- IO.print("READY")
    repeat(12n)
'''


def cpp_resident(source, count):
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
  int out[count];
#ifdef __CUDACC__
  int *d, *scores;
  CUDA(cudaDeviceSetLimit(cudaLimitStackSize, 32768));
  CUDA(cudaMalloc(&d, sizeof(out)));
  CUDA(cudaMalloc(&scores, count * 32 * sizeof(int)));
#endif
  puts("READY"); fflush(stdout);
  for (int offset = 11; offset >= 0; --offset) {{
#ifdef __CUDACC__
    children<<<count, 32>>>(scores, offset);
    CUDA(cudaGetLastError());
    combine<<<(count + 127) / 128, 128>>>(scores, d);
    CUDA(cudaGetLastError());
    CUDA(cudaMemcpy(out, d, sizeof(out), cudaMemcpyDeviceToHost));
#else
#pragma omp parallel for schedule(dynamic, 1)
    for (int i = 0; i < count; ++i)
      out[i] = 1 + solve(positions[(i + offset) & 15][0], positions[(i + offset) & 15][1], empty, -2, 2);
#endif
    for (int value : out) printf("%d\\n", value);
    puts("END"); fflush(stdout);
  }}
#ifdef __CUDACC__
  CUDA(cudaFree(d)); CUDA(cudaFree(scores));
#endif
}}
'''


def resident(command, folder, config, expected, count, gpu):
    """Timestamp batch boundaries before parsing; retain complete output and activity."""
    started = time.monotonic()
    result = dict(command=list(map(str, command)), batches=[], correct=False)
    monitor = Monitor(config) if gpu else None
    proc = None
    try:
        with (folder / 'stderr.txt').open('w') as err, (folder / 'stdout.txt').open('wb') as raw:
            proc = subprocess.Popen(['stdbuf', '-oL', *map(str, command)], stdout=subprocess.PIPE,
                                    stderr=err, env={**environment(), 'OMP_NUM_THREADS': '16',
                                    'OMP_PROC_BIND': 'true', 'OMP_PLACES': 'threads'}, start_new_session=True)
            if monitor:
                monitor.activity.known_benchmarks = {proc.pid: process_identity(proc.pid)['start_ticks']}
                monitor.start(proc.pid)
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ)
            pending = b''
            values = []
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
                while b'\n' in pending:
                    line, pending = pending.split(b'\n', 1)
                    if line == b'READY':
                        previous = time.monotonic()
                        result['startup_seconds'] = previous - started
                    elif line == b'END':
                        now = time.monotonic()
                        if previous is None:
                            raise ValueError('Missing READY')
                        result['batches'].append(dict(seconds=now - previous, output=values))
                        previous, values = now, []
                    else:
                        values.append(line.decode())
            selector.close()
            if proc.poll() is None:
                proc.wait(timeout=max(0.1, deadline - time.monotonic()))
            result['returncode'] = proc.returncode
            result['correct'] = proc.returncode == 0 and len(result['batches']) == 12 and not pending and not values
            for rep, batch in enumerate(result['batches']):
                batch['correct'] = batch['output'] == [str(expected[(i + 11 - rep) & 15]) for i in range(count)]
                result['correct'] &= batch['correct']
    except Exception as error:
        result['error'] = repr(error)
    finally:
        if proc and proc.poll() is None:
            import signal
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        result['process_seconds'] = time.monotonic() - started
        if proc and proc.stdout:
            proc.stdout.close()
        if monitor:
            result['gpu_activity'] = monitor.finish()
            result['correct'] &= not result['gpu_activity']['errors']
        write_json(folder / 'result.json', result)
    if not result['correct']:
        raise RuntimeError(f'Resident correctness/activity gate failed: {folder}')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--depths', type=int, nargs='+', choices=(4, 8, 12, 16), default=[4, 8, 12, 16])
    args = parser.parse_args()
    config = load_config(ROOT / 'applications-mnk.toml')
    config.update(mnk_games=[[5, 5, 4, 8]], threads=[1, 16])
    config['blocked_services'].append('bend-bench-applications.service')
    out = ROOT / 'runs' / time.strftime('mnk-sustained-%Y%m%d-%H%M%S')
    out.mkdir()
    write_json(out / 'provenance.json', dict(harness=provenance(config), script_sha256=hash_file(__file__), depths=args.depths))
    from validate_applications import wait_idle
    wait_idle(config, out)
    report = ['# Resident-process endgame throughput', '',
              'Repeated fixed corpus of 16 positions, two warmup batches and ten measured batches per process. Latency includes answer formatting, pipe delivery and host observation; it is not kernel time. Startup-to-READY is separate; first-use lazy setup is covered by warmups.', '',
              '| Positions per batch | Implementation | Mean delivered batch ms | Positions/second | Startup to READY ms |',
              '|---|---|---:|---:|---:|']
    with exclusive(config):
        for depth in args.depths:
            count = 1 << depth
            work = out / str(count)
            work.mkdir()
            (work / 'build').mkdir()
            stage(config, work)
            name = 'mnk-5-5-4-8'
            source = work / 'ports' / (name + '.bend')
            source.write_text(bend_resident(source.read_text(), depth))
            cpp = work / 'gpu/mnk.cpp'
            cpp.write_text(cpp_resident(cpp.read_text(), count))
            builds, cases = plan(config, work)
            for command in builds:
                result = execute(command, timeout=180)
                append(work / 'build.jsonl', result)
                if result['returncode']:
                    raise RuntimeError(f'Build failed: {work}')
            write_json(work / 'hashes.json', {str(p.relative_to(work)): hash_file(p) for p in work.rglob('*') if p.is_file()})
            expected = json.loads(source.with_suffix('.json').read_text())
            for case in cases:
                if case['implementation'] != 'bend' and case['threads'] == 1 and not case['implementation'].endswith('cuda'):
                    continue
                folder = work / f"{case['implementation']}-{case['threads']}"
                folder.mkdir()
                result = resident(case['command'], folder, config, expected, count, case['implementation'].endswith('cuda'))
                latency = statistics.mean(b['seconds'] for b in result['batches'][2:])
                report.append(f"| {count} | {folder.name} | {latency * 1000:.3f} | {count / latency:.1f} | {result['startup_seconds'] * 1000:.3f} |")
                (out / 'report.md').write_text('\n'.join(report) + '\n')
                print(report[-1], flush=True)
    write_json(out / 'completed.json', dict(report=str(out / 'report.md')))
    print('COMPLETE', out, flush=True)


if __name__ == '__main__':
    main()
