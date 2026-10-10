# nanoGPT generation: time per added sequence

Median compute seconds per size (correct runs only); a fit's per-sequence time is its marginal cost at the largest size.

| Implementation | 1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 | 256 | 512 | 1024 | 2048 | 4096 | 8192 | 16384 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bend-cpu | 0.451 | 0.448 | 0.45 | 0.657 | 0.638 | 1.29 | 3.35 | 9.04 | 21.7 | 47.6 | 98 | 196 | 394 | 802 | 1.58e+03 |
| bend-gpu | 134 | 200 | 202 | 206 | 213 | 226 | 231 | 136 | 209 | 207 | 215 | 230 | 239 |  |  |
| pytorch-cpu | 0.125 | 0.114 | 0.251 | 0.26 | 0.205 | 0.437 | 0.371 | 0.468 | 0.748 | 1.5 | 3.22 | 7.27 | 19.9 | 39.5 | 79.1 |
| pytorch-cuda | 0.447 | 0.444 | 0.439 | 0.506 | 0.461 | 0.471 | 0.496 | 0.521 | 0.594 | 0.738 | 1.05 | 1.57 | 2.87 | 5.77 | 11.5 |

| Implementation | Fixed cost | Seconds per added sequence | At sequences | Fit rms |
|---|---:|---:|---:|---:|
| bend-cpu | 0.626 s | 0.113 s | 16384 | 12.4% |
| bend-gpu | 148 s | 0.00496 s | 4096 | 16.7% |
| pytorch-cpu | 0.175 s | 0.00702 s | 16384 | 24.7% |
| pytorch-cuda | 0.456 s | 0.000778 s | 16384 | 3.2% |

| Ratio of per-sequence times | Value | At sequences |
|---|---:|---:|
| bend-cpu / pytorch-cpu | 16.1x | 16384 |
| bend-gpu / pytorch-cuda | 7.8x | 4096 |
| bend-gpu / bend-cpu | 0.0464x | 4096 |
