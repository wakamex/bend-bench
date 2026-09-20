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

pricing = table('runs/pricing-sustained-20260918-165158/report.md')
for row in data['rows']:
    if row['group'] == 'Repeated pricing requests':
        n = int(row['detail'].split()[0].replace(',', ''))
        for column, impl in [(1, 'bend'), (2, 'bend-cuda'), (4, 'local-openmp'), (5, 'local-cuda')]:
            values = [float(r[3]) for r in pricing if int(r[0]) == n and r[1] == impl]
            assert len(values) == 3
            assert row['ms'][column] == statistics.median(values)
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

assert len(data['rows']) == 40
assert not any(row['group'] == 'One-off option pricing' for row in data['rows'])
print('Verified 40 rows, source hashes, correctness gates and repeated-request medians.')
