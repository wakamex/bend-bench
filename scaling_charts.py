"""Draw the startup-scaling charts from every runs/startup-scaling-* summary.

uv run --locked --with matplotlib --with numpy --with scipy python scaling_charts.py [OUTPUT_DIR]
"""
from pathlib import Path
import math
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, NullFormatter  # noqa: E402

import scaling_fit  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'benchmarks/startup-scaling'

# Reference palette, light mode (dataviz references/palette.md). The conventional program's two
# series share its hue (solid: whole process, dashed: GPU work only).
SURFACE, INK, INK2, GRID, REF = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df', '#8a8984'
BLUE, ORANGE = '#2a78d6', '#eb6834'

# Scorecard order; title and knob per workload. Bend's 4 GB heap caps the library comparisons.
WORKLOADS = [
    ('bfs', 'Batched maze BFS', 'mazes'), ('editdist', 'Edit distance (cuDF)', 'string pairs'),
    ('gameoflife', 'Game of Life', 'soups'), ('hashmap', 'Hash tables', 'tables'),
    ('kmeans', 'K-means', 'Lloyd rounds'), ('lexer', 'Lexer', 'lines'),
    ('mandelbrot', 'Mandelbrot', 'iterations'), ('merkle-blocks', 'Merkle tree', 'blocks per leaf'),
    ('nbody', 'Three-body', 'steps'), ('queens', 'N-Queens', 'prefixes searched'),
    ('raytrace', 'Ray tracing', 'pixels'), ('symreg', 'Symbolic regression', 'population'),
    ('terrain', 'Terrain', 'relaxation sweeps'), ('tree-bitonic', 'Bitonic sort (CUB)', 'keys'),
    ('tree-matmul', 'Tree matmul (cuBLAS)', 'GEMM rounds'), ('tree-radix', 'Radix sort (CUB)', 'keys'),
    ('hotspot', 'Rodinia HotSpot', 'timesteps'),
]
ROWS = math.ceil(len(WORKLOADS) / 4)
LOWER_BOUND = {'tree-bitonic', 'tree-matmul', 'tree-radix'}


def panels():
    """One axis per workload on a grid of four columns; spare cells are hidden."""
    fig, axes = plt.subplots(ROWS, 4, figsize=(13, 2.75 * ROWS), facecolor=SURFACE, sharex=True, sharey=True)
    for ax in axes.flat[len(WORKLOADS):]:
        ax.set_visible(False)
    return fig, axes


