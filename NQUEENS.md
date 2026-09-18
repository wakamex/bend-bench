# N-Queens with bit-mask search

The earlier BOTS comparison gave Bend bit-mask search while the conventional solver repeatedly checked pairs of queens. This comparison gives both languages bit-mask search, counting every solution without symmetry reduction. It replaces that weak conventional baseline for performance conclusions; the original BOTS measurements remain historical evidence.

Run `nqueens.toml` for board sizes 8, 12 and 14, with 1, 2, 4, 8, 16 and 32 CPU threads. Each configuration checks the known solution count, excludes one warmup and measures ten process executions. A separate serial C++ variant bypasses OpenMP startup. The native regression test also checks C++ counts for sizes 1 through 8 against an independent board-based solver and compares Bend on sizes 4 and 8.

The OpenMP variants create tasks through three or five board rows and then use sequential bit-mask recursion. Both variants remain separately reported. This controls task-creation overhead without changing which solutions are explored. Bend retains natural child/sibling recursion with its existing structural fuel bound; it supplies no manual task cutoff. C++ uses a loop over available bits and Bend expresses that loop recursively. Thus the comparison tests practical implementations of the same search algorithm, including their respective scheduling costs.

The intended headline is time to enumerate all solutions with the strongest tested implementation. The old Bend-versus-BOTS speedup must not be presented as a language or scheduler advantage. Sorting continues to use its existing strong conventional baselines; matching a slower algorithm there would weaken the practical comparison.
