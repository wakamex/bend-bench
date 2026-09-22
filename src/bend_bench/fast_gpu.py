"""Fixed-input, GPU-only compiler regression portfolio."""
import gzip
import json
import math
from pathlib import Path
import struct
import time

from .core import append, hash_file, provenance

ASSETS = Path(__file__).parent / 'assets/fast_gpu'


def stage_fixtures(config, work):
    for source in ASSETS.glob('*.bend'):
        text = source.read_text().replace('@RODINIA@', config['rodinia']['path'])
        (work / 'ports' / source.name).write_text(text)
    for source in ASSETS.glob('*.gz'):
        (work / 'ports' / source.stem).write_bytes(gzip.decompress(source.read_bytes()))


def plan_fixtures(config, work, bend_build, case, cases, gpu_reason):
    hashes = {p.name: hash_file(p) for p in ASSETS.iterdir() if p.is_file()}
    for fixture in json.loads((ASSETS / 'manifest.json').read_text()):
        name = fixture['name']
        threads = fixture['threads']
        if threads > len(config['cpus']):
            raise ValueError(f'Fast GPU {name} requires {threads} available host CPU threads')
        binary = bend_build(work / 'ports' / fixture['source'], name, True)
        contract = {**fixture['contract'], 'fixture_hashes': hashes,
                    'timing': 'complete process including startup and output', 'profile': 'fast-gpu-v1'}
        case('gpu-regression', name, 'bend-cuda', threads, str(binary) + '-cuda',
             ['--threads', threads, '--gpu', config['gpu_heap']], fixture['expected_regex'], gpu_reason, contract)
        for key in ('expected_bits', 'expected_vector'):
            if key in fixture:
                cases[-1][key] = str(work / 'ports' / fixture[key])
        if 'regression_kind' in fixture:
            cases[-1]['regression_kind'] = fixture['regression_kind']
            cases[-1]['regression_reference'] = str(ASSETS / (name + '.json'))


def correct_special(case, result):
    try:
        reference = json.loads(Path(case['regression_reference']).read_text())
        lines = result['stdout'].splitlines()
        if not lines or lines.pop(0) != 'READY':
            return False
        if case['regression_kind'] == 'game-search':
            if len(lines) != 524289 or lines.pop() != 'END':
                return False
            return all(line == str(reference[(i + 1004) % 1024]) for i, line in enumerate(lines))
        if len(lines) != len(reference):
            return False
        for line, want in zip(lines, reference):
            tag, price, error, count = line.split()
            if tag != 'RESULT' or int(count) != want[2]:
                return False
            price, error = (struct.unpack('<f', struct.pack('<I', int(x)))[0] for x in (price, error))
            if not all(math.isfinite(x) and x >= 0 for x in (price, error)):
                return False
            if abs(price-want[0]) > .002 + .0001*abs(want[0]) or abs(error-want[1]) > .000002 + .001*abs(want[1]):
                return False
        return True
    except (ValueError, OSError, IndexError, struct.error):
        return False


def run(config, baseline=None, threshold=10):
    from .experiment import directory, measure, prepare, report
    from .gpu_activity import idle_snapshot
    from .regression import load_result, publish
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError('Regression threshold must be a finite positive percentage')
    if baseline is not None:
        baseline = load_result(baseline)  # Freeze the comparison input before waiting or executing.
    if config['suites'] != ['gpu-regression'] or not config['cuda'] or not config['require_idle_gpu']:
        raise ValueError('fast-gpu requires the GPU-only regression preset and GPU activity gates')
    evidence = provenance(config)
    folder = directory(config, evidence)
    folder.mkdir(parents=True, exist_ok=True)
    print('WAITING for 120 seconds of sampled GPU inactivity', flush=True)
    deadline, quiet, cursor = time.monotonic()+86400, None, time.time_ns()//1000
    while time.monotonic() < deadline:
        observation = idle_snapshot(config, cursor)
        append(folder / 'gpu-wait.jsonl', observation)
        if observation['samples']:
            cursor = max(s['timestamp_us'] for s in observation['samples'])
        if observation['errors']:
            quiet = None
        elif quiet is None:
            quiet = time.monotonic()
        if quiet is not None and time.monotonic()-quiet >= 120:
            break
        time.sleep(1)
    else:
        raise ValueError('No idle GPU window within 24 hours')
    if provenance(config) != evidence:
        raise ValueError('Inputs changed during GPU wait')
    folder = prepare(config)
    print('RUN', folder, flush=True)
    try:
        _, failed = measure(config, checking=True)
        # Retain failed cases while still exercising the rest of the portfolio.
        _, measured_failed = measure(config)
    finally:
        report(folder)
        text, concerns = publish(folder, baseline, threshold)
        print(text, flush=True)
    return folder, failed or measured_failed or concerns
