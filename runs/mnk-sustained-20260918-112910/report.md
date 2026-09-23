# Resident-process endgame throughput

Deterministic distinct legal positions, independently solved by the tuple-board oracle. Larger corpora preserve the original prefix. Two warmup batches per process. Latency includes answer formatting, pipe delivery and host observation; it is not kernel time. Full-process throughput counts all completed batches including warmups and includes startup and shutdown.

| Distinct positions | Positions per batch | Measured batches | Implementation | Mean delivered batch ms | Positions/second excluding warmups | Positions/second full process | Startup to READY ms |
|---:|---:|---:|---|---:|---:|---:|---:|
| 16 | 524288 | 30 | local-alpha-beta-cuda-1-run2 | 1199.422 | 437117.1 | 433826.4 | 150.126 |
| 16 | 524288 | 30 | local-alpha-beta-cuda-1-run0 | 1199.102 | 437233.8 | 433154.1 | 124.214 |
| 16 | 524288 | 30 | local-alpha-beta-tight-cuda-1-run2 | 1099.145 | 476996.3 | 473822.1 | 124.797 |
| 16 | 524288 | 30 | local-alpha-beta-position-tight-cuda-1-run0 | 965.424 | 543064.8 | 539674.4 | 133.224 |
| 16 | 524288 | 30 | local-alpha-beta-position-tight-cuda-1-run2 | 974.575 | 537965.5 | 534837.9 | 147.194 |
| 16 | 524288 | 30 | bend-16-run1 | 1013.806 | 517148.3 | 516148.8 | 1.940 |
| 16 | 524288 | 30 | bend-16-run0 | 983.788 | 532927.7 | 533483.3 | 3.112 |
| 16 | 524288 | 30 | bend-16-run2 | 974.352 | 538089.0 | 540256.8 | 2.062 |
| 16 | 524288 | 30 | local-alpha-beta-tight-cuda-1-run1 | 1099.655 | 476774.9 | 473138.2 | 161.865 |
| 16 | 524288 | 30 | local-alpha-beta-openmp-16-run1 | 612.259 | 856316.8 | 855575.9 | 3.520 |
| 16 | 524288 | 30 | local-alpha-beta-openmp-tight-16-run2 | 560.859 | 934793.8 | 935367.5 | 3.637 |
| 16 | 524288 | 30 | bend-cuda-16-run2 | 432.332 | 1212698.9 | 1210021.2 | 135.443 |
| 16 | 524288 | 30 | local-alpha-beta-tight-cuda-1-run0 | 1102.090 | 475721.8 | 472616.2 | 129.771 |
| 16 | 524288 | 30 | bend-cuda-16-run0 | 436.626 | 1200772.4 | 1206163.3 | 85.862 |
| 16 | 524288 | 30 | local-alpha-beta-openmp-16-run2 | 621.369 | 843762.8 | 841544.8 | 3.968 |
| 16 | 524288 | 30 | local-alpha-beta-cuda-1-run1 | 1201.161 | 436484.3 | 433765.4 | 157.774 |
| 16 | 524288 | 30 | local-alpha-beta-openmp-tight-16-run1 | 566.222 | 925940.0 | 926151.6 | 3.566 |
| 16 | 524288 | 30 | local-alpha-beta-position-tight-cuda-1-run1 | 954.998 | 548993.8 | 545016.0 | 157.820 |
| 16 | 524288 | 30 | local-alpha-beta-openmp-16-run0 | 624.661 | 839315.6 | 839460.3 | 3.689 |
| 16 | 524288 | 30 | local-alpha-beta-openmp-tight-16-run0 | 562.896 | 931412.0 | 931826.1 | 3.677 |
| 16 | 524288 | 30 | bend-cuda-16-run1 | 438.302 | 1196180.2 | 1199030.1 | 112.573 |
| 1024 | 524288 | 30 | local-alpha-beta-cuda-1-run2 | 1153.928 | 454350.8 | 451299.1 | 143.095 |
| 1024 | 524288 | 30 | local-alpha-beta-cuda-1-run0 | 1160.571 | 451750.1 | 448871.0 | 141.758 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-cuda-1-run2 | 957.109 | 547782.9 | 543662.1 | 125.928 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-cuda-1-run0 | 1132.951 | 462763.3 | 459738.3 | 124.964 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-cuda-1-run2 | 1138.000 | 460710.1 | 457671.0 | 141.014 |
| 1024 | 524288 | 30 | bend-16-run1 | 769.637 | 681214.4 | 684659.9 | 1.830 |
| 1024 | 524288 | 30 | bend-16-run0 | 770.955 | 680049.9 | 682506.9 | 1.907 |
| 1024 | 524288 | 30 | bend-16-run2 | 769.409 | 681416.9 | 684262.8 | 1.978 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-cuda-1-run1 | 960.862 | 545643.3 | 541189.1 | 160.385 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-16-run1 | 641.683 | 817051.4 | 816211.8 | 3.638 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-16-run2 | 566.571 | 925371.0 | 926478.9 | 3.499 |
| 1024 | 524288 | 30 | bend-cuda-16-run2 | 539.828 | 971213.1 | 975890.4 | 116.566 |
| 1024 | 524288 | 30 | local-alpha-beta-tight-cuda-1-run0 | 1192.650 | 439599.2 | 429065.9 | 165.600 |
| 1024 | 524288 | 30 | bend-cuda-16-run0 | 558.103 | 939410.1 | 943541.7 | 99.211 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-16-run2 | 666.409 | 786736.0 | 786450.2 | 3.749 |
| 1024 | 524288 | 30 | local-alpha-beta-cuda-1-run1 | 1164.028 | 450408.2 | 446365.0 | 159.332 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-16-run1 | 547.503 | 957598.0 | 957081.7 | 3.628 |
| 1024 | 524288 | 30 | local-alpha-beta-position-tight-cuda-1-run1 | 1128.991 | 464386.3 | 460993.9 | 159.571 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-16-run0 | 644.332 | 813691.7 | 813847.3 | 3.609 |
| 1024 | 524288 | 30 | local-alpha-beta-openmp-tight-16-run0 | 549.679 | 953808.2 | 953379.9 | 3.705 |
| 1024 | 524288 | 30 | bend-cuda-16-run1 | 536.186 | 977809.5 | 983609.9 | 115.569 |
