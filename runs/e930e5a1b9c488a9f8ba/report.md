# Bend benchmark results

Times are medians of correctness-gated measured executions, excluding checks and warmups. End-to-end includes process startup and output. Device-sequence event time is distinct from a kernel-only sum. Unmeasured metrics remain blank.

Preparation: passed. Fingerprint: `9ab1c169cd179fa75d3ba237f7eb2c053b08d9f06aabee7a077d9e6631ac167a`.

| Workload / implementation / threads | Gate | Profile gate | Checked | Runs | End-to-end seconds | Compute seconds | Device-sequence seconds | Kernel seconds | Speedup | Efficiency | Peak host RSS KiB |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cub/sort-12/serial-cpp/1 | passed | n/a | True | 10 | 0.003076 |  |  |  | 1.000000 | 1.000000 | 4100.000000 |
| cub/sort-12/cub-cuda/1 | passed | passed | True | 10 | 0.188303 |  | 0.000075 | 0.000023 | 1.000000 | 1.000000 | 135524.000000 |
| cub/sort-12/bend-cuda/16 | passed | passed | True | 10 | 0.240909 |  |  | 0.072155 |  |  | 97132.000000 |
| cub/sort-18/serial-cpp/1 | passed | n/a | True | 10 | 0.017351 |  |  |  | 1.000000 | 1.000000 | 4848.000000 |
| cub/sort-18/cub-cuda/1 | passed | passed | True | 10 | 0.187477 |  | 0.000178 | 0.000057 | 1.000000 | 1.000000 | 135584.000000 |
| cub/sort-18/bend-cuda/16 | passed | passed | True | 10 | 0.345134 |  |  | 0.166917 |  |  | 96900.000000 |
| cub/sort-23/serial-cpp/1 | passed | n/a | True | 10 | 0.586177 |  |  |  | 1.000000 | 1.000000 | 36592.000000 |
| cub/sort-23/cub-cuda/1 | passed | passed | True | 10 | 0.192266 |  | 0.000687 | 0.000631 | 1.000000 | 1.000000 | 135524.000000 |
| cub/sort-23/bend-cuda/16 | passed | passed | True | 10 | 0.937421 |  |  | 0.824577 |  |  | 97196.000000 |
| cub/reduce-12/serial-cpp/1 | passed | n/a | True | 10 | 0.002971 |  |  |  | 1.000000 | 1.000000 | 4104.000000 |
| cub/reduce-12/cub-cuda/1 | passed | passed | True | 10 | 0.187806 |  | 0.000042 | 0.000002 | 1.000000 | 1.000000 | 135584.000000 |
| cub/reduce-12/bend-cuda/16 | passed | passed | True | 10 | 0.115692 |  |  | 0.001457 |  |  | 96628.000000 |
| cub/reduce-18/serial-cpp/1 | passed | n/a | True | 10 | 0.003631 |  |  |  | 1.000000 | 1.000000 | 4848.000000 |
| cub/reduce-18/cub-cuda/1 | passed | passed | True | 10 | 0.188172 |  | 0.000046 | 0.000004 | 1.000000 | 1.000000 | 135564.000000 |
| cub/reduce-18/bend-cuda/16 | passed | passed | True | 10 | 0.115816 |  |  | 0.002202 |  |  | 96756.000000 |
| cub/reduce-23/serial-cpp/1 | passed | n/a | True | 10 | 0.024040 |  |  |  | 1.000000 | 1.000000 | 36592.000000 |
| cub/reduce-23/cub-cuda/1 | passed | passed | True | 10 | 0.188745 |  | 0.000046 | 0.000011 | 1.000000 | 1.000000 | 135524.000000 |
| cub/reduce-23/bend-cuda/16 | passed | passed | True | 10 | 0.120172 |  |  | 0.003100 |  |  | 96400.000000 |

## Scope

Vendor inputs retain upstream arithmetic and checksums. UTS preserves BOTS's SHA-1 tree. CUB uses library radix sort and reduction over matching wrapping-U32 inputs. HotSpot uses the archived Rodinia inputs and CUDA timestep, with a preserved OpenMP boundary correction and full-vector validation. Kernel sums, when present, come from separate correctness-checked Nsight executions; profiled wall time is not used as end-to-end time. Device peak memory, proof-system correspondence, Metal and AI-coding trials remain unmeasured.