def work(name, p):
    """Work relative to the scorecard size: ray tracing's multiplier is the image side."""
    k = p['multiplier']
    return k * k if name == 'raytrace' else min(k, 83521 / 11730) if name == 'queens' else k


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8, length=0)
    ax.grid(True, which='major', color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def times(v, _):
    return f'{v:,.0f}×' if v >= 1 else f'{v:g}×'


def axis_work(ax, knob):
    """One shared work axis, 1x to 16,384x, labeled every 16x; the knob sits under each panel."""
    ax.set_xscale('log', base=2)
    ax.set_xlim(0.7, 24000)
    ax.set_xticks([1, 16, 256, 4096])
    ax.xaxis.set_major_formatter(FuncFormatter(times))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.tick_params(labelbottom=True)
    ax.set_xlabel(f'work, × scorecard size ({knob})', fontsize=8, color=INK2)


def ratio_chart(data, fits, path):
    fig, axes = panels()
    for ax, (name, title, knob) in zip(axes.flat, WORKLOADS):
        style(ax)
        ps = data.get(name, [])
        ax.axhline(1, color=REF, linewidth=1, linestyle='--')
        if name in fits:
            ax.axhline(fits[name], color=BLUE, linewidth=1, linestyle=':')
            ax.annotate(f'work only {fits[name]:.3g}×', (0.97, 0.05), xycoords='axes fraction', ha='right', fontsize=8, color=INK2)
        if ps:
            xs, ys = [work(name, p) for p in ps], [p['bend_over_cuda'] for p in ps]
            ax.plot(xs, ys, color=BLUE, linewidth=2, marker='o', markersize=4, zorder=3)
            ax.plot(xs[-1:], ys[-1:], marker='o', markersize=8, linestyle='none', zorder=4,
                    markerfacecolor=SURFACE if name in LOWER_BOUND else BLUE, markeredgecolor=BLUE, markeredgewidth=2)
            note = f'{ys[-1]:.3g}×' + (' (lower bound)' if name in LOWER_BOUND else '')
            left = xs[-1] < 64  # near the left edge the label goes right, inside the panel
            ax.annotate(note, (xs[-1], ys[-1]), textcoords='offset points', xytext=(8 if left else -6, 8),
                        ha='left' if left else 'right', fontsize=9, color=INK)
        else:
            ax.text(0.5, 0.5, 'pending', transform=ax.transAxes, ha='center', color=INK2, fontsize=9)
        axis_work(ax, knob)
        ax.set_yscale('log')
        ax.set_ylim(0.3, 600)
        ax.set_yticks([1, 10, 100])
        ax.yaxis.set_major_formatter(FuncFormatter(times))
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.set_title(title, fontsize=10, color=INK, loc='left')
    fig.suptitle('Bend GPU time ÷ conventional GPU time as the work grows (dashed: equal time)',
                 fontsize=13, color=INK, x=0.01, ha='left')
    fig.text(0.01, 0.955, 'Above the line the conventional program is faster. Dotted: fitted work-only ratio. Open end marker: Bend ran out of its 4 GB heap before the library program\'s GPU work dominated.',
             fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def share_chart(data, path):
    fig, axes = panels()
    for ax, (name, title, knob) in zip(axes.flat, WORKLOADS):
        style(ax)
        ps = data.get(name, [])
        ax.axhline(75, color=REF, linewidth=1, linestyle='--')
        if ps:
            xs, ys = [work(name, p) for p in ps], [100 * p['cuda_device_share'] for p in ps]
            ax.plot(xs, ys, color=BLUE, linewidth=2, marker='o', markersize=4, zorder=3)
            left = xs[-1] < 64
            ax.annotate(f'{ys[-1]:.0f}%', (xs[-1], ys[-1]), textcoords='offset points', xytext=(8 if left else -6, 6),
                        ha='left' if left else 'right', fontsize=9, color=INK)
        else:
            ax.text(0.5, 0.5, 'pending', transform=ax.transAxes, ha='center', color=INK2, fontsize=9)
        axis_work(ax, knob)
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%'))
        ax.set_title(title, fontsize=10, color=INK, loc='left')
    fig.suptitle("Share of the conventional program's time spent on GPU work (dashed: 75%)",
                 fontsize=13, color=INK, x=0.01, ha='left')
    fig.text(0.01, 0.955, 'Below the line, process startup and host-side work dominate its time, so the Bend comparison mostly measures overhead.',
             fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def anatomy_chart(data, path, names=('mandelbrot', 'kmeans')):
    titles = {n: t for n, t, _ in WORKLOADS}
    knobs = {n: k for n, _, k in WORKLOADS}
    fig, axes = plt.subplots(1, len(names), figsize=(12, 4.8), facecolor=SURFACE)
    series = (('bend_seconds', 'Bend GPU, whole process', BLUE, '-'),
              ('cuda_seconds', 'CUDA, whole process', ORANGE, '-'),
              ('cuda_device_seconds', 'CUDA, GPU work only', ORANGE, '--'))
    for ax, name in zip(axes, names):
        style(ax)
        ps = data.get(name, [])
        xs = [work(name, p) for p in ps]
        for key, label, color, dash in series:
            ys = [p[key] for p in ps]
            ax.plot(xs, ys, color=color, linewidth=2, linestyle=dash, marker='o', markersize=4, label=label, zorder=3,
                    markerfacecolor=SURFACE if dash == '--' else color)
        ax.set_xscale('log', base=2)
        ax.set_yscale('log')
        ax.xaxis.set_major_formatter(FuncFormatter(times))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:g} s'))
        ax.set_title(titles[name], fontsize=11, color=INK, loc='left')
        ax.set_xlabel(f'work ({knobs[name]}), × scorecard size', fontsize=8, color=INK2)
    for ax in axes:
        ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc='upper left')
    fig.suptitle("CUDA's process time stays near its startup floor until its GPU work outgrows it",
                 fontsize=13, color=INK, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def times_chart(data, path):
    """All workloads: Bend and conventional process time with the conventional GPU work, on one scale."""
    fig, axes = panels()
    series = (('bend_seconds', 'Bend GPU, whole process', BLUE, '-'),
              ('cuda_seconds', 'Conventional GPU, whole process', ORANGE, '-'),
              ('cuda_device_seconds', 'Conventional GPU, GPU work only', ORANGE, '--'))
    for ax, (name, title, knob) in zip(axes.flat, WORKLOADS):
        style(ax)
        ps = data.get(name, [])
        if ps:
            xs = [work(name, p) for p in ps]
            for key, label, color, dash in series:
                ax.plot(xs, [p[key] for p in ps], color=color, linewidth=2, linestyle=dash, marker='o', markersize=3,
                        label=label, zorder=3, markerfacecolor=SURFACE if dash == '--' else color)
        else:
            ax.text(0.5, 0.5, 'pending', transform=ax.transAxes, ha='center', color=INK2, fontsize=9)
        axis_work(ax, knob)
        ax.set_yscale('log')
        ax.set_ylim(3e-4, 800)
        ax.set_yticks([0.001, 0.1, 10])
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:g} s'))
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.set_title(title, fontsize=10, color=INK, loc='left')
    handles, labels = axes.flat[2].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper right', ncol=3, frameon=False, fontsize=9, labelcolor=INK)
    fig.suptitle('Time per run as the work grows', fontsize=13, color=INK, x=0.01, ha='left')
    fig.text(0.01, 0.955, "The conventional program's process time sits on a startup floor near 0.2 s until its GPU work reaches it.",
             fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = scaling_fit.points()
    rows = [scaling_fit.analyse(n, t, w, data[n]) for n, t, w in scaling_fit.WORKLOADS if n in data] + [scaling_fit.queens_row(data)]
    fits = {r['name']: r['K'] for r in rows if r}
    ratio_chart(data, fits, OUT / 'ratio.png')
    share_chart(data, OUT / 'device-share.png')
    anatomy_chart(data, OUT / 'startup-floor.png')
    times_chart(data, OUT / 'times.png')
    missing = [n for n, _, _ in WORKLOADS if n not in data]
    print('wrote', OUT, 'missing:', missing)


if __name__ == '__main__':
    main()
