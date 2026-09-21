# Lowering Bend U32 reductions to CUB

Proposal, September 21, 2026. No compiler changes have been made for this proposal.

The first experiment is to make Bend execute a generated-integer summation through CUB instead of its generic GPU task scheduler, while preserving the exact answer and keeping ordinary Bend execution as a fallback. Measure the integrated path before investing in automatic recognition of arbitrary programs. If integration works, teach the compiler to recognize a narrow class of balanced U32 reductions without requiring users to change their source.

The existing standalone benchmark establishes a performance opportunity. It does not establish how fast CUB would be when called through Bend's executable, context management and runtime.

## Current workspace and evidence

| Resource | Location or identity |
|---|---|
| Compiler working fork | `/code/bend`, remote fork owned by `wakamex` |
| Compiler revision inspected | `b9d1352c9f45632447f40a2e927355c92f2be58c`; the working fork was clean at proposal creation |
| Immutable evaluation reference | `/code/bend2/upstream`, at the same revision; never modify it |
| Benchmark harness | `/code/bend-bench` |
| Current benchmark result commit | `9e16dc1`, recording the three new GPU library baselines |
| CUB dependency | `/code/bend-bench/sources/cccl-clang`, revision `ecfd3adfaa7ebcb81d80d5b297ab3551619fda02`, with an existing compatibility patch that must be preserved and recorded |
| Evaluation GPU and CPU | RTX 3090 and Ryzen 3950X, 16 physical CPU cores |
| Existing native toolchain | Clang CUDA compilation, CUDA 13.1; inspect current configuration rather than assuming tool versions are unchanged |

Read the applicable `AGENTS.md` files before work. In bend-bench, also read `README.md`, `VALIDATION.md` and `QUEUE.md` before preparing or running benchmarks. Inspect current Git status and service state; the paths and revisions above describe the starting evidence, not permission to overwrite later work.

Useful starting files:

- `/code/bend/bend2/comp.ts`: compiler, native-operation handling and embedded runtimes. At the inspected revision, `arr_op` is around line 1870, `emit_native` around 2114, and CUDA context, compilation and launch code around 4870–5000. Search the symbols rather than relying on fixed line numbers.
- `/code/bend/guide/GUIDE.md`: parallel-call contract, arrays and runtime representation. The guide says parallel calls are independent and should have similar runtimes; scheduling is fixed binary fork-join without work stealing.
- [Bend summation source](src/bend_bench/assets/gpu/reduce.bend): pure balanced recursion over generated U32 keys. It does not allocate a flat input array.
- [Standalone CUB implementation](src/bend_bench/assets/gpu/cub.cu): counting and transform iterators generate keys inside the reduction without materializing an input array.
- [Summation scaling results](SUMMATION_SCALING.md), `summation_scaling.py` and `reduction_crossover.py`: input sizes, large-count support, independent references, execution guards and timing methodology.
- [GPU library adapter results](VENDOR_GPU_LIBRARIES.md): recent CUB sorting/deduplication, cuBLAS matrix multiplication and cuDF edit-distance integrations. Their native adapters are in `src/bend_bench/assets/gpu/vendor-*`.
- [Baseline feasibility audit](GPU_BASELINE_AUDIT.md): later candidate operations and the semantic differences that prevent some apparent library substitutions.

The matched summation sweep found Bend ahead of standalone CUB end-to-end at 268 million and 537 million items, and CUB ahead at 1.07 billion and 2.15 billion. Startup materially affects the crossover. The 16-thread OpenMP control finished sooner than either GPU implementation at all four sizes. Preserve these CPU comparisons in interpretation; integration should earn its benefit through measurement.

## Intended compiler behavior

An eligible pure reduction has a known finite index range, an independently evaluable U32 generator and wrapping-U32 addition. The desired GPU implementation feeds that generator directly into CUB's reduction, avoiding both intermediate arrays and a generic task per recursive call. Unsupported programs continue through the existing runtime.

Explicit native operations and automatic recognition are complementary. A narrow internal operation gives code generation a reliable target. A later compiler pass can recognize equivalent source and emit that operation. The first prototype may expose a private test entry point, but should not establish a public intrinsic API prematurely.

