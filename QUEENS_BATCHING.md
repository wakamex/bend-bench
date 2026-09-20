# Matched 17×17 N-Queens batching

Upfront batching makes our recursive Bend solver 4.9× faster at 16 CPU threads on the same selected 17×17 search space. One-thread time is essentially unchanged. Moving from one to 16 threads gives 2.6× speedup with natural recursion and 12.5× with batching. All variants returned the same 6,899,189 solutions and 863,992,044 below-prefix search nodes across 117 checked executions.

| Implementation | 1 CPU thread | 16 CPU threads | CPU speedup |
|---|---:|---:|---:|
| Published Bend, batched | 12.206 s | 0.999 s | 12.2× |
| Our Bend, natural recursion | 9.466 s | 3.678 s | 2.6× |
| Our Bend, batched | 9.463 s | 0.754 s | 12.5× |
| OpenMP, batched | 4.583 s | 0.319 s | 14.4× |
| Serial C++ | 4.521 s | | |

Our batched version also finishes 1.3× faster than the published Bend solver at 16 threads. OpenMP remains 2.4× faster than our batched version. Each cell is the median of ten complete-program measurements after two warmups, with shuffled execution order. See the [full run report](runs/queens-batching-20260920/report.md) and [individual executions](runs/queens-batching-20260920/samples.jsonl).

## Matched search space

The first four queen columns encode a base-17 integer. Only legal prefixes with IDs below 11,730 are searched, matching the published input. Each implementation reports two separate U32 counters: solutions and candidate placements visited below row four. Every measured output must match the serial reference, whose combined checksum must also equal the published 2063750025. This is a selected-prefix search, not enumeration of every 17×17 solution.

The two recursive variants use identical generated source except for the main entrypoint. Both use our parallel child/sibling bit-mask search with the same counters and structural fuel. One discovers legal prefixes through ordinary recursive search. The other uses the published balanced tree over 131,072 permuted prefix indices, rejects out-of-range and illegal prefixes, and starts the same inner solver. Prefix discovery, permutation and division into batches change together as the explicit scheduling treatment; the below-prefix search stays fixed.

The published anchor retains its accumulator-based inner solver and prefix batching, with output changed from a checksum to the two counters. Comparing that anchor directly with our recursive solver changes both inner recursion and prefix organization. The matched recursive pair isolates prefix organization. OpenMP parallelizes the published C twin's prefix loop with dynamic chunks of 16; serial C++ uses the same solver without an OpenMP region.

## Measurement and checks

Each Bend variant and OpenMP run at one and 16 CPU threads; serial C++ runs at one. All nine configurations receive a correctness check, two warmups and ten measured complete-process executions, shuffled within each repetition. Builds use `-O3 -march=native -ffp-contract=off`. Small 5×5 and 8×8 cases check all compiled variants against an independent board-based reference, including a partially selected prefix range and the known 92 solutions for the complete 8×8 board.

The finite CPU-only run uses the shared benchmark lock, blocked-service checks, pinned source/configuration evidence, a two-hour total measurement budget and 180-second process timeouts. It preserves build logs, source and binary hashes, linked-library hashes, every output, timing, host peak memory and any failures. It does not replace historical N-Queens results or claim GPU measurements.

```sh
journalctl --user -u bend-bench-queens-batching.service -f
```
