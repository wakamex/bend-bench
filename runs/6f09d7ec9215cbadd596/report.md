# Bend benchmark results

Times are medians of correctness-gated measured executions, excluding checks and warmups. End-to-end includes process startup and output. Device-sequence event time is distinct from a kernel-only sum. Unmeasured metrics remain blank.

Preparation: passed. Fingerprint: `e35594a63c16e2f6c471cd87c2302150a41f74e93daad06f8a27204b524d8f6f`.

| Workload / implementation / threads | Gate | Profile gate | Checked | Runs | End-to-end seconds | Compute seconds | Device-sequence seconds | Kernel seconds | Speedup | Efficiency | Peak host RSS KiB |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bfs/bfs-10/bend/1 | passed | n/a | True | 10 | 0.012959 |  |  |  | 1.000000 | 1.000000 | 3432.000000 |
| bfs/bfs-10/gap-openmp/1 | passed | n/a | True | 10 | 0.005294 | 0.000034 |  |  | 1.000000 | 1.000000 | 4896.000000 |
| bfs/bfs-10/bend/2 | passed | n/a | True | 10 | 0.011849 |  |  |  | 1.093647 | 0.546823 | 3512.000000 |
| bfs/bfs-10/gap-openmp/2 | passed | n/a | True | 10 | 0.005455 | 0.000067 |  |  | 0.970624 | 0.485312 | 4928.000000 |
| bfs/bfs-10/bend/4 | passed | n/a | True | 10 | 0.009160 |  |  |  | 1.414653 | 0.353663 | 3464.000000 |
| bfs/bfs-10/gap-openmp/4 | passed | n/a | True | 10 | 0.005750 | 0.000106 |  |  | 0.920734 | 0.230184 | 4608.000000 |
| bfs/bfs-10/bend/8 | passed | n/a | True | 10 | 0.012176 |  |  |  | 1.064251 | 0.133031 | 3312.000000 |
| bfs/bfs-10/gap-openmp/8 | passed | n/a | True | 10 | 0.005922 | 0.000233 |  |  | 0.893959 | 0.111745 | 4928.000000 |
| bfs/bfs-10/bend/16 | passed | n/a | True | 10 | 0.012346 |  |  |  | 1.049661 | 0.065604 | 3468.000000 |
| bfs/bfs-10/gap-openmp/16 | passed | n/a | True | 10 | 0.006589 | 0.000454 |  |  | 0.803576 | 0.050223 | 4584.000000 |
| bfs/bfs-10/bend/32 | passed | n/a | True | 10 | 0.012022 |  |  |  | 1.077889 | 0.033684 | 3144.000000 |
| bfs/bfs-10/gap-openmp/32 | passed | n/a | True | 10 | 0.015833 | 0.003407 |  |  | 0.334396 | 0.010450 | 4628.000000 |
| bfs/bfs-10/bend-cuda/32 | passed | passed | True | 10 | 0.155016 |  |  | 0.036256 |  |  | 72896.000000 |
| bfs/bfs-10/gunrock-cuda/1 | passed | passed | True | 10 | 0.218513 |  | 0.017494 | 0.000069 | 1.000000 | 1.000000 | 125432.000000 |
| bfs/bfs-14/bend/1 | passed | n/a | True | 10 | 0.267755 |  |  |  | 1.000000 | 1.000000 | 3560.000000 |
| bfs/bfs-14/gap-openmp/1 | passed | n/a | True | 10 | 0.021643 | 0.000248 |  |  | 1.000000 | 1.000000 | 7472.000000 |
| bfs/bfs-14/bend/2 | passed | n/a | True | 10 | 0.172743 |  |  |  | 1.550020 | 0.775010 | 3756.000000 |
| bfs/bfs-14/gap-openmp/2 | passed | n/a | True | 10 | 0.020347 | 0.000200 |  |  | 1.063682 | 0.531841 | 7364.000000 |
| bfs/bfs-14/bend/4 | passed | n/a | True | 10 | 0.118408 |  |  |  | 2.261283 | 0.565321 | 4236.000000 |
| bfs/bfs-14/gap-openmp/4 | passed | n/a | True | 10 | 0.019562 | 0.000182 |  |  | 1.106351 | 0.276588 | 6928.000000 |
| bfs/bfs-14/bend/8 | passed | n/a | True | 10 | 0.154110 |  |  |  | 1.737422 | 0.217178 | 4700.000000 |
| bfs/bfs-14/gap-openmp/8 | passed | n/a | True | 10 | 0.022026 | 0.000347 |  |  | 0.982601 | 0.122825 | 6628.000000 |
| bfs/bfs-14/bend/16 | passed | n/a | True | 10 | 0.142198 |  |  |  | 1.882968 | 0.117685 | 4688.000000 |
| bfs/bfs-14/gap-openmp/16 | passed | n/a | True | 10 | 0.020476 | 0.000533 |  |  | 1.057013 | 0.066063 | 4828.000000 |
| bfs/bfs-14/bend/32 | passed | n/a | True | 10 | 0.100865 |  |  |  | 2.654576 | 0.082956 | 4492.000000 |
| bfs/bfs-14/gap-openmp/32 | passed | n/a | True | 10 | 0.028462 | 0.001138 |  |  | 0.760428 | 0.023763 | 5000.000000 |
| bfs/bfs-14/bend-cuda/32 | passed | passed | True | 10 | 0.690351 |  |  | 0.529892 |  |  | 85952.000000 |
| bfs/bfs-14/gunrock-cuda/1 | passed | passed | True | 10 | 0.249224 |  | 0.018667 | 0.000107 | 1.000000 | 1.000000 | 127228.000000 |
| bfs/bfs-18/bend/1 | passed | n/a | True | 10 | 7.177852 |  |  |  | 1.000000 | 1.000000 | 15296.000000 |
| bfs/bfs-18/gap-openmp/1 | passed | n/a | True | 10 | 0.324947 | 0.004974 |  |  | 1.000000 | 1.000000 | 48756.000000 |
| bfs/bfs-18/bend/2 | passed | n/a | True | 10 | 4.137933 |  |  |  | 1.734647 | 0.867323 | 15296.000000 |
| bfs/bfs-18/gap-openmp/2 | passed | n/a | True | 10 | 0.282161 | 0.002722 |  |  | 1.151636 | 0.575818 | 48428.000000 |
| bfs/bfs-18/bend/4 | passed | n/a | True | 10 | 2.589157 |  |  |  | 2.772273 | 0.693068 | 15260.000000 |
| bfs/bfs-18/gap-openmp/4 | passed | n/a | True | 10 | 0.260341 | 0.001548 |  |  | 1.248159 | 0.312040 | 48636.000000 |
| bfs/bfs-18/bend/8 | passed | n/a | True | 10 | 3.141818 |  |  |  | 2.284617 | 0.285577 | 15500.000000 |
| bfs/bfs-18/gap-openmp/8 | passed | n/a | True | 10 | 0.259694 | 0.001488 |  |  | 1.251271 | 0.156409 | 48096.000000 |
| bfs/bfs-18/bend/16 | passed | n/a | True | 10 | 2.834437 |  |  |  | 2.532373 | 0.158273 | 16524.000000 |
| bfs/bfs-18/gap-openmp/16 | passed | n/a | True | 10 | 0.256581 | 0.001852 |  |  | 1.266448 | 0.079153 | 47492.000000 |
| bfs/bfs-18/bend/32 | passed | n/a | True | 10 | 2.068309 |  |  |  | 3.470397 | 0.108450 | 20556.000000 |
| bfs/bfs-18/gap-openmp/32 | passed | n/a | True | 10 | 0.290238 | 0.003243 |  |  | 1.119590 | 0.034987 | 47212.000000 |
| bfs/bfs-18/bend-cuda/32 | passed | passed | True | 10 | 11.236950 |  |  | 10.963499 |  |  | 102324.000000 |
| bfs/bfs-18/gunrock-cuda/1 | passed | passed | True | 10 | 0.812332 |  | 0.015451 | 0.000241 | 1.000000 | 1.000000 | 153376.000000 |

## Scope

Vendor inputs retain upstream arithmetic and checksums. UTS preserves BOTS's SHA-1 tree. CUB uses library radix sort and reduction over matching wrapping-U32 inputs. HotSpot uses the archived Rodinia inputs and CUDA timestep, with a preserved OpenMP boundary correction and full-vector validation. Kernel sums, when present, come from separate correctness-checked Nsight executions; profiled wall time is not used as end-to-end time. Device peak memory, proof-system correspondence, Metal and AI-coding trials remain unmeasured.
