"""Remeasure the Bend cells of the scorecard's summation and pricing rows at a new Bend revision.

Each row repeats its original protocol with only the Bend implementations: summation takes the
median of ten checked executions after two warmups (reduction_crossover.measure); pricing takes
the median of three shuffled process means, each over 30 requests after two warmups, with the
per-path payoff audit first and quotes checked against the archived OpenMP reference.
"""
import argparse
import json
from pathlib import Path
import random
import statistics
import time

import reduction_crossover as reduction
from bend_bench.applications import pricing_reference
from bend_bench.core import exclusive, hash_file, load_config, provenance, write_json
from pricing_single_cpu import single_thread
from pricing_sustained import audit_quotes, prepare, run_case
from validate_applications import wait_idle

ROOT = Path(__file__).resolve().parent
PRICING_REFERENCE = ROOT / 'runs/pricing-sustained-20260918-165158/262144/local-openmp-0/result.json'


def summation(config, out):
    point = reduction.measure(config, out, 1 << 31, cpu=True, keep={'bend-1', 'bend-16', 'bend-cuda'})
    return {f'reduce-{1 << 31}/{k}': v for k, v in point['medians'].items()}


def pricing(config, out):
    vectors = [pricing_reference(1024, 256, rep * 1024) for rep in range(3)]
    for case in prepare(config, out / 'audit', 10, 256, 3, True):
        run_case(config, case, out / 'audit' / case['implementation'], 1024, 3, audit_quotes(vectors), vectors)
    cases = prepare(config, out / '262144', 18, 256, 32)
    cases += [single_thread(c) for c in cases if c['implementation'] == 'bend']
    reference = json.loads(PRICING_REFERENCE.read_text())
    assert reference['correct'] and len(reference['quotes']) == 32
    schedule = [(c, rep) for rep in range(3) for c in cases]
    random.Random(20260923).shuffle(schedule)
    write_json(out / 'schedule.json', [dict(case=c['id'], repetition=r) for c, r in schedule])
    means = {}
    for case, rep in schedule:
        result = run_case(config, case, out / '262144' / f"{case['implementation']}-{case['threads']}-{rep}",
                          262144, 32, reference['quotes'])
        means.setdefault(case['id'], []).append(statistics.mean(result['pricing_seconds'][2:]))
        print('RESULT', case['id'], rep, means[case['id']][-1], flush=True)
    write_json(out / 'process-means.json', means)
    return {k: statistics.median(v) for k, v in means.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('row', choices=('summation', 'pricing'))
    parser.add_argument('config', type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    out = ROOT / 'runs' / time.strftime(f'scorecard-{args.row}-%Y%m%d-%H%M%S')
    out.mkdir()
    write_json(out / 'provenance.json', dict(harness=provenance(config), row=args.row, config=str(args.config),
               scripts={p.name: hash_file(p) for p in [Path(__file__), ROOT / 'reduction_crossover.py',
                        ROOT / 'pricing_sustained.py', ROOT / 'pricing_single_cpu.py', args.config]}))
    print('OUTPUT', out, flush=True)
    wait_idle(config, out)
    with exclusive(config):
        medians = (summation if args.row == 'summation' else pricing)(config, out)
    write_json(out / 'summary.json', dict(medians_seconds=medians))
    write_json(out / 'completed.json', dict(status='passed'))
    print('COMPLETE', out, json.dumps(medians), flush=True)


if __name__ == '__main__':
    main()
