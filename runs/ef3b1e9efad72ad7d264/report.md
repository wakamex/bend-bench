# Bend benchmark results

Times are medians of correctness-gated measured executions, excluding checks and warmups. End-to-end includes process startup and output. Device-sequence event time is distinct from a kernel-only sum. Unmeasured metrics remain blank.

Preparation: passed. Fingerprint: `45209c4ceb4d6853e6de52ecc5882b7d640f4eee8247a711e29c92237c779ac2`.

| Workload / implementation / threads | Gate | Profile gate | Checked | Runs | End-to-end seconds | Compute seconds | Device-sequence seconds | Kernel seconds | Speedup | Efficiency | Peak host RSS KiB |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bfs/bfs-14/bend/1 | passed | n/a | True | 10 | 0.257351 |  |  |  | 1.000000 | 1.000000 | 3212.000000 |
| bfs/bfs-14/gap-openmp/1 | passed | n/a | True | 10 | 0.020060 | 0.000245 |  |  | 1.000000 | 1.000000 | 7384.000000 |
| bfs/bfs-14/bend/16 | passed | n/a | True | 10 | 0.149165 |  |  |  | 1.725270 | 0.107829 | 3792.000000 |
| bfs/bfs-14/gap-openmp/16 | passed | n/a | True | 10 | 0.018780 | 0.000538 |  |  | 1.068109 | 0.066757 | 4876.000000 |

## Scope

Vendor inputs retain upstream arithmetic and checksums. UTS preserves BOTS's SHA-1 tree. CUB uses library radix sort and reduction over matching wrapping-U32 inputs. HotSpot uses the archived Rodinia inputs and CUDA timestep, with a preserved OpenMP boundary correction and full-vector validation. Kernel sums, when present, come from separate correctness-checked Nsight executions; profiled wall time is not used as end-to-end time. Device peak memory, proof-system correspondence, Metal and AI-coding trials remain unmeasured.
