# Source attribution

The bend-bench harness and original contributions are MIT-licensed; see LICENSE. This does not replace the licenses of upstream code used by benchmark adapters or generated programs.

## Published-workload GPU libraries

The optional adapters call separately installed NVIDIA CUB, cuBLAS and cuDF libraries. The radix and matrix generators implement the pinned Bend workload contracts; the edit-distance adapter includes the upstream C generator and correctness oracle at build time. Existing Bend attribution below applies to that included source. cuDF and RMM are Apache-2.0 dependencies supplied through the locked optional environment in `dependencies/cudf`; their wheel distributions retain their own licenses and those of bundled dependencies. cuBLAS is distributed under NVIDIA's applicable SDK license. This repository does not bundle these libraries or relicense generated binaries.

## Application comparisons

The packaged N-Queens Bend port and C++ bit-mask baseline are original evaluation code, MIT-licensed. They implement the BOTS N-Queens problem and known solution counts without copying the BOTS array-based solver.

The BFS adapters include [GAP Benchmark Suite](https://github.com/sbeamer/gapbs) and [Gunrock](https://github.com/gunrock/gunrock) from separate pinned checkouts. GAP carries its Regents of the University of California BSD-style license; Gunrock is Apache-2.0. Gunrock also uses [ModernGPU](https://github.com/moderngpu/moderngpu), with Sean Baxter's BSD-style license, and NVIDIA CCCL. The full upstream licenses remain in those checkouts; preserve them when distributing resulting sources or binaries. The harness package does not bundle the repositories. The pricing and exact m,n,k controls are original MIT-licensed code. No source or model from `/code/mnk` is incorporated.

## NVIDIA CUB / CCCL

The GPU primitive adapter calls CUB from NVIDIA CCCL v3.1.0, commit `ecfd3adfaa7ebcb81d80d5b297ab3551619fda02`: https://github.com/NVIDIA/cccl. CCCL remains an external dependency with its component and per-file licenses. Its checkout preserves CUB, Thrust and libcu++ license notices. A four-line libcu++ declaration compatibility patch for Clang 22 is preserved in `patches/cccl-clang-deduction-guides.patch`; no CUB algorithm is changed. `assets/gpu/cub.cu` and `reference.cpp` adapt Bend's U32 input generator and output checksum contract, retaining Apache-2.0 coverage for those upstream-derived portions.

## Rodinia HotSpot

HotSpot targets the University of Virginia's original Rodinia 3.1 archive: https://www.cs.virginia.edu/~skadron/lava/Rodinia/Packages/rodinia_3.1.tar.bz2, SHA-256 `faebac7c11ed8f8fcf6bf2d7e85c3086fc2d11f72204d6dfc28dc5b2e8f2acfd`. Copyright (c) 2008-2011 University of Virginia. Its license is retained in `licenses/Rodinia.txt`. The adapter includes external CUDA/OpenMP sources at build time; generated OpenMP code adds the missing interior-cell branch in boundary tiles. The replacement driver uses the CUDA timestep on both backends, records timing and emits complete float bit patterns. The Bend port implements the same stencil using balanced trees. Retain Rodinia's notices when distributing derived sources or binaries.

Relevant papers credited by the suite are Che et al., “Rodinia: A Benchmark Suite for Heterogeneous Computing,” IISWC 2009, and Meng and Skadron, “Performance Modeling and Automatic Ghost Zone Optimization for Iterative Stencil Loops on GPUs,” ICS 2009.

## Bend benchmark adaptations

Copyright 2026 HigherOrderCO.

The custom published-workload CUDA adapters under `src/bend_bench/assets/gpu/vendor-*.cu` adapt Bend's generators, arithmetic and result contracts, with Apache-2.0 applying to upstream-derived portions. They include pinned upstream C references at build time for correctness checks; the source checkout remains unchanged.

The baseline assets under `src/bend_bench/assets/baselines/` adapt the algorithms, arithmetic, output contracts and structure of Bend's runtime benchmarks. Bend source: https://github.com/bendlang/bend, reference commit `b9d1352c9f45632447f40a2e927355c92f2be58c`, directory `bench/runtime`. Bend distributes those sources under Apache-2.0; the license is included in `licenses/Apache-2.0.txt`. Retain that license for upstream-derived portions of the assets and generated benchmark code.

Local changes add OpenMP loops, reductions and thread-local arenas; conventional parallel sorting; stored-tree Merkle proof extraction; CUDA Game of Life kernels; timing instrumentation; and build-time wrapper generation. Upstream sources are read from a separately pinned checkout and remain unchanged. No upstream NOTICE file was present in the captured repository.

## Barcelona OpenMP Tasks Suite

The UTS adapter targets BOTS: https://github.com/bsc-pm/bots, reference commit `2607a695128727a3f6c98754367705443663136d`. BOTS is a separate dependency with its own COPYING/LICENSE and per-file notices. Its repository LICENSE contains GPL version 2. The UTS source additionally credits the 2007 Unbalanced Tree Search Project Team and identifies its original MIT licensing. The SHA-1 source credits Dr Brian Gladman (2002) and includes its own license terms. BOTS files also credit Barcelona Supercomputing Center and Universitat Politecnica de Catalunya (2009). The harness does not bundle BOTS source files or binaries.

`assets/ports/uts.bend` implements the BOTS binomial-tree input and SHA-1 state-transition contract. `assets/baselines/uts-omp.c` supplies an OpenMP task implementation and compiles against BOTS headers and SHA-1 source from the external checkout. Distributing resulting BOTS-based benchmark binaries requires preserving the applicable upstream licensing and source obligations; the harness's MIT license does not relicense them.

`assets/gpu/uts.cu` is a project-written CUDA frontier traversal and fixed-message SHA-1 implementation. It links the same external BOTS RNG as a host correctness oracle and root-state generator; the resulting binary retains those dependency obligations.
