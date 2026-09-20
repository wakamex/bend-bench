# Matched 17×17 N-Queens batching

Does upfront batching explain Bend's stronger scaling on its published N-Queens workload? This experiment compares the published solver, our child/sibling recursive solver, and the same recursive solver with published-style batching. All three search the same selected 17×17 starting positions. OpenMP and serial C++ provide conventional baselines. Results will be saved in [the run report](runs/queens-batching-20260920/report.md).

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
