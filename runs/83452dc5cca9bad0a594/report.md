# Bend benchmark results

Times are medians of correctness-gated measured executions, excluding checks and warmups. End-to-end includes process startup and output. Device-sequence event time is distinct from a kernel-only sum. Unmeasured metrics remain blank.

Preparation: passed. Fingerprint: `b70e393b5fc01fe3c180c26b19796ef0c41ffaaad310ab055f85cdf1abaeee06`.

| Workload / implementation / threads | Gate | Profile gate | Checked | Runs | End-to-end seconds | Compute seconds | Device-sequence seconds | Kernel seconds | Speedup | Efficiency | Peak host RSS KiB |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mnk/mnk-4-4-3-6/bend/16 | pending | n/a | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-4-4-3-6/local-alpha-beta-openmp/16 | pending | n/a | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-4-4-3-6/bend-cuda/16 | pending | pending | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-4-4-3-6/local-alpha-beta-cuda/1 | pending | pending | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-4-4-3-8/bend/16 | pending | n/a | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-4-4-3-8/local-alpha-beta-openmp/16 | pending | n/a | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-4-4-3-8/bend-cuda/16 | pending | pending | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-4-4-3-8/local-alpha-beta-cuda/1 | pending | pending | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-5-5-4-6/bend/16 | pending | n/a | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-5-5-4-6/local-alpha-beta-openmp/16 | pending | n/a | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-5-5-4-6/bend-cuda/16 | pending | pending | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-5-5-4-6/local-alpha-beta-cuda/1 | pending | pending | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-5-5-4-8/bend/16 | pending | n/a | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-5-5-4-8/local-alpha-beta-openmp/16 | pending | n/a | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-5-5-4-8/bend-cuda/16 | pending | pending | True | 0 |  |  |  |  |  |  |  |
| mnk/mnk-5-5-4-8/local-alpha-beta-cuda/1 | pending | pending | True | 0 |  |  |  |  |  |  |  |

## Scope

Vendor inputs retain upstream arithmetic and checksums. UTS preserves BOTS's SHA-1 tree. CUB uses library radix sort and reduction over matching wrapping-U32 inputs. HotSpot uses the archived Rodinia inputs and CUDA timestep, with a preserved OpenMP boundary correction and full-vector validation. Kernel sums, when present, come from separate correctness-checked Nsight executions; profiled wall time is not used as end-to-end time. Device peak memory, proof-system correspondence, Metal and AI-coding trials remain unmeasured.
