# Resident-process game-search experiment

Keeping the process alive and increasing the batch to 65,536 positions makes Bend GPU about 22% faster than Bend's 16-thread CPU: 528,000 versus 432,000 positions per second. Conventional CUDA is close at 541,000; OpenMP remains fastest at 729,000. Every answer passed validation in all 20 configurations, each with two warmup batches and ten measured batches in one process.

| Positions per batch | Bend CPU, 16 threads, positions/s | Bend GPU, positions/s | OpenMP, 16 threads, positions/s | Conventional CUDA, positions/s |
|---|---:|---:|---:|---:|
| 16 | 24,547 | 485 | 172,596 | 512 |
| 256 | 247,958 | 9,619 | 663,192 | 10,014 |
| 4,096 | 349,250 | 105,045 | 753,169 | 104,885 |
| 65,536 | 431,581 | 527,583 | 729,056 | 540,920 |

At 65,536 positions, mean delivered batch latency is 151.9 ms for Bend CPU, 124.2 ms for Bend GPU, 89.9 ms for OpenMP and 121.2 ms for conventional CUDA. Bend's one-thread CPU takes 1,425.2 ms. The GPU benefit therefore appears at a substantially larger batch than the original 16-position test; removing startup alone was insufficient at the smaller sizes.

The [16–4,096-position report](runs/mnk-sustained-20260918-101844/report.md) and [65,536-position report](runs/mnk-sustained-20260918-102144/report.md) preserve all five implementations, startup times and evidence. Implementation commits are `0b3ffa8` and `07021f7`; the latter only extends the batch-size sweep and records the requested sizes. Both runs use Bend revision `b9d1352c9f45632447f40a2e927355c92f2be58c` on the Ryzen 9 3950X and RTX 3090.

## Workload and measurement

The experiment uses the 5×5 connect-4 corpus with eight empty squares, repeating its 16 independently checked positions to form batches of 16, 256, 4,096 and 65,536. This increases the amount of independent work without changing search difficulty or claiming additional distinct positions.

Each executable initializes once and emits 12 successive batches. The first two batches are warmups; the remaining ten determine throughput. Batch order rotates the corpus so every emitted answer can be checked against the reference in its expected position. Bend retains its source-level alpha-beta algorithm and parallel batch tree. OpenMP distributes positions and the conventional CUDA control distributes root moves, as in the preceding experiment. CUDA allocations in the conventional control are reused across batches.

The host records output-delivery boundaries and checks every answer. Reported mean batch latency is the total time between delivery of the second and twelfth batches divided by ten; throughput is the corresponding number of answers divided by that time. This includes computation, output formatting, pipe delivery and host observation. It is not a kernel-only measurement, and per-batch boundary intervals may reflect pipe buffering. Complete output, individual intervals, initialization-to-READY time, process wall time, compiler commands, generated source and binary hashes are retained. Lazy first-use initialization is covered by the warmups.

The finite diagnostic runs Bend at one and 16 CPU threads, OpenMP at 16 threads, and both GPU implementations. Each process has a 300-second limit. An invalid output or unapproved GPU activity stops the experiment and preserves its evidence. The shared benchmark lock and existing idle GPU gate apply. The approved transcription-worker canary exemption remains unchanged.

Run with `uv run --locked python mnk_sustained.py`. Results are written to a new timestamped `runs/mnk-sustained-*` directory. This is a focused experiment; its ten within-process batches are repeated measurements from one initialized process, not ten independent process launches.
