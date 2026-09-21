# GPU baselines for the 16 published workloads

All 16 workloads already have Bend GPU measurements. Fourteen still need a conventional GPU comparison. The best first additions are CUB sort-and-deduplicate, cuBLAS matrix multiplication and cuDF edit distance: each has an established GPU component that appears compatible with the actual task. Fixed-point Mandelbrot is the simplest useful custom-kernel follow-up.

Filling every cell is feasible in principle, but most need custom CUDA rather than an existing suite dropped into the harness. This audit checked the pinned C workload contracts against primary library APIs and example sources. It adds no measurements and changes no scorecard cells.

## Workload audit

Rows are in recommended implementation order. Low effort means a small adapter or kernel plus validation. Medium means several kernels, an input-layout adapter or substantial dependency integration. High means specialized scheduling, substantial semantic adaptation or difficult numerical validation. These are engineering estimates, not measured development times.

| Published workload and source contract | Candidate conventional GPU baseline | Required adaptation | Effort |
|---|---|---|---|
| [Radix sort and deduplication](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/tree-radix/main.c) | CUB radix sort followed by `DeviceSelect::Unique`. | Sort 2^22 generated 24-bit keys, remove duplicates, and reproduce the orderedness, count, sum and boundary checks. The existing bitonic-sort CUB measurement has a different output contract. | Low |
| [Matrix multiplication](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/tree-matmul/main.c) | cuBLAS batched GEMM, with a custom input and verification adapter. | 384 products of 128 × 128 matrices. Entries are 0–99: INT8 inputs and INT32 accumulation can preserve every product exactly. Reproduce the quadtree layout, wrapping-U32 Freivalds check and checksum. | Medium |
| [Edit distance](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/editdist/main.c) | cuDF `nvtext::edit_distance`. | 32,768 pairs of 256-symbol sequences. Encode the four symbols as single-byte characters and use pairwise Levenshtein distance, then the original checksum. Include string-column construction in complete-program time. Dependency integration is the main uncertainty. | Medium |
| [Mandelbrot](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/mandelbrot/main.c) | Custom fixed-point pixel kernel plus GPU histogram/reduction primitives. | 4096 × 4096 pixels, 51 iterations, signed 8.8 fixed-point arithmetic, histogram equalization and checksum. NVIDIA's floating-point sample is a reference for mapping work, not an equivalent implementation. | Low |
| [N-Queens](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/queens/main.c) | Custom prefix-search CUDA kernel using the already validated CPU contract. | Preserve the selected 17 × 17 prefix set and both solution and node counts. Distribute smaller search subtrees to avoid a few long searches determining runtime. The existing batching experiment supplies a correctness reference. | Medium |
| [Merkle tree](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/merkle/main.c) | Custom Speck leaf hashing and level-by-level tree construction. | 2^22 leaves, 30 chained blocks per leaf, custom parent hash, audit and proof verification. Reuse stored tree nodes for the proof. A SHA-based or Poseidon-based Merkle library would change the task. | Medium |
| [Lexer](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/lexer/main.c) | Custom CUDA scanner across independent generated lines. | 2^23 lines, exact identifier hashes, decimal parsing, punctuation and ordered token checksums. Start with a lane per line and check register/local-memory pressure. General text tokenization is a different contract. | Medium |
| [K-means](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/kmeans/main.c) | Custom assignment kernels and integer reductions. | 64 starts, 524,288 2D points, eight clusters, 20 iterations. Preserve integer centroid division, tie-breaking and empty-cluster behavior. cuVS's floating-point K-means API is not a direct replacement. | Medium |
| [Independent hash tables](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/hashmap/main.c) | cuCollections `static_set`, with custom batched keys and logical-bucket accounting. | 2,048 tables with 16,384 inserts and lookups each. Encode table identity in keys. Preserve deduplication, hit counts and the ordered fold of 4,096 original bucket lengths; the library's physical hash slots cannot supply that last result directly. | High |
| [Batched maze BFS](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/bfs/main.c) | Custom warp/block-per-maze traversal, with bounded batches. | 524,288 independent 32 × 32 mazes, not one shared graph. Preserve generated walls, reached counts and distance checksums. The existing shared-graph Gunrock result cannot fill this cell. | High |
| [Three-body ensemble](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/nbody/main.c) | Custom kernel across independent three-body systems. | 2^20 systems, 300 integration steps, softened force, histogram and bit-level digest. NVIDIA's all-pairs N-body sample is a different problem. Floating-point operation order and contraction require explicit checking. | High |
| [Ray tracing](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/raytrace/main.c) | Custom CUDA pixel tracer first; OptiX is a possible second implementation. | 6000 × 4096 pixels, nine spheres, four subpixel rays, shadows and depth-four reflections. Preserve intersection tie-breaking and quantized output. OptiX still needs matching scene, intersection and shading code; its acceleration structure may not help this small scene. | High |
| [Terrain](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/terrain/main.c) | Custom tile kernel preserving in-place dependencies. | 65,536 tiles of 64 × 64 cells and five Gauss–Seidel sweeps, followed by histogram and checksum. An anti-diagonal wavefront can preserve north/west dependencies, but synchronization is expensive. A Jacobi stencil would change the calculation. | High |
| [Symbolic regression](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/bench/runtime/symreg/main.c) | Custom expression evaluator and selection kernels. | 2^18 depth-five expression candidates, 110 evaluation points, U32 arithmetic including XOR, ordered tournament ties and hill climbing. EvoGP is relevant GPU tree-evaluation code, but adopting its default operators, fitness or selection would change the benchmark. | High |