Existing specialization and representation machinery provides places to investigate, not proof that the optimization is a small patch. Do not match benchmark names or hard-code the expected checksum. Automatic recognition must depend on the program's structure and arithmetic.

## First eligible program

The existing `reduce.bend` generator computes:

```text
x = (i + 1) * 2654435761
x = x XOR (x << 13)
x = x XOR (x >> 17)
x = x XOR (x << 5)
```

Every step uses U32 arithmetic. A depth-d reduction starting at index i visits the indices from `i * 2^d` through `(i + 1) * 2^d - 1`, with the source's wrapping index behavior. It adds the generated values modulo `2^32`.

For the first recognizer, require a provably bounded, non-wrapping index interval and a supported depth, initially the benchmark's `i = 0` case. Preserve the wider source language by falling back when those conditions cannot be established. Use a sufficiently wide count type: `2^31` elements must not become a negative signed 32-bit count. The tested CUB adapter already handles this with a 64-bit item count.

Wrapping-U32 addition is associative and commutative, so a different reduction tree preserves the result. That does not extend to arbitrary operations. Floating-point addition can change its answer when regrouped; repeatability within CUB is not equivalence to Bend's original reduction order.

## Runtime integration boundary

At the pinned revision, Bend retains a CUDA primary context, creates a managed heap, compiles its device program through NVRTC and launches `bend_dev` through the CUDA Driver API. CUB's device-wide reduction is a host-dispatched C++ facility. It cannot simply replace an expression executing inside `bend_dev`.

The first prototype should operate at a host-visible GPU call boundary and accept scalar inputs, returning a scalar U32. This deliberately avoids flattening recursive data, transferring ownership of arbitrary heap objects or supporting native calls from arbitrary nested GPU tasks.

A small separately compiled CUDA/C++ helper with a C ABI is one candidate bridge. Confirm that it can use Bend's existing primary context and the intended stream, allocate temporary storage, complete the operation and return its result safely. The receiving implementation session should choose the smallest compatible integration after inspecting the actual call boundary. Do not build a general FFI or plugin framework for this experiment.

The generated transform must execute as device code. An arbitrary Bend function pointer or suspended runtime task is not a CUB functor. Start with a narrow supported arithmetic subset, compiled into the helper, and reject or fall back on unsupported generator operations. This is also where compiler recognition must retain enough structure to generate the specialized function.

Record the helper source, CUB revision and patch, compiler flags, GPU architecture and binaries. If helpers are cached, changed generators or dependencies must invalidate them. Reuse existing build/cache mechanisms where possible; add a new cache only if measurements demonstrate the need.

## Experiment sequence and stop limits

### 1. Native bridge and integration cost

Timebox the first bridge investigation to two hours. Before building a recognizer, run the generated-U32 CUB reduction from a minimal Bend entry point using the actual runtime context. Check a small answer against the existing scalar reference, then compare stock Bend, integrated CUB and standalone CUB at the same inputs.

Record whether the prototype bypasses initialization that stock Bend still performs, or instead pays for both runtimes. Count both effects in complete-program time. A separate native executable launched by Bend is not the intended integration.

If two attempted fixes fail at the same integration gate, identify the failing layer and revisit the hypothesis before another edit. If integration overhead removes the benefit at every tested size, stop before implementing general recognition and document where the time goes.

### 2. Narrow automatic recognition

Proceed only after the bridge passes correctness and shows a useful measured benefit. Timebox an initial recognition spike to four hours. Recognize the balanced range reduction and supported U32 generator structurally, then emit the same internal native operation. Include renamed functions and equivalent small programs so the optimization is demonstrably broader than one benchmark name.

Require an observable compiler diagnostic or generated-code marker indicating whether lowering occurred. An unsupported program should visibly remain on the fallback path in development tests. If recognizing this narrow form requires a broad new IR or compiler redesign, stop and write down the missing representation instead of expanding the project silently.

### 3. Correctness and performance validation

