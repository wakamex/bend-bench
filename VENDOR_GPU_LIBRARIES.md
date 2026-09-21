# Published-workload GPU library adapters

These adapters add conventional GPU comparisons to the existing published-workload suite. The configuration is [vendor-gpu-libraries.toml](vendor-gpu-libraries.toml); baseline selection is explicit through `vendor_gpu`, so existing configurations retain their previous workload selection.

## CUB radix sort and deduplication

The adapter generates the published 2^22 24-bit keys, calls CUB radix sort and consecutive-duplicate removal, checks strict ordering and computes the published checksum. The correctness stage additionally copies every unique key back and compares the entire vector with CPU sort-and-deduplicate. Normal timing includes GPU generation, sorting, deduplication, checksum reduction, required result transfers, startup and cleanup. CUDA events separately cover generation through checksum reduction, excluding startup and result transfers.

Native correctness passed at depths 0, 6, 12 and 22, including the published checksum at depth 22. This is correctness evidence, not a performance measurement. No existing result or summary-table cell has been replaced.

## Reproduction

Adapt pinned source/tool paths and the approved resident-service cgroup to the target machine. The supplied configuration retains the shared execution lock, blocked-service checks and GPU activity monitoring.

```sh
uv run --locked bend-bench prepare vendor-gpu-libraries.toml
uv run --locked bend-bench check vendor-gpu-libraries.toml
uv run --locked bend-bench run vendor-gpu-libraries.toml
```

Opt-in native development checks retain build and execution logs under `runs/vendor-gpu-check-*/checks.jsonl`:

```sh
BEND_BENCH_VENDOR_GPU_TEST=1 uv run --locked python -m unittest discover -s tests -p test_vendor_gpu.py -v
```
