# Bend 2 on AMD through tinygrad

Source assessment, 2026-09-21. Reusing tinygrad is a plausible way to add an AMD execution backend while keeping Bend's scheduler and generated computation. It does not, by itself, explain or remove the performance gap between Bend's generic kernels and specialized GPU algorithms. Start with an optional backend that loads one compiled Bend kernel through tinygrad's KFD path. Keep CUDA and Metal, and defer a new GPU IR or direct instruction generator until measurements identify a limitation they would fix.

The smallest useful experiment is the same Bend kernel, with the same heap policy and launch sequence, running through HIP and through tinygrad's KFD machinery on one RX 9070 XT. That separates the benefit of direct submission from changes to Bend's algorithm, scheduler or memory placement.

## Inspected revisions and local evidence

| Source | Exact revision | Saved checkout |
|---|---|---|
| Bend upstream | `75cb8f3e041aeaad2b37e726c0a33ba19dc49df8` | `/code/bend-bench/sources/bend-current-20260921` |
| tinygrad upstream | `94ee753065770aff2aa5ba07dcf911aef298d508` | `/code/bend-bench/sources/tinygrad-20260921` |
| Existing Bend benchmark reference | `b9d1352c9f45632447f40a2e927355c92f2be58c` | `/code/bend2/upstream`, unchanged |

The [source manifest](benchmarks/tinygrad-backend-audit-20260921/manifest.json) records checkout revisions, source archive hashes, inspected-file hashes and saved AMD documentation. Archives and checkouts remain local under `sources/`. This assessment inspects current upstream architecture; existing benchmark figures belong to their original revisions. The current host has an RTX 3090 and no `/dev/kfd`. No AMD kernel, runtime integration or performance improvement was tested.

## Bend already controls GPU execution explicitly

The current `bend2/comp.ts` is 6,591 lines, including embedded native runtimes. Adding `bend2/bend.ts` and `bend2/main.ts` gives 11,219 lines, before other repository components. The roughly 6k figure describes a substantial compiler/runtime file, not the entire language implementation or the size of a replacement hardware stack.

