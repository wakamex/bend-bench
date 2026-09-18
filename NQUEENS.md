# N-Queens with bit-mask search

OpenMP finishes the 14-queen search about 16× sooner than Bend at 16 CPU threads: 14 ms versus 224 ms. Both enumerate all 365,596 solutions using bit masks. All 57 configurations passed correctness checks and ten measured repetitions on the Ryzen 9 3950X.

| Enumerate all solutions on a 14×14 board | 1 CPU thread | 16 CPU threads | 32 CPU threads |
|---|---:|---:|---:|
| Bend bit-mask recursion | 289.1 ms | 224.0 ms | 206.3 ms |
| C++ bit-mask OpenMP, tasks through row 3 | 145.5 ms | 14.0 ms | 16.0 ms |
| C++ bit-mask OpenMP, tasks through row 5 | 148.0 ms | 61.8 ms | 66.9 ms |
| C++ bit-mask serial, no OpenMP region | 141.4 ms | N/A | N/A |

Times include startup and output. At 16 threads, Bend gains 1.29× over its own one-thread run, while the row-3 OpenMP variant gains 10.37×. Creating tasks through five rows makes OpenMP slower than stopping at three; the extra scheduling work outweighs the benefit of splitting the search further. The 8-queen board takes only a few milliseconds including startup and does not benefit from more threads. On the 12-queen board, row-3 OpenMP takes 4.17 ms versus Bend's 9.34 ms at 16 threads.

The [full configuration report](runs/921fd5564318acbccf09/report.md) retains both OpenMP cutoffs at every size and thread count. The run preserves 684 executions, including checks and warmups, under identity `921fd5564318acbccf09`. Implementation commit: `9a677ba`. Tested Bend revision: `b9d1352c9f45632447f40a2e927355c92f2be58c`.

## Comparison contract

The earlier BOTS comparison gave Bend bit-mask search while the conventional solver repeatedly checked pairs of queens. This comparison gives both languages bit-mask search, counting every solution without symmetry reduction. It replaces that weak conventional baseline for performance conclusions; the original BOTS measurements remain historical evidence.

Run `nqueens.toml` for board sizes 8, 12 and 14, with 1, 2, 4, 8, 16 and 32 CPU threads. Each configuration checks the known solution count, excludes one warmup and measures ten process executions. A separate serial C++ variant bypasses OpenMP startup. The native regression test also checks C++ counts for sizes 1 through 8 against an independent board-based solver and compares Bend on sizes 4 and 8.

The OpenMP variants create tasks through three or five board rows and then use sequential bit-mask recursion. Both variants remain separately reported. This controls task-creation overhead without changing which solutions are explored. Bend retains natural child/sibling recursion with its existing structural fuel bound; it supplies no manual task cutoff. C++ uses a loop over available bits and Bend expresses that loop recursively. Thus the comparison tests practical implementations of the same search algorithm, including their respective scheduling costs.

The intended headline is time to enumerate all solutions with the strongest tested implementation. The old Bend-versus-BOTS speedup must not be presented as a language or scheduler advantage. Sorting continues to use its existing strong conventional baselines; matching a slower algorithm there would weaken the practical comparison.
