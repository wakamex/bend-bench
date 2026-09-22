"""Shared portable CPU/GPU snapshots and readable regression comparisons."""
import json
import math
from pathlib import Path
import statistics

from .core import fingerprint, rows, write_json
from .experiment import summarize

RESULT_SCHEMA = 'bend-bench-gpu-result-v1'
COMPARISON_SCHEMA = 'bend-bench-gpu-comparison-v1'
CPU_RESULT_SCHEMA = 'bend-bench-cpu-result-v1'
CPU_COMPARISON_SCHEMA = 'bend-bench-cpu-comparison-v1'


def target(result):
    return 'CPU' if result['schema'] == CPU_RESULT_SCHEMA else 'GPU'


def snapshot(summary):
    p = summary['provenance']
    config = p['config']
    cpu = config['suites'] == ['cpu-regression']
    policy = {k: config.get(k) for k in ('threads', 'cpus', 'repetitions', 'warmups',
              'gpu_heap', 'gpu_arch', 'require_idle_gpu', 'gpu_resident')}
    host, tools, toolkit = p['host'], p['tools'], p['toolkit']
    if cpu:
        host = {k: v for k, v in host.items() if k != 'gpu'}
        tools = {k: v for k, v in tools.items() if k in ('cc', 'bun')}
        toolkit = None
        policy = {k: config.get(k) for k in ('threads', 'cpus', 'repetitions', 'warmups')}
    return dict(schema=CPU_RESULT_SCHEMA if cpu else RESULT_SCHEMA, fingerprint=summary['fingerprint'],
                revision=p['sources']['bend']['commit'],
                patch_sha256=fingerprint(p['sources']['bend'].get('patch', '')),
                compatibility={k: fingerprint(v) for k, v in dict(host=host, policy=policy,
                               tools=tools, toolkit=toolkit, environment=p['environment']).items()},
                preparation=summary['preparation_status'], required_samples=config['repetitions'],
                gpu_mode=None if cpu else ('exclusive' if config.get('require_idle_gpu') else 'shared'),
                cases=[dict(case=r['case'], contract_sha256=fingerprint(r['contract']),
                            status=r['status'], checked=r['checked'], samples=r['samples'],
                            seconds=r['end_to_end_seconds'], reason=r.get('reason'))
                       for r in summary['cases'] if r['implementation'] == ('bend' if cpu else 'bend-cuda')])


def validate_result(value):
    if value.get('schema') not in (RESULT_SCHEMA, CPU_RESULT_SCHEMA) or not value.get('cases'):
        raise ValueError('Expected a CPU or GPU result with at least one Bend case')
    if set(value.get('compatibility', {})) != {'host', 'policy', 'tools', 'toolkit', 'environment'}:
        raise ValueError('Incomplete comparison compatibility metadata')
    if not isinstance(value.get('revision'), str) or 'fingerprint' not in value or 'patch_sha256' not in value:
        raise ValueError('Missing result identity')
    seen = set()
    required = value.get('required_samples', 10)
    if type(required) is not int or required < 1:
        raise ValueError('Invalid required sample count')
    for row in value['cases']:
        if row['case'] in seen or not row.get('contract_sha256'):
            raise ValueError('Duplicate case or missing workload contract')
        seen.add(row['case'])
        if row['status'] not in {'passed', 'failed', 'pending', 'unsupported'}:
            raise ValueError('Unknown result status')
        if type(row['samples']) is not int or row['samples'] < 0 or type(row['checked']) is not bool:
            raise ValueError('Invalid sample count or correctness gate')
        seconds = row['seconds']
        if row['status'] == 'passed':
            if (value['preparation'] != 'passed' or not row['checked'] or row['samples'] < required
                    or type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0):
                raise ValueError('Passed timing lacks successful gates or a finite positive time')
        elif seconds is not None:
            raise ValueError('Failed or incomplete case must not contain an accepted timing')
    return value


