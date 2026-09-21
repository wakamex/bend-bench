# Published-workload CUDA results

CUDA finishes sooner on eight of the eleven newly implemented comparisons. Bend finishes sooner on Mandelbrot, Merkle trees and the three-body ensemble. The largest CUDA advantages are lexer at 6.2× and ray tracing at 5.0×. Every new implementation passed full-output checks on four inputs, followed by one warmup and ten measured executions of the published input on an RTX 3090.

These eleven comparisons, the [three GPU library adapters](VENDOR_GPU_LIBRARIES.md), Game of Life and CUB sorting fill the conventional GPU column for all sixteen published workloads in the [scorecard](benchmarks/summary/index.html).

## Complete-program results

| Workload | Bend GPU, complete program | CUDA, complete program | Faster implementation | CUDA device sequence |
|---|---:|---:|---|---:|
| Mandelbrot | 0.159 s | 0.187 s | Bend 1.2× | 0.780 ms |
| N-Queens | 1.176 s | 0.582 s | CUDA 2.0× | 367.002 ms |
| Merkle tree and proof | 0.142 s | 0.191 s | Bend 1.3× | 2.313 ms |
| Lexer | 1.205 s | 0.193 s | CUDA 6.2× | 4.988 ms |
| K-means | 0.531 s | 0.255 s | CUDA 2.1× | 67.018 ms |
| Independent hash tables | 0.940 s | 0.308 s | CUDA 3.1× | 123.705 ms |
| Batched maze BFS | 0.528 s | 0.206 s | CUDA 2.6× | 16.111 ms |
| Three-body ensemble | 0.127 s | 0.189 s | Bend 1.5× | 3.266 ms |
| Ray tracing | 0.960 s | 0.194 s | CUDA 5.0× | 6.281 ms |
| Terrain | 0.271 s | 0.197 s | CUDA 1.4× | 11.013 ms |
| Symbolic regression | 0.653 s | 0.189 s | CUDA 3.4× | 1.994 ms |

Bend measurements come from the September 17 run `64b53b136d7cfde4ed9e`; the new CUDA measurements come from September 21 run `d5ad0d88f32d6e50f6a7`. All eleven source hashes and output contracts match between those runs. Bend used 32 host threads and the CUDA adapters used one host thread on the same Ryzen 9 3950X / RTX 3090 machine. GPU lane counts are independent of those host-thread settings.

Complete-program time includes startup, input generation, allocations, transfers, required results and cleanup. Several CUDA programs finish their device work in a few milliseconds but take around 0.19 seconds overall. Bend's complete-program wins above therefore do not establish faster GPU computation.

CUDA-event intervals appear separately as device-sequence time. Their boundaries follow each adapter's event markers: for example, N-Queens includes task uploads and result downloads, while maze BFS sums per-batch kernel intervals and excludes downloads. They are not uniformly kernel-only measurements; separate kernel profiling remains pending.

## Implementations and correctness

All eleven CUDA adapters are project-written. They retain the published inputs and required outputs while using conventional GPU layouts and scheduling.

| Workload | CUDA implementation and full-output check |
|---|---|
| Mandelbrot | Independent fixed-point escape calculations; compare every pixel's escape count and the weighted histogram. |
| N-Queens | Expand selected four-row prefixes by three more rows, then search subtrees with device stacks; compare both solution and visited-node counts for every original prefix. |
| Merkle tree | Parallel Speck leaves and stored tree levels, followed by audit and proof calculations; compare leaves, internal hashes, audits and proof results. |
| Lexer | One lane per generated line, with ordered token folding; compare every line's result. |
| K-means | Cache generated points and reduce integer cluster statistics; compare every centroid at every iteration and preserve tie and empty-cluster rules. |
| Hash tables | Open addressing with separate accounting for the original logical buckets; compare bucket lengths, lookups and per-table checksums. |
| Batched maze BFS | One warp per maze with bitset frontiers; compare every cell's distance, including unreachable cells. |
| Three-body ensemble | Original arithmetic per independent system, with correctly rounded square roots; compare every system's energy bucket and position digest. |
| Ray tracing | Original intersections, shading and reflections per pixel, with correctly rounded square roots; compare every quantized pixel. |
| Terrain | Diagonal wavefronts preserve the original in-place sweeps; compare complete tile output against the serial recurrence. |
| Symbolic regression | Warp-per-candidate evaluation with ordered tournament and hill climbing; compare candidates, tournament results and mutations. |

The pinned Bend source is `b9d1352c9f45632447f40a2e927355c92f2be58c`. Builds use Clang 22, CUDA 13.1, `-O3`, native CPU architecture flags, `sm_86` and disabled floating-point contraction. Exact commands, contract hashes and raw measurements remain in the run archive. The shared execution lock and GPU activity gates were enabled; the configured resident transcription worker is permitted by the existing policy.

## Validation and saved evidence

The completed queue passed 44 boundary/full-input native checks, then eleven harness checks, eleven excluded warmups and 110 measurements. The [saved summary](benchmarks/vendor-cuda-20260921/summary.json), [individual samples](benchmarks/vendor-cuda-20260921/samples.jsonl), [native-check log](benchmarks/vendor-cuda-20260921/native-checks.log) and [completion marker](benchmarks/vendor-cuda-20260921/completed.json) are included in the repository. Only the eleven new CUDA cases were measured; other configurations in the prepared summary remain pending and are not substituted for historical measurements.

The earlier v2 queue failed four checks in three-body simulation and ray tracing because the generated code used approximate square roots. Disabling assembler FMA did not fix them, and LLVM precision flags still emitted approximate square roots. Explicit `__fsqrt_rn` produced correctly rounded instructions and passed every check without loosening tolerances. The fix is commit `75256b3`.

Failed evidence remains in `runs/vendor-custom-check-78512v4g/`, with counterfactual builds in `runs/vendor-fmad-audit-kde9cmif/` and `runs/vendor-sqrt-audit-pdkuhc_7/`. The corrected standalone native run is `runs/vendor-custom-check-o_j0z6dz/`; the final queue repeated it in `runs/vendor-custom-check-i_7yzes4/`. No failed samples were erased or pooled with the successful run.

## Reproduction

Adapt local dependency paths in [vendor-gpu-custom.toml](vendor-gpu-custom.toml). To queue only these eleven CUDA cases using the existing idle-GPU gate:

```sh
uv run --locked python validate_vendor_cuda.py --request runs/vendor-cuda-new/request.json --enqueue
uv run --locked python validate_vendor_cuda.py --request runs/vendor-cuda-new/request.json
```

The runner pins inputs, waits for 120 seconds of sampled GPU inactivity, checks correctness and records ten measurements per case. It preserves failures and stops for inspection. Do not edit pinned inputs while a request is queued or running. The completed local user service was `bend-bench-vendor-cuda.service`, request `runs/vendor-cuda-validation-20260921-v3/request.json`.
