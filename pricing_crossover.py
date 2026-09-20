"""Double sustained pricing sizes under a per-request time limit."""
import argparse
import json
import os
from pathlib import Path
import random
import selectors
import statistics
import subprocess
import sys
import time

from bend_bench.core import append, environment, exclusive, execute, hash_file, load_config, provenance, write_json
from pricing_sustained import prepare, parse, compare_quotes, pricing_reference, audit_quotes, run_case
from validate_applications import wait_idle

ROOT = Path(__file__).resolve().parent
SCRIPTS = ['pricing_crossover.py', 'pricing_sustained.py', 'pricing_service.cpp', 'pricing_service.bend', 'validate_applications.py']


def watchdog(command, limit):
    """Stop a worker if it takes too long to deliver the next quote."""
    proc = subprocess.Popen(command, stdout=subprocess.PIPE)
    # Preserve the native GPU child's identity before it exits. The monitor's
    # existing identity file otherwise contains only this watchdog's PID.
    if path := os.environ.get('BEND_BENCH_PID_FILE'):
        with Path(path).open('a') as stream:
            stream.write(Path(f'/proc/{proc.pid}/stat').read_text().strip() + '\n')
    deadline = time.monotonic() + 180  # Initialization is outside quote timing.
    pending = b''
    with selectors.DefaultSelector() as selector:
        selector.register(proc.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(max(0, remaining)):
                proc.kill()
                proc.wait()
                print('PRICING_REQUEST_LIMIT_EXCEEDED', file=sys.stderr, flush=True)
                return 124
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                return proc.wait()
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
            pending += chunk
            while b'\n' in pending:
                line, pending = pending.split(b'\n', 1)
                if line == b'READY' or line.startswith(b'RESULT '):
                    deadline = time.monotonic() + limit


def pins(config):
    return dict(harness=provenance(config), scripts={name: hash_file(ROOT / name) for name in SCRIPTS})


class TimeLimit(Exception):
    pass


def run_gpu(config, case, folder, n, batches, limit, expected=None):
    folder.mkdir()
    command = [sys.executable, str(Path(__file__).resolve()), '--watchdog', str(limit), *case['command']]
    result = execute(command, env={**environment(), **case['env']}, measured=True,
                     timeout=180 + batches * limit + 30, gpu_policy=config)
    result['correct'] = False
    try:
        if result.get('contention_error') or result.get('gpu_activity', {}).get('errors'):
            raise RuntimeError('Unapproved GPU activity')
        if result['returncode'] == 124 and 'PRICING_REQUEST_LIMIT_EXCEEDED' in result['stderr']:
            raise TimeLimit('No next quote within the per-request limit')
        quotes, payoffs, times = parse(result, n, batches)
        if any(payoffs):
            raise ValueError('Performance run emitted full payoffs')
        if expected is not None:
            compare_quotes(quotes, expected)
        if max(times) > limit:
            raise TimeLimit('Measured quote exceeded the per-request limit')
        result.update(correct=True, quotes=quotes, pricing_seconds=times)
    except Exception as error:
        result['error'] = repr(error)
        write_json(folder / 'result.json', result)
        raise
    write_json(folder / 'result.json', result)
    return result


def write_report(out, points, reason):
    lines = ['# Sustained pricing size sweep', '',
             'Request-to-host price and standard error, with 256 observations per path. Each cell is the median of three process means, with two warmups and ten measured requests per process. Startup and output formatting are excluded. Implementations run in shuffled order. All completed rows passed quote checks; a separate independent small-input audit checks every payoff.', '',
             '| Paths | Bend GPU ms | Project CUDA ms | Bend / CUDA time |', '|---|---:|---:|---:|']
    for p in points:
        lines.append(f'| {p["paths"]:,} | {p["bend"]*1000:.3f} | {p["cuda"]*1000:.3f} | {p["ratio"]:.3f}× |')
    lines += ['', 'Status: ' + reason, '',
              'The per-request watchdog permits 180 seconds for startup, then at most 60 seconds between delivered quotes. Seed offsets retain wrapping-U32 arithmetic, so sufficiently large requests can reuse seeds across batches. The path-count cap is 2^30, below the existing signed-int API limit. These are project-written CUDA controls, not an established finance library. Earlier runs and failed attempts remain unchanged.', '']
    (out / 'report.md').write_text('\n'.join(lines))


def run(request):
    saved = json.loads(request.read_text())
    config, out = saved['config'], request.parent
    if (out / 'started.json').exists():
        raise RuntimeError('Request already started; preserve evidence and enqueue a fresh request')
    if pins(config) != saved['pins']:
        raise RuntimeError('Queued inputs changed')
    wait_idle(config, out)
    points = []
    with exclusive(config):
        if pins(config) != saved['pins']:
            raise RuntimeError('Queued inputs changed during idle wait')
        write_json(out / 'started.json', {'status': 'running'})
        deadline = time.monotonic() + 4 * 3600
        print('STAGE independent per-path audit', flush=True)
        vectors = [pricing_reference(1024, 256, rep * 1024) for rep in range(3)]
        write_json(out / 'oracle.json', vectors)
        audit = out / 'audit'
        for case in prepare(config, audit, 10, 256, 3, True):
            run_case(config, case, audit / case['implementation'], 1024, 3, audit_quotes(vectors), vectors)
        reason = 'Reached the 2^30 path-count cap.'
        for depth in range(16, 31):
            if time.monotonic() > deadline:
                reason = 'Stopped at the four-hour experiment budget.'
                break
            n = 1 << depth
            print('STAGE', n, 'paths x 256 observations', flush=True)
            work = out / str(n)
            cases = [c for c in prepare(config, work, depth, 256, 12)
                     if c['implementation'] in ('bend-cuda', 'local-cuda')]
            reference = None
            medians = {}
            timings = {c['implementation']: [] for c in cases}
            # Reference qualification is not included in performance medians.
            cuda = next(c for c in cases if c['implementation'] == 'local-cuda')
            try:
                reference = run_gpu(config, cuda, work / 'reference', n, 12, 60)['quotes']
                schedule = [(c, rep) for rep in range(3) for c in cases]
                random.Random(n).shuffle(schedule)
                write_json(work / 'schedule.json', [dict(case=c['id'], rep=r) for c, r in schedule])
                for case, rep in schedule:
                    result = run_gpu(config, case, work / f'{case["implementation"]}-{rep}', n, 12, 60, reference)
                    latency = statistics.mean(result['pricing_seconds'][2:])
                    timings[case['implementation']].append(latency)
                    print('SAMPLE', n, case['implementation'], rep, latency, flush=True)
            except TimeLimit as error:
                reason = f'Stopped at {n:,} paths: {error}. Partial samples are retained and excluded from the summary.'
                break
            medians = {key: statistics.median(values) for key, values in timings.items()}
            point = dict(paths=n, observations=256, bend=medians['bend-cuda'], cuda=medians['local-cuda'],
                         ratio=medians['bend-cuda'] / medians['local-cuda'])
            points.append(point)
            append(out / 'summary.jsonl', point)
            write_report(out, points, 'Running; larger sizes remain pending.')
            print('RESULT', json.dumps(point), flush=True)
            if point['ratio'] < 1:
                reason = f'Bend overtook the CUDA control at {n:,} paths; crossover requires confirmation.'
                break
        if pins(config) != saved['pins']:
            raise RuntimeError('Inputs changed during measurements')
    write_report(out, points, reason)
    write_json(out / 'completed.json', dict(reason=reason, points=len(points), report=str(out / 'report.md')))
    print('COMPLETE', out / 'report.md', reason, flush=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--watchdog':
        sys.exit(watchdog(sys.argv[3:], float(sys.argv[2])))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--enqueue', action='store_true')
    args = parser.parse_args()
    args.request = args.request.resolve()
    if args.enqueue:
        config = load_config(ROOT / 'applications.toml')
        config.update(suites=['pricing'], threads=[16], label='sustained-pricing-crossover')
        for key in ('gap', 'gunrock', 'moderngpu'):
            config.pop(key, None)
        config['blocked_services'] += ['bend-bench-applications.service', 'bend-bench-reduction-crossover.service']
        args.request.parent.mkdir(parents=True, exist_ok=False)
        write_json(args.request, dict(config=config, pins=pins(config), observations=256,
                                     start_depth=16, maximum_depth=30, request_limit_seconds=60,
                                     warmups=2, measured_requests=10, processes=3))
    else:
        try:
            run(args.request)
        except Exception as error:
            write_json(args.request.parent / 'failed.json', dict(error=repr(error)))
            raise


if __name__ == '__main__':
    main()
