# Resident-process game-search audit

The previous m,n,k Bend-versus-CUDA comparison is withdrawn. Both build commands targeted `mnk-5-5-4-8-cuda`; the later Bend build overwrote the conventional control. Both GPU labels therefore executed Bend, with different command-line settings and CPU affinity. The same naming collision affected every m,n,k game size, including historical one-shot measurements. Correct output alone did not detect the wrong implementation.

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

The next comparison must first verify distinct executables, then diagnose search versus delivery time and repeat matched CPU/GPU runs in shuffled order with hardware telemetry. It still evaluates a repeated 16-position corpus, not general game-search performance.
