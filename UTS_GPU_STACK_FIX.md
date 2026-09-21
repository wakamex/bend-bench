# Heap-backed GPU continuation stacks

The runtime fix resolves the stack failure on both UTS inputs without changing the Bend program. The patched GPU run correctly counts 4,112,897 nodes in 52 seconds and 30,399,117 nodes in 390 seconds. These are single correctness checks, not repeated benchmark timings. Ten-run comparisons on three existing GPU workloads show longer median execution times: 0.8% for Mandelbrot, 2.9% for ray tracing and 8.9% for N-Queens.

The fix is local commit `19fa5ae3643241c70bcfbf1bde67d8eb0d4cca30` in the user's Bend fork, based on evaluation revision `b9d1352c9f45632447f40a2e927355c92f2be58c`. The [patch](patches/bend-gpu-stack-spill.patch) preserves the complete change. The evaluation checkout remains unchanged, and the [original UTS GPU failures](UTS_GPU.md) remain valid results for the unpatched revision.

## Stack growth

Each GPU lane starts with the existing transposed 2,048-word stack. When a push would exceed its capacity, the lane allocates a larger power-of-two block from the runtime's existing heap allocator and copies its active stack words into contiguous storage. Further growth copies and releases the previous block. Returning from the work loop releases the final spill block. Lanes that stay within the original capacity allocate no spill storage.

The patch checks task-entry and continuation-argument pushes in addition to emitted call frames. CPU stack representation is unchanged. Stack growth remains bounded by available heap memory; it does not make arbitrary recursion free or improve the scheduler's load balancing. Metal shares this runtime source but has not been tested on this Linux host.

## Correctness checks

Both full UTS inputs return the expected node count and zero exhausted fuel: `4112897 0` and `30399117 0`. The original runtime failed both with its stack-limit error. The patched runtime completes them, but the unchanged recursive traversal remains slow on GPU.

| Test | Original CUDA runtime | Patched CUDA runtime | Other backends |
|---|---|---|---|
| Deep fork/join recursion, 16 branches of depth 8,192 | Stack-limit error | `537067536` | CPU, JavaScript and interpreter agree |
| Heap-owned arrays held across deep recursion, repeated eight times | Stack-limit error | `67158024` | CPU, JavaScript and interpreter agree |

Both patched tests also agree with the interpreter. They pass `compute-sanitizer --tool memcheck` with zero errors. Mandelbrot, ray tracing and N-Queens retain their published output checksums. Commands, executable hashes, native checks and sanitizer logs are preserved in `runs/gpu-stack-regression-xoirpdsc/` and the [repository evidence snapshot](benchmarks/uts-stack-20260921/).

An earlier iteration of the spill patch completed the 4,112,897-node UTS input correctly in a single 52-second check. Its larger-input check reached the 180-second timeout, preserved in `runs/7b7bd269c513c5f5127c/`. These are development correctness checks, not ten-repetition performance results.

## GPU performance cost

| Published workload | Original runtime | Patched runtime | Change in complete-program time |
|---|---:|---:|---:|
| Mandelbrot | 0.1382 s | 0.1394 s | +0.8% |
| Ray tracing | 0.9692 s | 0.9973 s | +2.9% |
| N-Queens | 1.2157 s | 1.3244 s | +8.9% |

Each cell is the median of ten correctness-passed executions on the RTX 3090, using 16 host threads and a 4 GB GPU heap. Each binary received one excluded warmup, and the 60 measured executions used a deterministically shuffled order. All output and GPU activity checks passed. These are fresh matched comparisons of the original and patched binaries, rather than comparisons with the September 17 scorecard.

The patch trades some performance for deeper recursion. The N-Queens regression is a reason to improve the common stack-access path before treating this as a performance-neutral replacement. No scheduler improvement is established by this change.

## Final validation

The [patched UTS configuration](uts-gpu-stack.toml) pins the committed fork and gives each input a 900-second limit. The finite user service `bend-bench-uts-stack.service` completed on September 21 at 19:03 EDT after 9 minutes 45 seconds. It checked both UTS inputs once, then ran the paired measurements above. The shared execution lock, GPU activity policy and separate source identities were enforced.

Final logs and completion evidence are under `runs/uts-stack-final-20260921/`; the UTS run is `c453203ceb92a34f628b`. The repository includes the [completion marker](benchmarks/uts-stack-20260921/completed.json), [UTS checks](benchmarks/uts-stack-20260921/uts-checks.jsonl), [paired samples](benchmarks/uts-stack-20260921/paired-samples.jsonl), [binary hashes](benchmarks/uts-stack-20260921/paired-binaries.json), [build commands](benchmarks/uts-stack-20260921/builds.jsonl), [regression checks](benchmarks/uts-stack-20260921/checks.jsonl) and [memory-check results](benchmarks/uts-stack-20260921/memcheck.jsonl). The scorecard retains the original pinned-runtime results; single correctness timings from a different runtime revision do not replace them.
