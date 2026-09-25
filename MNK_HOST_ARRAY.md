# Endgame search through host-array completion

Our fastest CUDA control produces 3.7× as many game-search answers per second as Bend GPU, and OpenMP on 16 CPU threads 35% more. The CUDA controls in the tables below ran 5-7× slower than they should have: their recursive search kept each GPU thread's stack in local memory. With the depth fixed at compile time ([6e9d3d3](src/bend_bench/assets/gpu/mnk.cpp)), the one-thread-per-position control completes a batch in 80.9 ms and the root-parallel control in 108.7 ms, while Bend GPU re-measured at 302.8 ms in the same run ([report](runs/mnk-sustained-20260925-173106/report.md)). The tables below keep the original measurements. All implementations solve the same positions and finish with every answer in a flat CPU-memory array; formatting and validation happen after timing ends. The final comparison passed every array value in all 12 process runs.

| Implementation | Median host-array completion per 524,288-position batch | Host-ready positions/second |
|---|---:|---:|
| Tight-bound OpenMP, 16 threads, mask-loop win check | 225.81 ms | 2,321,796 |
| Bend GPU | 304.15 ms | 1,723,779 |
| Project-written tight-bound CUDA, one thread per position, fixed-depth search (25 September) | 80.89 ms | 6,481,654 |
| Project-written tight-bound root-parallel CUDA, literal win checks | 601.12 ms | 872,183 |
| Project-written tight-bound root-parallel CUDA, mask-loop control | 636.07 ms | 824,257 |

The final run uses 1,024 distinct legal 5×5 connect-4 positions with eight empty squares, repeated to 524,288 positions per batch. Each implementation ran in three fresh processes in shuffled order, with two warmups and 30 measured batches per process. Table entries are medians of process means. Literal win checks improve CUDA throughput by 5.8% over the mask-loop control. [Final report](runs/mnk-sustained-20260918-161850/report.md).

Across the three processes, mean batch times ranged from 221.74–225.91 ms for OpenMP, 299.67–305.07 ms for Bend GPU, 600.59–601.39 ms for literal-mask CUDA and 636.06–636.48 ms for loop-based CUDA. These CUDA implementations are local controls, not established tuned game engines. The result covers repeated eight-empty-square endgames rather than a sweep of search difficulty.

## CPU-to-GPU scaling

The [preceding matched run](runs/mnk-sustained-20260918-160439/report.md) included Bend CPU16: 559.01 ms per batch versus 300.68 ms for Bend GPU, or 86% more throughput on GPU. It also measured 221.07 ms for OpenMP16, 636.05 ms for root-parallel CUDA and 811.14 ms for whole-position CUDA, both with mask loops. All 15 processes passed. These measurements remain separate from the final run above.

## Corrected timing boundary

Earlier Bend timings labeled “search-to-host” ended after GPU synchronization, before its completed answer tree had necessarily migrated to CPU memory. The generated runtime allocates CUDA managed memory with device-preferred placement; output traversal can trigger further transfers. The new endpoint includes this work and tree-to-array materialization. The earlier claimed host-ready advantage over OpenMP is withdrawn. Historical raw timings remain unchanged in the [earlier audit](MNK_SUSTAINED.md) and [optimization history](MNK_EXPANSION.md).

## Timed work and validation

OpenMP retains its preallocated result array and completion barrier. Conventional CUDA retains its synchronous result-array copy. A measurement adapter traverses Bend's completed tree into a preallocated, first-touched uint32 host array before reading the end clock. The traversal reads every answer and includes any managed-memory migration required by those reads. The Bend search and upstream compiler/runtime checkout remain unchanged.

The adapter instruments the generated C at the emit continuation and clock effect, refusing an unexpected generated layout. Uninstrumented and instrumented C files, adapter source, build commands and binary hashes are retained. This is benchmark-side native instrumentation, not a claim that Bend source now exposes a native flat-array API.

Each implementation saves the complete host array after its end timestamp. The harness checks every uint32 against the independent rotated-corpus oracle after the process finishes. It also continues checking the text stream. Wrong values, missing or extra bytes, invalid timings and unapproved GPU activity fail the measurement. Tests cover real compiled CPU backends, the chunked-output variant, and deliberately damaged binary evidence.

Bend uses nanosecond clock readings in the adapter; conventional controls use their existing steady-clock nanosecond intervals. Buffer allocation and first-touch initialization precede the first batch. Host-ready time includes Bend's tree-to-array conversion because the specified endpoint is a flat host array. Binary evidence I/O is outside that interval, but remains inside complete process and output-phase times. Those diagnostic delivery timings must not replace or be pooled with earlier delivery benchmarks.

## Reproduce the comparison

Combining the host-array and literal-win-variants options selects the four final implementations. OpenMP retains the faster mask-loop win check and dynamic scheduling with chunk size 1. Both CUDA variants use tight bounds and bulk output. All reference timings are freshly measured. The shared lock, idle admission, 180-second build limit, 300-second process limit and failure retention remain active.

```sh
uv run --locked python mnk_sustained.py --depths 19 --batches 30 --repeats 3 --multicore-only --telemetry --host-array --literal-win-variants --corpus-sizes 1024
```

Omit the literal-win-variants option to reproduce the five-implementation CPU-to-GPU comparison. For experiments specifically about text delivery, the [optimization history](MNK_EXPANSION.md) records bulk-output OpenMP and chunked-output Bend as the stronger measured variants. Text delivery and host-array completion are separate endpoints.
