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

On a shared host, `cpu_idle = {max_busy = 3.0, max_wait = 21600}` holds each sample until the configured CPUs carry at most three CPUs of other work, measured over 5 seconds, and stops the run if that takes more than six hours; `run` then resumes where it stopped. Each sample records the busy count it started at and how long it waited. Load that arrives during a sample is not detected.

For a smaller CPU experiment, select `suites = ["uts"]` and `uts_inputs = ["test"]` in the configuration. That BOTS input has 4,112,897 nodes; the upstream input named `tiny` is larger, at about 30 million nodes.

GPU kernel profiling is a separate stage after unprofiled measurements pass:

```sh
uv run --locked bend-bench profile applications-bfs.toml --nsys /path/to/nsys
uv run --locked bend-bench report runs/RUN_ID
```

## Machine-learning suite

`uv run --locked bend-bench run ml.toml` times bend-ml's GPT-2, nanoGPT, MNIST and matrix-product programs against PyTorch. It needs a pinned bend-ml checkout, its data and a Python with PyTorch; [ML.md](ML.md) covers the setup.

## Comparing Bend revisions

Before benchmarking a compiler change, check it against the checkout it changes. `compiler-check` emits C, JS and MJS for every fast-profile port, the generated compile-stress programs, and both checkouts' demos and tests, then builds and runs every test with a `#|` expectation:

```sh
uv run --locked bend-bench compiler-check ../bend-base ../bend-candidate --bun ../bend2/tools/bun-linux-x64/bun --output check.json
```

It lists the programs whose output changed and the tests whose status changed, and exits 1 when a test passes with the base but not with the candidate. It also compares compile time. After the parallel pass, one Bun process loads both compilers and times checking and C emission of every program both checkouts compile, inside the process, so Bun's startup and module loading drop out. Each program runs base, candidate, candidate, base, with nothing else compiling. The report totals checking and emission over the corpus, and lists every program the candidate takes 1.25x as long on and at least 50 ms longer; a small program varies by tens of milliseconds from run to run. Comparing a checkout with itself on the benchmark host gives totals of 0.998x and 1.014x, with no program listed. The timing adds about six minutes to a full check. Add `--identical` for a refactor, which should change no output at all. `--only REGEX` limits it to matching program paths. A full check takes about five minutes on the benchmark host.

To time the change, `paired` takes two fast-profile experiment files that pin the base and candidate checkouts, builds both, and times only the workloads whose compiled program differs. A workload with the same GPU program (past the key naming its source) and the same host machine code (addresses aside) on both sides cannot change speed, so it is reported as not timed; an edit that compiles to nothing, such as an unused `#define`, changes only the source copy the binary embeds:

```sh
uv run --locked bend-bench paired base.toml candidate.toml --workloads raytrace,editdist --blocks 10
```

After a correctness check and a warmup on each side, every workload runs in blocks of four processes, base (A) and candidate (B) as A B B A, then B A A B in the next block. Both versions sit at the same mean position in a block, so a background load that rises or falls steadily through it cancels exactly in the block's score, (A1 + A2) / (B1 + B2), where above 1x means the candidate is faster. The report gives the median block score and a 95% bootstrap interval of that median, both from the session's own blocks, so the interval reflects the load the comparison actually ran under. `--workloads` restricts the comparison to named workloads. Results go to `runs/paired-*/` (`samples.jsonl`, `summary.json`, `report.md`).

[scorecard_paired_cpu.py](scorecard_paired_cpu.py) runs the scorecard's archived Bend binaries and a newer revision's binaries alternately under the same load, after the `scorecard-*.toml` runs have built them. The [Bend 2.0.26 comparison](BEND_2_0_26.md) uses it.

## Startup-scaling sweep

[startup_scaling.py](startup_scaling.py) grows one work knob per GPU workload until the conventional program's startup stops dominating, and [scaling_fit.py](scaling_fit.py) and [scaling_charts.py](scaling_charts.py) turn the runs into the fits and charts in [Startup scaling](STARTUP_SCALING.md):

```sh
uv run --locked --with numpy --with scipy python startup_scaling.py --workloads mandelbrot
uv run --locked --with numpy --with scipy python scaling_fit.py
uv run --locked --with matplotlib --with numpy --with scipy python scaling_charts.py
```
