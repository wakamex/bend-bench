# Resident-process endgame throughput

Repeated fixed corpus of 16 positions, two warmup batches per process. Latency includes answer formatting, pipe delivery and host observation; it is not kernel time. Full-process throughput counts all completed batches including warmups and includes startup and shutdown.

| Positions per batch | Measured batches | Implementation | Mean delivered batch ms | Positions/second excluding warmups | Positions/second full process | Startup to READY ms |
|---|---:|---|---:|---:|---:|---:|
| 524288 | 100 | bend-cuda-16-run0 | 471.096 | 1112910.3 | 1115226.0 | 89.756 |
| 524288 | 100 | local-alpha-beta-cuda-1-run0 | 1212.519 | 432395.7 | 431568.3 | 148.474 |
