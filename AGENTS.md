# Benchmark execution

Commit changes atomically. For changes that affect benchmark results, include the measured before-and-after results in the commit message, identifying the workload and configuration. If the effect has not been measured, state that explicitly rather than implying an improvement. Keep implementation changes and subsequent result reporting in separate commits when measurements follow implementation.

Read README.md, VALIDATION.md and QUEUE.md before running benchmarks. Source checkouts and historical evidence in `/code/bend2` are immutable evaluation references. Use `/code/bend` for compiler fixes, with the exact commit and patch preserved separately.

Do not overlap benchmark runs or preparation with the legacy evaluation. The per-user harness lock and configured blocked services are required gates. Do not modify harness source, tests, tools or experiment configuration while a queued or active validation depends on them. Cancel the queued service explicitly before changing its pinned inputs, then enqueue a new validation.

Never discard failed samples, pool different fingerprints, count warmups as measurements or equate compilation with correctness. Distinguish process wall time, CPU compute regions, device-sequence event time and kernel-only duration. Host RSS is not device peak memory. Preserve unsupported and pending gates explicitly.

The finite packaged suites cover vendor benchmarks, CPU UTS, CUB sorting/reduction, Rodinia HotSpot, Asian-option pricing, exact m,n,k endgames, BFS with GAP/Gunrock, and machine learning from bend-ml against PyTorch (ML.md). Pricing and game-search controls are locally authored; do not call them established tuned baselines. Read APPLICATIONS.md for the distinct algorithms, arithmetic and input representations. Kernel profiling is a separate stage after correctness and unprofiled measurement gates. Additional BOTS programs, broader GAP inputs and algorithms, PBBS, other Rodinia programs, full MCTS, proof-system migration, Metal and AI-coding trials are separate outstanding work. A successful queue is not completion of the full research portfolio.
