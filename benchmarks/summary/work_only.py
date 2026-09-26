"""Copy the startup-scaling work-only GPU ratios into data.json.

uv run --locked --with numpy --with scipy python benchmarks/summary/work_only.py
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
import scaling_fit  # noqa: E402

# Scorecard row name -> scaling workload.
ROWS = {'Batched maze BFS': 'bfs', 'Edit distance': 'editdist', 'Game of Life soup census': 'gameoflife',
        'Independent hash tables': 'hashmap', 'K-means': 'kmeans', 'Lexer': 'lexer', 'Mandelbrot': 'mandelbrot',
        'Merkle tree and proof': 'merkle-blocks', 'Three-body ensemble': 'nbody', 'N-Queens': 'queens',
        'Ray tracing': 'raytrace', 'Symbolic regression': 'symreg', 'Terrain': 'terrain', 'Rodinia HotSpot': 'hotspot',
        'Tree bitonic sort': 'tree-bitonic', 'Tree matrix multiplication': 'tree-matmul',
        'Tree radix sort + deduplication': 'tree-radix', 'Option pricing': 'pricing',
        '5 × 5 connect-4 · alpha-beta': 'game-search'}


def main():
    data = scaling_fit.points()
    fits = {r['name']: r['K'] for r in [scaling_fit.analyse(n, t, w, data[n]) for n, t, w in scaling_fit.WORKLOADS if n in data]
            + [scaling_fit.queens_row(data)] if r}
    bounds = {n: data[n][-1]['bend_over_cuda'] for n, _ in scaling_fit.LOWER_BOUND}
    path = ROOT / 'data.json'
    card = json.loads(path.read_text())
    for row in card['rows']:
        name = ROWS.get(row['name'])
        value = scaling_fit.times(fits[name]) if name in fits else '>' + scaling_fit.times(bounds[name]) if name in bounds else None
        row.pop('gpu_work', None)
        if value:
            row['gpu_work'] = value
    path.write_text(json.dumps(card, indent=2, ensure_ascii=False) + '\n')
    print({row['name']: row.get('gpu_work') for row in card['rows']})


if __name__ == '__main__':
    main()
