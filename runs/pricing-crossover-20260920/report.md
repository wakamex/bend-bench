# Sustained pricing size sweep

Request-to-host price and standard error, with 256 observations per path. Each cell is the median of three process means, with two warmups and ten measured requests per process. Startup and output formatting are excluded. Implementations run in shuffled order. All completed rows passed quote checks; a separate independent small-input audit checks every payoff.

| Paths | Bend GPU ms | Project CUDA ms | Bend / CUDA time |
|---|---:|---:|---:|
| 65,536 | 1.548 | 0.172 | 9.027× |
| 131,072 | 2.163 | 0.286 | 7.550× |
| 262,144 | 3.315 | 0.483 | 6.860× |
| 524,288 | 5.409 | 0.897 | 6.033× |
| 1,048,576 | 9.743 | 1.756 | 5.547× |
| 2,097,152 | 15.971 | 3.475 | 4.596× |
| 4,194,304 | 31.048 | 6.915 | 4.490× |
| 8,388,608 | 61.162 | 13.729 | 4.455× |
| 16,777,216 | 121.359 | 27.954 | 4.341× |
| 33,554,432 | 243.215 | 56.367 | 4.315× |
| 67,108,864 | 485.445 | 113.862 | 4.263× |
| 134,217,728 | 970.164 | 228.934 | 4.238× |
| 268,435,456 | 1955.236 | 465.020 | 4.205× |
| 536,870,912 | 3912.849 | 930.933 | 4.203× |
| 1,073,741,824 | 7823.641 | 1874.269 | 4.174× |

Status: Reached the 2^30 path-count cap.

The per-request watchdog permits 180 seconds for startup, then at most 60 seconds between delivered quotes. Seed offsets retain wrapping-U32 arithmetic, so sufficiently large requests can reuse seeds across batches. The path-count cap is 2^30, below the existing signed-int API limit. These are project-written CUDA controls, not an established finance library. Earlier runs and failed attempts remain unchanged.
