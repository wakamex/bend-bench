# Resident-process endgame throughput

Repeated fixed corpus of 16 positions, two warmup batches per process. Latency includes answer formatting, pipe delivery and host observation; it is not kernel time. Full-process throughput counts all completed batches including warmups and includes startup and shutdown.

| Positions per batch | Measured batches | Implementation | Mean delivered batch ms | Positions/second excluding warmups | Positions/second full process | Startup to READY ms |
|---|---:|---|---:|---:|---:|---:|
| 524288 | 30 | local-alpha-beta-cuda-1-run2 | 1205.032 | 435082.1 | 432181.8 | 132.624 |
| 524288 | 30 | bend-16-run2 | 1019.319 | 514351.2 | 516807.6 | 2.211 |
| 524288 | 30 | local-alpha-beta-cuda-1-run0 | 1229.667 | 426365.9 | 423458.8 | 158.875 |
| 524288 | 30 | local-alpha-beta-openmp-16-run0 | 626.675 | 836619.0 | 835766.0 | 4.758 |
| 524288 | 30 | local-alpha-beta-cuda-1-run1 | 1205.494 | 434915.4 | 431380.7 | 161.354 |
| 524288 | 30 | local-alpha-beta-openmp-16-run1 | 621.483 | 843607.8 | 843117.2 | 3.777 |
| 524288 | 30 | bend-cuda-16-run2 | 440.102 | 1191287.6 | 1193756.9 | 115.124 |
| 524288 | 30 | bend-cuda-16-run1 | 437.085 | 1199511.5 | 1205300.3 | 98.138 |
| 524288 | 30 | bend-16-run0 | 974.987 | 537738.7 | 539303.3 | 1.855 |
| 524288 | 30 | local-alpha-beta-openmp-16-run2 | 626.888 | 836334.1 | 836402.4 | 3.696 |
| 524288 | 30 | bend-cuda-16-run0 | 436.498 | 1201123.8 | 1203417.3 | 115.948 |
| 524288 | 30 | bend-16-run1 | 975.471 | 537471.7 | 538524.9 | 1.765 |
