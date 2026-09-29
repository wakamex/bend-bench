# Measurement and reproducibility

## Builds and correctness

Release builds use `-O3` and native CPU architecture flags. Output checks use published expected results or independent references; the applications check every payoff, game outcome or graph distance. The packaged harness excludes correctness checks and warmups from timing summaries and requires at least ten successful measured executions.

Repeated-request experiments report their own sampling units and timing boundaries: [option pricing](PRICING_SUSTAINED.md), [game search](MNK_HOST_ARRAY.md) and [summation crossover](REDUCTION_CROSSOVER.md).

## CPU and GPU configurations

CPU scaling sweeps 1, 2, 4, 8, 16 and 32 threads where configured; the 32-thread point uses SMT.

The largest BFS GPU trace contains compute launches of 64 blocks × 128 threads = 8,192 threads. Raw report labels such as `bend-cuda/32` identify the host CPU worker setting; CUDA launch dimensions are recorded in the profiler traces.

## Timing and memory

End-to-end wall time, instrumented CPU compute time, CUDA event intervals and Nsight kernel-duration sums are distinct measurements. Event intervals can contain gaps between kernels. Profiled wall times never replace unprofiled measurements. Peak host RSS is recorded; peak device memory is not measured.

## GPU activity

Application runs permit GPU activity from the approved transcription service and record observed processes and activity. Earlier experiments used stricter GPU admission rules. Per-run configuration and evidence preserve these differences; results from different runs are not pooled. [Validation notes](VALIDATION.md) and [execution history](QUEUE.md) document completed checks and interruptions.

## Run provenance and resuming

Each run preserves source revisions and patches, configuration, tool identities, build logs, generated sources, binary hashes, linked-library hashes, individual samples and a report. Changing these inputs creates a new identity or invalidates preparation. Keep source checkouts available for rebuilding.

An unchanged packaged-harness run resumes without duplicating completed measurements. Failed samples remain in the evidence and keep that configuration failed; use a new experiment label to investigate it. Preparation and measurement share an execution lock, and configured blocked services prevent overlap with other benchmark jobs. Standalone experiment runners document their own restart rules in their linked reports.

## Compiler comparisons

To benchmark a compiler fix, set `bend.path` and the exact HEAD commit. Enable `allow_patch = true` for tracked changes and stage new files so their contents enter the preserved diff. Compare compatible runs with:

```sh
uv run --locked bend-bench compare runs/BEFORE runs/AFTER
```

Comparisons require matching host, workload contract and measurement policy. Different Bend revisions are allowed. Ratios are descriptive comparisons, not statistical significance tests.

[`compiler-check`](RUNNING.md#comparing-bend-revisions) answers a narrower question first: what does the change emit differently? Identical output across both checkouts' tests, demos and the benchmark ports shows a refactor cannot change any measurement, so it needs no benchmark run. Changed output shows which programs a real change reaches, and says nothing about whether they are still correct. The test lane covers that, by comparing each test's status under both checkouts. Both checkouts run side by side on the same host, because upstream's tests and their expected output change between releases, so stored hashes would go stale.
