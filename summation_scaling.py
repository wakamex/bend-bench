"""Matched CPU/GPU summation below and above one billion generated integers."""
import argparse
import json
from pathlib import Path
import sys
import time

import reduction_crossover as reduction
from bend_bench.core import execute, hash_file, load_config, write_json, exclusive
from validate_applications import wait_idle

ROOT = Path(__file__).resolve().parent
COUNTS = [1 << depth for depth in (28, 29, 30, 31)]
IMPLEMENTATIONS = ['bend-1', 'bend-16', 'bend-cuda', 'serial-cpp', 'openmp-16', 'cub-cuda']


def pins(config):
    files = ['summation_scaling.py', 'benchmarks/summary/verify.py',
             'benchmarks/summary/build.py', 'benchmarks/summary/template.html']
    return dict(reduction=reduction.pins(config), files={name: hash_file(ROOT / name) for name in files})


def report(out, points):
    lines = ['# CPU and GPU summation scaling', '',
             'Complete-program times include startup, generating the integers, wrapping-U32 summation and scalar output. All implementations generate inputs during reduction, without an input array. Each cell is the median of ten checked executions after two warmups. Implementation order is shuffled within each repetition.', '',
             '| Generated integers | Bend CPU1 seconds | Bend CPU16 seconds | Bend GPU seconds | Serial C++ seconds | OpenMP16 seconds | CUB seconds |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for point in points:
        values = ' | '.join(f'{point["medians"][key]:.6f}' for key in IMPLEMENTATIONS)
        lines.append(f'| {point["count"]:,} | {values} |')
    lines += ['', 'All sizes use the same balanced Bend reduction and the same deterministic input sequence. The new CPU controls fuse input generation and summation; the older serial control allocated and populated an input array. These are new matched measurements, not CPU values added to earlier GPU runs. Each size is checked against a separate scalar reference. CUB receives an explicit unsigned 64-bit item count, selecting 64-bit offsets in the pinned library, including at 2^31.', '',
              'Bend revision and patches, host configuration, compiler flags, prepared sources, binaries, linked-library hashes and individual measurements are preserved beside this report. The existing shared benchmark lock and GPU activity policy apply. The finite sweep has a two-hour measurement budget and a 180-second timeout per execution. Failed attempts remain archived.', '']
    (out / 'report.md').write_text('\n'.join(lines))


def publish(out, points):
    """Replace summation rows only after the full matched sweep passes."""
    cases, rows = [], []
    relative = str(out.relative_to(ROOT) / 'summary.json')
    for point in points:
        ids = [f'reduce-{point["count"]}/{key}' for key in IMPLEMENTATIONS]
        for case_id, key in zip(ids, IMPLEMENTATIONS):
            cases.append(dict(case=case_id, status='passed', checked=True, samples=10,
                              end_to_end_seconds=point['medians'][key]))
        rows.append(dict(group='GPU primitives', name='Integer summation',
                         detail=f'{point["count"]:,} generated U32 values',
                         baseline='Fused serial C++ / OpenMP / CUB reduction',
                         ms=[point['medians'][key]*1000 for key in IMPLEMENTATIONS],
                         cases=ids, link='../../SUMMATION_SCALING.md',
                         metric='complete program', source=relative))
    write_json(out / 'summary.json', dict(cases=cases))
    path = ROOT / 'benchmarks/summary/data.json'
    data = json.loads(path.read_text())
    first = next(i for i, row in enumerate(data['rows']) if row['name'] == 'Integer summation')
    data['rows'] = [row for row in data['rows'] if row['name'] != 'Integer summation']
    data['rows'][first:first] = rows[-1:]
    data['source_sha256'][relative] = hash_file(out / 'summary.json')
    data['measurement_dates'] = '17–20 September 2026'
    write_json(path, data)
    readme = ROOT / 'benchmarks/summary/README.md'
    readme.write_text(readme.read_text().replace('The 30 rows cover', f'The {len(data["rows"])} rows cover'))
    for command in ([sys.executable, ROOT / 'benchmarks/summary/verify.py'],
                    [sys.executable, ROOT / 'benchmarks/summary/build.py']):
        result = execute(command)
        if result['returncode']:
            raise RuntimeError(result['stdout'] + result['stderr'])
    notes = ROOT / 'SUMMATION_SCALING.md'
    notes.write_text(notes.read_text().replace('Results are pending in', 'Completed results are in'))


def run(request):
    out = request.parent
    saved = json.loads(request.read_text())
    config = saved['config']
    if (out / 'started.json').exists():
        raise RuntimeError('Request already started; enqueue a fresh directory')
    if pins(config) != saved['pins']:
        raise RuntimeError('Queued inputs changed')
    wait_idle(config, out)
    points = []
    with exclusive(config):
        if pins(config) != saved['pins']:
            raise RuntimeError('Queued inputs changed during wait')
        write_json(out / 'started.json', dict(status='running'))
        deadline = time.monotonic() + 7200
        for count in saved['counts']:
            if time.monotonic() > deadline:
                raise TimeoutError('Two-hour measurement budget exhausted')
            print('STAGE', count, 'integers; six matched configurations', flush=True)
            points.append(reduction.measure(config, out, count, cpu=True))
            report(out, points)
        if pins(config) != saved['pins']:
            raise RuntimeError('Inputs changed during measurements')
    write_json(out / 'measurements-complete.json', dict(points=len(points)))
    publish(out, points)
    write_json(out / 'completed.json', dict(report=str(out / 'report.md'), points=len(points)))
    print('COMPLETE', out / 'report.md', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--enqueue', action='store_true')
    args = parser.parse_args()
    request = args.request.resolve()
    if args.enqueue:
        config = load_config(ROOT / 'gpu-primitives.toml')
        config['label'] = 'matched-summation-scaling'
        config['gpu_resident'] = {'cgroup': '/user.slice/user-1000.slice/user@1000.service/app.slice/transcribe-worker.service'}
        config['blocked_services'] += ['bend-bench-applications.service', 'bend-bench-gpu.service',
                                       'bend-bench-pricing-crossover.service', 'bend-bench-reduction-crossover.service']
        request.parent.mkdir(parents=True, exist_ok=False)
        write_json(request, dict(config=config, pins=pins(config), counts=COUNTS))
    else:
        try:
            run(request)
        except Exception as error:
            write_json(request.parent / 'failed.json', dict(error=repr(error)))
            raise


if __name__ == '__main__':
    main()
