# Bend benchmark results

Times are medians of correctness-gated measured executions, excluding checks and warmups. End-to-end includes process startup and output. Device-sequence event time is distinct from a kernel-only sum. Unmeasured metrics remain blank.

Preparation: passed. Fingerprint: `a4e3571a9dfe94636e4aa18335991d7ac6eeca920a08ff1403fb255ab7242dc5`.

| Workload / implementation / threads | Gate | Profile gate | Checked | Runs | End-to-end seconds | Compute seconds | Device-sequence seconds | Kernel seconds | Speedup | Efficiency | Peak host RSS KiB |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mnk/mnk-4-4-3-6/bend/1 | passed | n/a | True | 10 | 0.002502 |  |  |  | 1.000000 | 1.000000 | 2488.000000 |
| mnk/mnk-4-4-3-6/local-alpha-beta-openmp/1 | passed | n/a | True | 10 | 0.002620 | 0.000010 |  |  | 1.000000 | 1.000000 | 4496.000000 |
| mnk/mnk-4-4-3-6/bend/16 | passed | n/a | True | 10 | 0.002962 |  |  |  | 0.844812 | 0.052801 | 2184.000000 |
| mnk/mnk-4-4-3-6/local-alpha-beta-openmp/16 | passed | n/a | True | 10 | 0.003411 | 0.000430 |  |  | 0.768037 | 0.048002 | 4548.000000 |
| mnk/mnk-4-4-3-8/bend/1 | passed | n/a | True | 10 | 0.013173 |  |  |  | 1.000000 | 1.000000 | 2488.000000 |
| mnk/mnk-4-4-3-8/local-alpha-beta-openmp/1 | passed | n/a | True | 10 | 0.002693 | 0.000031 |  |  | 1.000000 | 1.000000 | 4496.000000 |
| mnk/mnk-4-4-3-8/bend/16 | passed | n/a | True | 10 | 0.006102 |  |  |  | 2.158934 | 0.134933 | 2252.000000 |
| mnk/mnk-4-4-3-8/local-alpha-beta-openmp/16 | passed | n/a | True | 10 | 0.003231 | 0.000432 |  |  | 0.833562 | 0.052098 | 4552.000000 |
| mnk/mnk-5-5-4-6/bend/1 | passed | n/a | True | 10 | 0.004477 |  |  |  | 1.000000 | 1.000000 | 2436.000000 |
| mnk/mnk-5-5-4-6/local-alpha-beta-openmp/1 | passed | n/a | True | 10 | 0.002626 | 0.000021 |  |  | 1.000000 | 1.000000 | 4504.000000 |
| mnk/mnk-5-5-4-6/bend/16 | passed | n/a | True | 10 | 0.003251 |  |  |  | 1.377078 | 0.086067 | 2380.000000 |
| mnk/mnk-5-5-4-6/local-alpha-beta-openmp/16 | passed | n/a | True | 10 | 0.003177 | 0.000430 |  |  | 0.826560 | 0.051660 | 4420.000000 |
| mnk/mnk-5-5-4-8/bend/1 | passed | n/a | True | 10 | 0.082272 |  |  |  | 1.000000 | 1.000000 | 2460.000000 |
| mnk/mnk-5-5-4-8/local-alpha-beta-openmp/1 | passed | n/a | True | 10 | 0.002795 | 0.000177 |  |  | 1.000000 | 1.000000 | 4496.000000 |
| mnk/mnk-5-5-4-8/bend/16 | passed | n/a | True | 10 | 0.017604 |  |  |  | 4.673429 | 0.292089 | 2184.000000 |
| mnk/mnk-5-5-4-8/local-alpha-beta-openmp/16 | passed | n/a | True | 10 | 0.003305 | 0.000487 |  |  | 0.845654 | 0.052853 | 4472.000000 |

## Scope

Vendor inputs retain upstream arithmetic and checksums. UTS preserves BOTS's SHA-1 tree. CUB uses library radix sort and reduction over matching wrapping-U32 inputs. HotSpot uses the archived Rodinia inputs and CUDA timestep, with a preserved OpenMP boundary correction and full-vector validation. Kernel sums, when present, come from separate correctness-checked Nsight executions; profiled wall time is not used as end-to-end time. Device peak memory, proof-system correspondence, Metal and AI-coding trials remain unmeasured.
