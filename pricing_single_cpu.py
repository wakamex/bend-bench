"""Complete the archived 262,144-path pricing comparison at one CPU thread."""
import copy
import json
from pathlib import Path
import random
import statistics
import time

from bend_bench.core import exclusive, hash_file, load_config, write_json
from pricing_sustained import ROOT, audit_quotes, run_case


def single_thread(case):
    case = copy.deepcopy(case)
    command = case['command']
    assert command[:2] == ['taskset', '-c']
    command[2] = command[2].split(',')[0]
    if case['implementation'] == 'bend':
        command[command.index('--threads') + 1] = '1'
    else:
        assert case['implementation'] == 'local-openmp'
    case['env']['OMP_NUM_THREADS'] = '1'
    case['threads'] = 1
    case['id'] = case['id'].rsplit('/', 1)[0] + '/1'
    return case


def archived_cases(work):
    hashes = json.loads((work / 'hashes.json').read_text())
    for name, expected in hashes.items():
        assert hash_file(work / name) == expected, name
    plan = json.loads((work / 'plan.json').read_text())
    return [single_thread(c) for c in plan['cases']
            if c['implementation'] in ('bend', 'local-openmp')]


def main():
    source = ROOT / 'runs/pricing-sustained-20260918-165158'
    out = ROOT / 'runs' / time.strftime('pricing-single-cpu-%Y%m%d-%H%M%S')
    out.mkdir()
    config = load_config(ROOT / 'applications.toml')
    config['blocked_services'] += ['bend-bench-applications.service']
    pins = {str(p.relative_to(ROOT)): hash_file(p) for p in
            [Path(__file__), ROOT / 'pricing_sustained.py', ROOT / 'src/bend_bench/core.py']}
    write_json(out / 'provenance.json', dict(source=str(source), scripts=pins,
               config=config, warmups=2, measured_requests=30, processes=3,
               cpu_source='Same archived binaries; affinity and thread count changed to one'))
    print('OUTPUT', out, flush=True)
    with exclusive(config):
        audit = archived_cases(source / 'audit')
        cases = archived_cases(source / '262144')
        vectors = json.loads((source / 'oracle.json').read_text())
        for case in audit:
            run_case(config, case, out / 'audit' / case['implementation'],
                     1024, 3, audit_quotes(vectors), vectors)
        reference = json.loads((source / '262144/local-openmp-0/result.json').read_text())
        assert reference['correct'] and len(reference['quotes']) == 32
        schedule = [(c, rep) for rep in range(3) for c in cases]
        random.Random(20260922).shuffle(schedule)
        write_json(out / 'schedule.json', [dict(case=c, repetition=r) for c, r in schedule])
        timings = {c['implementation']: [] for c in cases}
        for case, rep in schedule:
            print('RUN', case['id'], rep, flush=True)
            result = run_case(config, case, out / f'{case["implementation"]}-{rep}',
                              262144, 32, reference['quotes'])
            value = statistics.mean(result['pricing_seconds'][2:])
            timings[case['implementation']].append(value)
            print('RESULT', case['implementation'], rep, value, flush=True)
        archived_cases(source / 'audit')
        archived_cases(source / '262144')
        assert all(hash_file(ROOT / name) == value for name, value in pins.items())
        write_json(out / 'summary.json', {name: statistics.median(values)
                                         for name, values in timings.items()})
        write_json(out / 'completed.json', dict(status='passed'))
    print('COMPLETE', out, flush=True)


if __name__ == '__main__':
    main()
