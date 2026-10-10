# Bend benchmark results

Times are medians of correctness-gated measured executions, excluding checks and warmups. End-to-end includes process startup and output. Device-sequence event time is distinct from a kernel-only sum. Unmeasured metrics remain blank.

Preparation: passed. Fingerprint: `6bbf783f6711de5d46e471477170842138cc76afeea369b90bebe2d6d49926ec`.

| Workload / implementation / threads | Gate | Profile gate | Checked | Runs | End-to-end seconds | Compute seconds | Device-sequence seconds | Kernel seconds | Speedup | Efficiency | Peak host RSS KiB |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ml/gpt2/bend/1 | passed | n/a | True | 10 | 10.010049 | 3.910500 |  |  | 1.000000 | 1.000000 | 1486036.000000 |
| ml/gpt2/pytorch/1 | passed | n/a | True | 10 | 2.043980 | 0.802494 |  |  | 1.000000 | 1.000000 | 724040.000000 |
| ml/gpt2/bend/16 | passed | n/a | True | 10 | 10.219545 | 3.894500 |  |  | 0.979500 | 0.061219 | 1485420.000000 |
| ml/gpt2/pytorch/16 | passed | n/a | True | 10 | 2.122665 | 0.802826 |  |  | 0.962931 | 0.060183 | 723552.000000 |
| ml/nanogpt/bend/1 | passed | n/a | True | 10 | 6.014471 | 5.486500 |  |  | 1.000000 | 1.000000 | 132180.000000 |
| ml/nanogpt/pytorch/1 | passed | n/a | True | 10 | 2.318461 | 1.204536 |  |  | 1.000000 | 1.000000 | 275620.000000 |
| ml/nanogpt/bend/16 | passed | n/a | True | 10 | 6.451378 | 5.924500 |  |  | 0.932277 | 0.058267 | 131736.000000 |
| ml/nanogpt/pytorch/16 | passed | n/a | True | 10 | 2.315691 | 1.194390 |  |  | 1.001196 | 0.062575 | 276276.000000 |
| ml/nanogpt-batch/bend/16 | passed | n/a | True | 10 | 100.897445 | 99.757000 |  |  |  |  | 134528.000000 |
| ml/nanogpt-batch/pytorch/16 | passed | n/a | True | 10 | 3.784932 | 2.636318 |  |  |  |  | 1036248.000000 |
| ml/nanogpt-batch/bend-cuda/16 | passed | pending | True | 10 | 198.373179 | 195.327000 |  |  |  |  | 288396.000000 |
| ml/nanogpt-batch/pytorch-cuda/16 | passed | pending | True | 10 | 2.673129 | 1.014053 |  |  |  |  | 1160172.000000 |
| ml/mnist/bend/1 | passed | n/a | True | 10 | 34.009524 | 31.356000 |  |  | 1.000000 | 1.000000 | 43172.000000 |
| ml/mnist/pytorch/1 | passed | n/a | True | 10 | 1.675377 | 0.421497 |  |  | 1.000000 | 1.000000 | 592564.000000 |
| ml/mnist/bend/16 | passed | n/a | True | 10 | 11.505223 | 10.412000 |  |  | 2.956007 | 0.184750 | 92576.000000 |
| ml/mnist/pytorch/16 | passed | n/a | True | 10 | 1.415036 | 0.253502 |  |  | 1.183982 | 0.073999 | 592904.000000 |
| ml/mnist/pytorch-cuda/16 | passed | pending | True | 10 | 2.127297 | 0.451315 |  |  |  |  | 1104712.000000 |
| ml/mm_array/bend/1 | passed | n/a | True | 10 | 0.075316 | 0.073000 |  |  | 1.000000 | 1.000000 | 2296.000000 |
| ml/mm_array/pytorch/1 | passed | n/a | True | 10 | 1.067532 | 0.002814 |  |  | 1.000000 | 1.000000 | 227636.000000 |
| ml/mm_array/bend/16 | passed | n/a | True | 10 | 0.076401 | 0.074000 |  |  | 0.985807 | 0.061613 | 2252.000000 |
| ml/mm_array/pytorch/16 | passed | n/a | True | 10 | 1.075122 | 0.001524 |  |  | 0.992940 | 0.062059 | 227528.000000 |
| ml/mv/bend/1 | passed | n/a | True | 10 | 0.176483 | 0.168000 |  |  | 1.000000 | 1.000000 | 65756.000000 |
| ml/mv/pytorch/1 | passed | n/a | True | 10 | 1.082420 | 0.012325 |  |  | 1.000000 | 1.000000 | 253152.000000 |
| ml/mv/bend/16 | passed | n/a | True | 10 | 0.179511 | 0.170000 |  |  | 0.983132 | 0.061446 | 65752.000000 |
| ml/mv/pytorch/16 | passed | n/a | True | 10 | 1.071356 | 0.012332 |  |  | 1.010327 | 0.063145 | 250784.000000 |

## Scope

Vendor inputs retain upstream arithmetic and checksums. UTS preserves BOTS's SHA-1 tree. CUB uses library radix sort and reduction over matching wrapping-U32 inputs. HotSpot uses the archived Rodinia inputs and CUDA timestep, with a preserved OpenMP boundary correction and full-vector validation. Kernel sums, when present, come from separate correctness-checked Nsight executions; profiled wall time is not used as end-to-end time. Device peak memory, proof-system correspondence, Metal and AI-coding trials remain unmeasured.
