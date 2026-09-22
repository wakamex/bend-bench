# Fast Bend GPU regression benchmark

The [CPU profile](FAST_CPU.md) uses the same harness and reporting code, with one- and 16-thread measurements and three CPU-specific input overrides.

Run the 22 workload families from the scorecard against a pinned Bend compiler, without rebuilding or measuring conventional implementations or CPU backends:

```sh
uv run --locked bend-bench gpu fast --plan
uv run --locked bend-bench gpu fast
uv run --locked bend-bench gpu fast --repetitions 10
```

The default [fast-gpu.toml](fast-gpu.toml) targets the stack-growth fork at `19fa5ae3643241c70bcfbf1bde67d8eb0d4cca30`. Copy that configuration and change `[bend].path` and `[bend].commit` to test another checkout and exact revision. An intentional uncommitted compiler patch requires `allow_patch = true`; its content and tracked-file hashes are preserved. The benchmark sources remain fixed independently of the compiler checkout.

```sh
uv run --locked bend-bench gpu fast candidate.toml
uv run --locked bend-bench compare runs/BASELINE_ID runs/CANDIDATE_ID
```

## Readable regression comparisons

Pass a baseline when running a new compiler:

```sh
uv run --locked bend-bench gpu fast candidate.toml --baseline runs/BASELINE_ID
```

The terminal report leads with overall performance, using the geometric mean of baseline/candidate time ratios, their range, and counts of faster and slower workloads. A compact table shows baseline time, candidate time and percentage change. Slowdowns above 10% appear under areas of concern. This is a screening threshold, not a statistical significance test; investigate flagged cases with repeated matched runs before attributing a close change to the compiler.

You can compare completed runs without running any benchmarks, or share the self-contained JSON result files:

```sh
uv run --locked bend-bench gpu-report runs/CANDIDATE_ID --baseline runs/BASELINE_ID
uv run --locked bend-bench gpu-report candidate-regression.json --baseline baseline-regression.json
uv run --locked bend-bench gpu fast candidate.toml --baseline baseline-regression.json --threshold 5
```

Baseline inputs may be a run directory, its `summary.json`, the compact `regression.json`, or a previous `comparison.json`. Passing a previous comparison uses its candidate result as the next baseline. Directory inputs are read from the underlying evidence rather than trusting a possibly stale report. JSON snapshots are portable reports of recorded gates and timings; retain raw samples for auditing.

A run writes `regression.json` and prints the readable report. Without a baseline it saves `regression.md`; with a baseline it saves `comparison.md` and `comparison.json`, including both result snapshots. `gpu-report` updates these files when given a run directory; when given a JSON file it only prints the report. Existing machine-readable `bend-bench compare` output remains unchanged.

The checker refuses timing ratios across changed hardware, compiler tools, CUDA toolkit, environment, execution policy or workload contracts. The Bend revision and patch are intentionally allowed to differ. Failed, missing and incompatible workloads remain listed and excluded from the geometric mean; a partial mean is labeled as a matched subset. Exit status is 0 for a complete result with no flagged concerns, 1 for failed/incomplete comparisons or a slowdown above the threshold, and 2 for invalid input or execution errors. A mean near one cannot conceal a failed workload or an individual regression.

Each run prints its directory and writes `report.md`, `summary.json`, commands, generated sources, binaries, source and library hashes, correctness results and individual timing samples. Comparison reports baseline-time / candidate-time for each compatible, passed workload: values above one mean the candidate is faster. Missing, failed or changed-contract results receive an explanation instead of a ratio. A repeated command resumes successful samples and does not retry failed ones.

## Workloads and runtime

| Workloads | Fast profile |
|---|---|
| Original 16 workloads | Unchanged published inputs, fixed source snapshots |
| Unbalanced Tree Search | Compact 293,367-node input with the original branching distribution |
| Summation | 2,147,483,648 generated integers |
| HotSpot | 1,024 × 1,024 grid, 100 steps |
| Shared-graph BFS | 262,144 vertices |
| Option pricing | 32 requests of 262,144 paths × 256 observations |
| Game search | One complete batch of 524,288 positions from the 1,024-position corpus |

