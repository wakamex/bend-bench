# bend-bench

A reproducible benchmark harness comparing [Bend](https://github.com/bendlang/bend)'s automatic parallel execution with OpenMP on CPU and CUDA on GPU. It checks answers, sweeps thread counts and input sizes, and records exact source revisions, build commands and individual measurements.

Bend makes it possible to use multiple CPU cores and a GPU from the same program, but the implementations tested here usually finish behind conventional parallel code. CPU scaling is its strongest result: on its published benchmarks, Bend gets almost as much speedup from 16 CPU threads as OpenMP does. GPU portability works, but pricing and graph traversal finish sooner on Bend's CPU backend at the tested sizes. Adding alpha-beta pruning brings its CPU game search close to the conventional implementation on these small endgame batches.

For someone choosing a language, Bend looks promising for writing parallel programs conveniently, but these results do not support choosing it for a performance advantage over established parallel implementations. This evaluation has not measured whether that convenience saves enough development effort to offset the performance gap.

## Results

Bend scales well across CPU cores on its published workloads, but conventional parallel implementations usually finish sooner. Its GPU backend accelerates the published Game of Life workload, while pricing and shared-graph BFS finish sooner on its 16-thread CPU backend at every tested input size.

These September 17–18, 2026 measurements use a Ryzen 9 3950X with 16 physical cores and 32 hardware threads, plus an RTX 3090. Results are medians of ten measured executions after correctness checks and warmups. The wall times below include startup, input preparation, transfers and output.

- CPU scaling: on Bend's 16 published workloads, Bend achieves 13.6× median speedup at 16 CPU threads relative to its own one-thread execution; OpenMP achieves 14.2× relative to its own. At 16 threads, Bend takes 32% longer than OpenMP at the median and wins 2 of 16 comparisons.
- Irregular recursive work: the Bend port of BOTS Unbalanced Tree Search gains no speedup on either tested tree. The canonical OpenMP implementations finish about 3.0× and 3.4× sooner at 16 threads.
- N-Queens: giving both languages bit-mask search reverses the earlier Bend win against BOTS. Enumerating all 365,596 solutions for 14 queens takes 224 ms in Bend versus 14 ms in OpenMP at 16 threads. [Results and implementation details](NQUEENS.md).
- Game search: alpha-beta pruning cuts Bend's 5×5 connect-4 batch from 17.6 ms to 3.14 ms at 16 CPU threads, alongside OpenMP's 3.34 ms. One-thread Bend is faster still at 2.68 ms: pruning leaves too little work in these batches to benefit from more threads. [Before-and-after results](MNK_RESULTS.md).
- Sustained game search: the corrected matched comparison delivers 1.20 million positions/second on Bend GPU, versus 837,000 with OpenMP16, 537,000 on Bend CPU16 and 435,000 with the project-written CUDA control. Each implementation ran in three fresh processes in shuffled order, using 524,288-position batches. The earlier CUDA-control comparisons are withdrawn because a filename collision made that label run Bend. [Corrected results, variability and audit](MNK_SUSTAINED.md).
- CPU-to-GPU portability: the pricing, exact game-search and shared-graph BFS ports run correctly on both backends. Using the GPU does not shorten the complete run for any tested pricing or BFS size. GPU performance of the improved game-search port has not been remeasured.
- GPU baselines: Bend beats the CUDA Game of Life implementation written for this project end-to-end, 0.135 versus 0.201 seconds. For 8,388,608-key sorting, NVIDIA CUB finishes in 0.192 seconds versus Bend's 0.937 seconds. CUB is much faster at summing the numbers. Bend starts up faster, which lets it finish this short test sooner.

Time to price an option, solve a batch of game positions, or find distances through a graph:

| Task and amount of work | Bend CPU, 16 threads | Conventional CPU, 16 threads | Bend GPU | Conventional GPU | Conventional baselines |
|---|---:|---:|---:|---:|---|
| Price an arithmetic Asian call using 262,144 simulated paths with 256 observations each | 0.228 s | 0.122 s | 0.262 s | 0.206 s | Project-written OpenMP and CUDA simulation; CUB payoff reduction |
| Solve 16 connect-4 endgames on a 5×5 board, each with eight empty squares | 0.00314 s | 0.00334 s | Pending remeasurement | Pending paired rerun | Alpha-beta in Bend and project-written OpenMP/CUDA controls |
| Find shortest-path distances from one vertex in a graph with 262,144 vertices and about 2.1 million directed edges | 2.83 s | 0.257 s | 11.24 s | 0.812 s | GAP OpenMP and Gunrock CUDA |

For the graph task shown, Bend GPU takes about 4× its own CPU time and 13.8× Gunrock's total time. Pricing is closer to the conventional CUDA implementation. The detailed reports include smaller jobs, where startup costs can change which GPU implementation finishes first. Bend's BFS uses immutable trees against conventional graph representations.

Detailed results:

- [All 16 published workloads and BOTS UTS](PERFORMANCE.md): CPU scaling, absolute timings and baseline choices; [complete configuration report](benchmarks/2026-09-17/report.md).
- [CUB sorting and reduction](runs/e930e5a1b9c488a9f8ba/report.md): end-to-end and kernel timings.
- [Pricing and historical exhaustive game search](runs/486e78825d4fa285adcc/report.md): all sizes and CPU thread counts. [Updated alpha-beta game search](MNK_RESULTS.md) supersedes those game-search CPU results.
- [Corrected BFS summary](BFS_RESULTS.md) and [full report](runs/6f09d7ec9215cbadd596/report.md): all 42 configurations and GPU profiles passed. Use this report for BFS; the earlier combined report's Bend BFS cases did not launch GPU kernels.
- [Rodinia HotSpot](runs/c058f6b3293bda1d65dd/report.md): all 54 configurations passed correctness and unprofiled timing; GPU profiling remains incomplete.

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
