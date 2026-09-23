# Resident-process endgame throughput

Repeated fixed corpus of 16 positions, two warmup batches per process. Latency includes answer formatting, pipe delivery and host observation; it is not kernel time. Full-process throughput counts all completed batches including warmups and includes startup and shutdown.

| Positions per batch | Measured batches | Implementation | Mean delivered batch ms | Positions/second excluding warmups | Positions/second full process | Startup to READY ms |
|---|---:|---|---:|---:|---:|---:|
| 524288 | 10 | bend-cuda-16 | 394.110 | 1330307.7 | 1320527.8 | 78.415 |
| 524288 | 10 | local-alpha-beta-cuda-1 | 386.224 | 1357472.0 | 1341958.6 | 81.221 |
| 524288 | 30 | bend-cuda-16 | 441.910 | 1186414.5 | 1192264.2 | 78.456 |
| 524288 | 30 | local-alpha-beta-cuda-1 | 431.948 | 1213777.1 | 1220176.8 | 77.979 |
| 524288 | 100 | bend-cuda-16 | 466.910 | 1122888.1 | 1125948.0 | 78.316 |
| 524288 | 100 | local-alpha-beta-cuda-1 | 461.868 | 1135146.4 | 1138022.5 | 79.425 |
