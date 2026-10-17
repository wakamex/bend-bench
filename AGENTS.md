# Benchmark execution

Commit changes atomically. For changes that affect benchmark results, include the measured before-and-after results in the commit message, identifying the workload and configuration. If the effect has not been measured, state that explicitly rather than implying an improvement. Keep implementation changes and subsequent result reporting in separate commits when measurements follow implementation.

Read README.md, VALIDATION.md and QUEUE.md before running benchmarks. Source checkouts and historical evidence in `/code/bend2` are immutable evaluation references. Use `/code/bend` for compiler fixes, with the exact commit and patch preserved separately.

Do not overlap benchmark runs or preparation with the legacy evaluation. The per-user harness lock and configured blocked services are required gates. Do not modify harness source, tests, tools or experiment configuration while a queued or active validation depends on them. Cancel the queued service explicitly before changing its pinned inputs, then enqueue a new validation.

Never discard failed samples, pool different fingerprints, count warmups as measurements or equate compilation with correctness. Distinguish process wall time, CPU compute regions, device-sequence event time and kernel-only duration. Host RSS is not device peak memory. Preserve unsupported and pending gates explicitly.

The finite packaged suites cover vendor benchmarks, CPU UTS, CUB sorting/reduction, Rodinia HotSpot, Asian-option pricing, exact m,n,k endgames, BFS with GAP/Gunrock, and machine learning from bend-ml against PyTorch (ML.md). Pricing and game-search controls are locally authored; do not call them established tuned baselines. Read APPLICATIONS.md for the distinct algorithms, arithmetic and input representations. Kernel profiling is a separate stage after correctness and unprofiled measurement gates. Additional BOTS programs, broader GAP inputs and algorithms, PBBS, other Rodinia programs, full MCTS, proof-system migration, Metal and AI-coding trials are separate outstanding work. A successful queue is not completion of the full research portfolio.

## Workload update checklist

When a change to a workload, its input staging or its baseline affects published numbers, complete these steps in order and commit the implementation change separately from the remeasured results:

1. Implementation and parity:
   - Update the workload source, input staging and output validation in `src/bend_bench/` and `tests/`.
   - If the workload is part of the GPU startup-scaling sweep, update its port builder in `startup_scaling.py` so the sweep stages the same inputs and arguments as the main harness.
   - Verify with a fast-profile run (`bend-bench cpu fast` or `bend-bench gpu fast`) and the unit test suite (`uv run --locked python -m unittest discover -s tests -v`, run when no benchmark process holds the harness lock), then commit the implementation change with before-and-after measurements.
2. Scorecard remeasurement and verification:
   - Remeasure the affected scorecard cells with their `scorecard-*.toml` or suite configuration pinned to the scorecard's Bend revision (`b9d1352c9f45632447f40a2e927355c92f2be58c`, or `d5fe6566` for `ml.toml`): run `prepare`, `check` and `run`.
   - Update `benchmarks/summary/data.json`: set `measurement_dates`, replace the affected `ms` entries (and `gpu_work` if the work-only ratio changed), point `case_sources` or `source` at the new `runs/<id>/summary.json`, and add the new summary's SHA-256 to `source_sha256`.
   - Rebuild `benchmarks/summary/index.html` with `uv run --locked python benchmarks/summary/build.py` and verify all rows, hashes and gates with `uv run --locked python benchmarks/summary/verify.py`.
3. Startup-scaling sweep and charts (when GPU times or fixed costs change):
   - Run `uv run --locked --with numpy --with scipy python startup_scaling.py --workloads <name> --config <scorecard-config>.toml` across the workload's full multiplier range (`1x` through its settled multiplier) when no other GPU compute job is active. Do not splice a partial `--max-multiplier` run over an older sweep's larger multipliers, since `scaling_fit.points()` overlays by multiplier and a day-to-day GPU state shift across the splice boundary distorts the marginal-slope settle check.
   - Run `uv run --locked --with numpy --with scipy python scaling_fit.py` to recompute the summary row and per-size markdown table in `STARTUP_SCALING.md`.
   - Run `uv run --locked --with matplotlib --with numpy --with scipy python scaling_charts.py` to regenerate `benchmarks/startup-scaling/ratio.png` (also displayed in `README.md`), `benchmarks/startup-scaling/times.png` (total process time, GPU work only and fitted `fixed cost + slope x` formulas), and `benchmarks/startup-scaling/device-share.png`.
4. Prose and workload reports:
   - Update any affected summary numbers, speedup or slowdown ranges, fixed-cost figures and method descriptions in `README.md`, `STARTUP_SCALING.md`, `benchmarks/summary/README.md` and the workload's report (`GPU_COMPARISON.md`, `PERFORMANCE.md`, `VENDOR_CUDA_COMPLETION.md`, `BFS_RESULTS.md`, `PRICING_SUSTAINED.md`, `MNK_HOST_ARRAY.md`, `UTS_GPU.md`, `ML.md`, `FAST_CPU.md`, `FAST_GPU.md`).

