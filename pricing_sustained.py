"""Finite sustained Asian-option pricing comparison with a CUDA qualification gate."""
import argparse
import json
import math
from pathlib import Path
import random
import re
import statistics
import struct
import time

from bend_bench.applications import pricing_reference, render
from bend_bench.core import append, environment, exclusive, execute, hash_file, load_config, provenance, write_json
from bend_bench.suites import plan, stage
from validate_applications import wait_idle

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'src/bend_bench/assets/gpu'


def bend_source(depth, steps, batches, audit):
    old = (ASSETS / 'pricing.bend').read_text()
    prefix = old[:old.index('def paths(')]
    if audit:
        prefix += old[old.index('def output('):old.index('def total(')]
    source = prefix + (ROOT / 'pricing_service.bend').read_text()
    fields = dict(AUDIT_FIELD=', values: Values', AUDIT_LEAF=', Value{x}',
                  AUDIT_A=', a', AUDIT_B=', b', AUDIT_PAIR=', Pair{a, b}',
                  AUDIT_VALUES=', values', AUDIT_PRINT='Unit <- IO.print(output(values, ""))')
    return render(source, dict(DEPTH=depth, STEPS=steps, DRIFT=repr(0.03 / steps),
                  VOL=repr(0.2 / math.sqrt(steps)), N=1 << depth, NM1=(1 << depth)-1,
                  BATCHES=batches, **{k: v if audit else '' for k, v in fields.items()}))


def cpp_source(batches, audit):
    old = (ASSETS / 'pricing.cpp').read_text()
    prefix = old[:old.index('#ifdef __CUDACC__\n__global__')]
    return f'#define BATCHES {batches}\n#define AUDIT {int(audit)}\n' + prefix + (ROOT / 'pricing_service.cpp').read_text()


def instrument_clock(source):
    old = '''Term io_now_run(Env e, Term* f, IoWork* w) {
  return (Term)(io_tick() / 1000000);
}'''
    if source.count(old) != 1:
        raise ValueError('Pinned clock implementation changed')
    return source.replace(old, r'''Term io_now_run(Env e, Term* f, IoWork* w) {
  static u64 stamps[3];
  static unsigned index = 0;
  u64 now = io_tick();
  stamps[index++] = now;
  if (index == 3) {
    fprintf(stderr, "PRICE_NS %llu %llu %llu\n",
      (unsigned long long)stamps[0], (unsigned long long)stamps[1], (unsigned long long)stamps[2]);
    index = 0;
  }
  return (Term)(now / 1000000);
}''')


def verify_quote_boundary(source):
    block = source.split('  WL_CASE(FID_EMIT)\n', 1)[1].split('  WL_CASE(', 1)[0]
    for slot in range(3):
        if not re.search(rf'\bu32 \w+ = r{slot};', block):
            raise ValueError('Quote is no longer three materialized scalar arguments at host emit')
    if 'FID_IO_NOW' in block or '#endif' not in block:
        raise ValueError('Host quote/timer ordering changed')


def prepare(config, work, depth, steps, batches, audit=False):
    work.mkdir()
    local = {**config, 'suites': ['pricing'], 'pricing_depths': [depth], 'pricing_steps': [steps], 'threads': [16]}
    # Stage static assets without invoking the large-input Python oracle.
    stage({**local, 'suites': []}, work)
    (work / 'ports').mkdir(exist_ok=True)
    source = work / f'ports/pricing-{depth}-{steps}.bend'
    source.write_text(bend_source(depth, steps, batches, audit))
    (work / 'gpu/pricing.cpp').write_text(cpp_source(batches, audit))
    builds, cases = plan(local, work)
    for case in cases:
        case.pop('expected_vector', None)
        case['contract'].update(output='price, nominal standard error, path count' + (' and every payoff' if audit else ''),
                                resident_batches=batches, seed_offset='batch_index * paths',
                                timing='simulation through all three host quote scalars',
                                payoff_audit=audit, standard_error_abs_tolerance=0.000002,
                                standard_error_rel_tolerance=0.001)
    write_json(work / 'plan.json', dict(builds=builds, cases=cases, depth=depth, steps=steps, batches=batches, audit=audit))
    for command in builds:
        result = execute(command, timeout=180)
        append(work / 'build.jsonl', result)
        if result['returncode']:
            raise RuntimeError(f"Build failed: {work}\n{result['stderr']}")
        if command[0] == local['tools']['bun'] and '-o' in command:
            c = Path(command[command.index('-o') + 1])
            original = c.read_text()
            if not audit:
                verify_quote_boundary(original)
            c.with_suffix('.original.c').write_text(original)
            c.write_text(instrument_clock(original))
    write_json(work / 'hashes.json', {str(p.relative_to(work)): hash_file(p) for p in work.rglob('*') if p.is_file()})
    return cases


