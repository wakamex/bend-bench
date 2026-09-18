# Corrected resident-process game-search comparison

Bend GPU delivers a median 1.20 million positions/second on the fixed repeated endgame corpus, versus 837,000 for OpenMP16, 537,000 for Bend CPU16 and 435,000 for the corrected project-written CUDA control. Each implementation ran in three fresh processes in a saved shuffled order, with two warmups and 30 measured batches of 524,288 positions per process. Every answer passed in all 12 process runs.

| Implementation | Median delivered positions/s across three processes | Minimum–maximum process throughput | Median search-to-host ms per batch |
|---|---:|---:|---:|
| Bend GPU | 1,199,512 | 1,191,288–1,201,124 | 82.1 |
| OpenMP, 16 CPU threads | 836,619 | 836,334–843,608 | 283.1 |
| Bend, 16 CPU threads | 537,472 | 514,351–537,739 | 779.1 |
| Project-written CUDA root-parallel control | 434,915 | 426,366–435,082 | 878.4 |

Bend GPU delivers 2.23× its own multicore CPU throughput, 1.43× OpenMP and 2.76× this CUDA control. The result compares these implementations on this repeated corpus; the CUDA control is not claimed to be tuned or optimal. Bend and OpenMP distribute complete positions, while CUDA distributes root moves and then performs recursive alpha-beta search. This difference can change the amount of pruning and work. Broader position diversity and stronger CUDA implementations remain separate work.

The [matched report](runs/mnk-sustained-20260918-110942/report.md), commit `b51893f`, preserves the shuffled schedule, generated sources, binary hashes, every batch output, phase timing and hardware observations. Throughput and search columns summarize process means using the median across three processes; individual batches are not counted as independent process repetitions. Search-to-host time includes result transfers and is not kernel-only time. Output formatting and delivery remain included in delivered throughput.

## Withdrawn historical CUDA comparisons

The previous m,n,k Bend-versus-CUDA comparisons are withdrawn. Both build commands targeted `mnk-5-5-4-8-cuda`; the later Bend build overwrote the conventional control. Both GPU labels therefore executed Bend, with different command-line settings and CPU affinity. The same naming collision affected every m,n,k game size, including historical one-shot measurements. Correct output alone did not detect the wrong implementation.

The control now builds to `-control-cuda`, and the planner rejects duplicate compiler output paths. A regression test checks that every m,n,k CUDA control has a distinct executable produced from the C++ source by the CUDA compiler. The other application suites use distinct control paths. Historical source, commands, hashes and outputs remain unchanged in their original run directories.

## Preserved Bend observations

The actual Bend-labeled runs remain Bend measurements. At 524,288 positions per batch, ten measured batches delivered 1,330,308 positions/second; 30 delivered 1,186,415; 100 delivered 1,122,888. In the 100-batch run, the first ten measured batches delivered 1,332,770 positions/second and the last ten 1,101,152. All answers passed. The slowdown was observed within the Bend run, but its cause remains unresolved.

The earlier ten-batch size sweep increased Bend throughput from 706,980 positions/second at 65,536 positions to 1,356,879 at 1,048,576, falling to 1,311,685 at 4,194,304. Replaying saved answers without search reached 4.47 million positions/second. That replay excludes the reader alone as the observed ceiling; it does not isolate search, formatting, transfers or hardware conditions.

The first matched CPU/Bend-GPU experiment at 65,536 positions recorded 431,581 positions/second for Bend CPU16, 527,583 for Bend GPU and 729,056 for OpenMP16. These were separate executables, but the revised observer and longer runs require a fresh matched comparison before updating that conclusion.

## Evidence

- [Initial 16–4,096-position sweep](runs/mnk-sustained-20260918-101844/report.md).
- [Initial 65,536-position run](runs/mnk-sustained-20260918-102144/report.md).
- [Logarithmic GPU sweep](runs/mnk-sustained-20260918-103906/report.md), implementation `56010dd`.
- [Duration sweep](runs/mnk-sustained-20260918-104836/report.md), implementation `458f10e`.
- [One-shot alpha-beta report](runs/5b94ff4c061b7685c7ca/report.md).

Every `local-alpha-beta-cuda` row in those reports is mislabeled Bend execution and must not be used as conventional CUDA evidence. All tests used Bend revision `b9d1352c9f45632447f40a2e927355c92f2be58c`, a Ryzen 9 3950X and an RTX 3090.

## Workload and measurement

The workload repeats 16 independently checked 5×5 connect-4 positions with eight empty squares. Increasing batch size increases independent work, not search diversity. Input order rotates between batches. Each process performs two warmup batches followed by the requested measured batches. Full raw answers, per-batch delivery latency, cumulative rates, source hashes, compiler commands and activity observations are retained.

Delivered throughput includes search, formatting, transfers and pipe delivery; it is not kernel time. Full-process throughput counts warmup answers too and includes startup and shutdown. Warmup-excluded throughput omits both warmups. GPU monitor setup and its sampling drain are outside process timing. Individual batches within one process are not independent process repetitions.

Reproduce the duration configuration with `uv run --locked python mnk_sustained.py --gpu-only --depths 19 --batches 10 30 100`. Results use new timestamped directories under `runs/`. The shared execution lock, idle GPU gate, approved transcription-worker exemption, 300-second per-process limit and 4 GB Bend GPU heap remain in force.

## Instrumented slowdown diagnostic

The corrected [100-batch diagnostic](runs/mnk-sustained-20260918-110302/report.md), commit `b51893f`, verifies every answer with distinct executables and records search-to-host and output intervals. Bend's first ten measured batches average 84.7 ms in search and 331.7 ms in output; the last ten average 82.8 ms in search and 386.8 ms in output. The observed Bend slowdown is in formatting and delivery, while the measured search interval remains stable.

The genuine conventional CUDA control averages 879.0 ms per batch in search-to-host and 333.5 ms in output. Its first and last ten search averages are 878.0 and 879.7 ms; output averages are 331.4 and 330.2 ms. It does not reproduce the earlier supposedly shared slowdown, because the earlier control label actually ran Bend. Bend's mean search-to-host interval is 82.2 ms in this diagnostic. These are host-side phase times, including transfer of results, not kernel-only sums.

Bend's sampled GPU SM clocks stayed around 2 GHz while temperature rose from roughly 48 to 62 C; its host RSS varied rather than growing monotonically. The CUDA control drove substantially more GPU activity and temperature reached 77 C, but its search interval remained stable. Raw GPU clocks, temperature, power, utilization and memory are in each process's `gpu-telemetry.csv`; `/proc` CPU and memory observations are in `host-telemetry.jsonl`. These observations locate the measured Bend slowdown in the output phase; they do not identify a specific allocator, formatting or pipe mechanism.

Reproduce the completed matched rerun with `uv run --locked python mnk_sustained.py --depths 19 --batches 30 --repeats 3 --multicore-only --telemetry`. Timers record when search results return to the host and when output completes. Bend's timer has millisecond resolution; the conventional timer uses nanoseconds. The full test suite passed 46 tests with three expected skips, and source distribution and wheel builds passed before the rerun.
