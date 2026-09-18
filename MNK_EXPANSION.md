# CUDA pruning and expanded endgame corpus

The expanded comparison completed with all 42 processes passing every answer check. On 1,024 distinct positions, Bend GPU delivered 971,213 positions/second, tight-bound OpenMP16 delivered 953,808, and Bend CPU16 delivered 681,214. The strongest tested CUDA control was tight-bound root-parallel search at 545,643, ahead of whole-position CUDA at 462,763. These are medians across three process means. The [complete report](runs/mnk-sustained-20260918-112910/report.md) preserves all process measurements.

Whole-position CUDA improved delivered throughput on the original 16 positions from 437,117 to 543,065 positions/second, but on the larger corpus tight-bound root splitting performed better. Tightening OpenMP bounds increased throughput from 813,692 to 953,808 positions/second on the larger corpus. Bend GPU's 1.8% delivered-throughput lead over the improved OpenMP control is smaller than observed process variability.

Delivered throughput includes different output strategies: C++ printed and flushed each answer while Bend constructed a string. Search-to-host medians on the expanded corpus were 176.80 ms for Bend GPU, 218.93 ms for tight OpenMP16, 555.57 ms for Bend CPU16, 636.37 ms for tight root CUDA and 811.12 ms for whole-position CUDA. These phases include GPU transfers where applicable. The follow-up below tests output handling independently.

The controls separate two changes. The original root-parallel CUDA implementation uses bounds [-2, 2] for scores in [-1, 1]. A second root-parallel build tightens those bounds to [-1, 1]. A third keeps the tighter bounds and assigns one complete position to each GPU thread. OpenMP is measured with both bounds as well. All searches enumerate empty squares in ascending order; the tight bounds correspond to Bend's [0, 2] score representation. Each variant has a distinct executable, and the original control remains available.

The larger corpus uses the same deterministic generator and preserves the original 16-position prefix. All 1,024 boards are distinct legal nonterminal 5×5 connect-4 positions with eight empty squares. Saved move histories establish reachability, and the independent tuple-board solver supplies every expected outcome. Positions are generated without selecting for performance or outcome. The corpus summary records win/draw/loss counts and a content hash.

The finite comparison uses both corpus sizes, 524,288 positions per batch, two warmups and 30 measured batches per process, and three fresh processes per implementation in shuffled order. Seven implementations give 42 processes in total: two Bend backends, two OpenMP variants and three CUDA variants. Every emitted answer is checked. Delivered throughput includes answer formatting and transfer to the observer; search-to-host timing is recorded separately. Neither is kernel-only time.

```sh
uv run --locked python mnk_sustained.py --depths 19 --batches 30 --repeats 3 --multicore-only --telemetry --control-variants --corpus-sizes 16 1024
```

GPU admission requires the existing 120-second quiet window, with a 24-hour deadline. Builds and measurements hold the shared benchmark lock. Each compilation has a 180-second limit and each measured process a 300-second limit. A failed build, wrong answer, timeout or unapproved GPU activity stops the run and preserves its evidence. There are no automatic retries. After two failed interventions at the same gate, reassess the hypothesis before changing another implementation detail.

## Bulk output and literal win-check comparison

The follow-up retains all seven existing implementations and adds two successive controls for each of the three tight-bound conventional implementations. First, bulk output constructs the same newline-delimited answer vector in memory and writes it as a buffer, with an explicit batch flush. Every answer is still checked; no checksum replaces validation. Second, a separately compiled variant keeps bulk output and substitutes literal winning-mask expressions for the mask-array loop. Both variants retain bounds, move order, inputs and parallel work assignment. Bend is unchanged. The report now shows search-to-host and output phases alongside delivered throughput.

This comparison completed with all 39 processes passing on the expanded 1,024-position corpus at 524,288 positions per batch, with two warmups, 30 measured batches and three shuffled process repetitions. [Full measurements](runs/mnk-sustained-20260918-133838/report.md).

| Tight-bound control | Original output, positions/s | Bulk output, positions/s | Bulk output and literal win checks, positions/s |
|---|---:|---:|---:|
| OpenMP, 16 threads | 942,836 | 1,458,105 | 1,177,883 |
| Root-parallel CUDA | 546,857 | 676,951 | 707,748 |
| Whole-position CUDA | 462,086 | 551,501 | 566,336 |

Bulk output improves OpenMP delivered throughput by 55% while its median search phase stays at 219–220 ms. Literal win checks slow its search to 307 ms, so the array loop remains the stronger measured CPU control. Bend GPU delivers 980,290 positions/s, with 180 ms search-to-host and 355 ms output phases. Its search completes sooner than OpenMP's, but bulk-output OpenMP delivers 49% more positions per second. These values are medians of process means, and separately summarized phases need not sum exactly to the median delivered latency.

```sh
uv run --locked python mnk_sustained.py --depths 19 --batches 30 --repeats 3 --multicore-only --telemetry --literal-win-variants --corpus-sizes 1024
journalctl --user -u bend-bench-mnk-io-win.service -f
```

## OpenMP scheduling and Bend output chunks

The next finite experiment changes OpenMP scheduling and Bend output independently. OpenMP retains tight bounds, the mask-array win check and bulk output, comparing dynamic chunks of 1, 16, 64 and 256 positions. Bend retains its search and compares the original single-string output against sequential subtree strings. Splitting the answer tree seven levels yields 128 chunks of 4,096 answers each at the configured batch size. Each chunk uses the existing IO.print; its added newline replaces the final answer's newline, preserving the exact byte stream and full answer validation.

The archived generated Bend C implementation's `io_print_run` calls `io_cstr` to materialize the string in a C buffer, prints it, then frees that buffer. Chunking tests whether smaller strings reduce output costs; no allocation or copying bottleneck has yet been demonstrated by profiling.

Eight configurations run three fresh processes each, on the same 1,024 positions and 524,288-position batches, with two warmups and 30 measurements per process. Both Bend CPU16 and GPU are included. Tests exercise the original and chunked output, all OpenMP chunk sizes and the complete oracle vector on real CPU executables. Performance and new GPU correctness are pending. Existing idle admission, execution locking, time limits and fail-closed evidence retention apply. Packed CUDA root moves, GPU stack profiling and additional search depths remain separate follow-ups.

```sh
uv run --locked python mnk_sustained.py --depths 19 --batches 30 --repeats 3 --multicore-only --telemetry --scheduling-output-variants --corpus-sizes 1024
journalctl --user -u bend-bench-mnk-scheduling-output.service -f
```