def float_bits(s):
    value = struct.unpack('f', struct.pack('I', int(s)))[0]
    if not math.isfinite(value):
        raise ValueError('Nonfinite price or payoff')
    return value


def parse(result, n, batches):
    if result['returncode'] or result.get('timeout') or result.get('gpu_activity', {}).get('errors'):
        raise ValueError('Execution or GPU activity gate failed')
    quotes, payoffs = [], []
    for line in result['stdout'].splitlines():
        if not line or line == 'READY':
            continue
        fields = line.split()
        if fields[0] == 'RESULT' and len(fields) == 4:
            mean, se, count = float_bits(fields[1]), float_bits(fields[2]), int(fields[3])
            if mean < 0 or se < 0 or count != n:
                raise ValueError('Invalid quote')
            quotes.append([mean, se, count])
            payoffs.append([])
        elif fields[0] == 'VALUE' and len(fields) == 2 and payoffs:
            payoffs[-1].append(float_bits(fields[1]))
        elif line.isdigit() and payoffs:  # Bend full-payoff audit stream.
            payoffs[-1].append(float_bits(line))
        else:
            raise ValueError(f'Unexpected output: {line[:100]}')
    times = []
    for line in result['stderr'].splitlines():
        if line.startswith('PRICE_NS '):
            _, start, ready, done = line.split()
            if not int(start) < int(ready) <= int(done):
                raise ValueError('Invalid pricing timestamps')
            times.append((int(ready)-int(start))/1e9)
    if len(quotes) != batches or len(times) != batches:
        raise ValueError('Incomplete pricing batches')
    return quotes, payoffs, times


def compare_quotes(quotes, expected):
    if len(quotes) != len(expected):
        raise ValueError('Quote count mismatch')
    for got, want in zip(quotes, expected):
        if not all(math.isfinite(x) for x in (*got, *want)) or got[2] != want[2] or abs(got[0]-want[0]) > 0.002 + 0.0001*abs(want[0]) or abs(got[1]-want[1]) > 0.000002 + 0.001*abs(want[1]):
            raise ValueError(f'Quote mismatch: {got} != {want}')


def audit_quotes(vectors):
    return [[statistics.mean(v), statistics.stdev(v)/math.sqrt(len(v)), len(v)] for v in vectors]


