"""Verify the scorecard snapshot against the local archived reports."""
import hashlib
import json
from pathlib import Path
import re
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
data = json.loads((HERE / 'data.json').read_text())
cases = {}
for relative, digest in data['source_sha256'].items():
    path = ROOT / relative
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, relative
    if path.name == 'summary.json':
        cases[relative] = {case['case']: case for case in json.loads(path.read_text())['cases']}

for row in data['rows']:
    for case_id, ms in zip(row.get('cases', []), row['ms']):
        if case_id is None:
            assert ms is None
            continue
        case = cases[row['source']][case_id]
        assert case['status'] == 'passed' and case['checked'] and case['samples'] >= 10
        assert ms == case['end_to_end_seconds'] * 1000, case_id

def table(relative):
    return [[s.strip() for s in line.split('|')[1:-1]]
            for line in (ROOT / relative).read_text().splitlines() if re.match(r'^\| \d', line)]

pricing_run = ROOT / 'runs/pricing-crossover-20260920'
pricing = max((json.loads(line) for line in (pricing_run / 'summary.jsonl').read_text().splitlines()), key=lambda p: p['paths'])
for row in data['rows']:
    if row['group'] == 'Repeated pricing requests':
        n = int(row['detail'].split()[0].replace(',', ''))
        assert n == pricing['paths']
        assert all(row['ms'][column] is None for column in (0, 1, 3, 4))
        for column, impl, key in [(2, 'bend-cuda', 'bend'), (5, 'local-cuda', 'cuda')]:
            values = []
            for rep in range(3):
                result = json.loads((pricing_run / str(n) / f'{impl}-{rep}' / 'result.json').read_text())
                assert result['correct'] and len(result['pricing_seconds']) == 12
                values.append(statistics.mean(result['pricing_seconds'][2:]))
            assert pricing[key] == statistics.median(values)
            assert abs(row['ms'][column] - pricing[key] * 1000) < 1e-9
    elif row['group'] == 'Repeated game-search batches':
        final = 'final cuda' in row['detail']
        run = '161850' if final else '160439'
        records = table(f'runs/mnk-sustained-20260918-{run}/report.md')
        implementations = [None, None if final else 'bend', 'bend-cuda', None,
                           'local-alpha-beta-openmp-tight-bulk',
                           'local-alpha-beta-tight-bulk-literal-cuda' if final else 'local-alpha-beta-tight-bulk-cuda']
        for column, impl in enumerate(implementations):
            if impl is None:
                assert row['ms'][column] is None
                continue
            values = [float(r[8]) for r in records if re.sub(r'-\d+-run\d+$', '', r[3]) == impl]
            assert len(values) == 3
            assert row['ms'][column] == statistics.median(values)

hotspot = [row for row in data['rows'] if row['name'] == 'Rodinia HotSpot']
assert len(hotspot) == 1 and hotspot[0]['cases'][0] == 'hotspot/hotspot-1024-100/bend/1'
queens = [row for row in data['rows'] if row['group'] == 'Bit-mask search' and row['name'] == 'N-Queens']
assert len(queens) == 1 and queens[0]['cases'][0] == 'nqueens/nqueens-14/bend/1'
bfs = [row for row in data['rows'] if row['group'] == 'Shared-graph traversal']
assert len(bfs) == 1 and bfs[0]['cases'][0] == 'bfs/bfs-18/bend/1'
assert len(data['rows']) == 30
assert not any(row['group'] == 'One-off option pricing' for row in data['rows'])
print('Verified 30 rows, source hashes, correctness gates and repeated-request medians.')
