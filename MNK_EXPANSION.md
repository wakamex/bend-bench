# CUDA pruning and expanded endgame corpus

This experiment tests whether the conventional CUDA control improves when each GPU thread searches a complete position and can prune across root moves. It then repeats the comparison with 1,024 distinct positions instead of 16. Performance results are pending.

The controls separate two changes. The original root-parallel CUDA implementation uses bounds [-2, 2] for scores in [-1, 1]. A second root-parallel build tightens those bounds to [-1, 1]. A third keeps the tighter bounds and assigns one complete position to each GPU thread. OpenMP is measured with both bounds as well. All searches enumerate empty squares in ascending order; the tight bounds correspond to Bend's [0, 2] score representation. Each variant has a distinct executable, and the original control remains available.

The larger corpus uses the same deterministic generator and preserves the original 16-position prefix. All 1,024 boards are distinct legal nonterminal 5×5 connect-4 positions with eight empty squares. Saved move histories establish reachability, and the independent tuple-board solver supplies every expected outcome. Positions are generated without selecting for performance or outcome. The corpus summary records win/draw/loss counts and a content hash.

The finite comparison uses both corpus sizes, 524,288 positions per batch, two warmups and 30 measured batches per process, and three fresh processes per implementation in shuffled order. Seven implementations give 42 processes in total: two Bend backends, two OpenMP variants and three CUDA variants. Every emitted answer is checked. Delivered throughput includes answer formatting and transfer to the observer; search-to-host timing is recorded separately. Neither is kernel-only time.

```sh
uv run --locked python mnk_sustained.py --depths 19 --batches 30 --repeats 3 --multicore-only --telemetry --control-variants --corpus-sizes 16 1024
```

GPU admission requires the existing 120-second quiet window, with a 24-hour deadline. Builds and measurements hold the shared benchmark lock. Each compilation has a 180-second limit and each measured process a 300-second limit. A failed build, wrong answer, timeout or unapproved GPU activity stops the run and preserves its evidence. There are no automatic retries. After two failed interventions at the same gate, reassess the hypothesis before changing another implementation detail.