Game of Life already has a project-written CUDA control. Bitonic sorting already has a CUB comparison on the same generated input and checked output. They are the two completed conventional GPU cells, although the implementations use different algorithms where appropriate.

## Three library-backed additions

### CUB sorting and deduplication

The existing pinned CCCL source provides both radix sorting and [consecutive-duplicate removal](https://github.com/NVIDIA/cccl/blob/ecfd3adfaa7ebcb81d80d5b297ab3551619fda02/cub/cub/device/device_select.cuh). Composing them matches the radix workload's output requirement. Preserve the unique count and checksum, rather than timing sorting alone. This reuses the dependency and integration work already done for CUB sorting and summation.

### cuBLAS matrix multiplication

This workload does not require arbitrary unsigned-integer matrix multiplication. Its generated entries lie between 0 and 99, so each output is at most `128 * 99 * 99 = 1,254,528`. Signed INT8 inputs and INT32 accumulation therefore suffice. [cuBLAS](https://docs.nvidia.com/cuda/cublas/index.html) documents this type combination for extended GEMM APIs. The dimensions also satisfy the documented four-element leading-dimension alignment requirement.

That makes a batched library implementation a plausible exact baseline. The subsequent Freivalds verification does use wrapping U32 arithmetic and needs a separate matching implementation. First smoke-test the installed toolkit's batched API, flattening order and output on small matrices. The archived online manual is newer than the installed CUDA 13.1 toolkit; documentation availability is not a local compatibility test.

### cuDF edit distance

The [nvtext API](https://github.com/NVIDIA/cudf/blob/cba08937526d54de1b15ded7b0b2769ee3d43759/cpp/include/nvtext/edit_distance.hpp) provides pairwise Levenshtein distance, matching the workload's recurrence. A one-to-one mapping of its four symbols to single-byte characters preserves the answer. The original generator and pair-weighted checksum stay in the adapter. This is a stronger candidate than substituting a sequence-alignment benchmark with different scoring rules, but its dependency cost should be checked before implementing a larger adapter.

## Candidates needing custom work

cuCollections is the fourth promising library-backed route, but the hash-table workload also observes logical bucket lengths. Recovering those from unique keys is part of the measured job, even if the container uses a different physical representation. [The container source](https://github.com/NVIDIA/cuCollections/blob/0bda929bebc39b50865eed2b3256bf35f976548d/include/cuco/static_set.cuh) is archived for that feasibility check.

Several familiar names conceal incompatible calculations. The [NVIDIA Mandelbrot example](https://github.com/NVIDIA/cuda-samples/blob/5443602d89ed99aede2e4b7bf329daddeadb320e/cpp/5_Domain_Specific/Mandelbrot/Mandelbrot_kernel.cuh) uses floating-point arithmetic, while this benchmark uses fixed-point integers. [NVIDIA's N-body example](https://github.com/NVIDIA/cuda-samples/blob/5443602d89ed99aede2e4b7bf329daddeadb320e/cpp/5_Domain_Specific/nbody/bodysystemcuda.cu) computes interactions in a shared system, while this benchmark runs independent three-body systems. [cuVS K-means](https://github.com/NVIDIA/cuvs/blob/241df2755c77d7660d3f0f03ec0949e0befaf338/cpp/include/cuvs/cluster/kmeans.hpp) exposes floating-point centroids; changing the benchmark's integer rounding would change later assignments.

[OptiX](https://github.com/NVIDIA/optix-sdk/tree/6a6c77392ef2bc9770b5c2e142cc5eefbd5b110d) and [EvoGP](https://github.com/EMI-Group/evogp/tree/5538d75470ee0fa444ee6bbe5ea98b2eed6e99f8) are relevant implementation resources for ray tracing and expression evaluation. Neither is a verified adapter for these exact workloads. For lexer, custom-hash Merkle, terrain and selected-prefix queens, this audit identified no established implementation that could fill the cell unchanged.

## Validation and measurement

Keep the generated inputs, required outputs and arithmetic contract fixed. Compare complete small outputs against the reference before relying on large-run checksums. For the floating-point workloads, inspect intermediate states as well as final digests; a different numerical calculation belongs in a separately labeled experiment.

A baseline may use flat arrays, cache reusable values, change scheduling or select a better algorithm while preserving the task. Record those choices. Copying the source representation is not required, and a functioning first-pass CUDA port is not evidence of a tuned baseline.

For each accepted implementation:

- Pin the library, adapter, compiler flags and any patches.
- Include generation, allocation, conversion, transfers, required verification and startup in complete-program timing.
- Report GPU computation separately, distinguishing kernel durations from a device sequence that includes transfers.
- Use release builds, warmups and at least ten measured repetitions, with the existing exclusive-run and GPU-activity gates.
- Retain the CPU comparison. A GPU implementation that loses to CPU is still informative for these fixed workloads.

Start with a small correctness and build probe for each library before integrating it into the harness. If two approaches fail the same semantic gate, revisit the assumed match before adding infrastructure.

## Saved evidence

The evaluation reference is Bend commit `b9d1352c9f45632447f40a2e927355c92f2be58c`. Candidate repository files were fetched at exact commits, not retained as moving-branch links. [The source manifest](benchmarks/gpu-baseline-audit-20260920/manifest.json) records URLs, revisions and SHA-256 hashes for the archived files and workload contracts.

Original candidate sources are saved locally in `sources/gpu-baseline-audit-20260920/`. Existing CCCL headers remain in `sources/cccl-clang/`; the immutable Bend contracts remain in `/code/bend2/upstream/`. These source directories are local evidence, not bundled dependencies. The cuBLAS original HTML is retained alongside a convenience Markdown extraction; the extraction omits introductory material and is not a complete replacement for the original page.

