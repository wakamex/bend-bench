"""Time empty Bend (CPU build) and OpenMP programs, the fixed cost under every CPU scorecard cell.

uv run --locked python benchmarks/cpu-startup/measure.py
"""
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BEND = ROOT.parent / 'bend2/upstream'  # the scorecard's Bend 2.0.3
FLAGS = ['-O3', '-march=native', '-ffp-contract=off']


def median_ms(command, env=None, runs=15):
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        subprocess.run(['taskset', '-c', '0-15', *command], env=env, capture_output=True, check=True)
        times.append(time.perf_counter() - start)
    return round(statistics.median(times) * 1e3, 2)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        subprocess.run([str(ROOT.parent / 'bend2/tools/bun-linux-x64/bun'), str(BEND / 'bend2/main.ts'), str(HERE / 'empty.bend'),
                        '-o', str(tmp / 'empty.c')], check=True)
        subprocess.run(['/usr/bin/clang', '-std=c11', *FLAGS, str(tmp / 'empty.c'), '-lpthread', '-lm', '-o', str(tmp / 'bend')], check=True)
        subprocess.run(['/usr/bin/clang', *FLAGS, '-fopenmp', str(HERE / 'empty-omp.c'), '-o', str(tmp / 'omp')], check=True)
        results = {}
        for threads in (1, 16):
            results[f'bend_{threads}_ms'] = median_ms([str(tmp / 'bend'), '--threads', str(threads), '--gpu', 'off'])
            results[f'openmp_{threads}_ms'] = median_ms([str(tmp / 'omp')], env={**os.environ, 'OMP_NUM_THREADS': str(threads)})
    results.update(runs=15, cpus='0-15', utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    (HERE / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(results)


if __name__ == '__main__':
    main()
