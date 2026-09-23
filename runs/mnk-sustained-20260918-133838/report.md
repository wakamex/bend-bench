# Resident-process endgame throughput

Deterministic distinct legal positions, independently solved by the tuple-board oracle. Larger corpora preserve the original prefix. Two warmup batches per process. Latency includes answer formatting, pipe delivery and host observation; it is not kernel time. Full-process throughput counts all completed batches including warmups and includes startup and shutdown.

| Distinct positions | Positions per batch | Measured batches | Implementation | Mean delivered batch ms | Positions/second excluding warmups | Positions/second full process | Startup to READY ms | Mean search-to-host ms | Mean output ms |
|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-bulk-literal-cuda-1-run1 | 925.755 | 566335.7 | 561540.9 | 155.885 | 787.081 | 138.667 |
| 1024 | 524288 | 30 | bend-cuda-16-run0 | 532.511 | 984557.7 | 993312.9 | 84.606 | 177.600 | 354.900 |
| 1024 | 524288 | 30 | bend-16-run0 | 776.739 | 674986.4 | 679196.8 | 1.871 | 561.433 | 215.300 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-cuda-1-run1 | 773.435 | 677869.4 | 670933.8 | 164.061 | 635.633 | 137.764 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-16-run2 | 580.276 | 903514.1 | 905975.7 | 3.667 | 219.109 | 361.161 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-bulk-cuda-1-run2 | 950.656 | 551501.1 | 546992.7 | 156.449 | 810.832 | 139.801 |
| 1024 | 524288 | 30 | bend-16-run1 | 782.319 | 670171.6 | 673242.0 | 1.865 | 563.267 | 219.100 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-bulk-16-run2 | 359.568 | 1458105.4 | 1454078.5 | 3.819 | 219.724 | 139.948 |
| 1024 | 524288 | 30 | local-alpha-beta-cuda-1-run1 | 1153.109 | 454673.3 | 451569.4 | 156.480 | 833.072 | 320.031 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-bulk-literal-cuda-1-run0 | 927.138 | 565491.0 | 561120.7 | 137.237 | 788.322 | 138.806 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-16-run1 | 668.708 | 784031.6 | 784903.1 | 3.652 | 308.281 | 360.420 |
| 1024 | 524288 | 30 | local-alpha-beta-cuda-1-run2 | 1153.788 | 454405.9 | 451288.4 | 159.999 | 834.357 | 319.423 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-cuda-1-run0 | 774.485 | 676950.8 | 670453.9 | 140.285 | 636.254 | 138.239 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-16-run0 | 554.604 | 945338.4 | 942632.4 | 3.608 | 218.636 | 335.961 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-bulk-literal-cuda-1-run2 | 924.913 | 566851.2 | 562124.0 | 152.320 | 785.813 | 139.094 |
| 1024 | 524288 | 30 | bend-cuda-16-run1 | 534.830 | 980289.7 | 989345.7 | 84.218 | 179.767 | 355.067 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-bulk-16-run0 | 356.744 | 1469649.6 | 1467702.6 | 3.449 | 220.162 | 136.733 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-literal-cuda-1-run2 | 740.353 | 708159.3 | 701033.2 | 153.994 | 600.856 | 139.488 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-cuda-1-run0 | 961.102 | 545507.1 | 541445.7 | 122.958 | 636.277 | 324.817 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-cuda-1-run2 | 1134.611 | 462086.2 | 458814.6 | 140.806 | 812.289 | 322.315 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-16-run0 | 648.499 | 808464.4 | 808610.3 | 3.439 | 307.866 | 340.626 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-cuda-1-run2 | 957.985 | 547281.9 | 542986.9 | 155.163 | 636.026 | 321.952 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-cuda-1-run0 | 1134.671 | 462061.7 | 459145.1 | 124.102 | 811.986 | 322.678 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-literal-cuda-1-run1 | 740.783 | 707748.5 | 701490.0 | 125.688 | 601.713 | 139.077 |
| 1024 | 524288 | 30 | bend-cuda-16-run2 | 536.301 | 977600.3 | 984964.2 | 85.693 | 181.733 | 354.567 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-literal-cuda-1-run0 | 745.660 | 703118.9 | 696582.7 | 139.467 | 601.486 | 144.158 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-cuda-1-run1 | 958.730 | 546857.0 | 542203.2 | 142.136 | 636.085 | 322.638 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-16-run1 | 556.076 | 942836.0 | 942199.8 | 4.123 | 219.108 | 336.960 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-bulk-literal-16-run2 | 441.599 | 1187248.8 | 1185504.8 | 3.691 | 305.139 | 136.661 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-bulk-literal-16-run1 | 445.110 | 1177883.2 | 1177304.6 | 3.701 | 306.931 | 138.333 |
| 1024 | 524288 | 30 | bend-16-run2 | 850.830 | 616208.0 | 621154.4 | 1.978 | 624.433 | 226.367 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-bulk-cuda-1-run2 | 774.938 | 676554.7 | 654794.8 | 257.373 | 617.652 | 157.245 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-bulk-literal-16-run0 | 466.152 | 1124715.7 | 1124172.8 | 3.518 | 323.886 | 142.433 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-bulk-16-run1 | 368.804 | 1421589.8 | 1414701.3 | 4.071 | 226.278 | 142.765 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-bulk-cuda-1-run1 | 1068.076 | 490871.3 | 490734.0 | 144.413 | 918.029 | 150.049 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-16-run2 | 656.540 | 798561.8 | 797871.8 | 3.806 | 311.271 | 345.262 |
| 1024 | 524288 | 30 | local-alpha-beta-cuda-1-run0 | 1156.112 | 453492.5 | 449303.2 | 147.314 | 826.158 | 329.946 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-bulk-cuda-1-run0 | 936.296 | 559959.7 | 555976.0 | 125.423 | 794.397 | 141.888 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-cuda-1-run1 | 1117.706 | 469074.9 | 464823.6 | 137.889 | 795.210 | 322.490 |
