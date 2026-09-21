# Heap-backed GPU continuation stacks

The runtime fix lets a GPU lane outgrow its fixed continuation stack without changing the Bend program. Two deep fork/join regression programs fail with the original runtime and pass with the patch on CUDA. They also pass on CPU, JavaScript and the interpreter; CUDA's memory checker reports zero errors for both.

The fix is local commit `19fa5ae3643241c70bcfbf1bde67d8eb0d4cca30` in the user's Bend fork, based on evaluation revision `b9d1352c9f45632447f40a2e927355c92f2be58c`. The [patch](patches/bend-gpu-stack-spill.patch) preserves the complete change. The evaluation checkout remains unchanged, and the [original UTS GPU failures](UTS_GPU.md) remain valid results for the unpatched revision.

## Stack growth

Each GPU lane starts with the existing transposed 2,048-word stack. When a push would exceed its capacity, the lane allocates a larger power-of-two block from the runtime's existing heap allocator and copies its active stack words into contiguous storage. Further growth copies and releases the previous block. Returning from the work loop releases the final spill block. Lanes that stay within the original capacity allocate no spill storage.

The patch checks task-entry and continuation-argument pushes in addition to emitted call frames. CPU stack representation is unchanged. Stack growth remains bounded by available heap memory; it does not make arbitrary recursion free or improve the scheduler's load balancing. Metal shares this runtime source but has not been tested on this Linux host.

## Correctness checks

| Test | Original CUDA runtime | Patched CUDA runtime | Other backends |
|---|---|---|---|
| Deep fork/join recursion, 16 branches of depth 8,192 | Stack-limit error | `537067536` | CPU, JavaScript and interpreter agree |
| Heap-owned arrays held across deep recursion, repeated eight times | Stack-limit error | `67158024` | CPU, JavaScript and interpreter agree |

Both patched tests pass `compute-sanitizer --tool memcheck` with zero errors. Mandelbrot, ray tracing and N-Queens also retain their published output checksums. Commands, executable hashes, native checks and sanitizer logs are preserved in `runs/gpu-stack-regression-xoirpdsc/`.

An earlier iteration of the spill patch completed the 4,112,897-node UTS input correctly in a single 52-second check. Its larger-input check reached the 180-second timeout, preserved in `runs/7b7bd269c513c5f5127c/`. These are development correctness checks, not ten-repetition performance results.

## Final validation

The [patched UTS configuration](uts-gpu-stack.toml) pins the committed fork and gives each input a 900-second limit. The finite user service `bend-bench-uts-stack.service` checks both UTS inputs once, then measures the original and patched GPU implementations of Mandelbrot, ray tracing and N-Queens ten times each after excluded warmups. Measurement order is deterministically shuffled. The shared execution lock, GPU activity policy and separate source identities remain enforced.

Final logs and completion evidence are under `runs/uts-stack-final-20260921/`. The run is still pending; neither the initial timings nor the pending checks replace the scorecard's pinned-runtime results. Follow progress with:

```sh
journalctl --user -u bend-bench-uts-stack.service -f
```
