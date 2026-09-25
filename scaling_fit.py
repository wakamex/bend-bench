"""Fit each startup-scaling workload's times and compare Bend with the conventional GPU program per unit of work.

uv run --locked --with numpy --with scipy python scaling_fit.py [--json OUT]

Each program's time is fitted as a + d*x + b*x^c (curve), with x the work relative to the published
size: d*x is the work, and the b*x^c term (either sign, c < 1 when negative) the curvature small sizes
show while the GPU fills or caches stop fitting. That term trades off against the fixed cost, so the
fixed cost per run and the crossover come from the simpler a + b*x^c (fit), which the small sizes pin
down. Bend is fitted on its process
time, the conventional program on its process time rebuilt without host load noise
(startup_scaling.conventional_time). The comparison is the marginal ratio at the largest measured size:
Bend's added time for more work over the conventional program's (marginal_ratio).
"""
import argparse
import glob
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import brentq, least_squares

from startup_scaling import WORKLOADS as SWEEPS, conventional_time

ROOT = Path(__file__).resolve().parent

# (name, title, work(k)): work relative to the scorecard size, when it is not the multiplier itself.
WORKLOADS = [
    ('bfs', 'Batched maze BFS', None), ('editdist', 'Edit distance (cuDF)', None),
    ('gameoflife', 'Game of Life', None), ('hashmap', 'Hash tables', None), ('kmeans', 'K-means', None),
    ('lexer', 'Lexer', None), ('mandelbrot', 'Mandelbrot', None), ('merkle-blocks', 'Merkle tree', None),
    ('nbody', 'Three-body', None),
    ('raytrace', 'Ray tracing', lambda k: k * k), ('symreg', 'Symbolic regression', None),
    ('terrain', 'Terrain', None), ('hotspot', 'Rodinia HotSpot', None),
]
# The library's work time is unmeasurable at every size Bend's heap allows: report the measured ratio only.
LOWER_BOUND = [('tree-bitonic', 'Bitonic sort (CUB)'), ('tree-matmul', 'Tree matmul (cuBLAS)'), ('tree-radix', 'Radix sort (CUB)')]
# Unsettled at the largest valid size: the reported work-only ratio, in place of the last fit.
# Edit distance: the fit moved from 4.36 to 4.16 with 128x the pairs, whose paired ratios span 3.63 to
# 4.27; the last doubling's added times give 4.33, and 256x overflows cuDF's 32-bit string offsets.
REPORTED = {'editdist': 4.3}
# Sweeps along a second knob, listed with every size but not fitted on their own.
EXTRA = [('queens', 'N-Queens, prefixes searched at 17 queens'), ('queens-board', 'N-Queens, board size'),
         ('merkle', 'Merkle tree, by tree depth'), ('lexer-length', 'Lexer, by line length')]


def points():
    """Latest point per workload and multiplier, with its fastest measured conventional host time where
    the sweep predates recording it."""
    found = {}
    for path in sorted(glob.glob(str(ROOT / 'runs/startup-scaling-*/summary.json'))):
        for name, value in json.loads(Path(path).read_text()).items():
            if isinstance(value, list):
                for p in value:
                    if 'cuda_host_floor' not in p:
                        samples = Path(path).parent / name / str(p['multiplier']) / 'samples.jsonl'
                        rows = [json.loads(line) for line in samples.read_text().splitlines()]
                        p = dict(p, cuda_host_floor=min(r['end_to_end_seconds'] - r['device_sequence_seconds'] for r in rows
                                                        if r.get('phase') == 'measure' and r['implementation'] == 'cuda'))
                    found.setdefault(name, {})[p['multiplier']] = p
    return {name: [by_k[k] for k in sorted(by_k)] for name, by_k in found.items()}


def curve(x, t):
    """a + d*x + b*x^c on log time (relative error), with a, d >= 0; b >= 0 with 0.2 <= c <= 3, or b < 0
    with c < 1 so the marginal cost rises toward d. The best of a few starts; returns the parameters,
    the model, its derivative and the rms relative error."""
    x, t = np.asarray(x, float), np.asarray(t, float)
    slope = max((t[-1] - t[0]) / (x[-1] - x[0]), 1e-7)
    best = None
    for sign, starts, top in ((1, (0.5, 1.5, 2.0), 3.0), (-1, (0.3, 0.6, 0.9), 0.99)):
        model = lambda p, v: math.exp(p[0]) + math.exp(p[1]) * v + sign * math.exp(p[2]) * v ** p[3]
        residual = lambda p: np.log(np.maximum(model(p, x), 1e-12)) - np.log(t)
        for c0 in starts:
            for share in (0.1, 0.5, 0.9):
                p0 = [math.log(max(t.min() * 0.5, 1e-4)), math.log(slope),
                      math.log(slope * share / x[-1] ** (c0 - 1) * (1 if sign > 0 else 0.5)), c0]
                r = least_squares(residual, p0, bounds=([-20, -30, -30, 0.2], [5, 5, 5, top]))
                if best is None or r.cost < best[0].cost:
                    best = (r, sign)
    r, sign = best
    a, d, b, c = math.exp(r.x[0]), math.exp(r.x[1]), sign * math.exp(r.x[2]), r.x[3]
    return dict(a=a, d=d, b=b, c=c, rms=float(np.sqrt(np.mean(r.fun ** 2))),
                time=lambda v: a + d * v + b * v ** c, marginal=lambda v: d + b * c * v ** (c - 1))


