"""Paired comparison of archived Bend b9d1352 binaries and new-revision binaries, CPU and GPU cells.

The machine carries other CPU work, so absolute times drift between days. Running the archived
scorecard binaries and the new ones alternately, under the same load, isolates the compiler's
effect. Each (row, threads) pair gets one warmup per version, then rounds in which both versions
run once in a seeded random order. Every execution is correctness-gated with the harness check of
its own run's plan; all samples, including failures, are kept.
"""
import argparse
import json
from pathlib import Path
import random
import statistics
import time

from bend_bench.core import append, correct, environment, exclusive, execute, hash_file, load_config, write_json

ROOT = Path(__file__).resolve().parent


def plan_cases(path):
    data = json.loads(Path(path).read_text())
    return {c['id']: c for c in data['cases']}


def pairs(new_runs):
    """(row, case id, old case, new case) for every Bend cell of the complete-program rows.

    UTS on the GPU is left out: both revisions stop at the machine stack limit there.
    """
    old_vendor = plan_cases(ROOT / 'runs/64b53b136d7cfde4ed9e/plan.json')
    sources = [('vendor', old_vendor, plan_cases(ROOT / new_runs['vendor'] / 'plan.json')),
               ('uts', old_vendor, plan_cases(ROOT / new_runs['uts'] / 'plan.json')),
               ('hotspot', plan_cases(ROOT / 'runs/c058f6b3293bda1d65dd/plan.json'),
                plan_cases(ROOT / new_runs['hotspot'] / 'plan.json')),
               ('bfs', plan_cases(ROOT / 'runs/6f09d7ec9215cbadd596/plan.json'),
                plan_cases(ROOT / new_runs['bfs'] / 'plan.json')),
               ('summation', plan_cases(ROOT / 'runs/summation-scaling-20260920/2147483648/prepared.json'),
                plan_cases(ROOT / new_runs['summation'] / '2147483648/prepared.json'))]
    wanted = json.loads((ROOT / 'benchmarks/summary/data.json').read_text())
    ids = {c for row in wanted['rows'] for c in (row.get('cases') or [])[:3] if c} - {'uts/tiny/bend-cuda/16'}
    out = []
    for row, old, new in sources:
        for case_id in sorted(ids & old.keys() & new.keys()):
            out.append((row, case_id, old[case_id], new[case_id]))
    return out


def gpu_clear():
    """True when the only GPU compute process is the approved transcription worker."""
    pids = execute(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'])['stdout'].split()
    for pid in pids:
        try:
            if 'transcribe-worker.service' not in Path(f'/proc/{pid}/cgroup').read_text():
                return False
        except OSError:
            pass
    return True


def run(case, config):
    gpu = case['implementation'].endswith('cuda')
    while gpu and not gpu_clear():
        print('WAITING unapproved GPU process', flush=True)
        time.sleep(60)
    try:
        result = execute(case['command'], env={**environment(), **case['env']}, timeout=300, measured=True,
                         gpu_policy=config if gpu else None)
    except ValueError as error:  # the activity monitor refused to start: a failed sample, kept
        return dict(returncode=None, timeout=False, end_to_end_seconds=None, contention_error=str(error), correct=False)
    result['correct'] = correct(case, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=5)
    parser.add_argument('--new-runs', type=Path, required=True, help='JSON map: vendor, uts, hotspot, bfs, summation run dirs')
    parser.add_argument('--resume-from', type=Path, action='append', default=[],
                        help='Earlier paired run whose completed cells are kept and not remeasured')
    args = parser.parse_args()
    new_runs = json.loads(args.new_runs.read_text())
    config = load_config(ROOT / 'scorecard-vendor.toml')
    out = ROOT / 'runs' / time.strftime('scorecard-paired-cpu-%Y%m%d-%H%M%S')
    out.mkdir()
    done = {k for run in args.resume_from for k in json.loads((run / 'summary.json').read_text())}
    todo = [t for t in pairs(new_runs) if t[1] not in done]
    write_json(out / 'provenance.json', dict(new_runs=new_runs, rounds=args.rounds, seed=20260924,
               script_sha256=hash_file(Path(__file__)), cells=[t[1] for t in todo],
               resumed_from=[str(r) for r in args.resume_from], kept_cells=sorted(done)))
    print('OUTPUT', out, len(todo), 'cells', flush=True)
    rng = random.Random(20260924)
    summary = {}
    with exclusive(config):
        for row, case_id, old, new in todo:
            times = {'old': [], 'new': []}
            for phase, rounds in (('warmup', 1), ('measure', args.rounds)):
                for rep in range(rounds):
                    order = [('old', old), ('new', new)]
                    rng.shuffle(order)
                    for version, case in order:
                        result = run(case, config)
                        append(out / 'samples.jsonl', dict(row=row, case=case_id, version=version, phase=phase, rep=rep, **result))
                        print(phase, case_id, version, rep, result['correct'], result['end_to_end_seconds'], flush=True)
                        if phase == 'measure' and result['correct']:
                            times[version].append((rep, result['end_to_end_seconds']))
            both = sorted(set(r for r, _ in times['old']) & set(r for r, _ in times['new']))
            ratios = [dict(times['new'])[r] / dict(times['old'])[r] for r in both]
            summary[case_id] = dict(row=row, rounds=len(both),
                                    old_median=statistics.median([t for _, t in times['old']] or [None]),
                                    new_median=statistics.median([t for _, t in times['new']] or [None]),
                                    new_over_old=statistics.median(ratios) if ratios else None,
                                    ratios=ratios)
            write_json(out / 'summary.json', summary)
    write_json(out / 'completed.json', dict(status='passed', cells=len(summary)))
    print('COMPLETE', out, flush=True)


if __name__ == '__main__':
    main()
