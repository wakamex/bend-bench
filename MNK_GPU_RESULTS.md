# Alpha-beta game-search CPU and GPU results

The conventional CUDA column is invalid. A build-output filename collision caused both GPU labels to execute Bend. These historical rows are retained for audit, not as a Bend-versus-CUDA comparison. See [audit status](MNK_SUSTAINED.md).

These results compare time to checked answers for exact game search. Each cell uses ten measurements after a correctness check and warmup. Wall time includes startup, input construction or loading, transfers and full output. CPU columns use 16 threads; kernel columns come from separate Nsight executions.

| Workload | Bend CPU wall seconds | Conventional CPU wall seconds | CPU baseline | Bend GPU wall seconds | Conventional GPU wall seconds | GPU baseline | Bend kernel seconds | Conventional kernel seconds |
|---|---:|---:|---|---:|---:|---|---:|---:|
| mnk-4-4-3-6 | 0.004092 | 0.005127 | local-alpha-beta-openmp | 0.114997 | 0.118350 | local-alpha-beta-cuda | 0.000795 | 0.000722 |
| mnk-4-4-3-8 | 0.004073 | 0.004602 | local-alpha-beta-openmp | 0.114679 | 0.113237 | local-alpha-beta-cuda | 0.001125 | 0.001033 |
| mnk-5-5-4-6 | 0.004192 | 0.004767 | local-alpha-beta-openmp | 0.116353 | 0.115601 | local-alpha-beta-cuda | 0.001646 | 0.001741 |
| mnk-5-5-4-8 | 0.004615 | 0.006281 | local-alpha-beta-openmp | 0.155533 | 0.149844 | local-alpha-beta-cuda | 0.035780 | 0.035857 |

[Full thread-scaling, memory and timing report](runs/5b94ff4c061b7685c7ca/report.md).
[Input contracts, baseline maturity and algorithm differences](APPLICATIONS.md). Pricing and m,n,k baselines are local controls; BFS uses GAP and Gunrock.