def marginal_ratio(points, work=lambda k: k):
    """Bend's added time per unit of work over the conventional program's, at the largest measured size."""
    x = [work(p['multiplier']) for p in points]
    bend, conv = curve(x, [p['bend_seconds'] for p in points]), curve(x, conventional_time(points, work))
    return bend['marginal'](x[-1]) / conv['marginal'](x[-1]), bend, conv


def fit(x, t):
    """a + b*x^c on log time (relative error). Returns a, b, c."""
    x, t = np.asarray(x, float), np.asarray(t, float)
    model = lambda p, v: math.exp(p[0]) + math.exp(p[1]) * v ** p[2]
    p0 = [math.log(max(t.min() * 0.5, 1e-4)), math.log(max((t.max() - t.min()) / x.max(), 1e-7)), 1.0]
    r = least_squares(lambda p: np.log(model(p, x)) - np.log(t), p0, x_scale='jac')
    return math.exp(r.x[0]), math.exp(r.x[1]), r.x[2]


def fit_time_time(tb, wc, r=None):
    """T_Bend = a_Bend + K * w_conv^r, where w_conv is the conventional program's measured GPU work time:
    no work axis, so a workload grown along more than one knob fits as one curve. r=None fits r, else it
    is held fixed. Returns a_Bend, K, r, the standard error of r, rms."""
    tb, wc = np.asarray(tb, float), np.asarray(wc, float)
    free = r is None
    model = lambda p: math.exp(p[0]) + math.exp(p[1]) * wc ** (p[2] if free else r)
    fit = least_squares(lambda p: np.log(model(p)) - np.log(tb), [math.log(0.1), 0.0] + ([1.0] if free else []),
                        x_scale='jac')
    se = float('nan')
    if free and len(tb) > 3:
        cov = np.linalg.pinv(fit.jac.T @ fit.jac) * float(fit.fun @ fit.fun) / (len(tb) - 3)
        se = float(math.sqrt(max(cov[2, 2], 0)))
    return math.exp(fit.x[0]), math.exp(fit.x[1]), (fit.x[2] if free else r), se, float(np.sqrt(np.mean(fit.fun ** 2)))


def crossover(bend, conv):
    """Work multiplier where Bend's fitted time meets the conventional program's, or None."""
    f = lambda lx: (bend[0] + bend[1] * math.exp(lx) ** bend[2]) - (conv[0] + conv[1] * math.exp(lx) ** conv[2])
    grid = np.linspace(math.log(1e-3), math.log(1e6), 400)
    values = [f(g) for g in grid]
    for g0, g1, v0, v1 in zip(grid, grid[1:], values, values[1:]):
        if v0 < 0 <= v1:  # Bend faster below, slower above
            return math.exp(brentq(f, g0, g1))
    return None


def analyse(name, title, work, ps):
    work = work or (lambda k: k)
    k, bend, conv = marginal_ratio(ps, work)
    previous = marginal_ratio(ps[:-1], work)[0] if len(ps) >= 5 else float('nan')
    x = [work(p['multiplier']) for p in ps]
    fb, fc = fit(x, [p['bend_seconds'] for p in ps]), fit(x, conventional_time(ps, work))
    return dict(name=name, title=title, sizes=len(ps), largest=ps[-1]['multiplier'],
                a_bend=fb[0], a_conv=fc[0], K=REPORTED.get(name, k), K_fit=k, cell=f'{REPORTED.get(name, k):.3g}×', settle=k / previous - 1,
                crossover=crossover(fb, fc), rms_bend=bend['rms'], rms_conv=conv['rms'],
                first_ratio=ps[0]['bend_over_cuda'], last_ratio=ps[-1]['bend_over_cuda'], last_share=ps[-1]['cuda_device_share'])


