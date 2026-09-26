# bend-bench

The [Bend](https://github.com/bendlang/bend) programming language lets you run the same code in parallel on CPU and GPU. This benchmark compares performance with OpenMP on CPU and CUDA on GPU. Bend's main benefit is verifiability, being fast is just a perk.

## Benchmark choice

Performance depends much more on the implementation than the language it was written in. Comparing implementations across languages can be tricky, as each language allows different optimizations. We compare against existing benchmarks and new implementations as well.

We compare Bend’s 16 published workloads with added parallel baselines written by GPT-6-Astra in C and OpenMP.

Additional benchmarks are chosen to span a few interesting dimensions:
- Pricing and game search contrast predictable independent work with uneven, decision-dependent work.
- HotSpot and BFS contrast regular local communication with irregular shared-data access.
- Sorting and summation from NVIDIA’s [CUB](https://github.com/NVIDIA/cccl/tree/main/cub) library compare to highly optimized primitives.
- Unbalanced Tree Search from [BOTS](https://github.com/bsc-pm/bots) tests Bend's [documented limitation](https://github.com/bendlang/bend/blob/b9d1352c9f45632447f40a2e927355c92f2be58c/README.md#limitations) that "Parallelism requires balanced calls. Flexible parallelism will be added later."

## Results

On Bend’s 16 published workloads, moving from one to 16 CPU threads gives Bend a median 13.6× speedup, compared with OpenMP’s 14.2×. Bend takes 32% longer than OpenMP at 16 threads at the median. The gaps vary widely by workload. Bend slightly beats OpenMP on Game of Life and tree matrix multiplication, and comes within 1.1–1.3× on several others. Sorting accounts for the largest differences: OpenMP finishes about 19× faster, despite Bend showing better thread scaling. [CPU results](PERFORMANCE.md).

For sorting, we also compare against NVIDIA’s CUB library, which finishes 4.9× faster than Bend GPU. [GPU sorting results](runs/e930e5a1b9c488a9f8ba/report.md).

All 16 published workloads now have conventional GPU comparisons. Among the eleven project-written CUDA additions, CUDA finishes sooner on eight, led by lexer at 6.2× and ray tracing at 5.0×. Bend finishes the complete program sooner on Mandelbrot, Merkle trees and three-body simulation. [GPU results](VENDOR_CUDA_COMPLETION.md), [full scorecard](benchmarks/summary/index.html).

For summation, Bend is faster below about 1 billion items, due to faster startup. CUB performs the calculation itself about 280× faster. [Summation results](runs/reduction-crossover-20260920/report.md).
  
Option pricing on an RTX 3090 is 68× faster than on 16 CPU threads of a 3950x. Our CUDA implementation is another 7.2× faster than Bend GPU. [Pricing results](PRICING_SUSTAINED.md).

For alpha-beta game search, Bend GPU is 1.9× faster than Bend on 16 CPU threads and 2.0× faster than our fastest CUDA implementation. OpenMP on 16 CPU threads is 1.3× faster than Bend GPU. [game-search results](MNK_HOST_ARRAY.md).

Irregular work is harder. Bend gains no CPU speedup on either UTS input. [UTS results](PERFORMANCE.md#uts-irregular-search).

On GPU, the unchanged Bend UTS port reaches the runtime's stack limit on both inputs. Our CUDA implementation completes the larger tree 6.5× faster than BOTS OpenMP on 16 CPU threads. [UTS GPU results](UTS_GPU.md).

Rodinia’s CUDA implementation finishes HotSpot sooner than Bend GPU. Gunrock also finishes BFS sooner on the two larger graphs, while Bend finishes sooner on the smallest. [HotSpot comparison](GPU_COMPARISON.md), [BFS results](BFS_RESULTS.md).

## Takeaways

Bend scales well across CPU cores on its published workloads, but gains no speedup on the irregular UTS trees. Moving the same Bend program to GPU can deliver large gains, especially for balanced independent workloads like option pricing. Implementations matter more than language choice. Bend benefits greatly from balanced work: batching the same N-Queens search made it 4.9× faster on 16 CPU threads, with essentially no change in single-thread time ([N-Queens batching comparison](QUEENS_BATCHING.md)).

## Run a benchmark

For compiler changes, [fast GPU regression testing](FAST_GPU.md) runs Bend GPU alone across all 22 workload families, and the [CPU profile](FAST_CPU.md) does the same at one and 16 threads:

```sh
uv run --locked bend-bench gpu fast
uv run --locked bend-bench cpu fast
```

Pin the compiler checkout and revision in `fast-gpu.toml` or `fast-cpu.toml`, and add `--baseline runs/BASELINE_ID` to compare against a saved run. [Running bend-bench](RUNNING.md) covers the other options, the full harness with conventional comparisons, and the startup-scaling sweep.

## Measurement and reproducibility

We use optimized builds, verify outputs and measure repeated executions after warmups. CPU tests sweep thread counts; GPU measurements distinguish complete-run time from GPU computation. Each run preserves its sources, configuration and individual measurements.

See [timing and memory measurements](MEASUREMENT.md#timing-and-memory), [GPU activity policy](MEASUREMENT.md#gpu-activity), [saved evidence and resuming runs](MEASUREMENT.md#run-provenance-and-resuming), and [comparing compiler changes](MEASUREMENT.md#compiler-comparisons).

## Remaining scope

Additional BOTS programs, broader GAP and PBBS workloads, Metal, controlled AI-coding trials and proof-system validation remain outstanding. Historical proof checks have not been migrated into this harness.

## Development and license

```sh
uv run --locked python -m unittest discover -s tests -v
```

Tests cover CLI entrypoints, provenance, output validation, failure retention, resume behavior and reporting. Opt-in native checks exercise CPU/CUDA backends and verify that Bend BFS actually launches GPU kernels.

The harness is [MIT-licensed](LICENSE). Bend-derived portions retain Apache-2.0 licensing, and external dependencies retain their own licenses. See [source attribution](THIRD_PARTY_NOTICES.md).
