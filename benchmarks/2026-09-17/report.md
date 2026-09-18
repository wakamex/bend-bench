# Bend benchmark results

Times are medians of correctness-gated measured executions, excluding checks and warmups. End-to-end includes process startup and output. Device-sequence event time is distinct from a kernel-only sum. Unmeasured metrics remain blank.

Preparation: passed. Fingerprint: `724334600b9aa1af788d719fb4610d96c541ffcb0f107682f1804dfe2d57ff5a`.

| Workload / implementation / threads | Gate | Checked | Runs | End-to-end seconds | Compute seconds | Device-sequence seconds | Kernel seconds | Speedup | Efficiency | Peak host RSS KiB |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| vendor/bfs/serial-c/1 | passed | True | 10 | 4.267624 |  |  |  | 1.000000 | 1.000000 | 2184.000000 |
| vendor/bfs/bend/1 | passed | True | 10 | 4.560058 |  |  |  | 1.000000 | 1.000000 | 2436.000000 |
| vendor/bfs/openmp/1 | passed | True | 10 | 4.222412 | 4.219689 |  |  | 1.000000 | 1.000000 | 5328.000000 |
| vendor/bfs/bend/2 | passed | True | 10 | 2.300352 |  |  |  | 1.982330 | 0.991165 | 2464.000000 |
| vendor/bfs/openmp/2 | passed | True | 10 | 2.138685 | 2.136064 |  |  | 1.974303 | 0.987151 | 5460.000000 |
| vendor/bfs/bend/4 | passed | True | 10 | 1.167040 |  |  |  | 3.907370 | 0.976843 | 2192.000000 |
| vendor/bfs/openmp/4 | passed | True | 10 | 1.082620 | 1.079608 |  |  | 3.900180 | 0.975045 | 5420.000000 |
| vendor/bfs/bend/8 | passed | True | 10 | 0.606769 |  |  |  | 7.515316 | 0.939414 | 2212.000000 |
| vendor/bfs/openmp/8 | passed | True | 10 | 0.550805 | 0.547882 |  |  | 7.665888 | 0.958236 | 5248.000000 |
| vendor/bfs/bend/16 | passed | True | 10 | 0.328214 |  |  |  | 13.893545 | 0.868347 | 2192.000000 |
| vendor/bfs/openmp/16 | passed | True | 10 | 0.288554 | 0.285715 |  |  | 14.633004 | 0.914563 | 5596.000000 |
| vendor/bfs/bend/32 | passed | True | 10 | 0.212424 |  |  |  | 21.466773 | 0.670837 | 2192.000000 |
| vendor/bfs/openmp/32 | passed | True | 10 | 0.175765 | 0.172677 |  |  | 24.023061 | 0.750721 | 5972.000000 |
| vendor/bfs/bend-cuda/32 | passed | True | 10 | 0.527544 |  |  |  |  |  | 90384.000000 |
| vendor/editdist/serial-c/1 | passed | True | 10 | 2.617002 |  |  |  | 1.000000 | 1.000000 | 2184.000000 |
| vendor/editdist/bend/1 | passed | True | 10 | 5.865410 |  |  |  | 1.000000 | 1.000000 | 2484.000000 |
| vendor/editdist/openmp/1 | passed | True | 10 | 2.618690 | 2.615964 |  |  | 1.000000 | 1.000000 | 5484.000000 |
| vendor/editdist/bend/2 | passed | True | 10 | 2.955764 |  |  |  | 1.984397 | 0.992199 | 2464.000000 |
| vendor/editdist/openmp/2 | passed | True | 10 | 1.327200 | 1.324546 |  |  | 1.973093 | 0.986547 | 5504.000000 |
| vendor/editdist/bend/4 | passed | True | 10 | 1.492744 |  |  |  | 3.929282 | 0.982321 | 2464.000000 |
| vendor/editdist/openmp/4 | passed | True | 10 | 0.669974 | 0.667013 |  |  | 3.908642 | 0.977161 | 5324.000000 |
| vendor/editdist/bend/8 | passed | True | 10 | 0.775255 |  |  |  | 7.565783 | 0.945723 | 2484.000000 |
| vendor/editdist/openmp/8 | passed | True | 10 | 0.342146 | 0.339481 |  |  | 7.653718 | 0.956715 | 5304.000000 |
| vendor/editdist/bend/16 | passed | True | 10 | 0.406189 |  |  |  | 14.440098 | 0.902506 | 2184.000000 |
| vendor/editdist/openmp/16 | passed | True | 10 | 0.183143 | 0.180387 |  |  | 14.298624 | 0.893664 | 5712.000000 |
| vendor/editdist/bend/32 | passed | True | 10 | 0.229631 |  |  |  | 25.542728 | 0.798210 | 2176.000000 |
| vendor/editdist/openmp/32 | passed | True | 10 | 0.147078 | 0.143970 |  |  | 17.804831 | 0.556401 | 5712.000000 |
| vendor/editdist/bend-cuda/32 | passed | True | 10 | 0.313773 |  |  |  |  |  | 90348.000000 |
| vendor/gameoflife/serial-c/1 | passed | True | 10 | 11.857855 |  |  |  | 1.000000 | 1.000000 | 2036.000000 |
| vendor/gameoflife/bend/1 | passed | True | 10 | 10.878930 |  |  |  | 1.000000 | 1.000000 | 2464.000000 |
| vendor/gameoflife/openmp/1 | passed | True | 10 | 11.936145 | 11.931396 |  |  | 1.000000 | 1.000000 | 11184.000000 |
| vendor/gameoflife/bend/2 | passed | True | 10 | 5.517050 |  |  |  | 1.971874 | 0.985937 | 2468.000000 |
| vendor/gameoflife/openmp/2 | passed | True | 10 | 6.007657 | 6.002833 |  |  | 1.986822 | 0.993411 | 11300.000000 |
| vendor/gameoflife/bend/4 | passed | True | 10 | 2.789975 |  |  |  | 3.899292 | 0.974823 | 2428.000000 |
| vendor/gameoflife/openmp/4 | passed | True | 10 | 3.037876 | 3.033080 |  |  | 3.929109 | 0.982277 | 11300.000000 |
| vendor/gameoflife/bend/8 | passed | True | 10 | 1.414044 |  |  |  | 7.693488 | 0.961686 | 2468.000000 |
| vendor/gameoflife/openmp/8 | passed | True | 10 | 1.539429 | 1.534490 |  |  | 7.753618 | 0.969202 | 11532.000000 |
| vendor/gameoflife/bend/16 | passed | True | 10 | 0.742040 |  |  |  | 14.660838 | 0.916302 | 2176.000000 |
| vendor/gameoflife/openmp/16 | passed | True | 10 | 0.823569 | 0.818564 |  |  | 14.493192 | 0.905824 | 9764.000000 |
| vendor/gameoflife/bend/32 | passed | True | 10 | 0.582823 |  |  |  | 18.665908 | 0.583310 | 2184.000000 |
| vendor/gameoflife/openmp/32 | passed | True | 10 | 0.727863 | 0.721923 |  |  | 16.398897 | 0.512466 | 6560.000000 |
| vendor/gameoflife/bend-cuda/32 | passed | True | 10 | 0.134592 |  |  |  |  |  | 87900.000000 |
| vendor/gameoflife/conventional-cuda/1 | passed | True | 10 | 0.201333 |  | 0.014380 |  | 1.000000 | 1.000000 | 134356.000000 |
| vendor/hashmap/serial-c/1 | passed | True | 10 | 1.021058 |  |  |  | 1.000000 | 1.000000 | 2440.000000 |
| vendor/hashmap/bend/1 | passed | True | 10 | 3.778342 |  |  |  | 1.000000 | 1.000000 | 2712.000000 |
| vendor/hashmap/openmp/1 | passed | True | 10 | 1.006901 | 1.003609 |  |  | 1.000000 | 1.000000 | 5492.000000 |
| vendor/hashmap/bend/2 | passed | True | 10 | 1.987310 |  |  |  | 1.901235 | 0.950617 | 2976.000000 |
| vendor/hashmap/openmp/2 | passed | True | 10 | 0.509987 | 0.506792 |  |  | 1.974367 | 0.987184 | 5464.000000 |
| vendor/hashmap/bend/4 | passed | True | 10 | 1.036724 |  |  |  | 3.644500 | 0.911125 | 3716.000000 |
| vendor/hashmap/openmp/4 | passed | True | 10 | 0.260053 | 0.257347 |  |  | 3.871905 | 0.967976 | 5688.000000 |
| vendor/hashmap/bend/8 | passed | True | 10 | 0.594085 |  |  |  | 6.359937 | 0.794992 | 5200.000000 |
| vendor/hashmap/openmp/8 | passed | True | 10 | 0.172453 | 0.169504 |  |  | 5.838710 | 0.729839 | 6556.000000 |
| vendor/hashmap/bend/16 | passed | True | 10 | 0.343665 |  |  |  | 10.994255 | 0.687141 | 7816.000000 |
| vendor/hashmap/openmp/16 | passed | True | 10 | 0.092906 | 0.089669 |  |  | 10.837854 | 0.677366 | 7656.000000 |
| vendor/hashmap/bend/32 | passed | True | 10 | 0.323291 |  |  |  | 11.687121 | 0.365223 | 12640.000000 |
| vendor/hashmap/openmp/32 | passed | True | 10 | 0.261803 | 0.257899 |  |  | 3.846020 | 0.120188 | 10136.000000 |
| vendor/hashmap/bend-cuda/32 | passed | True | 10 | 0.940431 |  |  |  |  |  | 85040.000000 |
| vendor/kmeans/serial-c/1 | passed | True | 10 | 3.191742 |  |  |  | 1.000000 | 1.000000 | 6076.000000 |
| vendor/kmeans/bend/1 | passed | True | 10 | 3.654954 |  |  |  | 1.000000 | 1.000000 | 23028.000000 |
| vendor/kmeans/openmp/1 | passed | True | 10 | 3.635243 | 3.632347 |  |  | 1.000000 | 1.000000 | 9896.000000 |
| vendor/kmeans/bend/2 | passed | True | 10 | 1.967433 |  |  |  | 1.857727 | 0.928863 | 20480.000000 |
| vendor/kmeans/openmp/2 | passed | True | 10 | 1.922139 | 1.918721 |  |  | 1.891249 | 0.945624 | 14812.000000 |
| vendor/kmeans/bend/4 | passed | True | 10 | 1.068147 |  |  |  | 3.421770 | 0.855443 | 19344.000000 |
| vendor/kmeans/openmp/4 | passed | True | 10 | 0.953388 | 0.950017 |  |  | 3.812975 | 0.953244 | 24540.000000 |
| vendor/kmeans/bend/8 | passed | True | 10 | 0.699987 |  |  |  | 5.221459 | 0.652682 | 22620.000000 |
| vendor/kmeans/openmp/8 | passed | True | 10 | 0.564019 | 0.560183 |  |  | 6.445253 | 0.805657 | 43972.000000 |
| vendor/kmeans/bend/16 | passed | True | 10 | 0.472168 |  |  |  | 7.740792 | 0.483799 | 22620.000000 |
| vendor/kmeans/openmp/16 | passed | True | 10 | 0.420270 | 0.414873 |  |  | 8.649782 | 0.540611 | 83164.000000 |
| vendor/kmeans/bend/32 | passed | True | 10 | 0.417257 |  |  |  | 8.759481 | 0.273734 | 26324.000000 |
| vendor/kmeans/openmp/32 | passed | True | 10 | 0.551554 | 0.544413 |  |  | 6.590910 | 0.205966 | 161312.000000 |
| vendor/kmeans/bend-cuda/32 | passed | True | 10 | 0.530980 |  |  |  |  |  | 85192.000000 |
| vendor/lexer/serial-c/1 | passed | True | 10 | 1.544646 |  |  |  | 1.000000 | 1.000000 | 2004.000000 |
| vendor/lexer/bend/1 | passed | True | 10 | 4.542112 |  |  |  | 1.000000 | 1.000000 | 2528.000000 |
| vendor/lexer/openmp/1 | passed | True | 10 | 1.595054 | 1.591321 |  |  | 1.000000 | 1.000000 | 5176.000000 |
| vendor/lexer/bend/2 | passed | True | 10 | 2.299391 |  |  |  | 1.975354 | 0.987677 | 2528.000000 |
| vendor/lexer/openmp/2 | passed | True | 10 | 0.830340 | 0.827021 |  |  | 1.920963 | 0.960482 | 5260.000000 |
| vendor/lexer/bend/4 | passed | True | 10 | 1.191339 |  |  |  | 3.812610 | 0.953153 | 2272.000000 |
| vendor/lexer/openmp/4 | passed | True | 10 | 0.405642 | 0.402932 |  |  | 3.932170 | 0.983042 | 5036.000000 |
| vendor/lexer/bend/8 | passed | True | 10 | 0.731255 |  |  |  | 6.211389 | 0.776424 | 2196.000000 |
| vendor/lexer/openmp/8 | passed | True | 10 | 0.254453 | 0.251420 |  |  | 6.268552 | 0.783569 | 5084.000000 |
| vendor/lexer/bend/16 | passed | True | 10 | 0.387359 |  |  |  | 11.725854 | 0.732866 | 2196.000000 |
| vendor/lexer/openmp/16 | passed | True | 10 | 0.149656 | 0.146780 |  |  | 10.658149 | 0.666134 | 5264.000000 |
| vendor/lexer/bend/32 | passed | True | 10 | 0.321261 |  |  |  | 14.138409 | 0.441825 | 2240.000000 |
| vendor/lexer/openmp/32 | passed | True | 10 | 0.285983 | 0.282503 |  |  | 5.577442 | 0.174295 | 5592.000000 |
| vendor/lexer/bend-cuda/32 | passed | True | 10 | 1.205302 |  |  |  |  |  | 83928.000000 |
| vendor/mandelbrot/serial-c/1 | passed | True | 10 | 4.627951 |  |  |  | 1.000000 | 1.000000 | 2020.000000 |
| vendor/mandelbrot/bend/1 | passed | True | 10 | 6.023355 |  |  |  | 1.000000 | 1.000000 | 2780.000000 |
| vendor/mandelbrot/openmp/1 | passed | True | 10 | 4.715212 | 4.712386 |  |  | 1.000000 | 1.000000 | 5192.000000 |
| vendor/mandelbrot/bend/2 | passed | True | 10 | 3.038014 |  |  |  | 1.982662 | 0.991331 | 2632.000000 |
| vendor/mandelbrot/openmp/2 | passed | True | 10 | 2.372501 | 2.369556 |  |  | 1.987444 | 0.993722 | 5244.000000 |
| vendor/mandelbrot/bend/4 | passed | True | 10 | 1.538965 |  |  |  | 3.913900 | 0.978475 | 2524.000000 |
| vendor/mandelbrot/openmp/4 | passed | True | 10 | 1.196301 | 1.193411 |  |  | 3.941493 | 0.985373 | 5292.000000 |
| vendor/mandelbrot/bend/8 | passed | True | 10 | 0.873332 |  |  |  | 6.896986 | 0.862123 | 2248.000000 |
| vendor/mandelbrot/openmp/8 | passed | True | 10 | 0.610679 | 0.607713 |  |  | 7.721258 | 0.965157 | 5096.000000 |
| vendor/mandelbrot/bend/16 | passed | True | 10 | 0.442066 |  |  |  | 13.625456 | 0.851591 | 2232.000000 |
| vendor/mandelbrot/openmp/16 | passed | True | 10 | 0.333416 | 0.330299 |  |  | 14.142123 | 0.883883 | 5428.000000 |
| vendor/mandelbrot/bend/32 | passed | True | 10 | 0.379230 |  |  |  | 15.883104 | 0.496347 | 2448.000000 |
| vendor/mandelbrot/openmp/32 | passed | True | 10 | 0.659881 | 0.653763 |  |  | 7.145547 | 0.223298 | 5684.000000 |
| vendor/mandelbrot/bend-cuda/32 | passed | True | 10 | 0.159211 |  |  |  |  |  | 78924.000000 |
| vendor/merkle/serial-c/1 | passed | True | 10 | 5.009620 |  |  |  | 1.000000 | 1.000000 | 133112.000000 |
| vendor/merkle/bend/1 | passed | True | 10 | 6.831147 |  |  |  | 1.000000 | 1.000000 | 133560.000000 |
| vendor/merkle/openmp/1 | passed | True | 10 | 2.461140 | 2.457012 |  |  | 1.000000 | 1.000000 | 70512.000000 |
| vendor/merkle/bend/2 | passed | True | 10 | 3.457629 |  |  |  | 1.975674 | 0.987837 | 133544.000000 |
| vendor/merkle/openmp/2 | passed | True | 10 | 1.244664 | 1.240529 |  |  | 1.977353 | 0.988677 | 70496.000000 |
| vendor/merkle/bend/4 | passed | True | 10 | 1.754066 |  |  |  | 3.894464 | 0.973616 | 133452.000000 |
| vendor/merkle/openmp/4 | passed | True | 10 | 0.636525 | 0.632025 |  |  | 3.866528 | 0.966632 | 70620.000000 |
| vendor/merkle/bend/8 | passed | True | 10 | 0.918819 |  |  |  | 7.434702 | 0.929338 | 133248.000000 |
| vendor/merkle/openmp/8 | passed | True | 10 | 0.331092 | 0.326836 |  |  | 7.433402 | 0.929175 | 70320.000000 |
| vendor/merkle/bend/16 | passed | True | 10 | 0.504594 |  |  |  | 13.537894 | 0.846118 | 132492.000000 |
| vendor/merkle/openmp/16 | passed | True | 10 | 0.180027 | 0.175555 |  |  | 13.670927 | 0.854433 | 69648.000000 |
| vendor/merkle/bend/32 | passed | True | 10 | 0.372007 |  |  |  | 18.362946 | 0.573842 | 132232.000000 |
| vendor/merkle/openmp/32 | passed | True | 10 | 0.156673 | 0.151977 |  |  | 15.708747 | 0.490898 | 69388.000000 |
| vendor/merkle/bend-cuda/32 | passed | True | 10 | 0.141866 |  |  |  |  |  | 79384.000000 |
| vendor/nbody/serial-c/1 | passed | True | 10 | 7.364004 |  |  |  | 1.000000 | 1.000000 | 2188.000000 |
| vendor/nbody/bend/1 | passed | True | 10 | 8.635381 |  |  |  | 1.000000 | 1.000000 | 2432.000000 |
| vendor/nbody/openmp/1 | passed | True | 10 | 7.351469 | 7.348728 |  |  | 1.000000 | 1.000000 | 5220.000000 |
| vendor/nbody/bend/2 | passed | True | 10 | 4.359656 |  |  |  | 1.980748 | 0.990374 | 2464.000000 |
| vendor/nbody/openmp/2 | passed | True | 10 | 3.698839 | 3.695797 |  |  | 1.987507 | 0.993754 | 5220.000000 |
| vendor/nbody/bend/4 | passed | True | 10 | 2.199322 |  |  |  | 3.926382 | 0.981596 | 2484.000000 |
| vendor/nbody/openmp/4 | passed | True | 10 | 1.881891 | 1.878921 |  |  | 3.906427 | 0.976607 | 5236.000000 |
| vendor/nbody/bend/8 | passed | True | 10 | 1.124240 |  |  |  | 7.681085 | 0.960136 | 2464.000000 |
| vendor/nbody/openmp/8 | passed | True | 10 | 0.955635 | 0.952748 |  |  | 7.692756 | 0.961595 | 5196.000000 |
| vendor/nbody/bend/16 | passed | True | 10 | 0.600484 |  |  |  | 14.380697 | 0.898794 | 2192.000000 |
| vendor/nbody/openmp/16 | passed | True | 10 | 0.500442 | 0.497556 |  |  | 14.689942 | 0.918121 | 5476.000000 |
| vendor/nbody/bend/32 | passed | True | 10 | 0.346710 |  |  |  | 24.906632 | 0.778332 | 2372.000000 |
| vendor/nbody/openmp/32 | passed | True | 10 | 0.338915 | 0.335882 |  |  | 21.691190 | 0.677850 | 5540.000000 |
| vendor/nbody/bend-cuda/32 | passed | True | 10 | 0.126697 |  |  |  |  |  | 79256.000000 |
| vendor/queens/serial-c/1 | passed | True | 10 | 4.786314 |  |  |  | 1.000000 | 1.000000 | 2160.000000 |
| vendor/queens/bend/1 | passed | True | 10 | 11.761275 |  |  |  | 1.000000 | 1.000000 | 2464.000000 |
| vendor/queens/openmp/1 | passed | True | 10 | 5.019228 | 5.016523 |  |  | 1.000000 | 1.000000 | 5240.000000 |
| vendor/queens/bend/2 | passed | True | 10 | 5.942378 |  |  |  | 1.979220 | 0.989610 | 2464.000000 |
| vendor/queens/openmp/2 | passed | True | 10 | 2.532238 | 2.529398 |  |  | 1.982131 | 0.991066 | 5160.000000 |
| vendor/queens/bend/4 | passed | True | 10 | 3.064051 |  |  |  | 3.838472 | 0.959618 | 2116.000000 |
| vendor/queens/openmp/4 | passed | True | 10 | 1.284261 | 1.281469 |  |  | 3.908263 | 0.977066 | 5332.000000 |
| vendor/queens/bend/8 | passed | True | 10 | 1.579392 |  |  |  | 7.446708 | 0.930839 | 2184.000000 |
| vendor/queens/openmp/8 | passed | True | 10 | 0.653091 | 0.650295 |  |  | 7.685344 | 0.960668 | 5216.000000 |
| vendor/queens/bend/16 | passed | True | 10 | 0.833675 |  |  |  | 14.107738 | 0.881734 | 2228.000000 |
| vendor/queens/openmp/16 | passed | True | 10 | 0.343239 | 0.340248 |  |  | 14.623118 | 0.913945 | 5496.000000 |
| vendor/queens/bend/32 | passed | True | 10 | 0.649663 |  |  |  | 18.103649 | 0.565739 | 2192.000000 |
| vendor/queens/openmp/32 | passed | True | 10 | 0.226930 | 0.223741 |  |  | 22.117936 | 0.691186 | 5668.000000 |
| vendor/queens/bend-cuda/32 | passed | True | 10 | 1.176182 |  |  |  |  |  | 79052.000000 |
| vendor/raytrace/serial-c/1 | passed | True | 10 | 8.090036 |  |  |  | 1.000000 | 1.000000 | 2192.000000 |
| vendor/raytrace/bend/1 | passed | True | 10 | 9.623470 |  |  |  | 1.000000 | 1.000000 | 2448.000000 |
| vendor/raytrace/openmp/1 | passed | True | 10 | 7.838944 | 7.836219 |  |  | 1.000000 | 1.000000 | 5268.000000 |
| vendor/raytrace/bend/2 | passed | True | 10 | 4.841646 |  |  |  | 1.987644 | 0.993822 | 2476.000000 |
| vendor/raytrace/openmp/2 | passed | True | 10 | 3.947567 | 3.944786 |  |  | 1.985766 | 0.992883 | 5172.000000 |
| vendor/raytrace/bend/4 | passed | True | 10 | 2.462313 |  |  |  | 3.908305 | 0.977076 | 2204.000000 |
| vendor/raytrace/openmp/4 | passed | True | 10 | 2.000755 | 1.997905 |  |  | 3.917994 | 0.979498 | 5244.000000 |
| vendor/raytrace/bend/8 | passed | True | 10 | 1.269614 |  |  |  | 7.579841 | 0.947480 | 2240.000000 |
| vendor/raytrace/openmp/8 | passed | True | 10 | 1.017723 | 1.014836 |  |  | 7.702432 | 0.962804 | 5244.000000 |
| vendor/raytrace/bend/16 | passed | True | 10 | 0.667246 |  |  |  | 14.422677 | 0.901417 | 2196.000000 |
| vendor/raytrace/openmp/16 | passed | True | 10 | 0.531689 | 0.528708 |  |  | 14.743478 | 0.921467 | 5500.000000 |
| vendor/raytrace/bend/32 | passed | True | 10 | 0.485868 |  |  |  | 19.806758 | 0.618961 | 2260.000000 |
| vendor/raytrace/openmp/32 | passed | True | 10 | 0.420899 | 0.417755 |  |  | 18.624298 | 0.582009 | 5756.000000 |
| vendor/raytrace/bend-cuda/32 | passed | True | 10 | 0.959704 |  |  |  |  |  | 79452.000000 |
| vendor/symreg/serial-c/1 | passed | True | 10 | 4.385660 |  |  |  | 1.000000 | 1.000000 | 2160.000000 |
| vendor/symreg/bend/1 | passed | True | 10 | 5.186741 |  |  |  | 1.000000 | 1.000000 | 2472.000000 |
| vendor/symreg/openmp/1 | passed | True | 10 | 4.415211 | 4.411308 |  |  | 1.000000 | 1.000000 | 9676.000000 |
| vendor/symreg/bend/2 | passed | True | 10 | 2.594849 |  |  |  | 1.998861 | 0.999430 | 2436.000000 |
| vendor/symreg/openmp/2 | passed | True | 10 | 2.215295 | 2.211126 |  |  | 1.993058 | 0.996529 | 9676.000000 |
| vendor/symreg/bend/4 | passed | True | 10 | 1.317329 |  |  |  | 3.937317 | 0.984329 | 2240.000000 |
| vendor/symreg/openmp/4 | passed | True | 10 | 1.123839 | 1.119666 |  |  | 3.928687 | 0.982172 | 9348.000000 |
| vendor/symreg/bend/8 | passed | True | 10 | 0.685666 |  |  |  | 7.564534 | 0.945567 | 2200.000000 |
| vendor/symreg/openmp/8 | passed | True | 10 | 0.571800 | 0.567688 |  |  | 7.721594 | 0.965199 | 9204.000000 |
| vendor/symreg/bend/16 | passed | True | 10 | 0.363709 |  |  |  | 14.260675 | 0.891292 | 2192.000000 |
| vendor/symreg/openmp/16 | passed | True | 10 | 0.302962 | 0.298651 |  |  | 14.573492 | 0.910843 | 9352.000000 |
| vendor/symreg/bend/32 | passed | True | 10 | 0.273352 |  |  |  | 18.974608 | 0.592956 | 2388.000000 |
| vendor/symreg/openmp/32 | passed | True | 10 | 0.253392 | 0.248864 |  |  | 17.424455 | 0.544514 | 6084.000000 |
| vendor/symreg/bend-cuda/32 | passed | True | 10 | 0.653206 |  |  |  |  |  | 79464.000000 |
| vendor/terrain/serial-c/1 | passed | True | 10 | 2.598664 |  |  |  | 1.000000 | 1.000000 | 2184.000000 |
| vendor/terrain/bend/1 | passed | True | 10 | 3.156830 |  |  |  | 1.000000 | 1.000000 | 2432.000000 |
| vendor/terrain/openmp/1 | passed | True | 10 | 2.602912 | 2.600033 |  |  | 1.000000 | 1.000000 | 5176.000000 |
| vendor/terrain/bend/2 | passed | True | 10 | 1.596925 |  |  |  | 1.976818 | 0.988409 | 2464.000000 |
| vendor/terrain/openmp/2 | passed | True | 10 | 1.315734 | 1.312927 |  |  | 1.978297 | 0.989148 | 5192.000000 |
| vendor/terrain/bend/4 | passed | True | 10 | 0.810996 |  |  |  | 3.892533 | 0.973133 | 2204.000000 |
| vendor/terrain/openmp/4 | passed | True | 10 | 0.671834 | 0.669276 |  |  | 3.874339 | 0.968585 | 5192.000000 |
| vendor/terrain/bend/8 | passed | True | 10 | 0.429777 |  |  |  | 7.345266 | 0.918158 | 2432.000000 |
| vendor/terrain/openmp/8 | passed | True | 10 | 0.343516 | 0.340718 |  |  | 7.577275 | 0.947159 | 5376.000000 |
| vendor/terrain/bend/16 | passed | True | 10 | 0.238508 |  |  |  | 13.235764 | 0.827235 | 2184.000000 |
| vendor/terrain/openmp/16 | passed | True | 10 | 0.181963 | 0.179199 |  |  | 14.304605 | 0.894038 | 5496.000000 |
| vendor/terrain/bend/32 | passed | True | 10 | 0.204602 |  |  |  | 15.429120 | 0.482160 | 2432.000000 |
| vendor/terrain/openmp/32 | passed | True | 10 | 0.170869 | 0.167521 |  |  | 15.233361 | 0.476043 | 5608.000000 |
| vendor/terrain/bend-cuda/32 | passed | True | 10 | 0.271478 |  |  |  |  |  | 78896.000000 |
| vendor/tree-bitonic/serial-c/1 | passed | True | 10 | 9.652226 |  |  |  | 1.000000 | 1.000000 | 133084.000000 |
| vendor/tree-bitonic/bend/1 | passed | True | 10 | 12.712495 |  |  |  | 1.000000 | 1.000000 | 143524.000000 |
| vendor/tree-bitonic/openmp/1 | passed | True | 10 | 0.573951 | 0.552759 |  |  | 1.000000 | 1.000000 | 53448.000000 |
| vendor/tree-bitonic/bend/2 | passed | True | 10 | 7.170623 |  |  |  | 1.772858 | 0.886429 | 148644.000000 |
| vendor/tree-bitonic/openmp/2 | passed | True | 10 | 0.301641 | 0.280794 |  |  | 1.902763 | 0.951381 | 69864.000000 |
| vendor/tree-bitonic/bend/4 | passed | True | 10 | 3.571587 |  |  |  | 3.559341 | 0.889835 | 151204.000000 |
| vendor/tree-bitonic/openmp/4 | passed | True | 10 | 0.168093 | 0.147362 |  |  | 3.414478 | 0.853620 | 77964.000000 |
| vendor/tree-bitonic/bend/8 | passed | True | 10 | 2.415974 |  |  |  | 5.261850 | 0.657731 | 154016.000000 |
| vendor/tree-bitonic/openmp/8 | passed | True | 10 | 0.131298 | 0.108806 |  |  | 4.371352 | 0.546419 | 81952.000000 |
| vendor/tree-bitonic/bend/16 | passed | True | 10 | 1.689053 |  |  |  | 7.526406 | 0.470400 | 158340.000000 |
| vendor/tree-bitonic/openmp/16 | passed | True | 10 | 0.087122 | 0.063604 |  |  | 6.587888 | 0.411743 | 84040.000000 |
| vendor/tree-bitonic/bend/32 | passed | True | 10 | 1.557225 |  |  |  | 8.163558 | 0.255111 | 174980.000000 |
| vendor/tree-bitonic/openmp/32 | passed | True | 10 | 0.070707 | 0.046340 |  |  | 8.117269 | 0.253665 | 84240.000000 |
| vendor/tree-bitonic/bend-cuda/32 | passed | True | 10 | 0.923526 |  |  |  |  |  | 85304.000000 |
| vendor/tree-matmul/serial-c/1 | passed | True | 10 | 5.506570 |  |  |  | 1.000000 | 1.000000 | 5236.000000 |
| vendor/tree-matmul/bend/1 | passed | True | 10 | 4.933897 |  |  |  | 1.000000 | 1.000000 | 3268.000000 |
| vendor/tree-matmul/openmp/1 | passed | True | 10 | 5.489128 | 5.485961 |  |  | 1.000000 | 1.000000 | 8288.000000 |
| vendor/tree-matmul/bend/2 | passed | True | 10 | 2.574276 |  |  |  | 1.916615 | 0.958308 | 3780.000000 |
| vendor/tree-matmul/openmp/2 | passed | True | 10 | 2.781510 | 2.778095 |  |  | 1.973434 | 0.986717 | 11096.000000 |
| vendor/tree-matmul/bend/4 | passed | True | 10 | 1.336907 |  |  |  | 3.690532 | 0.922633 | 5464.000000 |
| vendor/tree-matmul/openmp/4 | passed | True | 10 | 1.981606 | 1.977245 |  |  | 2.770040 | 0.692510 | 16680.000000 |
| vendor/tree-matmul/bend/8 | passed | True | 10 | 0.825433 |  |  |  | 5.977341 | 0.747168 | 8340.000000 |
| vendor/tree-matmul/openmp/8 | passed | True | 10 | 1.002639 | 0.997496 |  |  | 5.474682 | 0.684335 | 27908.000000 |
| vendor/tree-matmul/bend/16 | passed | True | 10 | 0.461580 |  |  |  | 10.689155 | 0.668072 | 13912.000000 |
| vendor/tree-matmul/openmp/16 | passed | True | 10 | 0.528838 | 0.521034 |  |  | 10.379595 | 0.648725 | 50684.000000 |
| vendor/tree-matmul/bend/32 | passed | True | 10 | 0.487980 |  |  |  | 10.110863 | 0.315964 | 25936.000000 |
| vendor/tree-matmul/openmp/32 | passed | True | 10 | 0.431370 | 0.417857 |  |  | 12.724878 | 0.397652 | 96192.000000 |
| vendor/tree-matmul/bend-cuda/32 | passed | True | 10 | 0.410898 |  |  |  |  |  | 85220.000000 |
| vendor/tree-radix/serial-c/1 | passed | True | 10 | 4.596106 |  |  |  | 1.000000 | 1.000000 | 217520.000000 |
| vendor/tree-radix/bend/1 | passed | True | 10 | 5.818877 |  |  |  | 1.000000 | 1.000000 | 667324.000000 |
| vendor/tree-radix/openmp/1 | passed | True | 10 | 0.256469 | 0.244785 |  |  | 1.000000 | 1.000000 | 20460.000000 |
| vendor/tree-radix/bend/2 | passed | True | 10 | 3.110122 |  |  |  | 1.870948 | 0.935474 | 667816.000000 |
| vendor/tree-radix/openmp/2 | passed | True | 10 | 0.143814 | 0.131453 |  |  | 1.783337 | 0.891668 | 36848.000000 |
| vendor/tree-radix/bend/4 | passed | True | 10 | 1.713048 |  |  |  | 3.396797 | 0.849199 | 668552.000000 |
| vendor/tree-radix/openmp/4 | passed | True | 10 | 0.080270 | 0.067785 |  |  | 3.195062 | 0.798765 | 36844.000000 |
| vendor/tree-radix/bend/8 | passed | True | 10 | 1.235344 |  |  |  | 4.710330 | 0.588791 | 651144.000000 |
| vendor/tree-radix/openmp/8 | passed | True | 10 | 0.064244 | 0.050248 |  |  | 3.992106 | 0.499013 | 36752.000000 |
| vendor/tree-radix/bend/16 | passed | True | 10 | 0.801143 |  |  |  | 7.263220 | 0.453951 | 658832.000000 |
| vendor/tree-radix/openmp/16 | passed | True | 10 | 0.043311 | 0.029201 |  |  | 5.921513 | 0.370095 | 36884.000000 |
| vendor/tree-radix/bend/32 | passed | True | 10 | 0.584238 |  |  |  | 9.959769 | 0.311243 | 733496.000000 |
| vendor/tree-radix/openmp/32 | passed | True | 10 | 0.033819 | 0.019926 |  |  | 7.583495 | 0.236984 | 36876.000000 |
| vendor/tree-radix/bend-cuda/32 | passed | True | 10 | 0.578903 |  |  |  |  |  | 85172.000000 |
| uts/test/serial-c/1 | passed | True | 10 | 0.406974 |  |  |  | 1.000000 | 1.000000 | 6008.000000 |
| uts/test/bend/1 | passed | True | 10 | 0.991691 |  |  |  | 1.000000 | 1.000000 | 2976.000000 |
| uts/test/openmp/1 | passed | True | 10 | 0.975078 |  |  |  | 1.000000 | 1.000000 | 8064.000000 |
| uts/test/openmp-cutoff-4/1 | passed | True | 10 | 0.385501 | 0.382809 |  |  | 1.000000 | 1.000000 | 5496.000000 |
| uts/test/openmp-cutoff-16/1 | passed | True | 10 | 0.385071 | 0.382280 |  |  | 1.000000 | 1.000000 | 5496.000000 |
| uts/test/openmp-cutoff-64/1 | passed | True | 10 | 0.387671 | 0.384822 |  |  | 1.000000 | 1.000000 | 5460.000000 |
| uts/test/bend/2 | passed | True | 10 | 0.988916 |  |  |  | 1.002806 | 0.501403 | 3232.000000 |
| uts/test/openmp/2 | passed | True | 10 | 0.675541 |  |  |  | 1.443402 | 0.721701 | 10092.000000 |
| uts/test/openmp-cutoff-4/2 | passed | True | 10 | 0.227137 | 0.224208 |  |  | 1.697216 | 0.848608 | 5708.000000 |
| uts/test/openmp-cutoff-16/2 | passed | True | 10 | 0.226727 | 0.223951 |  |  | 1.698387 | 0.849193 | 5792.000000 |
| uts/test/openmp-cutoff-64/2 | passed | True | 10 | 0.219292 | 0.216534 |  |  | 1.767832 | 0.883916 | 5760.000000 |
| uts/test/bend/4 | passed | True | 10 | 0.987985 |  |  |  | 1.003751 | 0.250938 | 3016.000000 |
| uts/test/openmp/4 | passed | True | 10 | 0.721483 |  |  |  | 1.351491 | 0.337873 | 12004.000000 |
| uts/test/openmp-cutoff-4/4 | passed | True | 10 | 0.228639 | 0.225922 |  |  | 1.686068 | 0.421517 | 5724.000000 |
| uts/test/openmp-cutoff-16/4 | passed | True | 10 | 0.229127 | 0.226300 |  |  | 1.680598 | 0.420149 | 5540.000000 |
| uts/test/openmp-cutoff-64/4 | passed | True | 10 | 0.220370 | 0.217458 |  |  | 1.759181 | 0.439795 | 5920.000000 |
| uts/test/bend/8 | passed | True | 10 | 1.047909 |  |  |  | 0.946352 | 0.118294 | 2652.000000 |
| uts/test/openmp/8 | passed | True | 10 | 0.549992 |  |  |  | 1.772896 | 0.221612 | 16428.000000 |
| uts/test/openmp-cutoff-4/8 | passed | True | 10 | 0.230023 | 0.227217 |  |  | 1.675924 | 0.209490 | 5468.000000 |
| uts/test/openmp-cutoff-16/8 | passed | True | 10 | 0.230434 | 0.227582 |  |  | 1.671065 | 0.208883 | 5312.000000 |
| uts/test/openmp-cutoff-64/8 | passed | True | 10 | 0.221139 | 0.218372 |  |  | 1.753065 | 0.219133 | 6052.000000 |
| uts/test/bend/16 | passed | True | 10 | 1.049394 |  |  |  | 0.945014 | 0.059063 | 2688.000000 |
| uts/test/openmp/16 | passed | True | 10 | 0.350979 |  |  |  | 2.778162 | 0.173635 | 23184.000000 |
| uts/test/openmp-cutoff-4/16 | passed | True | 10 | 0.237862 | 0.234951 |  |  | 1.620689 | 0.101293 | 5284.000000 |
| uts/test/openmp-cutoff-16/16 | passed | True | 10 | 0.238244 | 0.235260 |  |  | 1.616289 | 0.101018 | 5360.000000 |
| uts/test/openmp-cutoff-64/16 | passed | True | 10 | 0.229062 | 0.225912 |  |  | 1.692428 | 0.105777 | 5788.000000 |
| uts/test/bend/32 | passed | True | 10 | 1.025072 |  |  |  | 0.967436 | 0.030232 | 2704.000000 |
| uts/test/openmp/32 | passed | True | 10 | 0.263023 |  |  |  | 3.707202 | 0.115850 | 39056.000000 |
| uts/test/openmp-cutoff-4/32 | passed | True | 10 | 0.333548 | 0.330033 |  |  | 1.155758 | 0.036117 | 5628.000000 |
| uts/test/openmp-cutoff-16/32 | passed | True | 10 | 0.334617 | 0.331226 |  |  | 1.150781 | 0.035962 | 5792.000000 |
| uts/test/openmp-cutoff-64/32 | passed | True | 10 | 0.319917 | 0.316532 |  |  | 1.211787 | 0.037868 | 6200.000000 |
| uts/tiny/serial-c/1 | passed | True | 10 | 3.071482 |  |  |  | 1.000000 | 1.000000 | 6824.000000 |
| uts/tiny/bend/1 | passed | True | 10 | 7.368097 |  |  |  | 1.000000 | 1.000000 | 3764.000000 |
| uts/tiny/openmp/1 | passed | True | 10 | 7.447881 |  |  |  | 1.000000 | 1.000000 | 16788.000000 |
| uts/tiny/openmp-cutoff-4/1 | passed | True | 10 | 2.930554 | 2.927750 |  |  | 1.000000 | 1.000000 | 5980.000000 |
| uts/tiny/openmp-cutoff-16/1 | passed | True | 10 | 2.926972 | 2.924207 |  |  | 1.000000 | 1.000000 | 6016.000000 |
| uts/tiny/openmp-cutoff-64/1 | passed | True | 10 | 2.928739 | 2.925769 |  |  | 1.000000 | 1.000000 | 6016.000000 |
| uts/tiny/bend/2 | passed | True | 10 | 7.366731 |  |  |  | 1.000185 | 0.500093 | 3656.000000 |
| uts/tiny/openmp/2 | passed | True | 10 | 6.086114 |  |  |  | 1.223750 | 0.611875 | 25140.000000 |
| uts/tiny/openmp-cutoff-4/2 | passed | True | 10 | 2.861901 | 2.858876 |  |  | 1.023989 | 0.511994 | 6236.000000 |
| uts/tiny/openmp-cutoff-16/2 | passed | True | 10 | 2.862054 | 2.859087 |  |  | 1.022682 | 0.511341 | 6236.000000 |
| uts/tiny/openmp-cutoff-64/2 | passed | True | 10 | 2.862436 | 2.858981 |  |  | 1.023163 | 0.511582 | 6456.000000 |
| uts/tiny/bend/4 | passed | True | 10 | 7.375691 |  |  |  | 0.998970 | 0.249743 | 3472.000000 |
| uts/tiny/openmp/4 | passed | True | 10 | 5.490820 |  |  |  | 1.356424 | 0.339106 | 38660.000000 |
| uts/tiny/openmp-cutoff-4/4 | passed | True | 10 | 2.872891 | 2.870008 |  |  | 1.020071 | 0.255018 | 6316.000000 |
| uts/tiny/openmp-cutoff-16/4 | passed | True | 10 | 2.868261 | 2.865167 |  |  | 1.020469 | 0.255117 | 6292.000000 |
| uts/tiny/openmp-cutoff-64/4 | passed | True | 10 | 2.885050 | 2.881971 |  |  | 1.015143 | 0.253786 | 6328.000000 |
| uts/tiny/bend/8 | passed | True | 10 | 7.745786 |  |  |  | 0.951239 | 0.118905 | 3208.000000 |
| uts/tiny/openmp/8 | passed | True | 10 | 3.532168 |  |  |  | 2.108586 | 0.263573 | 54820.000000 |
| uts/tiny/openmp-cutoff-4/8 | passed | True | 10 | 2.871401 | 2.868392 |  |  | 1.020601 | 0.127575 | 6472.000000 |
| uts/tiny/openmp-cutoff-16/8 | passed | True | 10 | 2.867706 | 2.864749 |  |  | 1.020667 | 0.127583 | 6308.000000 |
| uts/tiny/openmp-cutoff-64/8 | passed | True | 10 | 2.872193 | 2.869124 |  |  | 1.019687 | 0.127461 | 6820.000000 |
| uts/tiny/bend/16 | passed | True | 10 | 7.796653 |  |  |  | 0.945033 | 0.059065 | 3208.000000 |
| uts/tiny/openmp/16 | passed | True | 10 | 2.263227 |  |  |  | 3.290823 | 0.205676 | 94040.000000 |
| uts/tiny/openmp-cutoff-4/16 | passed | True | 10 | 2.970953 | 2.967831 |  |  | 0.986402 | 0.061650 | 6512.000000 |
| uts/tiny/openmp-cutoff-16/16 | passed | True | 10 | 3.000614 | 2.997422 |  |  | 0.975458 | 0.060966 | 6472.000000 |
| uts/tiny/openmp-cutoff-64/16 | passed | True | 10 | 3.058036 | 3.054712 |  |  | 0.957719 | 0.059857 | 6832.000000 |
| uts/tiny/bend/32 | passed | True | 10 | 7.503693 |  |  |  | 0.981929 | 0.030685 | 3200.000000 |
| uts/tiny/openmp/32 | passed | True | 10 | 2.739140 |  |  |  | 2.719059 | 0.084971 | 167748.000000 |
| uts/tiny/openmp-cutoff-4/32 | passed | True | 10 | 4.206595 | 4.203278 |  |  | 0.696657 | 0.021771 | 6936.000000 |
| uts/tiny/openmp-cutoff-16/32 | passed | True | 10 | 4.191662 | 4.188178 |  |  | 0.698284 | 0.021821 | 6724.000000 |
| uts/tiny/openmp-cutoff-64/32 | passed | True | 10 | 4.272045 | 4.268428 |  |  | 0.685559 | 0.021424 | 7324.000000 |

## Scope

Vendor inputs retain upstream arithmetic and checksums. OpenMP uses loop parallelism and thread-local arenas; sort and Merkle use alternative algorithms. UTS preserves BOTS's SHA-1 tree, with a checked exhaustion counter in Bend. These baselines are not claimed to be exhaustively tuned. Kernel profiling, device peak memory, proof-system correspondence, Metal and AI-coding trials are not measured by this harness yet.
