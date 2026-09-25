"""Verify the scorecard snapshot against the local archived reports."""
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
data = json.loads((HERE / 'data.json').read_text())
cases = {}
for relative, digest in data['source_sha256'].items():
    path = ROOT / relative
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, relative
    if path.name == 'summary.json':
        cases[relative] = {case['case']: case for case in json.loads(path.read_text())['cases']}

for row in data['rows']:
    for column, (case_id, ms) in enumerate(zip(row.get('cases', []), row['ms'])):
        if case_id is None:
            assert ms is None
            continue
        source = row.get('case_sources', {}).get(case_id, row['source'])
        case = cases[source][case_id]
        if case['status'] == 'failed':
            assert ms is None and row.get('missing_labels', {}).get(str(column)), case_id
            assert case['samples'] == 0 and not case['checked'], case_id
            continue
        assert case['status'] == 'passed' and case['checked'] and case['samples'] >= 10
        assert ms == case['end_to_end_seconds'] * 1000, case_id

def table(relative):
    return [[s.strip() for s in line.split('|')[1:-1]]
            for line in (ROOT / relative).read_text().splitlines() if re.match(r'^\| \d', line)]

for row in data['rows']:
    if row['group'] == 'Repeated pricing requests':
        n = int(row['detail'].split()[0].replace(',', ''))
        assert n == 262144
        pricing_run = ROOT / 'runs/pricing-sustained-20260918-165158' / str(n)
        reference = json.loads((pricing_run / 'local-openmp-0/result.json').read_text())
        from pricing_sustained import compare_quotes
        for column, impl in enumerate(['bend', 'bend', 'bend-cuda', 'local-openmp', 'local-openmp', 'local-cuda']):
            run = ROOT / row['single_cpu_source'] if column in (0, 3) else pricing_run
            if column in (0, 3):
                assert json.loads((run / 'completed.json').read_text())['status'] == 'passed'
                schedule = json.loads((run / 'schedule.json').read_text())
                matching = [s['case'] for s in schedule if s['case']['implementation'] == impl]
                assert len(matching) == 3 and all(c['env']['OMP_NUM_THREADS'] == '1' and c['threads'] == 1 for c in matching)
            values = []
            for rep in range(3):
                result = json.loads((run / f'{impl}-{rep}' / 'result.json').read_text())
                assert result['correct'] and len(result['pricing_seconds']) == 32
                assert result['returncode'] == 0 and not result['timeout'] and not result.get('contention_error')
                compare_quotes(result['quotes'], reference['quotes'])
                if column in (0, 3):
                    assert result['command'][:3] == ['taskset', '-c', '0']
                    if impl == 'bend':
                        assert result['command'][-2:] == ['--threads', '1']
                values.append(statistics.mean(result['pricing_seconds'][2:]))
            assert abs(row['ms'][column] - statistics.median(values) * 1000) < 1e-9
    elif row['group'] == 'Repeated game-search batches':
        # CPU and Bend GPU cells from the matched 18 September run; the CUDA cell from the 25 September
        # rerun with the fixed-depth GPU search, where Bend GPU re-measured at 302.8 ms.
        matched, fixed = 'runs/mnk-sustained-20260918-160439/report.md', 'runs/mnk-sustained-20260925-173106/report.md'
        sources = [None, (matched, 'bend'), (matched, 'bend-cuda'), None,
                   (matched, 'local-alpha-beta-openmp-tight-bulk'), (fixed, 'local-alpha-beta-position-tight-bulk-cuda')]
        for column, source in enumerate(sources):
            if source is None:
                assert row['ms'][column] is None
                continue
            report, impl = source
            values = [float(r[8]) for r in table(report) if re.sub(r'-\d+-run\d+$', '', r[3]) == impl]
            assert len(values) == 3
            assert row['ms'][column] == statistics.median(values)

