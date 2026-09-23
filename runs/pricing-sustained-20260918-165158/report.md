# Sustained Asian-call pricing

Request-to-host quote timing includes simulation, payoff moments, reduction, price and standard error. Setup is outside repeated requests. Full-process wall time is retained separately. Two warmups, 30 measured batches and three fresh processes per implementation. Distinct deterministic path seeds per batch; the standard error uses the nominal independent-path formula.

| Paths | Implementation | Repetition | Mean quote ms | Paths/second |
|---:|---|---:|---:|---:|
| 65536 | local-cuda | 2 | 0.180 | 364603114.3 |
| 65536 | bend | 2 | 66.593 | 984131.0 |
| 65536 | local-cuda | 0 | 0.193 | 340058997.7 |
| 65536 | local-openmp | 0 | 35.375 | 1852614.7 |
| 65536 | local-cuda | 1 | 0.176 | 372787965.1 |
| 65536 | local-openmp | 1 | 34.493 | 1899976.1 |
| 65536 | bend-cuda | 2 | 1.800 | 36399985.0 |
| 65536 | bend-cuda | 1 | 2.943 | 22266769.6 |
| 65536 | bend | 0 | 65.425 | 1001699.6 |
| 65536 | local-openmp | 2 | 35.321 | 1855428.4 |
| 65536 | bend-cuda | 0 | 2.420 | 27083164.4 |
| 65536 | bend | 1 | 68.109 | 962222.8 |
| 262144 | local-cuda | 2 | 0.479 | 547682209.0 |
| 262144 | bend | 2 | 239.666 | 1093788.0 |
| 262144 | local-cuda | 0 | 0.488 | 536704332.7 |
| 262144 | local-openmp | 0 | 139.491 | 1879287.1 |
| 262144 | local-cuda | 1 | 0.490 | 535007736.0 |
| 262144 | local-openmp | 1 | 142.105 | 1844726.7 |
| 262144 | bend-cuda | 2 | 3.503 | 74825622.2 |
| 262144 | bend-cuda | 1 | 3.141 | 83457774.7 |
| 262144 | bend | 0 | 241.006 | 1087707.4 |
| 262144 | local-openmp | 2 | 138.042 | 1899014.9 |
| 262144 | bend-cuda | 0 | 3.501 | 74873956.7 |
| 262144 | bend | 1 | 239.653 | 1093850.3 |
