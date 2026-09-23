# Resident-process endgame throughput

Repeated fixed corpus of 16 positions, two warmup batches and ten measured batches per process. Latency includes answer formatting, pipe delivery and host observation; it is not kernel time. Startup-to-READY is separate; first-use lazy setup is covered by warmups.

| Positions per batch | Implementation | Mean delivered batch ms | Positions/second | Startup to READY ms |
|---|---|---:|---:|---:|
| 65536 | bend-1 | 1425.180 | 45984.4 | 1.866 |
| 65536 | bend-16 | 151.851 | 431580.9 | 2.069 |
| 65536 | local-alpha-beta-openmp-16 | 89.892 | 729055.7 | 2.756 |
| 65536 | bend-cuda-16 | 124.219 | 527582.5 | 122.886 |
| 65536 | local-alpha-beta-cuda-1 | 121.157 | 540919.5 | 93.912 |
