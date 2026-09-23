# Bend benchmark results

Times are medians of correctness-gated measured executions, excluding checks and warmups. End-to-end includes process startup and output. Device-sequence event time is distinct from a kernel-only sum. Unmeasured metrics remain blank.

Preparation: passed. Fingerprint: `c0a4f7afd080bfcbd4369017ec39735a8235e802682291e3dd9c833439ac70dc`.

| Workload / implementation / threads | Gate | Profile gate | Checked | Runs | End-to-end seconds | Compute seconds | Device-sequence seconds | Kernel seconds | Speedup | Efficiency | Peak host RSS KiB |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mnk/mnk-4-4-3-6/bend/1 | passed | n/a | True | 10 | 0.002292 |  |  |  | 1.000000 | 1.000000 | 2484.000000 |
| mnk/mnk-4-4-3-6/local-alpha-beta-openmp/1 | passed | n/a | True | 10 | 0.002752 | 0.000010 |  |  | 1.000000 | 1.000000 | 4568.000000 |
| mnk/mnk-4-4-3-6/bend/16 | passed | n/a | True | 10 | 0.002874 |  |  |  | 0.797264 | 0.049829 | 2360.000000 |
| mnk/mnk-4-4-3-6/local-alpha-beta-openmp/16 | passed | n/a | True | 10 | 0.003344 | 0.000431 |  |  | 0.822943 | 0.051434 | 4492.000000 |
| mnk/mnk-4-4-3-8/bend/1 | passed | n/a | True | 10 | 0.002282 |  |  |  | 1.000000 | 1.000000 | 2456.000000 |
| mnk/mnk-4-4-3-8/local-alpha-beta-openmp/1 | passed | n/a | True | 10 | 0.002634 | 0.000031 |  |  | 1.000000 | 1.000000 | 4576.000000 |
| mnk/mnk-4-4-3-8/bend/16 | passed | n/a | True | 10 | 0.002830 |  |  |  | 0.806442 | 0.050403 | 2184.000000 |
| mnk/mnk-4-4-3-8/local-alpha-beta-openmp/16 | passed | n/a | True | 10 | 0.003512 | 0.000416 |  |  | 0.749941 | 0.046871 | 4512.000000 |
| mnk/mnk-5-5-4-6/bend/1 | passed | n/a | True | 10 | 0.002329 |  |  |  | 1.000000 | 1.000000 | 2456.000000 |
| mnk/mnk-5-5-4-6/local-alpha-beta-openmp/1 | passed | n/a | True | 10 | 0.002621 | 0.000022 |  |  | 1.000000 | 1.000000 | 4568.000000 |
| mnk/mnk-5-5-4-6/bend/16 | passed | n/a | True | 10 | 0.002836 |  |  |  | 0.821197 | 0.051325 | 2180.000000 |
| mnk/mnk-5-5-4-6/local-alpha-beta-openmp/16 | passed | n/a | True | 10 | 0.003353 | 0.000411 |  |  | 0.781582 | 0.048849 | 4496.000000 |
| mnk/mnk-5-5-4-8/bend/1 | passed | n/a | True | 10 | 0.002680 |  |  |  | 1.000000 | 1.000000 | 2456.000000 |
| mnk/mnk-5-5-4-8/local-alpha-beta-openmp/1 | passed | n/a | True | 10 | 0.002816 | 0.000180 |  |  | 1.000000 | 1.000000 | 4460.000000 |
| mnk/mnk-5-5-4-8/bend/16 | passed | n/a | True | 10 | 0.003144 |  |  |  | 0.852259 | 0.053266 | 2312.000000 |
| mnk/mnk-5-5-4-8/local-alpha-beta-openmp/16 | passed | n/a | True | 10 | 0.003339 | 0.000486 |  |  | 0.843480 | 0.052718 | 4428.000000 |

## Scope

Vendor inputs retain upstream arithmetic and checksums. UTS preserves BOTS's SHA-1 tree. CUB uses library radix sort and reduction over matching wrapping-U32 inputs. HotSpot uses the archived Rodinia inputs and CUDA timestep, with a preserved OpenMP boundary correction and full-vector validation. Kernel sums, when present, come from separate correctness-checked Nsight executions; profiled wall time is not used as end-to-end time. Device peak memory, proof-system correspondence, Metal and AI-coding trials remain unmeasured.