def load_result(path):
    path = Path(path)
    if path.is_dir():
        result = snapshot(summarize(path))
        failed = {r['case']: r for r in rows(path / 'samples.jsonl') if not r['correct']}
        for case in result['cases']:
            if sample := failed.get(case['case']):
                case['reason'] = sample.get('contention_error') or ('process timeout' if sample['timeout'] else
                                 'process exit ' + str(sample['returncode']) if sample['returncode'] else 'output check failed')
        return validate_result(result)
    value = json.loads(path.read_text())
    if value.get('schema') in (COMPARISON_SCHEMA, CPU_COMPARISON_SCHEMA):
        value = value['candidate']
    elif 'provenance' in value and 'cases' in value:
        value = snapshot(value)
    return validate_result(value)


def comparison(before, after, threshold=10):
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError('Regression threshold must be a finite positive percentage')
    validate_result(before)
    validate_result(after)
    if target(before) != target(after):
        raise ValueError('CPU and GPU profiles require separate baselines')
    if before['fingerprint'] == after['fingerprint']:
        raise ValueError('Cannot compare a run with itself; collect fresh measurements')
    left = {r['case']: r for r in before['cases']}
    right = {r['case']: r for r in after['cases']}
    changed = [k for k, v in before['compatibility'].items() if after['compatibility'][k] != v]
    warnings = []
    if 'environment' in changed:
        warnings.append('Execution environment changed. Ratios describe the recorded runs, not an isolated compiler effect.')
        changed.remove('environment')
    results = []
    for key in sorted(left.keys() | right.keys()):
        a, b = left.get(key), right.get(key)
        issues = []
        if a is None:
            issues.append('missing baseline')
        elif a['status'] != 'passed':
            issues.append('baseline ' + a['status'])
        if b is None:
            issues.append('missing candidate')
        elif b['status'] != 'passed':
            issues.append('candidate ' + b['status'] + (': '+b['reason'] if b.get('reason') else ''))
        if changed:
            issues.append('changed ' + ', '.join(changed))
        if a and b and a['contract_sha256'] != b['contract_sha256']:
            issues.append('changed workload contract')
        ratio = None if issues else a['seconds']/b['seconds']
        change = None if issues else 100*(b['seconds']/a['seconds']-1)
        results.append(dict(case=key, before_seconds=a['seconds'] if a else None,
                            after_seconds=b['seconds'] if b else None, speed_ratio=ratio,
                            time_change_percent=change, issues=issues,
                            regression=change is not None and change > threshold))
    overall = aggregate(results)
    groups = {str(n): aggregate([r for r in results if r['case'].endswith('/'+str(n))]) for n in (1, 16)} if target(after) == 'CPU' else {}
    return dict(schema=CPU_COMPARISON_SCHEMA if target(after) == 'CPU' else COMPARISON_SCHEMA,
                baseline=before, candidate=after, threshold_percent=threshold,
                overall=overall, thread_groups=groups, scaling=scaling(before, after, results),
                cases=results, warnings=warnings, concerns=bool(warnings or overall['regressions'] or overall['uncomparable']))


def aggregate(results):
    ratios = [r['speed_ratio'] for r in results if r['speed_ratio'] is not None]
    return dict(matched=len(ratios), total=len(results),
                   geometric_mean=statistics.geometric_mean(ratios) if ratios else None,
                   minimum=min(ratios) if ratios else None, maximum=max(ratios) if ratios else None,
                   faster=sum(r > 1 for r in ratios), slower=sum(r < 1 for r in ratios),
                   regressions=sum(r['regression'] for r in results),
                   uncomparable=sum(bool(r['issues']) for r in results))


def scaling(before, after, comparisons=None):
    if target(after) != 'CPU':
        return []
    def pairs(result):
        rows = {r['case']: r for r in result['cases']} if result else {}
        values = {}
        for key, one in rows.items():
            if not key.endswith('/1'):
                continue
            prefix = key.rsplit('/', 1)[0]
            many = rows.get(prefix+'/16')
            valid = many and one['status'] == many['status'] == 'passed' and one['contract_sha256'] == many['contract_sha256']
            values[prefix] = one['seconds']/many['seconds'] if valid else None
        return values
    a, b = pairs(before), pairs(after)
    issues = {r['case'] for r in comparisons or [] if r['issues']}
    return [dict(case=k+'/16', before=a.get(k), after=b.get(k),
                 change_percent=100*(b[k]/a[k]-1) if a.get(k) is not None and b.get(k) is not None
                 and not {k+'/1', k+'/16'} & issues else None)
            for k in sorted(a.keys() | b.keys())]


