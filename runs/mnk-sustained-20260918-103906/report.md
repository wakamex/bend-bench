# Resident-process endgame throughput

Repeated fixed corpus of 16 positions, two warmup batches and ten measured batches per process. Latency includes answer formatting, pipe delivery and host observation; it is not kernel time. Startup-to-READY is separate; first-use lazy setup is covered by warmups.

| Positions per batch | Implementation | Mean delivered batch ms | Positions/second | Startup to READY ms |
|---|---|---:|---:|---:|
| 65536 | bend-cuda-16 | 92.698 | 706980.4 | 89.789 |
| 65536 | local-alpha-beta-cuda-1 | 89.665 | 730901.4 | 91.048 |
| 131072 | bend-cuda-16 | 130.089 | 1007559.8 | 88.618 |
| 131072 | local-alpha-beta-cuda-1 | 135.877 | 964637.0 | 93.366 |
| 262144 | bend-cuda-16 | 220.644 | 1188085.4 | 91.245 |
| 262144 | local-alpha-beta-cuda-1 | 222.031 | 1180666.0 | 94.588 |
| 524288 | bend-cuda-16 | 393.005 | 1334050.7 | 88.428 |
| 524288 | local-alpha-beta-cuda-1 | 388.308 | 1350186.0 | 95.276 |
| 1048576 | bend-cuda-16 | 772.785 | 1356878.9 | 88.729 |
| 1048576 | local-alpha-beta-cuda-1 | 759.392 | 1380810.4 | 88.749 |
| 2097152 | bend-cuda-16 | 1571.193 | 1334751.1 | 89.943 |
| 2097152 | local-alpha-beta-cuda-1 | 1582.429 | 1325274.3 | 88.804 |
| 4194304 | bend-cuda-16 | 3197.646 | 1311684.7 | 87.237 |
| 4194304 | local-alpha-beta-cuda-1 | 3186.618 | 1316224.3 | 90.288 |
