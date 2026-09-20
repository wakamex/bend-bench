# bend-bench

The [Bend](https://github.com/bendlang/bend) programming lanauage lets you run the same code in parallel on CPU and GPU. This benchmark compares performance with OpenMP on CPU and CUDA on GPU. Bend's main benefit is verifiability, being fast is just a perk.

## Benchmark choice

Performance depends much more on the implementation than the language it was written in. Comparing implementations across languages can be tricky, as each language allows different optimizations. We compare against existing benchmarks and new implementations as well.

We compare Bend’s 16 published workloads with added parallel baselines written by GPT-6-Astra in C and OpenMP.

Additional benchmarks are chosen to span a few interesting dimensions:
- Pricing and game search contrast predictable independent work with uneven, decision-dependent work.
- HotSpot and BFS contrast regular local communication with irregular shared-data access.
- Sorting and summation from NVIDIA’s [CUB](https://github.com/NVIDIA/cccl/tree/main/cub) library compare to highly optimized primitives.
- Unbalanced Tree Search from [BOTS](https://github.com/bsc-pm/bots) tests Bend's [documented limitation](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/README.md#limitations) that "Parallelism requires balanced calls. Flexible parallelism will be added later."

Not tested: dense linear algebra, FFTs, database operations

## Results

On Bend’s 16 published workloads, moving from one to 16 CPU threads gives Bend a median 13.6× speedup, compared with OpenMP’s 14.2×. Bend takes 32% longer than OpenMP at 16 threads at the median. [CPU results](/code/bend-bench/PERFORMANCE.md). For sorting, we also compare against NVIDIA’s CUB library, which finishes 4.9× faster than Bend GPU. [GPU sorting results](runs/e930e5a1b9c488a9f8ba/report.md).

Option pricing on an RTX 3090 is 68× faster than on a 3950x. Our CUDA implementation is another 7.2× faster than Bend GPU. [Pricing results](/code/bend-bench/PRICING_SUSTAINED.md).

For alpha-beta game search, Bend GPU is 1.9× faster than Bend on 16 CPU threads and 2.0× faster than our fastest CUDA implementation. OpenMP on 16 CPU threads is 1.3× faster than Bend GPU. [game-search results](/code/bend-bench/MNK_HOST_ARRAY.md).

Irregular work is harder. Bend gains no CPU speedup on either UTS input. [UTS results](/code/bend-bench/PERFORMANCE.md#uts-irregular-search).

Rodinia’s CUDA implementation finishes HotSpot sooner than Bend GPU. Gunrock also finishes BFS sooner on the two larger graphs, while Bend finishes sooner on the smallest. HotSpot comparison (GPU_COMPARISON.md), BFS results (BFS_RESULTS.md).

## Takeaways

Bend GPU does better on shorter tasks, which benefit from its faster load time compared to CUDA.

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