The default uses one measured repetition; its complete runtime has not yet been measured. The earlier 15–25 minute estimate applied to ten repetitions and excluded waiting for other GPU work. Compilation and GPU-idle waiting do not shrink with the repetition count. Most individual programs finish in under a second. HotSpot and BFS retain their larger inputs to exercise memory behavior; reducing them could hide performance changes. Compact UTS takes about four seconds rather than about 390 seconds. Game search runs one full batch per process rather than 32; every returned answer is still checked.

The compact UTS input retains irregular recursion and the stack-growth requirement, but its conventional CUDA comparison is dominated by startup. It is for compiler regression testing, not a replacement for the [large-tree comparison](UTS_GPU.md). The [compact UTS report](UTS_COMPACT.md) records both behaviors.

## Measurement and correctness

The command prints total elapsed time when it finishes or exits with an error, including GPU-idle waiting, compilation and testing. Individual workload timings remain separate.

Every case receives a correctness execution, one excluded warmup and one measured execution by default. Use `--repetitions N` to collect more measurements; use the same count for baseline and candidate. Runs with fewer than ten measurements are labeled quick screens. This profile reports complete-process wall time, including initialization, all requests, transfers, formatting and output. It does not reuse the scorecard's request-to-host timing adapters. Pricing and game-search numbers therefore compare only with other runs of this same fast profile, not with the scorecard's request latency. No kernel profiling is included.

The fixed fixtures preserve the existing reference contracts: exact published outputs and wrapping-U32 summation, UTS node count and zero exhausted fuel, the full BFS distance vector, the full HotSpot grid with its established tolerance, every pricing quote with the existing price/error tolerances, and every game-search answer against the independently checked corpus. The reference outputs are snapshots from the original experiments, not outputs generated by the candidate compiler. Their hashes participate in the run identity and comparison contract. Fixture origins are recorded in the packaged manifest.

When another GPU process blocks a run, the error includes its PID, process name, allocated VRAM and peak sampled GPU compute utilization when available. Utilization describes the observed sampling window, not lifetime compute usage. Missing utilization samples are reported as unavailable, not as proof of inactivity; an exited process may have utilization samples but no remaining VRAM reading.

The command starts without a timed GPU-idle wait. Add `--wait-idle` to wait for 120 seconds of sampled GPU inactivity before preparation. Both modes use the shared benchmark lock, configured blocked services and GPU activity checks during execution; disabling the wait does not permit contaminated measurements. The existing transcription-worker exemption remains configured. Unknown GPU work invalidates an overlapping sample. The process timeout is 60 seconds; failures remain in the evidence and cause a nonzero command exit while other cases still receive their checks and measurements. Compiler/build failure stops preparation.

The host preset requires 32 available logical CPUs because it preserves the existing 16- or 32-host-thread GPU launch settings per workload. It needs the pinned Bend checkout, Bun, Clang, CUDA and the existing Rodinia input archive and extracted data. BOTS, CUB, Gunrock and conventional compiler builds are unnecessary: the fixed Bend sources and correctness fixtures are packaged with the harness.

`gpu fast` runs directly in your terminal. It does not create, start or require a benchmark systemd service. The supplied host-specific configuration does query systemd to avoid overlapping the listed `blocked_services`; on another machine without those services, set `blocked_services = []` and remove the host-specific `[gpu_resident]` exemption. GPU activity monitoring and the shared benchmark lock remain active.

Optionally, on a systemd host, wrap the command yourself to survive terminal disconnection:

```sh
systemd-run --user --unit=bend-bench-fast-gpu --property=WorkingDirectory=/code/bend-bench /code/bend-bench/.venv/bin/python -m bend_bench gpu fast /code/bend-bench/fast-gpu.toml
journalctl --user -u bend-bench-fast-gpu -f
```
