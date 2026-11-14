"""Summary of a metal/compare.sh log: test status, probe programs, build and runtime timing.

The first side named in the log is the base (A), the other the candidate (B). Runtime blocks
are scored as in `paired`: (A1 + A2) / (B1 + B2) per A B B A or B A A B block, above 1 when
the candidate is faster, with the median block and a bootstrap interval of that median.
"""
import statistics
from collections import defaultdict

from .paired import block_ratio, score


def parse(text):
    sides, tests, probes, outputs = [], defaultdict(dict), defaultdict(dict), {}
    builds = defaultdict(lambda: defaultdict(lambda: ([], [])))
    runs = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    def side(name):
        if name not in sides:
            if len(sides) == 2:
                raise ValueError(f'A third side in the log: {name}')
            sides.append(name)
        return name

    section = None
    for line in text.splitlines():
        word = line.split()
        if not word:
            continue
        if word[0] == '==':
            section = ' '.join(word[1:])
        elif word[0] in ('PASS', 'FAIL', 'BUILDFAIL') and len(word) == 3:
            if section == 'programs':
                probes[word[2]][side(word[1])] = 'build failed'
            else:
                tests[word[2]][side(word[1])] = word[0]
        elif word[0] == 'prog' and len(word) >= 4:
            probes[word[1]][side(word[2])] = (float(word[3]), ' '.join(word[4:]))
        elif word[0] == 'build' and len(word) == 6:
            compile_s, gpu_s = builds[word[1]][side(word[2])]
            compile_s.append(float(word[4]))
            gpu_s.append(float(word[5]))
        elif word[0] in ('same-output', 'DIFF-output') and len(word) == 2:
            outputs[word[1]] = word[0] == 'same-output'
        elif word[0] == 'run' and len(word) == 5:
            runs[word[2]][int(word[1])][side(word[3])].append(float(word[4]))
    if len(sides) != 2:
        raise ValueError('The log needs results for two sides')
    return dict(sides=sides, tests=tests, probes=probes, builds=builds, runs=runs, outputs=outputs)


def summarize(log):
    base, candidate = log['sides']
    results = []
    for name, blocks in log['runs'].items():
        ratios = [block_ratio({'A': times[base], 'B': times[candidate]}) for _, times in sorted(blocks.items())]
        results.append(dict(case=name, **score(ratios),
                            base_median=statistics.median(t for b in blocks.values() for t in b[base]),
                            candidate_median=statistics.median(t for b in blocks.values() for t in b[candidate])))
    builds = []
    for name, by_side in log['builds'].items():
        (a_compile, a_gpu), (b_compile, b_gpu) = by_side[base], by_side[candidate]
        builds.append(dict(case=name, runs=min(len(a_compile), len(b_compile)),
                           compile=(statistics.median(a_compile), statistics.median(b_compile)),
                           gpu_build=(statistics.median(a_gpu), statistics.median(b_gpu))))
    return dict(base=base, candidate=candidate, results=results, builds=builds)


def render(log):
    s = summarize(log)
    base, candidate = s['base'], s['candidate']
    lines = ['# Metal comparison', '', f'Base `{base}`, candidate `{candidate}`.', '']
    tests = log['tests']
    passed = {v: sum(t.get(v) == 'PASS' for t in tests.values()) for v in (base, candidate)}
    lines += [f'Bang tests with `--gpu on`: {base} passes {passed[base]}, {candidate} passes {passed[candidate]}.', '']
    changed = sorted(n for n, t in tests.items() if t.get(base) != t.get(candidate))
    if changed:
        lines += ['| Test | ' + base + ' | ' + candidate + ' |', '|---|---|---|']
        lines += [f'| {n} | {tests[n].get(base, "absent")} | {tests[n].get(candidate, "absent")} |' for n in changed] + ['']
    if log['probes']:
        def cell(value):
            return value if isinstance(value, str) else f'{value[0]:.3f} s, `{value[1]}`'
        lines += ['Probe programs, wall time and last output line:', '',
                  f'| Program | {base} | {candidate} |', '|---|---|---|']
        lines += [f'| {n} | {cell(p.get(base, "absent"))} | {cell(p.get(candidate, "absent"))} |'
                  for n, p in sorted(log['probes'].items())] + ['']
    if s['builds']:
        lines += ['Build, median seconds over alternated runs: `bend -o` (which includes one GPU build) and a further `+RTS --gpu-build`:', '',
                  f'| Program | Runs a side | bend -o, {base} | bend -o, {candidate} | --gpu-build, {base} | --gpu-build, {candidate} |',
                  '|---|---:|---:|---:|---:|---:|']
        lines += [f'| {b["case"]} | {b["runs"]} | {b["compile"][0]:.3f} | {b["compile"][1]:.3f} | {b["gpu_build"][0]:.3f} | {b["gpu_build"][1]:.3f} |'
                  for b in s['builds']] + ['']
    differ = sorted(n for n, same in log['outputs'].items() if not same)
    if log['outputs']:
        lines += [f'Runtime output differs between the sides for: {", ".join(differ)}.' if differ else
                  f'Runtime output is identical on both sides for all {len(log["outputs"])} programs.', '']
    if s['results']:
        lines += ['Runtime: each block runs base (A) and candidate (B) as A B B A or B A A B and scores (A1 + A2) / (B1 + B2);'
                  ' above 1x means the candidate is faster. The interval is a 95% bootstrap interval of the median block;'
                  ' with four blocks it spans every block score, so a verdict means all blocks agree.', '',
                  f'| Program | Median s, {base} | Median s, {candidate} | Blocks | Median block | 95% interval | Verdict |',
                  '|---|---:|---:|---:|---:|---:|---|']
        lines += [f'| {r["case"]} | {r["base_median"]:.4f} | {r["candidate_median"]:.4f} | {r["blocks"]} | {r["median"]:.3f}x | '
                  f'{r["low"]:.3f}x to {r["high"]:.3f}x | {r["verdict"]} |'
                  for r in s['results']] + ['']
    return '\n'.join(lines)
