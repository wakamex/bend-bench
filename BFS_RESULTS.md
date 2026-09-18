# BFS comparison results

These results compare time to checked answers for graph traversal. Each cell uses ten measurements after a correctness check and warmup. Wall time includes startup, input construction or loading, transfers and full output. CPU columns use 16 threads; kernel columns come from separate Nsight executions.

| Workload | Bend CPU wall seconds | Conventional CPU wall seconds | CPU baseline | Bend GPU wall seconds | Conventional GPU wall seconds | GPU baseline | Bend kernel seconds | Conventional kernel seconds |
|---|---:|---:|---|---:|---:|---|---:|---:|
| bfs-10 | 0.012346 | 0.006589 | gap-openmp | 0.155016 | 0.218513 | gunrock-cuda | 0.036256 | 0.000069 |
| bfs-14 | 0.142198 | 0.020476 | gap-openmp | 0.690351 | 0.249224 | gunrock-cuda | 0.529892 | 0.000107 |
| bfs-18 | 2.834437 | 0.256581 | gap-openmp | 11.236950 | 0.812332 | gunrock-cuda | 10.963499 | 0.000241 |

[Full thread-scaling, memory and timing report](runs/6f09d7ec9215cbadd596/report.md).
[Input contracts, baseline maturity and algorithm differences](APPLICATIONS.md). Pricing and m,n,k baselines are local controls; BFS uses GAP and Gunrock.

## Parallel convergence-check experiment

Explicitly forking the two recursive tree comparisons did not improve the tested 16-thread CPU execution. On the 16,384-vertex graph, median end-to-end time increased from 142.516 ms to 149.165 ms, about 4.7%. One-thread time changed from 262.858 ms to 257.351 ms. Each version passed full-distance correctness checks and ten measured repetitions after one warmup. These sequential before-and-after runs do not establish statistical significance, but provide no reason to adopt the candidate as a multicore optimization. The original implementation is retained; GPU behavior of this candidate was not measured.

The only source change was replacing `Bool.and(same(a, c), same(b, d))` with parallel bindings `x y = same(a, c) same(b, d)` followed by `Bool.and(x, y)`. Graph generation, traversal and output were unchanged. GAP controls were rerun under the same configuration: 16-thread times were 18.541 ms before and 18.780 ms after. Preserved generated sources, build commands and individual samples are in the [original report](runs/8a466d1294a9f6950d1e/report.md) and [candidate report](runs/ef3b1e9efad72ad7d264/report.md).
