# CUB and Rodinia GPU comparison

The question is whether Bend's automatic parallel execution is competitive with established GPU implementations on the same problem. The new comparisons use NVIDIA CUB for sorting and reduction, and Rodinia HotSpot for a complete stencil application. GPU correctness and performance results are pending an uncontended RTX 3090 window. CPU development checks already pass for the HotSpot port at every selected size and timestep count.

## Comparison contracts

| Workload | Bend implementation | Conventional implementation | Inputs and outputs |
|---|---|---|---|
| Unsigned integer sorting | Vendor tree-bitonic source, changing only depth | CUB DeviceRadixSort::SortKeys, followed by sortedness/checksum reduction | 4,096, 262,144 and 8,388,608 identical generated U32 keys; vendor order-sensitive checksum and sortedness checks; CUB correctness stage additionally compares every sorted value with std::sort |
| Unsigned integer reduction | Balanced recursive generation and wrapping-U32 sum | CUB DeviceReduce::Sum over a transformed counting iterator | Same three sizes and key generator; wrapping-U32 sum checked against an independent serial reference |
| HotSpot thermal stencil | Balanced row/grid trees, cached boundary values, recursive parallel branches | Rodinia 3.1 CUDA shared-memory kernel at pyramid heights 1, 2 and 4; corrected Rodinia OpenMP at one and 16 threads | Original 64 × 64, 512 × 512 and 1,024 × 1,024 temperature/power inputs, each for 10 and 100 timesteps; every output cell checked |

CUB is the primary primitive-performance reference. Its radix sort is an algorithmic alternative to Bend's bitonic sort, so this measures the best available library approach among the implementations tested, rather than language overhead with a fixed algorithm. Neither a library nor an established suite establishes a universal optimal-performance bound. Rodinia adds an application-level comparison and an explicit sweep of its time-blocking parameter; all variants remain visible in the detailed report.

## Timing and validation

Each configuration has one correctness execution, one excluded warmup and ten measured process executions. Release builds use `-O3`, native CPU architecture flags, CUDA `sm_86` and disabled floating-point contraction. End-to-end time includes process creation, device initialization, input preparation or parsing, transfers, computation and output. HotSpot emits all output float bit patterns on every backend. Its end-to-end result therefore includes full-result serialization; the separate kernel timings expose compute performance.

CUDA events in conventional adapters measure the device sequence, which can include gaps between kernels. The `profile` stage separately collects one warmup and ten Nsight executions and sums recorded CUDA kernel durations. Profiled process wall times are never substituted for unprofiled end-to-end measurements. Host peak RSS is recorded; device peak memory is not measured.

The CUB workloads generate their inputs inside the program on both sides. Reduction fuses generation into its iterator, matching Bend's generation-and-sum workload. Sorting includes generation, sorting and checksum work in its device sequence. HotSpot reads the same archived text inputs; CUDA input transfers and Bend data conversion/transfers are included in end-to-end time.

HotSpot uses Rodinia CUDA's physical coefficients, timestep and clamped boundaries. Bend uses F32 arithmetic; the CUDA kernel retains its upstream mixed-precision intermediates. Validation rejects missing values, nonfinite values and cells whose absolute error exceeds `0.0001 + 0.000001 * abs(reference)`. The tolerance is fixed before GPU measurements. The CPU reference is a direct scalar stencil, independent of the blocked and tree implementations.

The Bend GPU annotation covers the entire simulation loop, so the port does not request a separate host/device round trip on each timestep. Parallel work is expressed with recursive branch pairs; the port supplies no work queue, thread assignment, task cutoff or GPU launch geometry.

## Rodinia correctness corrections

The unmodified OpenMP implementation leaves `delta` unchanged for interior cells of a tile touching the grid boundary. A deterministic 64 × 64, one-timestep counterfactual produced 2,820 erroneous boundary-tile cells and zero erroneous interior-tile cells. Its maximum absolute error was 0.0196647644. The reproduced diagnostic is `assets/gpu/hotspot-audit.cpp`; the captured execution is in `runs/hotspot-development/development.jsonl`.

The generated OpenMP patch adds the missing interior-cell branch. The replacement driver also uses CUDA's timestep, because the original OpenMP driver divides it by an additional 1,000. The CUDA compute source is included unchanged. Generated source, the exact boundary patch, coefficient values and independent expected outputs are retained in every prepared run.

After correction, all cells pass at the three stock sizes after ten timesteps, with maximum absolute OpenMP errors of 0.0000305176, 0.0000305176 and 0.0000610352. Bend matches the scalar reference bit-for-bit on the 64 × 64, ten-step check. Additional development checks pass for Bend at all six size/timestep combinations on 16 CPU threads. These are correctness checks, not published timing results.

## Pinned sources

- Bend 2.0.3: `b9d1352c9f45632447f40a2e927355c92f2be58c`, archived in `/code/bend2/upstream`.
- NVIDIA CCCL v3.1.0: `ecfd3adfaa7ebcb81d80d5b297ab3551619fda02`, archived in `/code/bend2/cccl`. The build checkout is `sources/cccl-clang`. Its [four-line compatibility patch](patches/cccl-clang-deduction-guides.patch) changes libcu++ deduction-guide annotations for Clang 22; CUB algorithms remain unchanged.
- [Rodinia 3.1 original archive](https://www.cs.virginia.edu/~skadron/lava/Rodinia/Packages/rodinia_3.1.tar.bz2): SHA-256 `faebac7c11ed8f8fcf6bf2d7e85c3086fc2d11f72204d6dfc28dc5b2e8f2acfd`, stored at `/code/bend2/sources/rodinia_3.1.tar.bz2`, with selected sources and stock inputs in `/code/bend2/rodinia/rodinia_3.1`.

Run provenance records actual source-file hashes, patches, compiler/toolkit identities, generated sources, binaries and linked-library hashes. The setup uses Clang 22.1.8, GCC 16.2.1 and CUDA 13.1. Attribution and licensing are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Reproduction

The supplied local configurations are [gpu-primitives.toml](gpu-primitives.toml) and [gpu-hotspot.toml](gpu-hotspot.toml). Edit paths for another machine. The commands do not download dependencies or modify archived sources. When using a fresh CCCL v3.1.0 checkout with Clang 22, apply the preserved compatibility patch and leave `allow_patch = true` so the patch is included in provenance.

```sh
uv run --locked bend-bench prepare gpu-primitives.toml
uv run --locked bend-bench check gpu-primitives.toml
uv run --locked bend-bench run gpu-primitives.toml
uv run --locked bend-bench profile gpu-primitives.toml --nsys /usr/local/cuda-13.1/bin/nsys
```

Repeat with `gpu-hotspot.toml`. The configured resident model may retain its GPU memory while idle. Its PID, process start time and host boot ID are pinned; actual memory bytes and GPU UUID are saved in `gpu-wait.jsonl` and each execution's `gpu_activity` record. The queue requires 120 seconds of sampled inactivity. During execution, NVML observations every 250 ms detect work by that resident and reject foreign compute contexts, while allowing the benchmark's own process tree. A 1.1-second post-execution counter-drain delay is outside the measured wall time. Unknown processes, changed resident identity and unavailable telemetry block execution; detected contention invalidates the sample. Sampling can miss very brief bursts, so these results describe monitored shared residency rather than guaranteed hardware exclusivity. The harness never stops another workload or automatically retries a failed sample.
