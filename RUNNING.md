# Running bend-bench

The [README](README.md) covers the quick regression runs. This guide covers everything else: fast-run options, the full harness, the scorecard remeasurements and the startup-scaling sweep.

## Fast regression runs

[Fast GPU regression testing](FAST_GPU.md) runs Bend GPU alone across all 22 workload families, using compact UTS and one full game-search batch. Workloads where Bend's startup would be more than 20% of the run use a larger size. The [CPU regression profile](FAST_CPU.md) covers the same families at one and 16 threads with CPU-appropriate input sizes.

```sh
uv run --locked bend-bench gpu fast
uv run --locked bend-bench cpu fast
```

GPU sharing is allowed by default. Add `--exclusive-gpu` to reject other GPU activity, or `--wait-idle` to wait for an idle GPU and then run exclusively. Use `--repetitions N` for more measurements.

Fast commands collect fresh measurements and save a new run directory each time. `--baseline runs/<id>` compares the new measurements with a saved run; `--resume runs/<id>` explicitly continues an existing run instead.

To compile once and reuse binaries, use `--build-only --output builds/my-build`, then `--build builds/my-build`. See [reusable builds](BUILDS.md) for CPU/GPU examples and integrity checks.

Edit `fast-gpu.toml` or `fast-cpu.toml` to pin the compiler checkout and revision. Add `--baseline runs/BASELINE_ID` or pass a saved `regression.json` to get speed comparisons and flagged slowdowns. `bend-bench regression-report runs/CANDIDATE_ID --baseline runs/BASELINE_ID` compares existing results without rerunning them. CPU reports separate single-thread performance, multicore performance and thread scaling. Results are separate from the scorecard.

## Full harness

Requirements: Linux, uv, Git, `taskset`, GNU time, Bun, Clang and an OpenMP-enabled C++ compiler. GPU runs additionally require a compatible CUDA toolchain and NVIDIA GPU; kernel profiling requires Nsight Systems.

Choose a configuration and edit its source paths, exact commits, tool paths, CPU affinity and workload selection for your machine:

| Configuration | Workloads |
|---|---|
| [experiment.toml](experiment.toml) | Published benchmarks and BOTS UTS |
| [gpu-primitives.toml](gpu-primitives.toml) | CUB sorting and reduction |
| [gpu-hotspot.toml](gpu-hotspot.toml) | Rodinia HotSpot |
| [applications.toml](applications.toml) | Pricing, m,n,k and shared-graph BFS |
| [applications-bfs.toml](applications-bfs.toml) | Corrected BFS comparison alone |
| [nqueens.toml](nqueens.toml) | Bend and C++ bit-mask N-Queens, with serial and OpenMP task variants |
| `scorecard-*.toml` | The scorecard's Bend cells alone, pinned to a newer Bend revision |

The supplied configurations reference the evaluation machine's local source checkouts. Paths resolve relative to the configuration file. Obtain the pinned dependencies and adapt those paths before running; the harness does not download sources or install toolchains.

```sh
uv run --locked bend-bench plan experiment.toml
uv run --locked bend-bench prepare experiment.toml
uv run --locked bend-bench check experiment.toml
uv run --locked bend-bench run experiment.toml
uv run --locked bend-bench report runs/RUN_ID
```

`plan` previews commands without executing the workloads. `prepare` builds into a fingerprinted run directory. `check` verifies every selected configuration's output. `run` requires those checks, excludes warmups and collects at least ten measurements. `report` summarizes saved evidence. The CLI is also available through `python -m bend_bench`.

For a smaller CPU experiment, select `suites = ["uts"]` and `uts_inputs = ["test"]` in the configuration. That BOTS input has 4,112,897 nodes; the upstream input named `tiny` is larger, at about 30 million nodes.

GPU kernel profiling is a separate stage after unprofiled measurements pass:

```sh
uv run --locked bend-bench profile applications-bfs.toml --nsys /path/to/nsys
uv run --locked bend-bench report runs/RUN_ID
```

## Comparing Bend revisions

[scorecard_paired_cpu.py](scorecard_paired_cpu.py) runs the scorecard's archived Bend binaries and a newer revision's binaries alternately under the same load, after the `scorecard-*.toml` runs have built them. The [Bend 2.0.26 comparison](BEND_2_0_26.md) uses it.

## Startup-scaling sweep

[startup_scaling.py](startup_scaling.py) grows one work knob per GPU workload until the conventional program's startup stops dominating, and [scaling_fit.py](scaling_fit.py) and [scaling_charts.py](scaling_charts.py) turn the runs into the fits and charts in [Startup scaling](STARTUP_SCALING.md):

```sh
uv run --locked --with numpy --with scipy python startup_scaling.py --workloads mandelbrot
uv run --locked --with numpy --with scipy python scaling_fit.py
uv run --locked --with matplotlib --with numpy --with scipy python scaling_charts.py
```
