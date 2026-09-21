# Published-workload GPU library adapters

These adapters add conventional GPU comparisons to the existing published-workload suite. The configuration is [vendor-gpu-libraries.toml](vendor-gpu-libraries.toml); baseline selection is explicit through `vendor_gpu`, so existing configurations retain their previous workload selection.

All 21 configurations passed a fresh combined harness correctness check in `runs/182bf42ec81e810fd617`: serial C, Bend and OpenMP at one and 16 threads, Bend GPU and the new GPU library baseline for each workload. Preparation preserved source, compiler, toolkit, installed-library and binary hashes. All three new adapters passed full-output checks on the published input sizes. There are no timing repetitions in this run yet; existing performance tables remain unchanged.

The regression suite passed 68 tests with six expected opt-in/environment skips, followed by the added installed-cuDF identity test and focused adapter tests. Native opt-in checks were also run separately, as described below. Both wheel and source distribution builds passed.

## CUB radix sort and deduplication

The adapter generates the published 2^22 24-bit keys, calls CUB radix sort and consecutive-duplicate removal, checks strict ordering and computes the published checksum. The correctness stage additionally copies every unique key back and compares the entire vector with CPU sort-and-deduplicate. Normal timing includes GPU generation, sorting, deduplication, checksum reduction, required result transfers, startup and cleanup. CUDA events separately cover generation through checksum reduction, excluding startup and result transfers.

Native correctness passed at depths 0, 6, 12 and 22, including the published checksum at depth 22. This is correctness evidence, not a performance measurement. No existing result or summary-table cell has been replaced.

## cuBLAS matrix multiplication

The adapter uses batched INT8-input, INT32-output cuBLAS GEMM for the published 384 products of 128 × 128 matrices. Generated entries are 0–99, so every result is exact in INT32. GPU kernels reproduce the quadtree generators, wrapping-U32 Freivalds verification and published checksum. A failed Freivalds check exits nonzero. Column-major cuBLAS receives the operands in reverse order to compute the required row-major products.

Native correctness passed for 4 × 4, 8 × 8, 32 × 32 and the full published 128 × 128 batch. Small checksums match the actual upstream quadtree C implementation. Every output entry, including all 6,291,456 entries in the full batch, matches conventional CPU multiplication; the full checksum matches the published pin. The installed cuBLAS accepted the integer batched API. Performance remains unmeasured.

The event interval covers GPU generation, GEMM and Freivalds/checksum kernels. Complete-process timing additionally includes library startup, allocations, result transfers and cleanup. Full CPU multiplication is a correctness-stage check and is excluded from normal timed executions. The harness hashes cuBLAS and cuBLASLt along with its existing toolkit and linked-library evidence.

## cuDF edit distance

The native C++ adapter uses `nvtext::edit_distance` for the published 32,768 pairs of 256-symbol sequences. It reuses the pinned upstream C sequence generator and maps symbols 0–3 to ASCII A–D, preserving every edit distance. String offsets and characters are uploaded as cuDF column views. Results return to the host for the original wrapping-U32 checksum. Input generation, column construction, transfers, library initialization and cleanup remain inside complete-process timing.

The correctness stage checks every distance against the original rolling-row C dynamic program. Native checks passed for one, 64 and all 32,768 pairs; the full checksum matches the published pin. CUDA events span uploads, library execution and result download, so this interval is a device sequence, not kernel-only time. Performance remains unmeasured.

The optional dependency environment pins libcudf/librmm 26.8.0 and all resolved wheel hashes. Its libcudf source revision is `ff5b362d7c06ae5837fd7a7337e2ae20895f324d`, distinct from the development revision inspected during the feasibility audit. Preparation records the installed headers, libraries, distribution metadata and lock hash and verifies the declared libcudf revision. Wheel libraries are linked explicitly so execution resolves their transitive dependencies without changing the shell's library path. Initial failed header-compilation and library-loading checks are retained alongside successful development checks.

## Reproduction

Install the optional cuDF C++ dependency from its separate locked environment. Python/uv supplies the binary distribution; the measured executable is native C++ and does not start Python.

```sh
uv sync --locked --project dependencies/cudf
```

Adapt pinned source/tool paths and the approved resident-service cgroup to the target machine. The supplied configuration retains the shared execution lock, blocked-service checks and GPU activity monitoring.

```sh
uv run --locked bend-bench prepare vendor-gpu-libraries.toml
uv run --locked bend-bench check vendor-gpu-libraries.toml
uv run --locked bend-bench run vendor-gpu-libraries.toml
```

Opt-in native development checks retain build and execution logs under `runs/vendor-gpu-check-*/checks.jsonl`, `runs/vendor-matmul-check-*/checks.jsonl` and `runs/vendor-editdist-check-*/checks.jsonl`:

```sh
BEND_BENCH_VENDOR_GPU_TEST=1 uv run --locked python -m unittest discover -s tests -p test_vendor_gpu.py -v
```