Compare the same source with lowering enabled and disabled, plus the independent scalar implementation and existing standalone CUB control. Include CPU fallback checks. Measure one causal change at a time; do not change the scheduler, arithmetic, workload size and library integration together.

Start with inexpensive cases, then use the existing powers-of-two scaling points through `2^31` items. Bound individual executions to 180 seconds and a first measurement session to 30 minutes after GPU admission. Stop on correctness errors or unapproved GPU activity; retain the failure. Further sweeps, tuning and persistent-service experiments require a concrete reason from the first results.

## Correctness requirements

- Exact U32 output agreement, including multiplication, shifts, XOR and reduction overflow. Do not promote the accumulation to a mathematically unbounded integer result.
- Depth-zero and one-element cases, varied seeds or generator constants, supported nonzero interval starts, and the supported count boundaries. If an explicit primitive accepts an empty range, test its identity separately; depth zero in the existing source means one item, not zero.
- Small randomized programs in the supported arithmetic subset, checked against reference semantics, lowering-disabled execution and lowering-enabled execution. Verify that the optimized path actually ran.
- Negative recognition tests: non-additive combination, mismatched child ranges, unsupported captures, floating-point accumulation and observable effects must not be silently lowered to this primitive.
- Ownership and lifetime checks at the bridge: temporaries remain valid until completion, the returned value is available before the continuation uses it, and repeated calls release or safely reuse storage.
- Checked error propagation for allocation, compilation and launch failures. Unsupported capability may use a deliberate fallback; a failed execution must not masquerade as successful lowering.
- CPU-only builds and the ordinary non-lowered GPU path remain functional without the optional helper dependency.

A source proof alone does not validate this optimization. Keep the source-level definition and its meaning intact; do not introduce an unchecked logical axiom to justify a faster implementation. The compiler transformation and native bridge add obligations at the implementation layer. Differential testing is necessary evidence, but is not a formal proof of compiler correctness.

## Timing and acceptance

Report complete-process wall time first, including ordinary runtime startup, allocation, transfers, synchronization and output. Record JIT/cache state. Separate an initial uncached compilation run from steady cached execution; neither should be silently substituted for the other. Preserve ordinary startup costs in the end-to-end result even when a warmup populates a code cache.

Collect at least ten measured executions after excluded warmups, with interleaved or shuffled implementations. Separately measure the device sequence and, after unprofiled measurements, kernel-only durations. Do not present a CUDA-event interval containing transfers or host launch gaps as the sum of kernel durations. Track temporary device-memory requirements separately from host RSS.

Accept the prototype as useful when exactness and fallback tests pass and the integrated path reproducibly improves complete-program time at some meaningful tested sizes. Report every tested size, including regressions. If only device computation improves, report that narrower result and investigate startup before enabling lowering by default. A size-dependent dispatch threshold needs integrated measurements; do not copy the standalone crossover threshold.

## Operational rules and handoff

Before execution, inspect active user services, including `bend2-evaluation.service` and any bend-bench validation jobs, and acquire the existing per-user harness lock. Use the existing GPU admission/activity policy. Its configured transcription-worker exemption includes canaries; preserve that policy and record observed activity. Never stop another workload to obtain the GPU. If waiting is required, use a finite systemd user job rather than token-consuming polling.

Make compiler changes only in `/code/bend`, preserving the starting commit and exact patch. Keep benchmark configurations, adapters and result reporting in `/code/bend-bench`. Read `/code/bend/AGENTS.md` if present before editing there. Never alter the pinned evaluation checkout or delete failed measurements. Do not edit dependencies or harness inputs while an active benchmark depends on them.

Commit atomically and locally. Separate implementation commits from subsequent result reporting. Result-affecting commit messages must state measured before/after values or explicitly say the effect is unmeasured. Do not push or open an upstream contribution without a separate request.

The initial deliverables are a minimal bridge, an exact correctness test set, a pinned stock-versus-integrated measurement report and a decision on whether to proceed with recognition. If recognition is justified, add the narrow pass and its rejection tests in a separate commit. Sorting/deduplication, scans, histograms, matrix multiplication, floating-point reductions and a general native-operation framework are subsequent work, not prerequisites for this experiment.
