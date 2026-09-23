# Resident-process endgame throughput

Primary measurement: computation through materialization of every result in a preallocated flat host uint32 array. Every binary result is checked against the independent oracle after execution. Binary evidence writes, text formatting and delivery are outside the timed host-ready interval. Delivered timings include those diagnostic writes and must not be pooled with earlier delivery benchmarks. Search-to-host columns below use this new host-array boundary. Two warmups are excluded.

| Distinct positions | Positions per batch | Measured batches | Implementation | Mean delivered batch ms | Positions/second excluding warmups | Positions/second full process | Startup to READY ms | Mean search-to-host ms | Mean output ms |
|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-cuda-1-run2 | 767.271 | 683315.3 | 676069.3 | 161.272 | 636.558 | 130.695 |
| 1024 | 524288 | 30 | bend-16-run2 | 755.883 | 693610.4 | 694646.6 | 2.452 | 559.014 | 197.033 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-cuda-1-run0 | 767.473 | 683135.1 | 676253.5 | 158.353 | 636.049 | 131.406 |
| 1024 | 524288 | 30 | bend-cuda-16-run0 | 527.208 | 994460.9 | 1003597.7 | 84.034 | 300.683 | 226.600 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-bulk-16-run2 | 349.614 | 1499617.8 | 1496026.3 | 3.665 | 221.066 | 128.722 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-bulk-16-run1 | 348.633 | 1503838.6 | 1500021.6 | 3.700 | 220.967 | 127.809 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-cuda-1-run1 | 766.391 | 684100.1 | 677307.7 | 156.214 | 635.296 | 131.070 |
| 1024 | 524288 | 30 | bend-16-run1 | 757.296 | 692316.0 | 695623.4 | 2.066 | 557.052 | 200.367 |
| 1024 | 524288 | 30 | bend-cuda-16-run1 | 524.043 | 1000466.8 | 1005736.9 | 114.042 | 298.536 | 225.567 |
| 1024 | 524288 | 30 | bend-cuda-16-run2 | 533.655 | 982446.8 | 989999.6 | 85.732 | 302.626 | 231.000 |
| 1024 | 524288 | 30 | bend-16-run0 | 787.925 | 665403.1 | 669795.7 | 1.899 | 568.891 | 219.200 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-bulk-cuda-1-run1 | 942.831 | 556078.6 | 551397.5 | 158.085 | 811.136 | 131.685 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-bulk-16-run0 | 352.362 | 1487922.7 | 1486778.4 | 3.802 | 222.125 | 130.391 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-bulk-cuda-1-run0 | 946.878 | 553701.5 | 548896.4 | 159.025 | 810.177 | 136.686 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-bulk-cuda-1-run2 | 942.036 | 556547.6 | 551908.0 | 137.133 | 811.676 | 130.366 |
