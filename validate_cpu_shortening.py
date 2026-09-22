"""Measure three shorter CPU inputs against the completed full-input profile."""
import json
from pathlib import Path
import statistics

from bend_bench.core import append, correct, environment, execute, exclusive, hash_file, load_config, provenance, write_json
from bend_bench.suites import plan, stage

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / 'runs/257a7afdc515d4cd801b'
OUTPUT = ROOT / 'runs/cpu-shortening-20260922-three-reps'
CHANGES = {
    'gameoflife': ('def size() -> Nat:\n  18n', 'def size() -> Nat:\n  16n'),
    'nbody': ('def sy() -> Nat:\n  17n', 'def sy() -> Nat:\n  15n'),
    'hotspot': ('solve!(100n,', 'solve!(10n,'),
}


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected exactly one marker: {old}')
    return text.replace(old, new)


def main():
    config = load_config(ROOT / 'fast-cpu.toml')
    with exclusive(config):
        OUTPUT.mkdir(exist_ok=False)
        work = OUTPUT / 'work'
        stage(config, work)
        evidence = provenance(config)
        write_json(OUTPUT / 'provenance.json', evidence)
        baseline = json.loads((BASELINE / 'summary.json').read_text())
        write_json(OUTPUT / 'baseline-summary.json', baseline)
        builds, cases = plan(config, work)
        cases = [c for c in cases if c['workload'] in CHANGES]
        for name, (old, new) in CHANGES.items():
            source = work / 'ports' / (name + '.bend')
            source.write_text(replace_once(source.read_text(), old, new))
        expected = {}
        for name, old, new in [('gameoflife', 'uint32_t size = 18u;', 'uint32_t size = 16u;'),
                               ('nbody', '#define SY 17', '#define SY 15')]:
            original = Path('/code/bend2/upstream/bench/runtime') / name / 'main.c'
            source = work / 'ports' / (name + '-reference.c')
            source.write_text(replace_once(original.read_text(), old, new))
            binary = work / 'build' / (name + '-reference')
            result = execute([config['tools']['cc'], '-O3', '-march=native', '-ffp-contract=off', source, '-lm', '-o', binary])
            append(OUTPUT / 'builds.jsonl', result)
            if result['returncode']:
                raise RuntimeError(result['stderr'])
            result = execute([binary])
            append(OUTPUT / 'oracles.jsonl', {**result, 'source_sha256': hash_file(original)})
            if result['returncode'] or not result['stdout'].strip().isdigit():
                raise RuntimeError('C reference failed')
            expected[name] = result['stdout'].strip()
        bits = Path('runs/c058f6b3293bda1d65dd/work/ports/hotspot-1024-10.bits')
        (work / 'ports/hotspot-short.bits').write_bytes((ROOT / bits).read_bytes())
        for case in cases:
            if case['workload'] == 'hotspot':
                case['expected_bits'] = str(work / 'ports/hotspot-short.bits')
            else:
                case['expected_regex'] = expected[case['workload']]
            case['contract']['shortening'] = CHANGES[case['workload']]
        outputs = {str(work / 'build' / name) + suffix for name in CHANGES for suffix in ('', '.c')}
        for command in builds:
            if command[-1] not in outputs:
                continue
            result = execute(command, timeout=120)
            append(OUTPUT / 'builds.jsonl', result)
            if result['returncode']:
                raise RuntimeError(result['stderr'])
        write_json(OUTPUT / 'plan.json', cases)
        write_json(OUTPUT / 'hashes.json', {str(p.relative_to(work)): hash_file(p) for p in work.rglob('*') if p.is_file()})
        rows = []
        for case in cases:
            times = []
            for phase, count in [('check', 1), ('warmup', 1), ('measure', 3)]:
                for rep in range(count):
                    result = execute(case['command'], env={**environment(), **case['env']}, timeout=60, measured=True)
                    passed = correct(case, result)
                    append(OUTPUT / 'samples.jsonl', dict(case=case['id'], phase=phase, rep=rep, correct=passed, **result))
                    print(phase, case['id'], rep, result['end_to_end_seconds'], passed, flush=True)
                    if not passed:
                        raise RuntimeError('Correctness failed; failed sample preserved')
                    if phase == 'measure':
                        times.append(result['end_to_end_seconds'])
            old = next(c for c in baseline['cases'] if c['case'] == case['id'])
            rows.append(dict(workload=case['workload'], threads=case['threads'], before=old['end_to_end_seconds'], after=statistics.median(times), samples=times))
        if provenance(config) != evidence:
            raise RuntimeError('Provenance changed during experiment')
        write_json(OUTPUT / 'results.json', rows)
        print('COMPLETE', OUTPUT, flush=True)


if __name__ == '__main__':
    main()
