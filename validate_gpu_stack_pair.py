"""Alternate patched/unpatched GPU measurements with one pinned resident exception."""
import argparse
import json
from pathlib import Path
import time
import uuid

from bend_bench.core import exclusive, idle_gpu, load_config, write_json
from bend_bench.experiment import prepare, report, sample, validate
from bend_bench.gpu_activity import process_identity
from bend_bench.regression import publish

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resident-pid', type=int, required=True)
    args = parser.parse_args()
    resident = process_identity(args.resident_pid)
    started = time.perf_counter()
    identity = uuid.uuid4().hex
    configs = []
    for name, filename in [('patched', 'fast-gpu.toml'), ('unpatched', 'fast-gpu-unpatched.toml')]:
        config = load_config(ROOT / filename)
        config.update(repetitions=3, require_idle_gpu=True, gpu_resident=resident,
                      _run_id=identity, label='stack-pair-'+name)
        configs.append(config)
    output = ROOT / 'runs' / ('gpu-stack-pair-' + identity[:12])
    output.mkdir()
    write_json(output / 'request.json', dict(configs=configs, resident=resident,
        policy='Only the pinned resident may overlap; its activity is allowed and recorded',
        ordering='Per workload: alternate implementations; reverse first implementation each repetition',
        phases={'check': 1, 'warmup': 1, 'measure': 3}))
    print('PAIR', output, flush=True)
    folders = []
    try:
        idle_gpu(configs[0])
        for config in configs:
            folders.append(prepare(config))
        write_json(output / 'runs.json', dict(patched=str(folders[0]), unpatched=str(folders[1])))
        plans = [json.loads((folder / 'plan.json').read_text())['cases'] for folder in folders]
        if [c['id'] for c in plans[0]] != [c['id'] for c in plans[1]]:
            raise ValueError('Workload plans differ')
        # Hold one shared admission lock across the entire paired measurement sequence.
        with exclusive(configs[0]):
            prepared = [validate(config, folder) for config, folder in zip(configs, folders)]
            for index in range(len(plans[0])):
                failed = set()
                for phase, count in [('check', 1), ('warmup', 1), ('measure', 3)]:
                    for rep in range(count):
                        order = (0, 1) if (index + rep) % 2 == 0 else (1, 0)
                        for side in order:
                            if side in failed:
                                continue
                            print(configs[side]['label'], phase, rep, flush=True)
                            result = sample(configs[side], folders[side], prepared[side]['fingerprint'],
                                            plans[side][index], phase, rep)
                            if not result['correct']:
                                failed.add(side)
                for config, folder in zip(configs, folders):
                    validate(config, folder)
    except BaseException as error:
        write_json(output / 'stopped.json', dict(error=str(error), elapsed_seconds=time.perf_counter()-started))
        raise
    finally:
        for folder in folders:
            report(folder)
        if len(folders) == 2:
            text, concerns = publish(folders[1], folders[0])
            print(text, flush=True)
    write_json(output / 'completed.json', dict(elapsed_seconds=time.perf_counter()-started,
        concerns=concerns, comparison=str(folders[1] / 'comparison.md')))
    print('COMPLETE', output, flush=True)


if __name__ == '__main__':
    main()
