"""Compare what two Bend compiler checkouts emit, and how their tests fare.

Output identity: every program is emitted as C, JS and MJS by both checkouts,
and the hashes are compared with each checkout's own path masked. A refactor
should change nothing; a real compiler change shows exactly which programs it
touches. Identical output is not a correctness claim: that is the test lane's
job. Test lane: every test with a `#|` expectation is built natively by both
checkouts and run, and a test that passes with BASE but not with CANDIDATE is
a regression.

The corpus is the fast-profile ports, the compile-stress programs, and each
checkout's demos and tests. Programs present in only one checkout are listed
but not compared.
"""
import concurrent.futures
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .compile_stress import write as write_stress
from .core import write_json

PORTS = Path(__file__).parent / 'assets/fast_gpu'
OUTPUTS = ('c', 'js', 'mjs')


def corpus(base, candidate, shared):
    programs = {f'shared/{p.name}': (p, p) for p in sorted([*PORTS.glob('*.bend'), *shared])}
    for pattern in ('demos/*/main.bend', 'tests/**/*.bend'):
        for key in sorted({str(p.relative_to(c)) for c in (base, candidate) for p in c.glob(pattern)}):
            programs[key] = tuple(c / key if (c / key).exists() else None for c in (base, candidate))
    return programs


def bend(bun, checkout, source, out):
    try:
        return subprocess.run([bun, checkout / 'bend2/main.ts', source, '-o', out], cwd=source.parent,
                              capture_output=True, timeout=300)
    except subprocess.TimeoutExpired:
        return None


def emit(bun, checkout, source, scratch):
    hashes = {}
    for kind in OUTPUTS:
        out = scratch / f'out.{kind}'
        result = bend(bun, checkout, source, out)
        if result is None:
            body = b'TIMEOUT'
        elif out.exists():
            body = out.read_bytes()
        else:
            body = b'ERROR ' + result.stdout[-400:] + result.stderr[-400:]
        hashes[kind] = hashlib.sha256(body.replace(bytes(checkout), b'<checkout>')).hexdigest()
        out.unlink(missing_ok=True)
    return hashes


def expected(source):
    return [line[2:] for line in source.read_text().splitlines() if line.startswith('#|')]


def lane(bun, checkout, source, scratch):
    binary = scratch / source.stem  # Bend's tests expect a binary named after the test (tests/io/args)
    result = bend(bun, checkout, source, binary)
    if result is None:
        return 'build-timeout'
    if result.returncode or not binary.exists():
        return 'build-fail'
    try:
        run = subprocess.run([binary], cwd=source.parent, capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return 'timeout'
    return 'pass' if run.stdout.splitlines() == expected(source) else 'wrong'


def check(base, candidate, bun, only=None, jobs=None):
    base, candidate = Path(base).resolve(), Path(candidate).resolve()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        programs = corpus(base, candidate, write_stress(tmp / 'stress'))
        if only:
            programs = {k: v for k, v in programs.items() if re.search(only, k)}

        def one(item):
            key, sources = item
            if None in sources:
                return key, None
            scratch = Path(tempfile.mkdtemp(dir=tmp))
            row = {'outputs': {}, 'tests': {}}
            for side, checkout, source in zip(('base', 'candidate'), (base, candidate), sources):
                row['outputs'][side] = emit(bun, checkout, source, scratch)
                if key.startswith('tests/') and expected(source):
                    row['tests'][side] = lane(bun, checkout, source, scratch)
            return key, row

        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs or max(1, (os.cpu_count() or 2) // 2)) as pool:
            rows = dict(pool.map(one, programs.items()))
    changed = {k: [kind for kind in OUTPUTS if r['outputs']['base'][kind] != r['outputs']['candidate'][kind]]
               for k, r in rows.items() if r}
    tests = {k: r['tests'] for k, r in rows.items() if r and r['tests']}
    return dict(base=str(base), candidate=str(candidate), programs=len(programs),
                only_in_base=sorted(k for k, (_, c) in programs.items() if c is None),
                only_in_candidate=sorted(k for k, (b, _) in programs.items() if b is None),
                changed={k: v for k, v in changed.items() if v},
                tests={status: sum(t['candidate'] == status for t in tests.values()) for status in sorted({t['candidate'] for t in tests.values()})},
                test_status=tests, test_changes={k: t for k, t in tests.items() if t['base'] != t['candidate']},
                regressions=sorted(k for k, t in tests.items() if t['base'] == 'pass' and t['candidate'] != 'pass'))


def render(result, limit=40):
    compared = result['programs'] - len(result['only_in_base']) - len(result['only_in_candidate'])
    lines = ['# Compiler check', '', f"Base `{result['base']}`, candidate `{result['candidate']}`.", '',
             '## Emitted output', '',
             f"{len(result['changed'])} of {compared} programs emit different output (C, JS or MJS)."
             + (' The candidate emits the same output as the base.' if not result['changed'] else '')]
    if result['changed']:
        lines.append('')
    lines += [f"- {k}: {', '.join(v)}" for k, v in sorted(result['changed'].items())[:limit]]
    if len(result['changed']) > limit:
        lines.append(f"- and {len(result['changed']) - limit} more (see the JSON).")
    for side in ('base', 'candidate'):
        if result[f'only_in_{side}']:
            lines += ['', f"Only in the {side}, not compared: " + ', '.join(result[f'only_in_{side}'])]
    lines += ['', '## Test lane', '', 'Candidate: ' + ', '.join(f'{n} {s}' for s, n in result['tests'].items()) + '.', '']
    if result['test_changes']:
        lines += ['| Test | Base | Candidate |', '|---|---|---|']
        lines += [f"| {k} | {t['base']} | {t['candidate']} |" for k, t in sorted(result['test_changes'].items())]
    else:
        lines.append('Every test has the same status with both checkouts.')
    if result['regressions']:
        lines += ['', f"{len(result['regressions'])} test(s) pass with the base but not with the candidate."]
    return '\n'.join(lines) + '\n'


def run(base, candidate, bun, output=None, only=None, jobs=None, identical=False):
    result = check(base, candidate, bun, only, jobs)
    if output is not None:
        write_json(output, result)
    failed = bool(result['regressions']) or (identical and bool(result['changed']))
    return render(result), failed
