# Remaining published-workload CUDA baselines

Goal: add conventional CUDA comparisons for the eleven original workloads still missing one, preserving generated inputs, arithmetic and required outputs. Implementations and subsequent measured results are committed separately. No existing measurement is replaced by a compile-only result.

| Workload | Implementation | GPU correctness | Ten measured repetitions |
|---|---|---|---|
| Mandelbrot | Compiles; pixel-parallel fixed-point escape counts and weighted histogram reduction | Pending idle GPU | Pending |
| N-Queens | Compiles; split selected prefixes into smaller subtrees, iterative device search | Pending idle GPU | Pending |
| Merkle tree | Pending | Pending | Pending |
| Lexer | Pending | Pending | Pending |
| K-means | Pending | Pending | Pending |
| Hash tables | Pending | Pending | Pending |
| Batched maze BFS | Pending | Pending | Pending |
| Three-body ensemble | Pending | Pending | Pending |
| Ray tracing | Pending | Pending | Pending |
| Terrain | Pending | Pending | Pending |
| Symbolic regression | Pending | Pending | Pending |

The first Mandelbrot native check was refused by the GPU activity gate before compilation or execution because an unapproved GPU process was active. No workload was stopped or exempted. A separate compile-only check passed, with evidence in `runs/vendor-custom-build-i7n433kf/build.jsonl`. The regression suite passed 71 tests with seven expected skips. Mandelbrot verification compares every escape count with the pinned C implementation, all histogram statistics, and the final original checksum, including the published 4096 × 4096 input. These GPU checks remain pending.

N-Queens compilation passed in `runs/vendor-queens-build-l8ftajs6/build.jsonl`; focused adapter tests passed with native GPU checks skipped. The host expands each legal four-row prefix by three rows, accounting for every visited node, then the GPU searches those independent subtrees with explicit stacks. Verification compares both solution and node counts for every selected prefix with the original recursive C search. Prefix expansion, transfers and final host aggregation remain in complete-process timing.

Use [vendor-gpu-custom.toml](vendor-gpu-custom.toml) for the implemented additions. Each new workload must first pass small and published-input output checks; collect one excluded warmup and ten complete-process measurements only after correctness passes. Device-sequence timings are separate from process wall times. Preserve all failed attempts. Check the existing execution lock, blocked services and GPU activity policy before every run, and never edit inputs while a validation using them is queued or active.

Keep each implementation attempt bounded: compile and validate a minimal correct mapping before tuning; after two failures at the same gate, inspect the semantic or tooling premise instead of adding another workaround. Do not substitute a different numerical task to fill a cell. If source semantics or hardware requires a scope change, record the evidence and request direction.
