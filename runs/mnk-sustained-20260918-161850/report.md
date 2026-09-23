# Resident-process endgame throughput

Primary measurement: computation through materialization of every result in a preallocated flat host uint32 array. Every binary result is checked against the independent oracle after execution. Binary evidence writes, text formatting and delivery are outside the timed host-ready interval. Delivered timings include those diagnostic writes and must not be pooled with earlier delivery benchmarks. Search-to-host columns below use this new host-array boundary. Two warmups are excluded.

| Distinct positions | Positions per batch | Measured batches | Implementation | Mean delivered batch ms | Positions/second excluding warmups | Positions/second full process | Startup to READY ms | Mean search-to-host ms | Mean output ms |
|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-literal-cuda-1-run2 | 732.710 | 715546.5 | 706190.9 | 165.622 | 601.121 | 131.587 |
| 1024 | 524288 | 30 | bend-cuda-16-run2 | 540.100 | 970724.5 | 975529.5 | 87.605 | 299.670 | 240.400 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-literal-cuda-1-run0 | 731.669 | 716564.5 | 709642.8 | 138.137 | 601.386 | 130.273 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-bulk-16-run0 | 357.047 | 1468398.7 | 1467623.5 | 3.695 | 225.811 | 131.374 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-literal-cuda-1-run1 | 731.512 | 716717.8 | 708832.5 | 163.881 | 600.595 | 130.903 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-bulk-16-run1 | 348.807 | 1503089.9 | 1499179.3 | 3.792 | 221.744 | 127.237 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-cuda-1-run2 | 770.398 | 680541.4 | 673866.4 | 156.646 | 636.478 | 133.837 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-cuda-1-run1 | 767.803 | 682841.6 | 676432.5 | 124.666 | 636.060 | 131.785 |
| 1024 | 524288 | 30 | bend-cuda-16-run0 | 543.347 | 964923.2 | 971832.7 | 85.945 | 305.069 | 238.233 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-bulk-16-run2 | 355.363 | 1475360.6 | 1473757.1 | 3.592 | 225.913 | 129.590 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-cuda-1-run0 | 767.230 | 683351.5 | 676257.3 | 157.810 | 636.073 | 131.144 |
| 1024 | 524288 | 30 | bend-cuda-16-run1 | 537.007 | 976314.7 | 982650.5 | 88.083 | 304.150 | 232.800 |
