# Matched 17×17 N-Queens batching

Each implementation searches the same legal four-row prefixes with base-17 IDs below 11,730. Every run must return the exact solution and below-prefix node counts: `6899189 863992044`. The two recursive variants share the same inner search; their difference is recursive prefix discovery versus the published balanced, permuted prefix batch. The published variant is an anchor with a different, accumulator-based inner search.

| Implementation | 1 CPU thread seconds | 16 CPU threads seconds | CPU speedup |
|---|---:|---:|---:|
| published-batch | 12.205839 | 0.999333 | 12.21× |
| recursive | 9.466285 | 3.678182 | 2.57× |
| recursive-batch | 9.463113 | 0.754232 | 12.55× |
| openmp | 4.583406 | 0.318677 | 14.38× |
| serial | 4.521399 |  |  |

Complete-program times include startup and printing the two counters. Each cell requires ten checked measurements after two warmups; order is shuffled within each repetition. Counters use wrapping U32 arithmetic. Small-board tests independently verify counts with a board-based reference. The full-size serial reference must reproduce the published checksum 2063750025. Prefix-construction work differs by design; both recursive variants count the same search nodes below those prefixes. This is a CPU experiment, not a GPU measurement.
