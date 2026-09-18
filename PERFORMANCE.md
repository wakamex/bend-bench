# Bend performance against parallel baselines

Bend achieves substantial CPU speedup on its vendor benchmarks, but the tested OpenMP implementations usually finish sooner. The naturally recursive UTS port gains no speedup from additional Bend threads on either input. This report compares checked implementations on identical workload inputs; all displayed wall times are medians of ten measured process executions.

The September 17, 2026 run used an AMD Ryzen 9 3950X with 16 physical cores and 32 hardware threads, plus an NVIDIA RTX 3090. The [complete report](benchmarks/2026-09-17/report.md) includes every configuration, compute-region timing where available and peak host RSS. [Methods and provenance](#methods-and-provenance) identify the exact compiler revision and measurement rules.

## Thread scaling and CPU results

Across the 16 workloads, Bend's median speedup over itself is 3.89x at four threads, 7.39x at eight, 13.58x at 16 and 16.99x at 32. The 32-thread point uses SMT, not 32 physical cores. Median parallel efficiency is 84.9% at 16 threads and 53.1% at 32.

OpenMP's median speedup at 16 threads is 14.22x relative to its own one-thread execution, compared with Bend's 13.58x. These thread-scaling ratios measure each implementation against itself; absolute wall times below compare the implementations directly.

At 16 threads, Bend takes 1.32x the OpenMP wall time at the median. It finishes sooner on Game of Life and tree matrix multiplication, 2 of 16 workloads. At 32 threads it wins 3 of 16, with a median Bend/OpenMP time ratio of 1.18. Bend on one thread takes 1.24x the serial C time at the median.

Times below are complete process wall time in seconds. The OpenMP implementations use conventional loops and reductions; sorting uses GNU parallel sort, and Merkle proof extraction reuses a stored tree. Those algorithm and representation changes are part of the baseline comparison, not isolated measurements of scheduler overhead.

| Workload | Serial C, 1 thread | Bend, 1 thread | Bend, 16 threads | OpenMP, 16 threads | Bend, 32 threads | OpenMP, 32 threads | Bend CUDA |
|---|---:|---:|---:|---:|---:|---:|---:|
| Batched 32 by 32 maze BFS | 4.268 | 4.560 | 0.328 | 0.289 | 0.212 | 0.176 | 0.528 |
| Edit distance | 2.617 | 5.865 | 0.406 | 0.183 | 0.230 | 0.147 | 0.314 |
| Independent 4 by 4 Game of Life soup census | 11.858 | 10.879 | 0.742 | 0.824 | 0.583 | 0.728 | 0.135 |
| Independent hash tables | 1.021 | 3.778 | 0.344 | 0.093 | 0.323 | 0.262 | 0.940 |
| K-means | 3.192 | 3.655 | 0.472 | 0.420 | 0.417 | 0.552 | 0.531 |
| Lexer | 1.545 | 4.542 | 0.387 | 0.150 | 0.321 | 0.286 | 1.205 |
| Mandelbrot | 4.628 | 6.023 | 0.442 | 0.333 | 0.379 | 0.660 | 0.159 |
| Merkle tree and proof | 5.010 | 6.831 | 0.505 | 0.180 | 0.372 | 0.157 | 0.142 |
| Three-body ensemble | 7.364 | 8.635 | 0.600 | 0.500 | 0.347 | 0.339 | 0.127 |
| N-Queens | 4.786 | 11.761 | 0.834 | 0.343 | 0.650 | 0.227 | 1.176 |
| Ray tracer | 8.090 | 9.623 | 0.667 | 0.532 | 0.486 | 0.421 | 0.960 |
| Symbolic regression | 4.386 | 5.187 | 0.364 | 0.303 | 0.273 | 0.253 | 0.653 |
| Terrain | 2.599 | 3.157 | 0.239 | 0.182 | 0.205 | 0.171 | 0.271 |
| Tree bitonic sort versus GNU parallel sort | 9.652 | 12.712 | 1.689 | 0.087 | 1.557 | 0.071 | 0.924 |
| Tree matrix multiplication | 5.507 | 4.934 | 0.462 | 0.529 | 0.488 | 0.431 | 0.411 |
| Tree radix sort/deduplication versus GNU parallel sort/deduplication | 4.596 | 5.819 | 0.801 | 0.043 | 0.584 | 0.034 | 0.579 |

The largest 16-thread gaps are sorting: Bend takes 19.4x and 18.5x the OpenMP wall time for bitonic and radix workloads respectively. Good speedup relative to Bend's own one-thread execution does not imply competitiveness with a different parallel algorithm.

## UTS irregular search

UTS generates an irregular tree using SHA-1 state transitions, creating a load-balancing test outside the vendor suite. The Bend port preserves that generator and naturally forks child and sibling recursion without a manual work queue, subtree balancing or scheduler cutoff. It also checks that its termination fuel was not exhausted.

Neither input gets faster at 16 Bend threads: the 4,112,897-node tree takes 0.992 seconds on one thread and 1.049 seconds on 16; the 30,399,117-node tree takes 7.368 and 7.797 seconds. Both are about 6% slower at 16 threads. Canonical BOTS OpenMP reaches 0.351 and 2.263 seconds at 16 threads.

The additional OpenMP variants avoid creating tasks for leaves and switch to sequential recursion at the labeled depth cutoff. All variants are shown below rather than selecting the fastest cutoff independently for each headline. The cutoff variants help the smaller input but scale poorly on the larger tree; they are not uniformly better than canonical BOTS.

| UTS input and node count | Threads | Bend seconds | Canonical BOTS OpenMP seconds | OpenMP cutoff 4 seconds | OpenMP cutoff 16 seconds | OpenMP cutoff 64 seconds |
|---|---:|---:|---:|---:|---:|---:|
| `test`, 4,112,897 nodes | 1 | 0.992 | 0.975 | 0.386 | 0.385 | 0.388 |
| `test`, 4,112,897 nodes | 2 | 0.989 | 0.676 | 0.227 | 0.227 | 0.219 |
| `test`, 4,112,897 nodes | 4 | 0.988 | 0.721 | 0.229 | 0.229 | 0.220 |
| `test`, 4,112,897 nodes | 8 | 1.048 | 0.550 | 0.230 | 0.230 | 0.221 |
| `test`, 4,112,897 nodes | 16 | 1.049 | 0.351 | 0.238 | 0.238 | 0.229 |
| `test`, 4,112,897 nodes | 32 | 1.025 | 0.263 | 0.334 | 0.335 | 0.320 |
| `tiny`, 30,399,117 nodes | 1 | 7.368 | 7.448 | 2.931 | 2.927 | 2.929 |
| `tiny`, 30,399,117 nodes | 2 | 7.367 | 6.086 | 2.862 | 2.862 | 2.862 |
| `tiny`, 30,399,117 nodes | 4 | 7.376 | 5.491 | 2.873 | 2.868 | 2.885 |
| `tiny`, 30,399,117 nodes | 8 | 7.746 | 3.532 | 2.871 | 2.868 | 2.872 |
| `tiny`, 30,399,117 nodes | 16 | 7.797 | 2.263 | 2.971 | 3.001 | 3.058 |
| `tiny`, 30,399,117 nodes | 32 | 7.504 | 2.739 | 4.207 | 4.192 | 4.272 |

Canonical serial C takes 0.407 seconds for `test` and 3.071 seconds for `tiny`. BOTS's input name `tiny` is historical; it is the larger input here. These findings apply to this natural recursive port and these two trees, not every possible Bend implementation of UTS.

## GPU results

Bend CUDA's median speedup over Bend on one CPU thread is 10.84x across the vendor workloads. That comparison measures acceleration over a CPU implementation, not competitiveness with conventional GPU code.

The implemented conventional CUDA comparison is the Game of Life soup census:

| Implementation | Complete process wall time, seconds | Device-sequence event time, seconds | Kernel-only time |
|---|---:|---:|---|
| Bend CUDA | 0.134592 | Not measured | Not measured |
| Conventional CUDA | 0.201333 | 0.014380 | Not measured |

Bend's complete-process time is 33% shorter in this comparison. The conventional CUDA event interval excludes process startup and other host work, so it must not be compared directly with Bend's complete-process time. This packaged run contains no matched kernel-only comparison. It also does not measure a large evolving Game of Life grid: the workload is a balanced batch of independent 4 by 4 toroidal soups.

## Methods and provenance

- Bend 2.0.3 commit: `b9d1352c9f45632447f40a2e927355c92f2be58c`; unmodified evaluation checkout.
- BOTS commit: `2607a695128727a3f6c98754367705443663136d`.
- Toolchain: Bun 1.4.2, Clang 22.1.8, GCC 16.2.1 for GNU parallel sort, CUDA 13.1, NVIDIA driver 610.57.04.
- Release compilation: `-O3 -march=native -ffp-contract=off`. CPU affinity selects 1, 2, 4, 8, 16 and 32 logical CPUs; IDs 0-15 are distinct physical cores. OpenMP binding and thread counts are explicit.
- GPU configuration: RTX 3090 with 24 GiB device memory, Bend heap set to 4 GiB, GPU code prebuilt, 32 host threads for the Bend CUDA cases.
- Each configuration has one correctness execution, one excluded warmup and ten measured executions. All 3,444 executions passed their output contracts; 2,870 are timing samples across 287 configurations. Compilation is separate from process wall time.
- Vendor checks use the release's published output pins. UTS checks exact node counts and zero Bend fuel exhaustion. Passing these checks is not a proof of compiler correctness.
- Aggregate ratios are calculated per workload from unrounded medians, then summarized using the median of those 16 ratios. Workloads receive equal weight. Values in the tables are rounded only for display.
- The packaged suite started after the earlier evaluation finished. Configurations ran sequentially, without deliberate overlap between benchmark jobs. This was one host session with a fixed run order, not randomized independent sessions or an exclusively reserved machine; close timing differences need confirmation.

The [full configuration report](benchmarks/2026-09-17/report.md) is a preserved copy of this run's generated report. The local raw evidence remains under `runs/64b53b136d7cfde4ed9e/`, which is excluded from Git. It includes `samples.jsonl`, `summary.json`, exact commands, source and binary hashes, toolchain metadata and build logs. The full research assessment and its separate proof and kernel-profile evidence remain in `/code/bend2`; their timings are not mixed into this summary.

| Evidence identifier | Value |
|---|---|
| Run directory ID | `64b53b136d7cfde4ed9e` |
| Prepared experiment fingerprint | `724334600b9aa1af788d719fb4610d96c541ffcb0f107682f1804dfe2d57ff5a` |
| Raw sample log SHA-256 | `d3a43beae4c7ece4f1cfadcfc71bb60ec9c44ec897fc7f7c594b7682228898c9` |
| Summary JSON SHA-256 | `24d7a4c93a712ef1b42406bb2401c0d991a80aa5337c25414d65842fb9b8b68d` |
| Preserved full report SHA-256 | `fe0f740653aef8ca09ca3cc07f0fa7b58016df2e4a573e371fffc436d8801005` |

## Remaining comparisons

The existing baselines are conventional implementations, not a claim of exhaustive tuning. This hardware does not test reproduction of the promotional Apple M4 Max timings. The vendor BFS is a batch of independent small maze searches, so a large-graph BFS test remains necessary. Further BOTS programs, GAP, PBBS, Rodinia, additional conventional GPU implementations, matched kernel timings, device peak memory, Metal, proof-system correspondence and controlled AI-coding trials remain outside this packaged result.
