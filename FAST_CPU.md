# Fast Bend CPU regression benchmark

Run the same 22 workload families as the GPU profile at one and 16 CPU threads:

```sh
uv run --locked bend-bench cpu fast --plan
uv run --locked bend-bench cpu fast
uv run --locked bend-bench cpu fast --repetitions 3
uv run --locked bend-bench cpu fast --repetitions 10
uv run --locked bend-bench cpu fast candidate.toml --baseline runs/BASELINE_ID
```

The default [fast-cpu.toml](fast-cpu.toml) pins the compiler checkout, revision and host CPU affinity. Copy it and change `[bend].path` and `[bend].commit` for another compiler version. Workload sources and correctness references remain fixed. The profile builds each CPU executable once and runs it at both thread counts, with no GPU kernels, GPU idle wait, conventional controls or CPU/GPU overlap. The shared benchmark lock and blocked-service checks still apply.

## Input selection

| Workloads | CPU profile | Reason |
|---|---|---|
| Original 16 published workloads | Original inputs | Preserve the known CPU scaling tests and exact output contracts |
| UTS | Existing 4,112,897-node BOTS input | Around one second on Bend CPU; more useful work than the GPU profile's compact tree |
| Summation | 268,435,456 generated integers | Reduces the single-thread cost while retaining a large balanced reduction |
| Option pricing | One request, 262,144 paths × 256 observations | Roughly 2.4 seconds single-thread; retains all paths and final quote checks |
| Game search | One full 524,288-position batch | Same batch and corpus as the fast GPU profile |
| HotSpot | 1,024 × 1,024 grid, 100 steps | Preserve the larger memory-access workload |
| Shared-graph BFS | 262,144 vertices | Preserve the larger irregular shared-graph workload |

Input sizes are fixed, not adapted to the candidate compiler. The historical measurements guide these choices; the native CPU checks verify the changed summation, pricing and UTS variants at both thread counts, alongside game search. Some original single-thread workloads take 7–14 seconds. Budget roughly 9–10 minutes for all 44 configurations with the default one measured repetition, or about 15 minutes with three. These estimates use the completed ten-repetition baseline, which took 34 minutes 45 seconds.

## Single-thread, multicore and scaling results

The readable comparison reports separate geometric-mean speed ratios and ranges for CPU1 and CPU16. Each per-case row shows baseline time, candidate time and percentage change. A thread-scaling table shows CPU1/CPU16 speedup before and after the compiler change. Scaling changes are descriptive: faster single-thread code can reduce the speedup ratio even when multicore time is unchanged. Slowdown flags are based on measured execution time, not the scaling ratio alone.

```sh
uv run --locked bend-bench cpu-report runs/CANDIDATE_ID --baseline baseline-regression.json
```

`regression-report` is the shared CPU/GPU report command; `cpu-report` and `gpu-report` are aliases. Both profiles accept run directories, `summary.json`, portable `regression.json`, or a previous `comparison.json`. CPU and GPU results require separate baselines. Reports and exit statuses follow the [shared comparison rules](FAST_GPU.md#readable-regression-comparisons), including the configurable 10% slowdown flag, visible missing or failed cases, and explicit incompatibility when workloads or measurement policies change. GPU driver/toolkit metadata does not determine compatibility for a CPU-only run; host CPU metadata, used compiler tools, environment and execution policy do.

Every configuration receives a correctness run, one excluded warmup and one measured complete-process execution by default. Use `--repetitions N` to override the TOML count, including `--repetitions 10` to confirm a suspected regression. Reports label runs with fewer than ten measurements as quick screens and retain the requested sample count in saved results. Comparisons require matching repetition policies; use the same count for baseline and candidate. Pricing measures a full process returning one quote, rather than the scorecard's sustained-request boundary. Correctness checks use the same independent saved references as the GPU profile, with the matching first quote for CPU pricing, the saved scalar summation result for the smaller input, and the original BOTS node-count contract for UTS. Full HotSpot grids, BFS distance vectors and game-search answers remain checked.

For a run that survives terminal disconnection:

```sh
systemd-run --user --unit=bend-bench-fast-cpu --property=WorkingDirectory=/code/bend-bench /code/bend-bench/.venv/bin/python -m bend_bench cpu fast /code/bend-bench/fast-cpu.toml
journalctl --user -u bend-bench-fast-cpu -f
```

## Shared implementation

CPU and GPU commands use the same fixture staging, build planning, special-output validation, execution, report generation, portable snapshots and comparison code. CPU-specific data consists of three input overrides and the existing UTS source snapshot. The GPU workload contracts remain unchanged by this refactor. Broad core-count and size sweeps remain separate follow-ups for investigating a regression or assessing a release.