def label(case):
    name = case.split('/')[1]
    text = {'bfs': 'Batched maze BFS', 'editdist': 'Edit distance', 'gameoflife': 'Game of Life',
            'hashmap': 'Independent hash tables', 'kmeans': 'K-means', 'lexer': 'Lexer',
            'mandelbrot': 'Mandelbrot', 'merkle': 'Merkle tree and proof', 'nbody': 'Three-body ensemble',
            'queens': 'N-Queens', 'raytrace': 'Ray tracing', 'symreg': 'Symbolic regression',
            'terrain': 'Terrain', 'tree-bitonic': 'Tree bitonic sort', 'tree-matmul': 'Tree matrix multiplication',
            'tree-radix': 'Tree radix sort + deduplication', 'uts-compact': 'Unbalanced Tree Search (compact)',
            'summation': 'Integer summation', 'hotspot': 'Rodinia HotSpot', 'bfs-shared': 'Shared-graph BFS',
            'uts-test': 'Unbalanced Tree Search (4.1M nodes)',
            'pricing': 'Option pricing (32 requests)', 'game-search': 'Game search (one full batch)'}.get(name, name)
    if case.startswith('cpu-regression/'):
        text = text.replace('32 requests', 'one request') + ' · CPU' + case.rsplit('/', 1)[1]
    return text


def duration(value):
    return '-' if value is None else f'{value*1000:,.2f} ms'


def aligned_tables(lines):
    """Keep Markdown tables aligned when printed directly in a terminal."""
    output, index = [], 0
    while index < len(lines):
        if not lines[index].startswith('|'):
            output.append(lines[index]); index += 1
            continue
        table = []
        while index < len(lines) and lines[index].startswith('|'):
            table.append([c.strip() for c in lines[index].split('|')[1:-1]])
            index += 1
        widths = [max(len(row[col]) for row in table) for col in range(len(table[0]))]
        for row_index, row in enumerate(table):
            cells = [('-' * width if row_index == 1 else cell.ljust(width)) for cell, width in zip(row, widths)]
            output.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(output)


