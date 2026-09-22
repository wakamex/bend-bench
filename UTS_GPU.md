# Unbalanced Tree Search on GPU

The project-written CUDA implementation finishes the larger BOTS tree 6.5× faster than the previously measured canonical BOTS OpenMP implementation on 16 CPU threads. The unchanged Bend port fails on GPU for both inputs with the pinned runtime's stack-limit error. Its failed executions are recorded as failures, not timings.

Both CUDA inputs passed checks against the original BOTS SHA-1 generator, node counts, leaf counts, maximum depth and sums of all five state words across every generated node. Times below are medians of ten complete-program executions after one excluded warmup on an RTX 3090.

| BOTS input | Generated nodes | Bend GPU | Project CUDA | BOTS OpenMP, 16 CPU threads | CUDA advantage over OpenMP |
|---|---:|---|---:|---:|---:|
| `test` | 4,112,897 | GPU stack limit | 0.226 s | 0.351 s | 1.6× |
| `tiny` | 30,399,117 | GPU stack limit | 0.348 s | 2.263 s | 6.5× |

The BOTS name `tiny` denotes the larger of these two inputs. CPU times come from the September 17 run on the Ryzen 9 3950X; GPU checks and timings were taken September 21. See [CPU scaling](PERFORMANCE.md#uts-irregular-search) and the [saved GPU summary](benchmarks/uts-gpu-20260921/summary.json).

## CUDA traversal

The CUDA implementation generates the tree while traversing it. Each level expands the current non-leaf nodes in parallel, applies the original SHA-1 state transition to each child index, and appends newly discovered non-leaf children to the next frontier. It does not precompute the tree or balance work using known subtree sizes. The tree's branching decisions, seed and node-count contract match BOTS.

Two fixed-capacity frontier buffers each hold up to 1,048,576 SHA-1 states, consuming 40 MiB together. Capacity overflow rejects the run rather than truncating it. The host receives the frontier count after each level. The measured program also accumulates state-word checksums; the separate correctness mode compares these with a full CPU traversal using the external BOTS RNG implementation. Three boundary inputs check an empty root, a single leaf and 4,096 leaf children with different seeds. The full inputs have depths 1,572 and 6,974 and leaf counts 3,599,034 and 20,266,744, respectively.

This is project-written CUDA, not an upstream BOTS GPU implementation. It deliberately uses a conventional frontier layout rather than reproducing Bend's recursive scheduling. Complete-program timing includes root generation, CUDA startup, allocation, traversal, synchronization, transfers and cleanup. Median CUDA-event intervals are 36.4 ms and 155.6 ms; these span uploads, traversal and per-level host synchronization, and are not isolated kernel times.

## Bend GPU stack limit

The exact Bend source used for the CPU results is compiled with the pinned CUDA backend and run with 16 host threads and a 4 GB GPU heap. Both input checks return `bend: memory fault (machine stack overflow?)`. They produce no accepted node count. No warmups or performance samples were taken for the failing cases.

The generated runtime reserves 2,048 words per GPU lane through `STAK_LEN`; `WL_ROOM` reports this same error when a lane's continuation stack reaches its bound. Increasing the host stack to 64 MiB did not resolve the smaller input's GPU failure. The CUDA-capable binary successfully produced `4112897 0` with GPU execution disabled, and a debugger run exited with the error without stopping on a host fault. These checks locate the limitation in the GPU runtime rather than the host stack setting. Increasing the GPU heap does not change the fixed `STAK_LEN` definition.

No runtime patch, traversal rewrite or manual balancing was applied to obtain a Bend timing. A larger GPU continuation stack or a revised port would require a separate, explicitly labeled comparison. The pinned evaluation checkout remains unchanged.

A subsequent [fork-only runtime fix](UTS_GPU_STACK_FIX.md) adds heap-backed stack growth and completes both inputs correctly, but slows three tested existing GPU workloads by 0.8–8.9%. Its validation and measurements are separate from the pinned results above.

## Reproduction and evidence

A [compact 293,367-node input](UTS_COMPACT.md) completes on the stack-growth fork in 3.85 seconds and retains Bend's lack of CPU scaling. It changes the conventional GPU ranking because CUDA startup dominates at that size, so the main scorecard retains the larger tree.

The [UTS GPU configuration](uts-gpu.toml) explicitly enables `uts_gpu`; existing configurations retain their CPU-only UTS selection. Adapt dependency and tool paths before running:

```sh
BEND_BENCH_UTS_GPU_TEST=1 uv run --locked python -m unittest discover -s tests -p test_uts_gpu.py -v
uv run --locked bend-bench prepare uts-gpu.toml
uv run --locked bend-bench check uts-gpu.toml
```

The final command includes CPU cases and is expected to report the pinned Bend GPU failures. The recorded experiment selected only the four GPU cases. Failed checks were retained without retrying; only the two correctness-passed CUDA cases received a warmup and ten measurements. No other benchmark was active, and the existing GPU activity policy and shared execution lock were enforced.

Run `3ac2408a1d8cae8d6139` preserves source, build and binary provenance. The repository includes its [summary](benchmarks/uts-gpu-20260921/summary.json), [individual samples](benchmarks/uts-gpu-20260921/samples.jsonl), [host-stack counterfactual](benchmarks/uts-gpu-20260921/stack-audit.jsonl) and [debugger evidence](benchmarks/uts-gpu-20260921/gdb-audit.jsonl). Native CUDA checks are retained locally in `runs/uts-gpu-check-8zu86e2_/`. Bend is pinned to `b9d1352c9f45632447f40a2e927355c92f2be58c` and BOTS to `2607a695128727a3f6c98754367705443663136d`; the adapter commit is `233c5cf`.

The regression suite passed 77 tests with nine expected skips, the opt-in native UTS tests passed separately, and both package distributions built successfully.
