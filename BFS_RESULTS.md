# BFS comparison results

These results compare time to checked answers for graph traversal. Each cell uses ten measurements after a correctness check and warmup. Wall time includes startup, input construction or loading, transfers and full output. CPU columns use 16 threads; kernel columns come from separate Nsight executions.

| Workload | Bend CPU wall seconds | Conventional CPU wall seconds | CPU baseline | Bend GPU wall seconds | Conventional GPU wall seconds | GPU baseline | Bend kernel seconds | Conventional kernel seconds |
|---|---:|---:|---|---:|---:|---|---:|---:|
| bfs-10 | 0.012346 | 0.006589 | gap-openmp | 0.155016 | 0.218513 | gunrock-cuda | 0.036256 | 0.000069 |
| bfs-14 | 0.142198 | 0.020476 | gap-openmp | 0.690351 | 0.249224 | gunrock-cuda | 0.529892 | 0.000107 |
| bfs-18 | 2.834437 | 0.256581 | gap-openmp | 11.236950 | 0.812332 | gunrock-cuda | 10.963499 | 0.000241 |

[Full thread-scaling, memory and timing report](runs/6f09d7ec9215cbadd596/report.md).
[Input contracts, baseline maturity and algorithm differences](APPLICATIONS.md). Pricing and m,n,k baselines are local controls; BFS uses GAP and Gunrock.
