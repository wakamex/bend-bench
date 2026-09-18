# Alpha-beta endgame search

Adding alpha-beta pruning makes Bend's 5×5 connect-4 batch with eight empty squares 5.6× faster at 16 CPU threads: 17.604 ms becomes 3.144 ms. The unchanged OpenMP solver takes 3.339 ms in the new run. Each batch contains the same 16 legal positions, checked against an independent Python solver, with one warmup and ten measured executions per configuration.

| Batch of 16 exact endgames | Bend before, 1 thread | Bend alpha-beta, 1 thread | Bend before, 16 threads | Bend alpha-beta, 16 threads | OpenMP alpha-beta, 16 threads, new run |
|---|---:|---:|---:|---:|---:|
| 4×4 connect-3, six empty squares | 2.502 ms | 2.292 ms | 2.962 ms | 2.874 ms | 3.344 ms |
| 4×4 connect-3, eight empty squares | 13.173 ms | 2.282 ms | 6.102 ms | 2.830 ms | 3.512 ms |
| 5×5 connect-4, six empty squares | 4.477 ms | 2.329 ms | 3.251 ms | 2.836 ms | 3.353 ms |
| 5×5 connect-4, eight empty squares | 82.272 ms | 2.680 ms | 17.604 ms | 3.144 ms | 3.339 ms |

All times include process startup and output. After pruning, one-thread Bend is faster than 16-thread Bend on every tested batch. These jobs now finish in a few milliseconds, so the small differences against OpenMP do not establish a sustained search-throughput advantage. Larger batches or deeper endgames would be needed to test useful scaling of this implementation.

## Implementation and correctness

The previous Bend solver evaluated every terminal-pruned branch through a parallel 32-slot move tree. The replacement scans only legal moves in increasing board-index order and uses alpha-beta bounds to skip branches that cannot change the result. Scores remain 0/1/2 for loss/draw/win, with negation implemented as `2 - score`. The initial bounds are 0 and 2. Independent positions remain parallel; sibling moves within each position are sequential so they can share tighter bounds. This changes both pruning and move enumeration, so the measurements describe the complete replacement rather than isolating the cost of either change.

OpenMP also distributes positions, while the unchanged CUDA control distributes root moves before searching each subtree with alpha-beta. No heuristic cutoff, transposition table, symmetry reduction or learned evaluation is used. Structural fuel 128 exceeds the maximum dependency-path bound of 55 calls for the supported nine-empty-square limit; exhaustion produces an invalid score that is rejected rather than accepted as an outcome.

The JavaScript backend passes independent-oracle checks for 48 additional 3×3 positions with two, four and six empty squares. All four benchmark corpora, totaling 64 positions, pass CPU checks at one and 16 threads and CUDA-backend correctness checks. CUDA timing and kernel profiling of the replacement remain unmeasured; the previous exhaustive port's GPU timings do not describe this implementation.

## Preserved evidence

- [Before: fresh exhaustive-port CPU run](runs/bd0bc9c94d677e60bf0f/report.md).
- [After: alpha-beta CPU run](runs/908512f46e454d93bc3f/report.md).
- [Alpha-beta CPU/CUDA correctness checks](runs/83452dc5cca9bad0a594/report.md).

The CPU comparison uses the same four corpora, CPU affinity, one/16-thread settings, compiler revision, release flags and repetition policy on the Ryzen 9 3950X. Bend revision is `b9d1352c9f45632447f40a2e927355c92f2be58c`. CPU-only runs disable GPU monitoring; the separate CUDA check retains the configured activity policy. An initial diagnostic that unnecessarily monitored GPU activity during CPU measurements was interrupted and its partial samples retained. Each completed run preserves generated source, build commands, binary hashes and individual outputs.
