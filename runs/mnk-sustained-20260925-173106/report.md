# Resident-process endgame throughput

Primary measurement: computation through materialization of every result in a preallocated flat host uint32 array. Every binary result is checked against the independent oracle after execution. Binary evidence writes, text formatting and delivery are outside the timed host-ready interval. Delivered timings include those diagnostic writes and must not be pooled with earlier delivery benchmarks. Search-to-host columns below use this new host-array boundary. Two warmups are excluded.

| Distinct positions | Positions per batch | Measured batches | Implementation | Mean delivered batch ms | Positions/second excluding warmups | Positions/second full process | Startup to READY ms | Mean search-to-host ms | Mean output ms |
|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-bulk-cuda-1-run1 | 219.761 | 2385722.7 | 2292337.0 | 170.476 | 80.541 | 139.199 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-cuda-1-run2 | 247.200 | 2120908.0 | 2059239.1 | 144.537 | 108.337 | 138.871 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-cuda-1-run0 | 246.722 | 2125015.0 | 2051943.7 | 148.711 | 108.668 | 138.042 |
| 1024 | 524288 | 30 | bend-cuda-16-run1 | 555.320 | 944117.9 | 949920.2 | 106.354 | 299.161 | 256.067 |
| 1024 | 524288 | 30 | bend-cuda-16-run2 | 562.661 | 931801.1 | 941558.1 | 85.972 | 313.075 | 249.533 |
| 1024 | 524288 | 30 | bend-cuda-16-run0 | 556.165 | 942683.9 | 951686.6 | 90.470 | 302.781 | 253.433 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-bulk-cuda-1-run2 | 216.694 | 2419489.7 | 2325757.9 | 149.605 | 81.024 | 135.712 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-bulk-cuda-1-run0 | 217.480 | 2410743.7 | 2320926.9 | 141.397 | 80.888 | 136.549 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-cuda-1-run1 | 252.715 | 2074620.8 | 2006655.6 | 139.684 | 109.229 | 143.541 |