hotspot = [row for row in data['rows'] if row['name'] == 'Rodinia HotSpot']
assert len(hotspot) == 1 and hotspot[0]['cases'][0] == 'hotspot/hotspot-1024-100/bend/1'
queens = [row for row in data['rows'] if row['name'] == 'N-Queens']
assert len(queens) == 1 and queens[0]['group'] == 'Published workloads'
bfs = [row for row in data['rows'] if row['group'] == 'Shared-graph traversal']
assert len(bfs) == 1 and bfs[0]['cases'][0] == 'bfs/bfs-18/bend/1'
summation = [row for row in data['rows'] if row['name'] == 'Integer summation']
sizes = [int(row['detail'].split()[0].replace(',', '')) for row in summation]
assert sizes == [1 << 31]
if summation:
    for row, size in zip(summation, sizes):
        records = [json.loads(line) for line in (ROOT / row['source']).parent.joinpath(str(size), 'samples.jsonl').read_text().splitlines()]
        for case_id, ms in zip(row['cases'], row['ms']):
            samples = [r for r in records if r['case'] == case_id]
            assert len(samples) == 13 and all(r['correct'] and r['returncode'] == 0 and not r['timeout'] and not r.get('contention_error') for r in samples)
            measured = [r for r in samples if r['phase'] == 'measure']
            assert sorted(r['rep'] for r in measured) == list(range(10))
            assert ms == statistics.median(r['end_to_end_seconds'] for r in measured) * 1000
games = [row for row in data['rows'] if row['group'] == 'Repeated game-search batches']
assert len(games) == 1
sorting = [row for row in data['rows'] if row['name'] == 'Tree bitonic sort']
assert len(sorting) == 1 and sorting[0]['cases'][5] == 'cub/sort-23/cub-cuda/1'
assert sorting[0]['case_sources'][sorting[0]['cases'][5]] == 'runs/e930e5a1b9c488a9f8ba/summary.json'
assert not any(row['name'] == 'Integer sorting' for row in data['rows'])
uts = [row for row in data['rows'] if row['group'] == 'Irregular recursive search']
assert len(uts) == 1 and uts[0]['name'] == 'Unbalanced Tree Search' and uts[0]['cases'][0] == 'uts/tiny/bend/1'
assert uts[0]['cases'][2] == 'uts/tiny/bend-cuda/16' and uts[0]['missing_labels']['2'] == 'Stack limit'
assert uts[0]['cases'][5] == 'uts/tiny/conventional-cuda/1'
uts_source = 'benchmarks/uts-gpu-20260921/summary.json'
uts_samples = [json.loads(line) for line in (ROOT / uts_source).with_name('samples.jsonl').read_text().splitlines()]
for dataset in ('test', 'tiny'):
    failed_id = f'uts/{dataset}/bend-cuda/16'
    failed = [r for r in uts_samples if r['case'] == failed_id]
    assert len(failed) == 1 and failed[0]['phase'] == 'check' and failed[0]['returncode'] == 1
    assert not failed[0]['correct'] and not failed[0].get('contention_error')
    assert 'memory fault (machine stack overflow?)' in failed[0]['stderr']
    cuda_id = f'uts/{dataset}/conventional-cuda/1'
    successful = [r for r in uts_samples if r['case'] == cuda_id]
    assert len(successful) == 12 and all(r['correct'] for r in successful)
    measured = [r for r in successful if r['phase'] == 'measure']
    assert sorted(r['rep'] for r in measured) == list(range(10))
    assert statistics.median(r['end_to_end_seconds'] for r in measured) == cases[uts_source][cuda_id]['end_to_end_seconds']
assert len(data['rows']) == 21 + len(summation)
assert not any(row['group'] == 'One-off option pricing' for row in data['rows'])
published = [row for row in data['rows'] if row['group'] == 'Published workloads']
assert len(published) == 16 and all(row['ms'][5] is not None for row in published)
custom = [row for row in published if row.get('case_sources', {}).get(row['cases'][5]) == 'benchmarks/vendor-cuda-20260921/summary.json']
assert len(custom) == 11
print(f'Verified {len(data["rows"])} rows, source hashes, correctness gates and repeated-request medians.')
