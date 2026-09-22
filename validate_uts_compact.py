"""Measure a compact UTS input and retain the original-runtime counterfactual."""
import json
from pathlib import Path
import time

from bend_bench.core import exclusive, hash_file, load_config, provenance, write_json
from bend_bench.experiment import prepare, sample, validate, report
from validate_applications import wait_idle

ROOT = Path(__file__).resolve().parent


def main():
    config = load_config(ROOT / 'uts-compact.toml')
    out = ROOT / 'runs' / time.strftime('uts-compact-validation-%Y%m%d-%H%M%S')
    out.mkdir()
    pins = provenance(config)
    runner_hash = hash_file(__file__)
    write_json(out / 'request.json', dict(config=config, provenance=pins, runner_hash=runner_hash,
                                         stop_limit='One candidate, maximum 60 seconds per process; no automatic retries'))
    print('OUTPUT', out, flush=True)
    wait_idle(config, out)
    assert provenance(config) == pins and hash_file(__file__) == runner_hash
    original = {**config, 'label': 'uts-compact-original',
                'bend': {'path': '/code/bend2/upstream', 'commit': 'b9d1352c9f45632447f40a2e927355c92f2be58c'}}
    original_run = prepare(original)
    with exclusive(original):
        identity = validate(original, original_run)['fingerprint']
        cases = json.loads((original_run / 'plan.json').read_text())['cases']
        gpu = next(c for c in cases if c['implementation'] == 'bend-cuda')
        check = sample(original, original_run, identity, gpu, 'check', 0)
        report(original_run)
        print('ORIGINAL_GPU_CHECK', check['correct'], check['end_to_end_seconds'], flush=True)
    # Use the original runtime when it passes; the fork is needed only for stack growth.
    selected = original if check['correct'] else config
    run = original_run if check['correct'] else prepare(config)
    write_json(out / 'runs.json', dict(original=str(original_run), selected=str(run), fork_used=not check['correct']))
    with exclusive(selected):
        identity = validate(selected, run)['fingerprint']
        cases = json.loads((run / 'plan.json').read_text())['cases']
        gpu = next(c for c in cases if c['implementation'] == 'bend-cuda')
        if run != original_run:
            check = sample(selected, run, identity, gpu, 'check', 0)
        if not check['correct'] or check['end_to_end_seconds'] >= 10:
            report(run)
            raise RuntimeError('Candidate fails the correct-and-under-10-seconds gate; inspect before further selection')
        for case in cases:
            for phase, count in [('check', 1), ('warmup', 1), ('measure', 10)]:
                for rep in range(count):
                    if case['id'] == gpu['id'] and phase == 'check':
                        continue
                    result = sample(selected, run, identity, case, phase, rep)
                    print(phase, case['id'], rep, result['end_to_end_seconds'], result['correct'], flush=True)
                    if not result['correct']:
                        report(run)
                        raise RuntimeError('Failed measurement retained; no automatic retry')
        validate(selected, run)
        report(run)
    write_json(out / 'completed.json', dict(run=str(run)))
    print('COMPLETE', run, flush=True)


if __name__ == '__main__':
    main()
