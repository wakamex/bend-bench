# Local validation

The application extension passes 35 tests, with three skips, including the real Bend/JavaScript comparisons against independent small-input oracles and real OpenMP/CUDA compiler source checks. The queued job explicitly enables the skipped native CPU/CUDA application smoke test before preparing the full 182-configuration sweep. The other skips are the inactive legacy-service test and the separately exercised GPU-contention probe. Both source distribution and wheel build successfully. Native application performance remains pending the queue gates.

The CUB and HotSpot extension builds successfully, and 23 automated tests pass with one environment-dependent skip. Tests include the preserved `clang++` invocation, all six primitive reference outputs, float-vector rejection cases and kernel extraction from a real archived Nsight SQLite export. HotSpot CPU development checks pass across all selected sizes and timestep counts. GPU execution remains pending the idle-window queue described in [QUEUE.md](QUEUE.md); successful builds are not counted as GPU correctness or performance evidence.

The resident-aware activity gate adds four tests. Its explicit hardware run passes against the real NVML driver and a three-second CUDA workload, including a foreign workload entirely inside a measured interval that endpoint checks would miss. The foreign workload is correctly rejected despite a correct program output. A separate monitored Nsight execution also passes. Evidence is retained in `runs/gpu-residency-monitor-smoke.jsonl` and `runs/monitor-nsys-5a_z_2di/`. Routine tests skip the opt-in GPU workload; it was run separately with `BEND_BENCH_GPU_TEST=1` before requeueing.

The full packaged suite completed successfully on 2026-09-17 at 20:50 EDT: all 287 configurations and 3,444 executions passed. The package is located at `/code/bend-bench`, separate from the historical evaluation in `/code/bend2`, and does not reuse its timing samples. See [performance results](PERFORMANCE.md) and the [complete configuration report](benchmarks/2026-09-17/report.md).

The unittest suite covers both CLI entrypoints, real Git patch generation and reverse-apply validation, real process output and timeout handling, execution locking, source identity stability, altered-binary rejection, correctness and warmup gates, failure retention, duplicate/foreign sample rejection, reporting and comparison compatibility. A tiny real C executable exercises preparation, checking, ten measurements and a resume that appends no duplicate records.

Workspace acceptance tests read actual archived outputs for all 16 vendor workloads and both Bend and canonical serial BOTS UTS. They also stage the migrated baseline generator and UTS templates. The legacy service overlap gate is tested against the real active systemd user service, including access to the user bus.

The package builds as both a wheel and a source distribution. The wheel contains the baseline generator, static CPU/CUDA baselines and UTS source template. It does not contain downloaded third-party repositories or historical result files.

Fresh builds, correctness checks and repeated measurements completed for all 16 vendor workloads and both configured UTS inputs. A second `run` invocation left the sample log unchanged. Self-comparison returned a ratio of one for every configuration; this validates comparison mechanics, not independent reproducibility. The default experiment preserves exclusion of an active legacy service. Proof-system tests have not yet been migrated.

Maintainer verification commands:

```sh
uv --no-config run --locked python -m unittest discover -s tests -v
uv --no-config build --no-sources
```

This host has a personal uv `exclude-newer` setting. It conflicts with a policy-neutral lock when plain `uv run --locked` inherits that cutoff. The lock intentionally contains no personal cutoff; maintainer verification uses the configured policy-neutral commands above. Public commands in the README remain standard uv commands.
