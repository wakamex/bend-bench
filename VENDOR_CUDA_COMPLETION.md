# Remaining published-workload CUDA baselines

Goal: add conventional CUDA comparisons for the eleven original workloads still missing one, preserving generated inputs, arithmetic and required outputs. Implementations and subsequent measured results are committed separately. No existing measurement is replaced by a compile-only result.

| Workload | Implementation | GPU correctness | Ten measured repetitions |
|---|---|---|---|
| Mandelbrot | Compiles; pixel-parallel fixed-point escape counts and weighted histogram reduction | Pending idle GPU | Pending |
| N-Queens | Compiles; split selected prefixes into smaller subtrees, iterative device search | Pending idle GPU | Pending |
| Merkle tree | Compiles; parallel Speck leaves, stored levels, separate audit and proof verification | Pending idle GPU | Pending |
| Lexer | Compiles; independent generated lines with ordered token folds and warp reductions | Pending idle GPU | Pending |
| K-means | Compiles; cached points, parallel assignment and integer centroid reductions | Pending idle GPU | Pending |
| Hash tables | Compiles; bounded open addressing with original logical bucket accounting | Pending idle GPU | Pending |
| Batched maze BFS | Pending | Pending | Pending |
| Three-body ensemble | Pending | Pending | Pending |
| Ray tracing | Pending | Pending | Pending |
| Terrain | Pending | Pending | Pending |
| Symbolic regression | Pending | Pending | Pending |

The first Mandelbrot native check was refused by the GPU activity gate before compilation or execution because an unapproved GPU process was active. No workload was stopped or exempted. A separate compile-only check passed, with evidence in `runs/vendor-custom-build-i7n433kf/build.jsonl`. The regression suite passed 71 tests with seven expected skips. Mandelbrot verification compares every escape count with the pinned C implementation, all histogram statistics, and the final original checksum, including the published 4096 × 4096 input. These GPU checks remain pending.

N-Queens compilation passed in `runs/vendor-queens-build-l8ftajs6/build.jsonl`; focused adapter tests passed with native GPU checks skipped. The host expands each legal four-row prefix by three rows, accounting for every visited node, then the GPU searches those independent subtrees with explicit stacks. Verification compares both solution and node counts for every selected prefix with the original recursive C search. Prefix expansion, transfers and final host aggregation remain in complete-process timing.

Merkle compilation passed in `runs/vendor-merkle-build-zhychlbb/build.jsonl`. The adapter builds flat stored tree levels, then performs the original audit recurrence in a separate pass and verifies a proof using stored sibling hashes. Correctness checks compare every leaf, internal hash and audit value with CPU reference calculations, plus the original proof generator and verifier. The compiler reports the pinned upstream renamed `main` has no explicit return; that unused reference entry point is never called. Focused adapter planning tests passed; GPU checks remain pending.

Lexer compilation passed in `runs/vendor-lexer-build-ddlwrh_8/build.jsonl`, with the same unused-reference-entry warning. Each lane generates and scans a complete line, preserving identifier hashing, decimal parsing and token order; warp sums combine the independent line results. Verification checks every line's result against the upstream generator and scanner, including all 2^23 published lines. Focused planning tests passed; native correctness and timing remain pending.

K-means and all four preceding adapters compiled in `runs/vendor-custom-build-yn1k9j3a/build.jsonl`. The K-means adapter caches the generated points, computes per-block integer sums for eight clusters, and updates all 64 starts over 20 iterations. It retains integer division, lower-index distance ties and unchanged empty clusters. Verification checks the generated point vector and every centroid at every iteration against the original C tree-based calculation. The shared custom-adapter tests now cover every configured workload and provide separate opt-in compilation and GPU-execution checks.

Hash tables and all preceding adapters compiled in `runs/vendor-custom-build-5zd9yrym/build.jsonl`. The CUDA implementation uses 32,768 open-addressed slots for at most 16,384 keys per table, preserving deduplication with atomic insertion. Separate counters retain the original 4,096 logical bucket lengths rather than substituting the CUDA table's physical layout. Verification checks every logical bucket, hit count and per-table checksum against the pinned chain-table reference, including empty and single-key inputs. GPU execution remains pending.

Use [vendor-gpu-custom.toml](vendor-gpu-custom.toml) for the implemented additions. Each new workload must first pass small and published-input output checks; collect one excluded warmup and ten complete-process measurements only after correctness passes. Device-sequence timings are separate from process wall times. Preserve all failed attempts. Check the existing execution lock, blocked services and GPU activity policy before every run, and never edit inputs while a validation using them is queued or active.

Keep each implementation attempt bounded: compile and validate a minimal correct mapping before tuning; after two failures at the same gate, inspect the semantic or tooling premise instead of adding another workaround. Do not substitute a different numerical task to fill a cell. If source semantics or hardware requires a scope change, record the evidence and request direction.
