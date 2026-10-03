"""Paired base/candidate timing in ABBA and BAAB blocks, scored per block.

A workload that compiles to the same program on both sides cannot change speed, so it is
reported as unchanged and not timed. The same program means the same GPU program past the
8-byte key that names its source, and the same host machine code with addresses removed: a
change to the emitted C that compiles to nothing (an unused #define, a comment) only moves the
source copy the binary embeds for the GPU build, and the addresses after it. Every other selected workload runs as blocks of four
processes, A B B A then B A A B in turn: both versions sit at the same mean position in a
block, so background drift that is linear over the block cancels exactly in the block's score,
(A1+A2) / (B1+B2) (above 1: the candidate is faster), and each version runs once before and
once after the other; a workload reports the median over blocks and a bootstrap interval of
that median, taken from this session's own blocks.
"""
import hashlib
import json
import random
import re
import subprocess
import statistics
import time
from pathlib import Path

from .core import append, correct, environment, exclusive, execute, fingerprint, hash_file, write_json
from .experiment import prepare

ORDERS = ('ABBA', 'BAAB')


def block_ratio(times):
    """times: {'A': [a1, a2], 'B': [b1, b2]} -> (a1+a2) / (b1+b2)."""
    a, b = times['A'], times['B']
    if len(a) != 2 or len(b) != 2 or min(a + b) <= 0:
        raise ValueError('A block needs two positive times per side')
    return (a[0] + a[1]) / (b[0] + b[1])


def score(ratios, resamples=10000, seed=0):
    """Median block ratio and a 95% percentile-bootstrap interval of the median."""
    if not ratios:
        raise ValueError('No blocks to score')
    rng = random.Random(seed)
    medians = sorted(statistics.median(rng.choices(ratios, k=len(ratios))) for _ in range(resamples))
    low, high = medians[int(0.025 * resamples)], medians[int(0.975 * resamples) - 1]
    verdict = 'faster' if low > 1 else 'slower' if high < 1 else 'no detected change'
    return dict(median=statistics.median(ratios), low=low, high=high, blocks=len(ratios), verdict=verdict)


def cases_of(run):
    return {c['id']: c for c in json.loads((run / 'plan.json').read_text())['cases'] if not c['unsupported']}


def program(case):
    """The executed code of a case's binary, or None if it cannot be read."""
    binary = next((Path(a) for a in case['command'] if '/work/build/' in str(a)), None)
    if binary is None or not binary.is_file():
        return None
    code = subprocess.run(['objdump', '-d', '--no-addresses', '--no-show-raw-insn', binary],
                          capture_output=True, text=True)
    if code.returncode != 0:
        return None
    host = re.sub(r'(0x)?[0-9a-f]{4,}|<[^>]*>', '', code.stdout.split('\n', 2)[-1])
    device = binary.with_name(binary.name + '.gpu')
    gpu = hashlib.sha256(device.read_bytes()[8:]).hexdigest() if device.is_file() else None
    return hashlib.sha256(host.encode()).hexdigest(), gpu


def time_once(config, run, case, out, side, block, slot, phase):
    env = {**environment(), **case['env']}
    command = [*case['command'], *(case.get('check_args', []) if phase == 'check' else [])]
    result = execute(command, cwd=run / 'work', env=env, timeout=config['timeout'], measured=True,
                     gpu_policy=config if config.get('require_idle_gpu') else None)
    ok = correct(case, result)
    append(out / 'samples.jsonl', dict(case=case['id'], side=side, block=block, slot=slot, phase=phase,
                                       correct=ok, **result))
    if not ok:
        raise ValueError(f'{side} {case["id"]} gave a wrong or contended result in {phase}; see {out / "samples.jsonl"}')
    return result['end_to_end_seconds']


def run(base, candidate, workloads=None, blocks=8, warmups=1):
    if blocks < 2:
        raise ValueError('At least two blocks are needed for an interval')
    for key in ('suites', 'threads', 'cpus', 'gpu_heap', 'timeout'):
        if base.get(key) != candidate.get(key):
            raise ValueError(f'Base and candidate configurations differ in {key}')
    runs = {'A': prepare(base), 'B': prepare(candidate)}
    configs = {'A': base, 'B': candidate}
    cases = {side: cases_of(runs[side]) for side in runs}
    if cases['A'].keys() != cases['B'].keys():
        raise ValueError('Base and candidate plan different cases')
    chosen = [i for i in cases['A'] if workloads is None or cases['A'][i]['workload'] in workloads]
    if workloads is not None and {cases['A'][i]['workload'] for i in chosen} != set(workloads):
        raise ValueError('Unknown workload; choose from: ' + ', '.join(sorted({c['workload'] for c in cases['A'].values()})))
    same = [i for i in chosen if program(cases['A'][i]) is not None
            and program(cases['A'][i]) == program(cases['B'][i])]
    timed = [i for i in chosen if i not in same]
    identity = fingerprint(dict(runs={s: str(r) for s, r in runs.items()},
                                prepared={s: hash_file(r / 'prepared.json') for s, r in runs.items()},
                                cases=timed, blocks=blocks, warmups=warmups, started=time.time_ns()))
    out = Path(base['output']) / ('paired-' + identity[:16])
    out.mkdir(parents=True)
    write_json(out / 'request.json', dict(base=str(runs['A']), candidate=str(runs['B']), blocks=blocks,
                                          warmups=warmups, same_program=same, timed=timed, orders=ORDERS))
    print('PAIRED', out, flush=True)
    results = []
    with exclusive(base):
        for case_id in timed:
            for side in ('A', 'B'):
                time_once(configs[side], runs[side], cases[side][case_id], out, side, -1, -1, 'check')
                for rep in range(warmups):
                    time_once(configs[side], runs[side], cases[side][case_id], out, side, -1, rep, 'warmup')
            ratios = []
            for block in range(blocks):
                order, times = ORDERS[block % 2], {'A': [], 'B': []}
                for slot, side in enumerate(order):
                    times[side].append(time_once(configs[side], runs[side], cases[side][case_id], out, side, block, slot, 'measure'))
                ratios.append(block_ratio(times))
                print(f'{case_id} block {block} {order}: {ratios[-1]:.3f}', flush=True)
            results.append(dict(case=case_id, ratios=ratios, **score(ratios)))
    summary = dict(same_program=same, results=results)
    write_json(out / 'summary.json', summary)
    text = render(summary, runs)
    (out / 'report.md').write_text(text)
    return out, text


def render(summary, runs):
    lines = ['# Paired comparison', '', f'Base `{runs["A"]}`, candidate `{runs["B"]}`.', '']
    if summary['results']:
        lines += ['Each block runs base (A) and candidate (B) as A B B A or B A A B and scores (A1 + A2) / (B1 + B2);'
                  ' above 1x means the candidate is faster. The interval is a 95% bootstrap interval of the median block.', '',
                  '| Workload | Blocks | Median, candidate speedup | 95% interval | Verdict |', '|---|---:|---:|---:|---|']
        for r in summary['results']:
            lines.append(f'| {r["case"]} | {r["blocks"]} | {r["median"]:.3f}x | {r["low"]:.3f}x to {r["high"]:.3f}x | {r["verdict"]} |')
        lines.append('')
    if summary['same_program']:
        lines += [f'Not timed, the same compiled program on both sides ({len(summary["same_program"])}): '
                  + ', '.join(summary['same_program']) + '.', '']
    return '\n'.join(lines)