[comp.ts](https://github.com/bendlang/bend/blob/75cb8f3e041aeaad2b37e726c0a33ba19dc49df8/bend2/comp.ts) provides these existing integration seams:

| Location at the inspected revision | Existing responsibility | AMD adaptation |
|---|---|---|
| Device dialect macros, around lines 3400-3500 | CUDA/Metal address spaces, shared memory, fences, barriers and device dispatch | Add an AMD device dialect without pretending HIP is NVRTC |
| Heap and scheduler definitions, around lines 3500-3800 | Tagged terms, heap locations, stacks, atomics, 128-thread groups and scratch layout | Preserve representation; audit memory ordering and wave assumptions |
| `bend_dev`, around line 4716 | Generic GPU kernel receiving `Corpus H` and `u32 pass` | Compile this entry point alone for the first code-object test |
| `gpu_run`, around line 5009 | Ordered frontier-growth, execution and packing passes | Preserve the pass sequence and its dependencies |
| CUDA `gpu_probe`, `gpu_map`, `gpu_make`, `gpu_load`, `gpu_kernel`, `gpu_pass`, around lines 5125-5260 | Device selection, managed allocation, NVRTC compilation, named-kernel loading, launch and synchronization | Replace these host operations behind a small backend boundary |
| `corpus_setup`, around line 5357 | Initializes the shared heap and static image on the host | Accept a validated host/device allocation and preserve initialization visibility |
| [main.ts](https://github.com/bendlang/bend/blob/75cb8f3e041aeaad2b37e726c0a33ba19dc49df8/bend2/main.ts), around lines 347-366 | Selects Metal/CUDA build flags and libraries | Add explicit AMD selection after the standalone launch experiment works |

The generated CUDA code already chooses workgroup size, uses shared memory, atomics, device fences and barriers, and manages its own stacks and work rings. Its device recursion is dispatched through explicit continuations/stacks rather than requiring arbitrary native GPU recursion. These are useful foundations for an AMD port.

Consequently, direct KFD access is not a prerequisite for controlling LDS, wave operations or memory layout: HIP/AMDGPU compilation can express those too. Replacing the driver-facing layer leaves Bend's work partitioning, heap traffic and task granularity intact. A claim that generic C syntax causes the performance gap needs a generated-code or profiling example.

## Smallest integration boundary

```text
Existing Bend frontend and optimizer
  -> existing generated computation + AMD device dialect
  -> HIP/AMDGPU compiler -> one AMD code object
  -> small pinned tinygrad launch adapter
  -> KFD allocation, queues and synchronization
  -> amdgpu kernel driver -> RX 9070 XT
```

Initially, use tinygrad as a pinned Python dependency rather than copying selected driver files. Build Bend's generated host side as a shared library with a small bridge for heap allocation, program loading, GPU passes and synchronization. Let a Python host own tinygrad device and allocation objects, retain their lifetimes, and pass the validated heap pointer into the native host. A callback per GPU pass is a reasonable prototype; a callback per Bend task is not. The host shared-library interface and callback boundary are proposed work, not existing Bend APIs.

The adapter's contract should be little more than allocation with explicit CPU/GPU visibility, loading a single compiled kernel, dispatching `(heap_pointer, pass)` with a specified grid, and waiting for completion. Compile and cache outside repeated measurements. A separate helper process would complicate pointer sharing and add transport costs, so keep the first experiment in one process.

This design avoids introducing a new compiler IR just to launch Bend's existing kernel. A later native implementation of the bridge is justified only if Python overhead or packaging proves material.

## Reusable tinygrad components

Paths below refer to the pinned tinygrad revision. These are internal interfaces, not a promised standalone driver API.

| Source and interface | Reuse | Required adaptation or boundary |
|---|---|---|
| [runtime/ops_amd.py](https://github.com/tinygrad/tinygrad/blob/94ee753065770aff2aa5ba07dcf911aef298d508/tinygrad/runtime/ops_amd.py): `KFDIface` | Device discovery, VM acquisition, allocation/mapping, queue creation and doorbells | Select KFD explicitly; verify permissions, allocation flags, visibility and lifetimes |
| Same file: `AMDDevice`, `AMDAllocator` | Architecture discovery, device state, buffers and synchronization integration | Keep their supporting modules; copying these classes alone is insufficient |
| Same file: `AMDComputeQueue`, `AMDComputeAQLQueue`, `AMDSDMAQueue` | Kernel dispatch and memory-transfer command encoding | Use the device's existing selection; match argument ABI, launch dimensions, scratch and LDS requirements |
| Same file: `amd_build_program`, `_amd_program_image`, `AMDProgramData` | Code-object parsing, upload and resource metadata | Prove compatibility with the emitted code object; first prototype should contain one kernel |
| [runtime/support/hcq2.py](https://github.com/tinygrad/tinygrad/blob/94ee753065770aff2aa5ba07dcf911aef298d508/tinygrad/runtime/support/hcq2.py): `layout_args`, `pack_args`, queue compilation/linking | Argument packing, dependency handling and host command execution | Construct a minimal program/call representation with explicit heap reads and writes |
| [device.py](https://github.com/tinygrad/tinygrad/blob/94ee753065770aff2aa5ba07dcf911aef298d508/tinygrad/device.py): `BufferSpec`, `BufferStorage`, `Compiled` | Buffer ownership and device/renderer selection | Preserve allocation objects until all native and GPU use ends |
| [runtime/support/compiler_amd.py](https://github.com/tinygrad/tinygrad/blob/94ee753065770aff2aa5ba07dcf911aef298d508/tinygrad/runtime/support/compiler_amd.py): `HIPCompiler`, `HIPCCCompiler` | Source-to-code-object compilation through COMGR or hipcc | Add Bend's headers/macros and exact arithmetic flags; inspect unresolved symbols and emitted metadata |
| [runtime/support/compiler_llvm.py](https://github.com/tinygrad/tinygrad/blob/94ee753065770aff2aa5ba07dcf911aef298d508/tinygrad/runtime/support/compiler_llvm.py): `AMDLLVMCompiler` | Compiles LLVM IR for AMD | Requires an LLVM IR producer; it cannot directly accept Bend's generated C |
| `runtime/autogen`, `runtime/support/hcq.py` and supporting ELF/MMIO code | KFD/HSA/register bindings, file access and low-level utilities | Retain transitive dependencies and audit source/licensing provenance |
| [runtime/ops_nv.py](https://github.com/tinygrad/tinygrad/blob/94ee753065770aff2aa5ba07dcf911aef298d508/tinygrad/runtime/ops_nv.py) | An eventual analogous NVIDIA launch path | Separate port and validation project; leave the existing CUDA backend in place initially |

Tinygrad's tensor operations, autodiff, tensor scheduling and optimization search are unnecessary for the proposed generic Bend kernel. Some UOp execution metadata is still needed to use the current launch path. `AMDDevice` supplies HCQ program hooks and initializes `runtime_t` as `None`; a design centered on an older standalone `AMDProgram` constructor would target the wrong interface.

An existing source-to-binary wrapper can be studied in [extra/gptoss_kernels/rmsnorm/__init__.py](https://github.com/tinygrad/tinygrad/blob/94ee753065770aff2aa5ba07dcf911aef298d508/extra/gptoss_kernels/rmsnorm/__init__.py). It constructs an `Ops.PROGRAM` with sink, linear operations, source and compiled binary. [engine/realize.py](https://github.com/tinygrad/tinygrad/blob/94ee753065770aff2aa5ba07dcf911aef298d508/tinygrad/engine/realize.py) handles compiled programs and execution. Follow that pinned representation rather than importing the tensor compiler wholesale. Declare the Bend heap as both read and written and preserve ordering between passes; incorrect metadata could permit invalid scheduling.

## Memory, synchronization and kernel ABI are the main risks

### Shared heap visibility

Bend's CUDA path requires concurrent managed-memory support and uses `cuMemAllocManaged`. The CPU initializes and accesses the corpus, and GPU passes mutate it before execution returns to host continuations. Ordinary device-local allocation plus a final output copy is not equivalent.

`KFDIface.alloc` supports USERPTR, coherent/uncached GTT and CPU-accessible VRAM configurations. Those are useful building blocks, but none should be described as an already-proven replacement for Bend's managed-memory contract. Start with a small explicitly coherent host-visible allocation, serialize host and device phases, and verify CPU-to-GPU-to-CPU visibility across repeated passes. Record where the memory resides. Host-resident memory can make a correct prototype very slow; CPU-visible VRAM can make host traversal expensive and may require Resizable BAR.

Bend's offset-based heap references help, but every native pointer and host/device boundary still needs an audit. Do not assume separate host and device virtual addresses are harmless merely because most terms use offsets. Expanding to a multi-gigabyte corpus is a separate capacity and memory-policy gate.

### Queue atomics and barriers

The runtime publishes work through ring payload writes followed by release publication, with acquiring consumers. Port the atomic helpers and fences by their required semantics, not by matching macro names. Workgroup barriers alone do not establish cross-workgroup visibility. Test a producer/consumer message-passing kernel, cross-group contention, repeated pass boundaries, deep recursion and heap exhaustion before trusting benchmark checksums.

Preserve the initial 128-thread workgroup and scheduler layout. RDNA4 wave size, register pressure and occupancy need inspection; workgroup size and wave size are different quantities. Sweep group counts only after correctness. Changing the scheduler and driver path together would obscure the cause of any improvement or regression.

### Code-object and launch compatibility

Tinygrad's `_amd_program_image` takes the kernel descriptor from the start of `.rodata` and accepts relocation type `R_AMDGPU_REL64`. It is not a general named-symbol HIP module loader. Bend's CUDA source can also contain `window_dev`, so the first AMD build should isolate `bend_dev`. Inspect the actual object with LLVM ELF tools for kernel descriptors, relocations, external symbols, argument offsets, private scratch, wave mode and LDS size before launching.

Bend currently requests `TG_HOLD * 8 = 18,432` bytes of dynamic CUDA shared memory. Tinygrad's AMD path derives LDS requirements from the code-object descriptor. A fixed-size shared array in the single-kernel prototype is simpler than adding a general dynamic-LDS launch API. Verify its descriptor and occupancy; keep the same logical scratch capacity.

The argument layout is a corpus pointer followed by a 32-bit pass value, subject to the emitted ABI's padding and implicit arguments. Tinygrad's packing and dispatch-pointer support must match the compiled object. Do not assume a CUDA-style `void **args` interface exists.

Bend disables floating-point contraction in its CUDA compilation. Tinygrad's default compiler options are not a substitute for Bend's numeric contract. Preserve widths, overflow, division and shift behavior, and prevent contraction/reassociation where the source semantics require it. Any proof attached to the source still depends on correctness of the new compiler/runtime path.

## RDNA4 support, dependencies and licensing

AMD identifies the RX 9070 XT as `gfx1201` in its [versioned compatibility matrix](https://rocm.docs.amd.com/en/docs-7.1.0/compatibility/compatibility-matrix.html). Tinygrad's AMD device code accepts gfx12 targets, and its renderers and instruction definitions include RDNA4 support. This establishes an implementation path, not validation of a particular kernel, firmware, motherboard or distribution combination.

Use the existing `amdgpu` kernel driver through KFD. The pinned [environment syntax](https://github.com/tinygrad/tinygrad/blob/94ee753065770aff2aa5ba07dcf911aef298d508/docs/env_vars.md) permits explicit selection such as `DEV=KFD+AMD:HIP:gfx1201`; validate the detected device architecture rather than using an override to conceal a mismatch. KFD needs the relevant device-node permissions. The separate [AM userspace-driver route](https://github.com/tinygrad/tinygrad/blob/94ee753065770aff2aa5ba07dcf911aef298d508/docs/developer/am.md) involves PCI ownership and driver unbinding and is outside the initial prototype. Do not allow an implicit fallback to that route on a shared machine.

Direct KFD submission can avoid the HIP runtime for execution while still using COMGR, HIP headers/device libraries or hipcc for compilation. Calling this a ROCm-free backend would be misleading without specifying the compiler and dependencies. The existing Fedora host is also not an AMD validation environment simply because the source supports gfx1201.

Tinygrad is [MIT licensed](https://github.com/tinygrad/tinygrad/blob/94ee753065770aff2aa5ba07dcf911aef298d508/LICENSE); Bend is [Apache-2.0 licensed](https://github.com/bendlang/bend/blob/75cb8f3e041aeaad2b37e726c0a33ba19dc49df8/LICENSE). These project licenses do not appear to block the proposed reuse with appropriate notices. Audit generated bindings, imported definitions, compiler libraries and any redistributed firmware individually rather than assuming the repository license covers all dependencies. Keeping tinygrad pinned as a dependency initially makes the boundary easier to track.

There is no demonstrated stable C ABI for the chosen runtime components. Their dependencies include `device.py`, UOps, HCQ, helpers and generated bindings. Upgrading tinygrad is therefore an adapter-maintenance task requiring compile/load/launch tests. Copying the AMD file into Bend would create ownership of a driver subsystem, not a tiny self-contained backend.

## Specialized operations are a separate optimization

Recognizing a pure, fixed-width reduction or map and producing a flat specialized kernel could remove task and heap overhead. That opportunity exists with Bend's current CUDA backend and with a conventional HIP backend; it does not require KFD integration first. The [CUB lowering proposal](BEND_CUB_LOWERING_PROPOSAL.md) defines a narrow initial semantic contract and fallback strategy.

For AMD, rocPRIM/hipCUB are candidates for reduction, scan and radix sorting, and rocBLAS/hipBLASLt are candidates for supported matrix operations. Confirm supported types, layouts, accumulation and determinism for each operation. Floating-point reassociation and tensor-core precision are semantic decisions, not automatic substitutions.

These libraries are not simply device binaries to drop into tinygrad's queue. For example, [rocPRIM reduction](https://rocm.docs.amd.com/projects/rocPRIM/en/docs-7.1.1/device_ops/reduce.html) exposes a HIP host API taking a `hipStream_t` and temporary storage. Interoperability between that runtime's allocations/streams and custom KFD queues must be established explicitly. A conventional HIP backend may be the simpler route if access to these libraries is the main goal. A custom standalone specialized kernel avoids that particular host-library boundary but assumes responsibility for its implementation and tuning.

Only introduce an operation-level GPU IR when multiple real lowerings need to share recognition and semantic checks. Initially, a narrow recognized operation with a checked native call is enough. Direct RDNA instruction generation is a later option for an isolated kernel with a demonstrated compiler/codegen problem; it also transfers instruction selection, register allocation, spills, scheduling and target maintenance into the project.

## Staged prototype and decision gates

These are proposed bounded experiments, not delivery estimates. Stop each stage when its gate fails; after two failed interventions at one gate, revise the hypothesis before changing another layer.

1. Device and compiler smoke test, at most two hours once an RX 9070 XT is available. Record hardware, kernel, firmware, KFD version, toolchain and exact commits. Force KFD. Compile and execute a tiny externally compiled single-kernel program through the pinned tinygrad binary-program path. Test scalar argument packing, buffer writes and completion. Failure here blocks Bend integration and should be attributed to device access, compilation, object loading or launch separately.
2. Heap and ordering spike, at most four hours. Test one small host-visible corpus with bidirectional updates, ring publication, cross-workgroup atomics and repeated ordered passes. Match each result against a CPU reference. Stop if correct visibility requires a different memory protocol; document that design before attempting a full runtime port.
3. Generic Bend port, one focused implementation day before reassessment. Work in `/code/bend`, preserving a base revision and local patch, never in the evaluation reference. Add the AMD dialect and isolated `bend_dev` code object, the small same-process host bridge, and explicit backend selection. Preserve the scheduler. Require integer tree reduction, allocation-heavy recursion and an input/output round trip to agree with the reference. If the bridge expands into a new general runtime framework, compare again with a conventional HIP port before proceeding.
4. Correctness corpus and runtime counterfactual. Differentially test generated small programs against the interpreter and existing compiled backends; include arithmetic edges, closures, recursive allocation, error paths and repeated host/device transitions. Then run the same AMD binary and comparable heap policy through HIP and KFD. If memory policies cannot be matched, report the difference and do not attribute the whole timing gap to queue submission. Allow at most one bounded measurement session per configuration; retain failures and use timeouts.
5. Performance characterization. Use warmups and at least ten measured repetitions on reserved hardware. Separate compilation, startup, host/device synchronization, transfers, device execution and sustained throughput. Begin with balanced arithmetic, sustained option pricing, tree allocation and irregular UTS as distinct workload classes. Record group count, heap placement, register/scratch/LDS usage and device memory as well as wall time. Compare with conventional HIP/rocPRIM implementations on the same AMD card; RTX 3090 versus RX 9070 XT alone cannot isolate backend quality.
6. One specialization only after profiling. Choose a fixed-width integer map/reduction, implement the cheapest checked specialized path, and compare it with the generic Bend kernel and rocPRIM. Include packing/unpacking costs and small-to-large inputs. Retain the generic fallback and test unsupported cases. Defer scans, sorting, matrix lowering and a general GPU IR until this experiment demonstrates a reusable benefit.

Keep a KFD backend if it delivers useful deployment control, observability or measured submission improvements at acceptable maintenance cost. If HIP runs the same kernel equally well and makes library integration easier, prefer it for the initial AMD backend. If generic-kernel execution dominates time, spend the next optimization on the measured scheduler, representation or kernel bottleneck rather than replacing the launch layer.
