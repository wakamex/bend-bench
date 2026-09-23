# Continued MNK scheduling and output comparison

Passed original measurements are retained and labeled. Rejected attempts remain in the original run; replacements have separate paths. The original timing script, provenance and saved artifacts were verified unchanged. Search-to-host includes transfers and is not kernel-only time.

| Implementation | Repetition | Origin | Delivered positions/s | Search-to-host ms | Output ms |
|---|---:|---|---:|---:|---:|
| local-alpha-beta-openmp-tight-bulk | 0 | retained original | 1451861.0 | 222.789 | 138.481 |
| local-alpha-beta-openmp-tight-bulk-chunk16 | 0 | retained original | 1477646.0 | 217.940 | 136.982 |
| bend-chunks | 2 | retained original | 700757.9 | 563.500 | 184.767 |
| bend-chunks | 0 | retained original | 676866.7 | 583.400 | 191.167 |
| bend | 2 | retained original | 663548.4 | 568.933 | 221.233 |
| bend-chunks-cuda | 0 | retained original | 1143737.7 | 174.333 | 284.067 |
| bend | 0 | retained original | 560327.5 | 689.067 | 246.600 |
| local-alpha-beta-openmp-tight-bulk-chunk64 | 1 | retained original | 1448420.8 | 223.500 | 138.631 |
| bend-chunks | 1 | retained original | 619745.6 | 649.733 | 196.267 |
| bend-chunks-cuda | 2 | continuation | 1182550.7 | 173.933 | 269.433 |
| bend | 1 | continuation | 618060.2 | 623.767 | 224.433 |
| local-alpha-beta-openmp-tight-bulk-chunk64 | 2 | continuation | 1522724.5 | 216.832 | 127.631 |
| bend-cuda | 2 | continuation | 1016516.3 | 174.533 | 341.200 |
| local-alpha-beta-openmp-tight-bulk | 2 | continuation | 1526173.8 | 219.325 | 124.408 |
| bend-chunks-cuda | 1 | continuation | 1200291.3 | 173.067 | 263.733 |
| local-alpha-beta-openmp-tight-bulk-chunk256 | 0 | continuation | 1513979.9 | 219.615 | 126.843 |
| local-alpha-beta-openmp-tight-bulk | 1 | continuation | 1519884.1 | 219.679 | 125.428 |
| local-alpha-beta-openmp-tight-bulk-chunk16 | 1 | continuation | 1532934.3 | 217.049 | 125.033 |
| local-alpha-beta-openmp-tight-bulk-chunk256 | 1 | continuation | 1508266.2 | 221.216 | 126.563 |
| local-alpha-beta-openmp-tight-bulk-chunk256 | 2 | continuation | 1519862.2 | 219.446 | 125.665 |
| bend-cuda | 0 | continuation | 1005114.9 | 175.767 | 345.900 |
| local-alpha-beta-openmp-tight-bulk-chunk16 | 2 | continuation | 1516471.8 | 217.404 | 128.493 |
| local-alpha-beta-openmp-tight-bulk-chunk64 | 0 | continuation | 1513979.6 | 217.237 | 129.183 |
| bend-cuda | 1 | continuation | 1007308.7 | 176.533 | 343.967 |
