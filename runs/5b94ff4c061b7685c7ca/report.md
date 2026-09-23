# Bend benchmark results

Times are medians of correctness-gated measured executions, excluding checks and warmups. End-to-end includes process startup and output. Device-sequence event time is distinct from a kernel-only sum. Unmeasured metrics remain blank.

Preparation: passed. Fingerprint: `4974f59d8721916b2f98babeec34799ae5ac908bbd23b079f0b26de5cfc0279d`.

| Workload / implementation / threads | Gate | Profile gate | Checked | Runs | End-to-end seconds | Compute seconds | Device-sequence seconds | Kernel seconds | Speedup | Efficiency | Peak host RSS KiB |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mnk/mnk-4-4-3-6/bend/16 | passed | n/a | True | 10 | 0.004092 |  |  |  |  |  | 3512.000000 |
| mnk/mnk-4-4-3-6/local-alpha-beta-openmp/16 | passed | n/a | True | 10 | 0.005127 | 0.000485 |  |  |  |  | 4816.000000 |
| mnk/mnk-4-4-3-6/bend-cuda/16 | passed | passed | True | 10 | 0.114997 |  |  | 0.000795 |  |  | 70732.000000 |
| mnk/mnk-4-4-3-6/local-alpha-beta-cuda/1 | passed | passed | True | 10 | 0.118350 |  |  | 0.000722 | 1.000000 | 1.000000 | 71048.000000 |
| mnk/mnk-4-4-3-8/bend/16 | passed | n/a | True | 10 | 0.004073 |  |  |  |  |  | 3520.000000 |
| mnk/mnk-4-4-3-8/local-alpha-beta-openmp/16 | passed | n/a | True | 10 | 0.004602 | 0.000480 |  |  |  |  | 4696.000000 |
| mnk/mnk-4-4-3-8/bend-cuda/16 | passed | passed | True | 10 | 0.114679 |  |  | 0.001125 |  |  | 70648.000000 |
| mnk/mnk-4-4-3-8/local-alpha-beta-cuda/1 | passed | passed | True | 10 | 0.113237 |  |  | 0.001033 | 1.000000 | 1.000000 | 71228.000000 |
| mnk/mnk-5-5-4-6/bend/16 | passed | n/a | True | 10 | 0.004192 |  |  |  |  |  | 3504.000000 |
| mnk/mnk-5-5-4-6/local-alpha-beta-openmp/16 | passed | n/a | True | 10 | 0.004767 | 0.000505 |  |  |  |  | 4756.000000 |
| mnk/mnk-5-5-4-6/bend-cuda/16 | passed | passed | True | 10 | 0.116353 |  |  | 0.001646 |  |  | 70892.000000 |
| mnk/mnk-5-5-4-6/local-alpha-beta-cuda/1 | passed | passed | True | 10 | 0.115601 |  |  | 0.001741 | 1.000000 | 1.000000 | 71048.000000 |
| mnk/mnk-5-5-4-8/bend/16 | passed | n/a | True | 10 | 0.004615 |  |  |  |  |  | 3516.000000 |
| mnk/mnk-5-5-4-8/local-alpha-beta-openmp/16 | passed | n/a | True | 10 | 0.006281 | 0.001213 |  |  |  |  | 4532.000000 |
| mnk/mnk-5-5-4-8/bend-cuda/16 | passed | passed | True | 10 | 0.155533 |  |  | 0.035780 |  |  | 70908.000000 |
| mnk/mnk-5-5-4-8/local-alpha-beta-cuda/1 | passed | passed | True | 10 | 0.149844 |  |  | 0.035857 | 1.000000 | 1.000000 | 71240.000000 |

## Scope

Vendor inputs retain upstream arithmetic and checksums. UTS preserves BOTS's SHA-1 tree. CUB uses library radix sort and reduction over matching wrapping-U32 inputs. HotSpot uses the archived Rodinia inputs and CUDA timestep, with a preserved OpenMP boundary correction and full-vector validation. Kernel sums, when present, come from separate correctness-checked Nsight executions; profiled wall time is not used as end-to-end time. Device peak memory, proof-system correspondence, Metal and AI-coding trials remain unmeasured.
