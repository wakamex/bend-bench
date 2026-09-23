# Resident-process endgame throughput

Repeated fixed corpus of 16 positions, two warmup batches and ten measured batches per process. Latency includes answer formatting, pipe delivery and host observation; it is not kernel time. Startup-to-READY is separate; first-use lazy setup is covered by warmups.

| Positions per batch | Implementation | Mean delivered batch ms | Positions/second | Startup to READY ms |
|---|---|---:|---:|---:|
| 16 | bend-1 | 0.443 | 36144.2 | 2.011 |
| 16 | bend-16 | 0.652 | 24546.5 | 1.752 |
| 16 | local-alpha-beta-openmp-16 | 0.093 | 172595.9 | 2.532 |
| 16 | bend-cuda-16 | 32.978 | 485.2 | 90.342 |
| 16 | local-alpha-beta-cuda-1 | 31.221 | 512.5 | 90.672 |
| 256 | bend-1 | 5.748 | 44540.3 | 1.966 |
| 256 | bend-16 | 1.032 | 247957.8 | 2.022 |
| 256 | local-alpha-beta-openmp-16 | 0.386 | 663192.1 | 3.101 |
| 256 | bend-cuda-16 | 26.613 | 9619.2 | 91.561 |
| 256 | local-alpha-beta-cuda-1 | 25.565 | 10013.5 | 93.493 |
| 4096 | bend-1 | 92.271 | 44390.8 | 2.212 |
| 4096 | bend-16 | 11.728 | 349250.0 | 1.839 |
| 4096 | local-alpha-beta-openmp-16 | 5.438 | 753169.2 | 2.591 |
| 4096 | bend-cuda-16 | 38.993 | 105045.1 | 103.493 |
| 4096 | local-alpha-beta-cuda-1 | 39.052 | 104884.9 | 87.967 |
