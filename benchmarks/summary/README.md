# Benchmark scorecard

Open [index.html](index.html) in a browser. It is self-contained and needs no network connection. Switch between relative time and milliseconds with the controls above the scorecard. The PNG exporter captures only the scorecard, including its legend and measurement notes.

The 26 rows cover all 16 published workloads, with CUB added to the bitonic-sort GPU comparison, and the larger Unbalanced Tree Search input, plus the largest summation input, the largest shared-graph BFS input, the largest HotSpot input, option pricing at 262,144 paths, the matched CPU/GPU host-array game-search comparison and four machine-learning workloads from [bend-ml](../../ML.md) against [PyTorch](https://pytorch.org/). Pricing uses the smaller request size to show all six CPU/GPU measurements; the larger-request crossover sweep remains in the linked pricing report. A note below the table summarizes the summation crossover and links to the full sweep. Two section headings separate published workloads and additional workloads. Columns show Bend and conventional comparisons on one CPU thread, 16 CPU threads and GPU. Missing measurements remain blank. Historical superseded implementations, invalid CUDA results and intermediate optimization variants are excluded.

`data.json` preserves times in milliseconds, source-report hashes and case identifiers where available. Complete-program figures are taken from correctness-passed JSON summaries with at least ten measured samples. Repeated-request figures are medians of the three process means in the archived reports. The bitonic-sort row adds CUB radix sort on the same 8,388,608 keys and output contract. That GPU cell comes from a separate run, preserved through its per-case source override and archived report hash; the other five cells retain their original measurements. The game-search row uses one matched CPU/GPU run; unmeasured cells are not backfilled across runs. HotSpot consistently uses CUDA pyramid height 1. The conventional one-thread column uses the baseline named in each section, which can be serial C/C++ rather than a one-thread OpenMP run.

All sixteen published rows now have a conventional GPU comparison. Eleven cells use the September 21 [custom CUDA results](../../VENDOR_CUDA_COMPLETION.md); three use the September 20 [CUB, cuBLAS and cuDF results](../../VENDOR_GPU_LIBRARIES.md). Game of Life and bitonic-sort comparisons retain their earlier sources. Existing Bend and CPU measurements are unchanged. Per-case source overrides and hashes preserve these separate runs.

Pricing combines the September 18 CPU16/GPU measurements with September 22 single-thread measurements of the same archived binaries at 262,144 paths and 256 observations. All six cells use three process means, each excluding two warmups and including 30 measured requests. The single-thread run changes only thread count and affinity, checks every quote, and repeats the independent small-input payoff audit. Per-result hashes and the saved single-thread schedule preserve the two measurement dates.

The machine-learning rows come from the 9 October run on Bend d5fe6566, a later revision than the other rows' b9d1352. They show the timed region after loading, the median of ten runs each held until other work used at most three CPUs: GPT-2 small and nanoGPT inference for one sequence, nanoGPT inference for a batch of 1,024 sequences on the CPU and the GPU, and one MNIST training epoch. Single-sequence inference and MNIST have no Bend GPU cell, since bend-ml's matrix products do not split across GPU lanes; the two inference rows have no PyTorch CUDA cell either. bend-ml's two product kernels, `mm_array` and `mv`, are reported in ML.md only.

The larger UTS row includes the September 21 [CUDA traversal result](../../UTS_GPU.md). Bend GPU is labeled “Stack limit” because its correctness check failed; no failure duration is presented as a benchmark time. The archived failed case is verified alongside the successful CUDA samples.

Rebuild the HTML after editing the data or template:

```sh
uv run --locked python benchmarks/summary/build.py
```

With the original local `runs/` archives available, verify the snapshot against every cited report:

```sh
uv run --locked python benchmarks/summary/verify.py
```

Export at twice the CSS resolution with Playwright and Chromium installed:

```sh
uv run --no-project --with playwright python benchmarks/summary/build.py --png runs/scorecard.png
uv run --no-project --with playwright python benchmarks/summary/build.py --metric ms --png runs/scorecard-ms.png
```

Use `--browser /path/to/chromium` for an existing browser installation. Otherwise install Playwright's Chromium with `uv run --no-project --with playwright playwright install chromium`. Browser rendering uses `--disable-gpu` and does not run benchmarks.
