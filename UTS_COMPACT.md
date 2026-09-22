# Compact UTS completes in 3.85 seconds but changes the CUDA comparison

A 293,367-node tree brings patched Bend GPU below ten seconds while retaining irregular recursive work. Bend still gains no CPU speedup, and its GPU remains about 46× slower than its 16-thread CPU execution, close to the large tree's roughly 50×. Conventional CUDA behaves differently: startup makes it 6.2× slower than OpenMP16 on the compact tree, whereas it was 6.5× faster on the large tree. The compact input is useful for quick regression checks; the main scorecard retains the large tree because the GPU comparison does not carry over.

## Measured times

| Input | Bend 1 CPU thread | Bend 16 CPU threads | Bend GPU, stack-growth fork | BOTS serial C | BOTS OpenMP16 | Project CUDA |
|---|---:|---:|---:|---:|---:|---:|
| Compact: 293,367 nodes | 0.0792 s | 0.0830 s | 3.8522 s | 0.0570 s | 0.0331 s | 0.2054 s |
| Original large: 30,399,117 nodes | 7.3681 s | 7.7967 s | 389.96 s, one correctness check | 3.0715 s | 2.2632 s | 0.3482 s |

The compact cells are medians of ten measured complete-program executions after a correctness check and one warmup. The large Bend GPU figure is a single successful check of the stack-growth fork, so ratios using it are approximate. Large CPU cells retain the original runtime. Both inputs fail on the original GPU runtime; these failures remain preserved separately. Compact Bend CPU and GPU use fork `19fa5ae3643241c70bcfbf1bde67d8eb0d4cca30`, whose CPU continuation representation is unchanged from the pinned original.

## Ratio comparison

| Ratio | Compact | Large |
|---|---:|---:|
| Bend CPU1 / CPU16: thread speedup | 0.95× | 0.95× |
| Bend CPU16 / BOTS OpenMP16: time penalty | 2.51× | 3.44× |
| Bend GPU / Bend CPU16: time penalty | 46.4× | about 50.0× |
| Bend GPU / project CUDA: time penalty | 18.8× | about 1,120× |
| BOTS OpenMP16 / project CUDA: GPU speedup | 0.16× | 6.50× |

Canonical BOTS OpenMP itself gains 2.47× from one to 16 threads on the compact input (0.0817 to 0.0331 seconds). This is distinct from comparing the separate serial implementation with OpenMP.

CUDA's compact device-sequence median is 0.0161 seconds, against 0.2054 seconds for the complete program. That interval includes uploads, traversal and host synchronization between levels; it is not isolated kernel time. The fixed overhead overwhelms the traversal when the input is this small. Comparing only CUDA's device interval against Bend's complete-program time would not fix the mismatch.

## Fixed input and correctness

The [compact input](src/bend_bench/assets/inputs/uts/compact.input) keeps BOTS `tiny`'s seed 8, non-leaf probability 0.333332, branching factor 3 and compute granularity 1. Only root arity changes from 2,000 to 512. It therefore traverses a fixed prefix of the original tree's root subtrees without precomputing work sizes or adding manual load balancing. The first 128 root children account for 161,921 descendant nodes, about 55% of the total. The full compact tree has depth 694 and 195,748 leaves.

The initial CPU discovery checked root arities 128, 256 and 512. The largest candidate was selected before GPU timing, and only that candidate was timed. CUDA's independent traversal of the external BOTS SHA-1 generator verifies node count, leaf count, depth and all five state-word sums. Canonical BOTS and Bend verify the node count; Bend additionally reports zero exhausted recursion fuel. Bend does not emit the CUDA checksum vector.

The original GPU runtime failed its compact correctness check. The stack-growth fork passed in 3.89 seconds, satisfying the predeclared correct-and-under-ten-seconds gate, and then all seven configurations passed ten measurements each. No failed samples were discarded or retried.

## Evidence and reproduction

Run [uts-compact.toml](uts-compact.toml) with the normal harness for repeatable checks. [validate_uts_compact.py](validate_uts_compact.py) additionally checks the original runtime before selecting the fork, enforces the ten-second admission gate and retains both runs. It uses the shared execution lock, GPU activity monitoring and a two-minute quiet window. The September 22 service finished in 6 minutes 58 seconds, including the idle wait and compilation.

The tracked [summary](benchmarks/uts-compact-20260922/summary.json), [samples](benchmarks/uts-compact-20260922/samples.jsonl), [build plan](benchmarks/uts-compact-20260922/plan.json), [source provenance](benchmarks/uts-compact-20260922/provenance.json), [original-runtime failure](benchmarks/uts-compact-20260922/original-runtime-check.jsonl) and [input discovery](benchmarks/uts-compact-20260922/input-discovery.jsonl) preserve the result. Local full run: `runs/254001a94e61170c195c`; original-runtime counterfactual: `runs/596a40dfc333314ec124`. See [large-tree GPU results](UTS_GPU.md) and [stack-fix validation](UTS_GPU_STACK_FIX.md).
