# Bend benchmark results

Times are medians of correctness-gated measured executions, excluding checks and warmups. End-to-end includes process startup and output. Device-sequence event time is distinct from a kernel-only sum. Unmeasured metrics remain blank.

Preparation: passed. Fingerprint: `11766e2e546fe1b0abefb6c7a80f150f34b5551f739ac0be7af3e410e1dd3b28`.

| Workload / implementation / threads | Gate | Profile gate | Checked | Runs | End-to-end seconds | Compute seconds | Device-sequence seconds | Kernel seconds | Speedup | Efficiency | Peak host RSS KiB |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bfs/bfs-14/bend/1 | passed | n/a | True | 10 | 0.262858 |  |  |  | 1.000000 | 1.000000 | 3212.000000 |
| bfs/bfs-14/gap-openmp/1 | passed | n/a | True | 10 | 0.019578 | 0.000237 |  |  | 1.000000 | 1.000000 | 7384.000000 |
| bfs/bfs-14/bend/16 | passed | n/a | True | 10 | 0.142516 |  |  |  | 1.844415 | 0.115276 | 4692.000000 |
| bfs/bfs-14/gap-openmp/16 | passed | n/a | True | 10 | 0.018541 | 0.000537 |  |  | 1.055949 | 0.065997 | 5020.000000 |

## Scope

Vendor inputs retain upstream arithmetic and checksums. UTS preserves BOTS's SHA-1 tree. CUB uses library radix sort and reduction over matching wrapping-U32 inputs. HotSpot uses the archived Rodinia inputs and CUDA timestep, with a preserved OpenMP boundary correction and full-vector validation. Kernel sums, when present, come from separate correctness-checked Nsight executions; profiled wall time is not used as end-to-end time. Device peak memory, proof-system correspondence, Metal and AI-coding trials remain unmeasured.