def queens_row(data):
    """N-Queens grows along two knobs (prefixes searched at 17 queens, then the board), so Bend's time is
    fitted against the conventional program's measured GPU time. None below five sizes."""
    queens = data.get('queens', []) + data.get('queens-board', [])
    if len(queens) < 5:
        return None
    tb, wc = [p['bend_seconds'] for p in queens], [p['cuda_device_seconds'] for p in queens]
    aB, K, r, se, rms = fit_time_time(tb, wc)
    linear = abs(r - 1) <= max(2 * se, 0.05) if not math.isnan(se) else abs(r - 1) <= 0.05
    if linear:
        aB, K, r, se, rms = fit_time_time(tb, wc, 1.0)
    aC = float(np.median([p['cuda_seconds'] - p['cuda_device_seconds'] for p in queens]))
    return dict(name='queens', title='N-Queens', sizes=len(queens), a_bend=aB, a_conv=aC, K=K,
                cell=f'{K:.3g}×' if linear else f't^{r:.2f}', settle=float('nan'), crossover=None, rms_bend=rms, rms_conv=0.0,
                last_ratio=queens[-1]['bend_over_cuda'], last_share=queens[-1]['cuda_device_share'])


def markdown(rows, bounds, data):
    """The fit table and a table of every size per workload, for STARTUP_SCALING.md."""
    lines = ['| Workload | Work grown | Sizes | Bend ÷ conventional at the scorecard size | Bend ÷ conventional at the largest size '
             '| Conventional GPU share at the largest size | Work-only ratio | Change without the largest size '
             '| Fixed cost, Bend | Fixed cost, conventional |', '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        knob = 'prefixes searched at 17 queens, then board size' if r['name'] == 'queens' else SWEEPS[r['name']]['knob']
        largest = f"{r['largest']:,}×" if 'largest' in r else 'board 19'
        change = '' if math.isnan(r['settle']) else f"{100 * r['settle']:+.1f}%"
        lines.append(f"| {r['title']} | {knob} | 1× to {largest} | {r.get('first_ratio', data['queens'][0]['bend_over_cuda']):.2f} "
                     f"| {r['last_ratio']:.2f} | {100 * r['last_share']:.0f}% | {r['cell']} | {change} | {r['a_bend']:.3f} s | {r['a_conv']:.3f} s |")
    lines += ['', "| Library comparison | Largest size Bend's heap allows | Bend ÷ library there | Library GPU share there |",
              '|---|---:|---:|---:|']
    lines += [f"| {b['title']} | {b['largest']:,}× | {b['last_ratio']:.1f} | {100 * b['last_share']:.0f}% |" for b in bounds]
    titles = [(n, t) for n, t, _ in WORKLOADS] + [(n, t) for n, t in LOWER_BOUND] + EXTRA
    for name, title in titles:
        if name not in data:
            continue
        lines += ['', f'### {title}', '', f"| Multiplier | {SWEEPS[name]['knob']} | Bend GPU seconds | Conventional seconds "
                  '| Conventional GPU seconds | Conventional host floor seconds | Bend ÷ conventional | Checked against serial C |',
                  '|---:|---:|---:|---:|---:|---:|---:|---|']
        for p in data[name]:
            lines.append(f"| {p['multiplier']:,}× | {p['value']:,} | {p['bend_seconds']:.3f} | {p['cuda_seconds']:.3f} "
                         f"| {p['cuda_device_seconds']:.4f} | {p['cuda_host_floor']:.3f} | {p['bend_over_cuda']:.2f} "
                         f"| {'yes' if p['serial_verified'] else 'no'} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', type=Path)
    parser.add_argument('--markdown', type=Path, help='Write the fit table and every size as Markdown')
    args = parser.parse_args()
    data = points()
    rows = [analyse(n, t, w, data[n]) for n, t, w in WORKLOADS if len(data.get(n, [])) >= 3]
    queens = queens_row(data)
    if queens:
        rows.append(queens)
    bounds = [dict(name=n, title=t, largest=data[n][-1]['multiplier'], last_ratio=data[n][-1]['bend_over_cuda'],
                   last_share=data[n][-1]['cuda_device_share']) for n, t in LOWER_BOUND if n in data]
    print(f"{'Workload':22} {'sizes':>5} {'fixed Bend s':>12} {'fixed conv s':>12} {'work only':>10} {'settle':>7} "
          f"{'crossover':>10} {'rms B/C %':>10} {'last ratio':>10}")
    for r in rows:
        cross = f"{r['crossover']:.2f}×" if r['crossover'] else 'never'
        print(f"{r['title']:22} {r['sizes']:>5} {r['a_bend']:12.3f} {r['a_conv']:12.3f} {r['cell']:>10} {100 * r['settle']:+6.1f}% "
              f"{cross:>10} {100 * r['rms_bend']:4.1f}/{100 * r['rms_conv']:<4.1f} {r['last_ratio']:10.2f}")
    for b in bounds:
        print(f"{b['title']:22} lower bound: {b['last_ratio']:.1f}× at {b['largest']}× (library GPU share {100 * b['last_share']:.0f}%)")
    if args.markdown:
        args.markdown.write_text(markdown(rows, bounds, data))
    if args.json:
        args.json.write_text(json.dumps(dict(fits=rows, lower_bounds=bounds), indent=2) + '\n')


if __name__ == '__main__':
    main()