def render(result, compared=None):
    passed = sum(r['status'] == 'passed' for r in result['cases'])
    unit = 'configurations' if target(result) == 'CPU' else 'workloads'
    lines = [f'# Bend {target(result)} regression results', '',
             f"Bend `{result['revision'][:12]}` · {passed}/{len(result['cases'])} {unit} complete.", '']
    if result.get('required_samples', 10) < 10:
        lines += [f"Quick screen: {result['required_samples']} measured execution(s) per configuration, after a separate correctness check and warmup. Confirm suspected regressions with --repetitions 10.", '']
    if target(result) == 'GPU':
        lines += [f"GPU mode: {result.get('gpu_mode', 'not recorded')}." + (' Other GPU work may affect these timings.' if result.get('gpu_mode') == 'shared' else ''), '']
    if compared is None:
        failures = [r for r in result['cases'] if r['status'] in {'failed', 'unsupported'}]
        if failures:
            lines += ['## Areas of concern', '']
            lines += [f"- {label(r['case'])}: {r.get('reason') or r['status']}." for r in failures]
            lines.append('')
        lines += ['No baseline supplied. Pass a previous run directory, summary.json, regression.json or comparison.json with --baseline.', '',
                  '| Workload | Time | Measured runs | Gate |', '|---|---:|---:|---|']
        lines += [f"| {label(r['case'])} | {duration(r['seconds'])} | {r['samples']} | {r['status']}" + (': '+r['reason'] if r.get('reason') else '') + ' |' for r in result['cases']]
    else:
        o = compared['overall']
        lines += [f"Baseline: `{compared['baseline']['revision'][:12]}`. Matched {o['matched']}/{o['total']} {unit}.", '']
        if o['geometric_mean'] is not None and target(result) == 'GPU':
            prefix = 'Matched subset' if o['uncomparable'] else 'Overall'
            delta = 100*(1/o['geometric_mean']-1)
            verdict = 'unchanged' if abs(delta) < .05 else f"{abs(delta):.1f}% {'more' if delta > 0 else 'less'} time"
            lines += [f"{prefix}: {verdict}. Speed ratio {o['geometric_mean']:.3f}× (geometric mean; higher is faster). Range {o['minimum']:.3f}–{o['maximum']:.3f}×. {o['faster']} faster, {o['slower']} slower.", '']
        for threads, group in compared.get('thread_groups', {}).items():
            if group['geometric_mean'] is not None:
                lines += [f"CPU{threads}: {group['geometric_mean']:.3f}× speed ratio; range {group['minimum']:.3f}–{group['maximum']:.3f}×; {group['matched']}/{group['total']} comparable cases.", '']
        lines += ['## Areas of concern', '']
        for warning in compared.get('warnings', []):
            lines.append(f'- {warning}')
        concerns = [r for r in compared['cases'] if r['issues'] or r['regression']]
        if not concerns and not compared.get('warnings'):
            lines += [f"No incomplete comparisons or slowdowns above {compared['threshold_percent']:g}%.", '']
        for row in sorted(concerns, key=lambda r: (not bool(r['issues']), -(r['time_change_percent'] or 0))):
            text = '; '.join(row['issues']) if row['issues'] else f"{row['time_change_percent']:.1f}% longer ({duration(row['before_seconds'])} → {duration(row['after_seconds'])})"
            lines.append(f"- {label(row['case'])}: {text}.")
        lines += ['', '| Workload | Baseline | Candidate | Time change | Gate |', '|---|---:|---:|---:|---|']
        for r in compared['cases']:
            change = '-' if r['time_change_percent'] is None else f"{r['time_change_percent']:+.1f}%"
            gate = '; '.join(r['issues']) or ('REGRESSION' if r['regression'] else 'comparable')
            lines.append(f"| {label(r['case'])} | {duration(r['before_seconds'])} | {duration(r['after_seconds'])} | {change} | {gate} |")
        lines += ['', f"The {compared['threshold_percent']:g}% slowdown threshold is a screening rule, not a statistical significance test. The geometric mean gives each matched workload equal weight. Failed or incompatible cases are excluded from ratios and remain listed above."]
    if target(result) == 'CPU':
        lines += ['', '## Thread scaling', '', 'CPU1 time divided by CPU16 time. A smaller speedup can also result from improved single-thread code; it is not independently a slowdown flag.', '',
                  '| Workload | Baseline speedup | Candidate speedup | Scaling change |', '|---|---:|---:|---:|']
        values = compared['scaling'] if compared else scaling(None, result)
        for row in values:
            a = '-' if row['before'] is None else f"{row['before']:.2f}×"
            b = '-' if row['after'] is None else f"{row['after']:.2f}×"
            change = '-' if row['change_percent'] is None else f"{row['change_percent']:+.1f}%"
            lines.append(f"| {label(row['case']).rsplit(' · CPU', 1)[0]} | {a} | {b} | {change} |")
    lines += ['', 'Times are complete-process medians from correctness-gated runs. These are separate from scorecard request-latency measurements.',
              f"Candidate result identity: `{result['fingerprint']}`. Compiler patch identity: `{result['patch_sha256']}`.", '']
    return aligned_tables(lines)


def publish(run, baseline=None, threshold=10):
    run = Path(run)
    result = load_result(run)
    before = validate_result(baseline) if isinstance(baseline, dict) else load_result(baseline) if baseline is not None else None
    compared = comparison(before, result, threshold) if before is not None else None
    write_json(run / 'regression.json', result)
    text = render(result, compared)
    target = run / ('comparison.md' if compared else 'regression.md')
    target.write_text(text)
    if compared:
        write_json(run / 'comparison.json', compared)
    failed = any(r['status'] != 'passed' for r in result['cases'])
    return text, bool(failed or (compared and compared['concerns']))