def run_case(config, case, folder, n, batches, expected=None, vectors=None):
    folder.mkdir(parents=True)
    gpu = case['implementation'].endswith('cuda')
    result = execute(case['command'], env={**environment(), **case['env']}, timeout=300,
                     measured=True, gpu_policy=config if gpu else None)
    result['correct'] = False
    try:
        quotes, payoffs, times = parse(result, n, batches)
        if expected is not None:
            compare_quotes(quotes, expected)
        if vectors is not None:
            for actual, wanted in zip(payoffs, vectors):
                if len(actual) != len(wanted) or any(abs(a-b) > 0.002 + 0.0001*abs(b) for a, b in zip(actual, wanted)):
                    raise ValueError('Independent per-path payoff mismatch')
        elif any(payoffs):
            raise ValueError('Timed run emitted full payoffs')
        result.update(correct=True, quotes=quotes, pricing_seconds=times)
    except Exception as error:
        result['error'] = repr(error)
    write_json(folder / 'result.json', result)
    if not result['correct']:
        raise RuntimeError(f'Pricing validation failed: {folder}')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--depths', type=int, nargs='+', choices=(16, 18, 20), default=[16, 18])
    args = parser.parse_args()
    config = load_config(ROOT / 'applications.toml')
    config.update(suites=['pricing'], threads=[16], pricing_steps=[256], pricing_depths=args.depths)
    config['blocked_services'] += ['bend-bench-applications.service']
    out = ROOT / 'runs' / time.strftime('pricing-sustained-%Y%m%d-%H%M%S')
    out.mkdir()
    write_json(out / 'provenance.json', dict(harness=provenance(config), arguments=vars(args),
               scripts={p.name: hash_file(p) for p in [Path(__file__), ROOT/'pricing_service.cpp', ROOT/'pricing_service.bend']},
               qualification='median OpenMP16/CUDA pricing latency >= 1.2 at each size', warmups=2, measured_batches=30, repeats=3))
    for name in ('pricing_sustained.py', 'pricing_service.cpp', 'pricing_service.bend'):
        (out / name).write_text((ROOT / name).read_text())
    wait_idle(config, out)
    report = ['# Sustained Asian-call pricing', '',
              'Request-to-host quote timing includes simulation, payoff moments, reduction, price and standard error. Setup is outside repeated requests. Full-process wall time is retained separately. Two warmups, 30 measured batches and three fresh processes per implementation. Distinct deterministic path seeds per batch; the standard error uses the nominal independent-path formula.', '',
              '| Paths | Implementation | Repetition | Mean quote ms | Paths/second |',
              '|---:|---|---:|---:|---:|']
    with exclusive(config):
        print('STAGE independent per-path audit', flush=True)
        vectors = [pricing_reference(1024, 256, rep*1024) for rep in range(3)]
        write_json(out / 'oracle.json', vectors)
        audit = out / 'audit'
        cases = prepare(config, audit, 10, 256, 3, True)
        for case in cases:
            run_case(config, case, audit / case['implementation'], 1024, 3, audit_quotes(vectors), vectors)
        for depth in args.depths:
            n = 1 << depth
            print('STAGE conventional GPU qualification', n, flush=True)
            work = out / str(n)
            cases = prepare(config, work, depth, 256, 32)
            controls = [next(c for c in cases if c['implementation'] == name)
                        for name in ('local-openmp', 'local-cuda')]
            reference, rates = None, {}
            # Untimed oracle audit above precedes this separate qualification.
            for case in controls:
                latencies = []
                for rep in range(3):
                    r = run_case(config, case, work / 'qualification' / f"{case['implementation']}-{rep}", n, 32, reference)
                    if reference is None:
                        reference = r['quotes']
                    latencies.append(statistics.mean(r['pricing_seconds'][2:]))
                rates[case['implementation']] = statistics.median(latencies)
            ratio = rates['local-openmp'] / rates['local-cuda']
            write_json(work / 'qualification.json', dict(latencies=rates, cpu_over_gpu=ratio, passed=ratio >= 1.2))
            if ratio < 1.2:
                raise RuntimeError(f'Conventional GPU qualification failed at {n}: {ratio:.3f}x')
            print('QUALIFIED', n, ratio, flush=True)
            schedule = [(c, rep) for rep in range(3) for c in cases]
            random.Random(20260918).shuffle(schedule)
            write_json(work / 'schedule.json', [dict(case=c['id'], repetition=r) for c, r in schedule])
            for case, rep in schedule:
                print('RUN', n, case['implementation'], rep, flush=True)
                r = run_case(config, case, work / f"{case['implementation']}-{rep}", n, 32, reference)
                latency = statistics.mean(r['pricing_seconds'][2:])
                report.append(f"| {n} | {case['implementation']} | {rep} | {latency*1000:.3f} | {n/latency:.1f} |")
                (out / 'report.md').write_text('\n'.join(report) + '\n')
                print(report[-1], flush=True)
    write_json(out / 'completed.json', dict(report=str(out / 'report.md')))
    print('COMPLETE', out, flush=True)


if __name__ == '__main__':
    main()
