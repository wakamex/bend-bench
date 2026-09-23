# Single-job summation crossover

Complete-program medians include startup, generation, summation and output. Each point has an independent scalar correctness check, two warmups and ten measured executions per implementation in shuffled order. Existing worker-canary exemptions apply; other GPU activity fails the run.

| Generated integers | Bend GPU seconds | CUB seconds | Bend/CUB time ratio |
|---|---:|---:|---:|
| 8,388,608 | 0.116800 | 0.186481 | 0.626 |
| 16,777,216 | 0.117701 | 0.184206 | 0.639 |
| 33,554,432 | 0.118670 | 0.187826 | 0.632 |
| 67,108,864 | 0.122504 | 0.186968 | 0.655 |
| 134,217,728 | 0.129346 | 0.186830 | 0.692 |
| 268,435,456 | 0.142519 | 0.185009 | 0.770 |
| 536,870,912 | 0.169821 | 0.187301 | 0.907 |
| 570,425,344 | 0.231338 | 0.183288 | 1.262 |
| 603,979,776 | 0.232977 | 0.184902 | 1.260 |
| 671,088,640 | 0.233961 | 0.181646 | 1.288 |
| 805,306,368 | 0.232239 | 0.178493 | 1.301 |
| 1,073,741,824 | 0.223473 | 0.183826 | 1.216 |

Measured crossover bracket: [536870912, 570425344]. A null bracket means no crossover was found within the size cap. A null lower bound means CUB already won at the starting size. This is a local bracket, not proof of a universal or monotonic threshold.

Power-of-two points retain the original Bend reduction. Intermediate points join unchanged power-of-two reductions into a prefix of the same generated sequence. These intermediate points have unequal top-level branches. All original source copies, generated adapters, build commands, artifact hashes and failed samples are retained.
