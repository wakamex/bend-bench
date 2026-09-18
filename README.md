# bend-bench

A reproducible benchmark harness comparing [Bend](https://github.com/bendlang/bend)'s automatic parallel execution with OpenMP on CPU and CUDA on GPU. It checks answers, sweeps thread counts and input sizes, and records exact source revisions, build commands and individual measurements.

Bend can use multiple CPU cores and a GPU from the same program. In these tests it scales well on its published CPU workloads, and its GPU backend speeds up sustained game search. Conventional parallel implementations usually finish sooner.

This evaluation measures execution speed and correctness against conventional parallel implementations. It does not measure development effort or the benefits of Bend's proof system.

## Results

These September 17–18, 2026 measurements use a Ryzen 9 3950X with 16 physical cores and 32 hardware threads, plus an RTX 3090. Answers are checked against published outputs or independent reference implementations before results are accepted.

### CPU scaling

On Bend's 16 published workloads, using 16 CPU threads gives Bend a median 13.6× speedup over its own one-thread execution; OpenMP gains 14.2× over its own. Similar scaling does not mean equal running time: at 16 threads, Bend takes 32% longer than OpenMP at the median and wins 2 of 16 comparisons. The added irregular-tree search from BOTS shows a different pattern: Bend gains no speedup on either tested tree, while OpenMP finishes about 3.0× and 3.4× sooner at 16 threads. [CPU results and thread-count sweeps](PERFORMANCE.md).

### Game search on CPU and GPU

The GPU makes Bend's exact game search faster: a matched comparison measured 86% more answers per second than Bend CPU16. OpenMP on 16 CPU threads provides 35% more answers per second than Bend GPU, while Bend beats the strongest CUDA implementation written for this project.

| Implementation | Exact endgame positions solved per second |
|---|---:|
| OpenMP, 16 CPU threads | 2.32 million |
| Bend GPU | 1.72 million |
| Project-written CUDA, root-parallel search with literal win checks | 872,000 |

Each batch repeats 1,024 distinct 5×5 connect-4 endgames, each with eight empty squares, to 524,288 positions. Timing includes solving them and making every answer available in a CPU-memory array; formatting and validation happen afterward. Results are medians across three fresh processes, each with two warmups and 30 measured batches. [Full comparison, CPU-to-GPU scaling and methods](MNK_HOST_ARRAY.md).

### Pricing, graph traversal and GPU primitives

Moving a Bend program to the GPU does not always help. Pricing and shared-graph BFS finish sooner on Bend CPU16 at every tested input size. Conventional parallel implementations also finish sooner in the examples below.

Complete-run time to price an option or find distances through a graph, including startup, input preparation, transfers and output:

| Task and amount of work | Bend CPU, 16 threads | Conventional CPU, 16 threads | Bend GPU | Conventional GPU | Conventional baselines |
|---|---:|---:|---:|---:|---|
| Price an arithmetic Asian call using 262,144 simulated paths with 256 observations each | 0.228 s | 0.122 s | 0.262 s | 0.206 s | Project-written OpenMP and CUDA simulation; CUB payoff reduction |
| Find shortest-path distances from one vertex in a graph with 262,144 vertices and about 2.1 million directed edges | 2.83 s | 0.257 s | 11.24 s | 0.812 s | GAP OpenMP and Gunrock CUDA |

These complete-run times are medians of ten measured executions after warmups. For the graph shown, Bend GPU takes about 4× its own CPU time and 13.8× Gunrock's total time. Bend uses immutable trees where the conventional baselines use graph arrays. See the [pricing measurements](runs/486e78825d4fa285adcc/report.md) and [BFS results](BFS_RESULTS.md) for size sweeps and implementation details.

Mature GPU primitives provide a stronger baseline than serial C: NVIDIA CUB sorts 8,388,608 keys in 0.192 seconds end-to-end versus Bend's 0.937 seconds. CUB also sums numbers much faster during computation; Bend's shorter startup can make it finish a short reduction job sooner. [Sorting and reduction measurements](runs/e930e5a1b9c488a9f8ba/report.md). The suite also includes [Rodinia HotSpot thermal simulation](runs/c058f6b3293bda1d65dd/report.md), whose correctness and unprofiled measurements passed; GPU profiling remains incomplete.

## Workloads and comparison strength

| Workloads | Purpose | Baselines |
|---|---|---|
| Bend's 16 published benchmarks | Reproduce supplied inputs and test CPU scaling | Serial C and OpenMP implementations written for this project, plus its CUDA Game of Life implementation |
| BOTS Unbalanced Tree Search | Irregular recursive task creation and load balancing | Canonical BOTS OpenMP task implementations and labeled cutoff variants |
| Sorting and reduction | Compare recursive programs with mature GPU primitives | NVIDIA CUB |
| Asian-option pricing | Independent Monte Carlo paths followed by payoff aggregation | Project-written OpenMP and CUDA implementations using identical random streams |
| Exact m,n,k endgames | Recursive search with known outcomes from an independent solver | Project-written OpenMP and CUDA alpha-beta implementations |
| N-Queens | Enumerate all solutions with bit-mask search in both languages | Project-written serial C++ and OpenMP task implementations; [comparison contract](NQUEENS.md) |
| Shared-graph BFS | Irregular graph traversal and memory access | GAP OpenMP and Gunrock CUDA |
| HotSpot thermal simulation | Repeated local-neighbor updates | Rodinia OpenMP and CUDA, with CUDA pyramid-height variants |

Pricing tests a prescribed set of simulated paths; variance reduction and time to a target pricing accuracy are outside this comparison.

Bend's published BFS batches independent small mazes, whereas the added BFS traverses one shared graph. Its published Game of Life benchmark counts independent 4×4 soups. See [application contracts](APPLICATIONS.md) and [CUB/HotSpot contracts and source corrections](GPU_COMPARISON.md) for input definitions, arithmetic, algorithms and preserved patches.

## Run a benchmark

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

## Measurement and reproducibility

CPU scaling sweeps 1, 2, 4, 8, 16 and 32 threads where configured; the 32-thread point uses SMT. Release builds use `-O3` and native CPU architecture flags. Output checks use published expected results or independent references; the applications check every payoff, game outcome or graph distance.

The largest BFS GPU trace contains compute launches of 64 blocks × 128 threads = 8,192 threads. Raw report labels such as `bend-cuda/32` identify the host CPU worker setting; CUDA launch dimensions are recorded in the profiler traces.

End-to-end wall time, instrumented CPU compute time, CUDA event intervals and Nsight kernel-duration sums are distinct measurements. Event intervals can contain gaps between kernels. Profiled wall times never replace unprofiled measurements. Peak host RSS is recorded; peak device memory is not measured.

Application runs permit GPU activity from the approved transcription service and record observed processes and activity. Earlier experiments used stricter GPU admission rules. Per-run configuration and evidence preserve these differences; results from different runs are not pooled. [Validation notes](VALIDATION.md) and [execution history](QUEUE.md) document completed checks and interruptions.

Each run preserves source revisions and patches, configuration, tool identities, build logs, generated sources, binary hashes, linked-library hashes, individual samples and a report. Changing these inputs creates a new identity or invalidates preparation. Keep source checkouts available for rebuilding.

An unchanged run resumes without duplicating completed measurements. Failed samples remain in the evidence and keep that configuration failed; use a new experiment label to investigate it. Preparation and measurement share an execution lock, and configured blocked services prevent overlap with other benchmark jobs.

To benchmark a compiler fix, set `bend.path` and the exact HEAD commit. Enable `allow_patch = true` for tracked changes and stage new files so their contents enter the preserved diff. Compare compatible runs with:

```sh
uv run --locked bend-bench compare runs/BEFORE runs/AFTER
```

Comparisons require matching host, workload contract and measurement policy. Different Bend revisions are allowed. Ratios are descriptive comparisons, not statistical significance tests.

## Remaining scope

Additional BOTS programs, broader GAP and PBBS workloads, Metal, controlled AI-coding trials and proof-system validation remain outstanding. Historical proof checks have not been migrated into this harness.

## Development and license

```sh
uv run --locked python -m unittest discover -s tests -v
```

Tests cover CLI entrypoints, provenance, output validation, failure retention, resume behavior and reporting. Opt-in native checks exercise CPU/CUDA backends and verify that Bend BFS actually launches GPU kernels.

The harness is [MIT-licensed](LICENSE). Bend-derived portions retain Apache-2.0 licensing, and external dependencies retain their own licenses. See [source attribution](THIRD_PARTY_NOTICES.md).
