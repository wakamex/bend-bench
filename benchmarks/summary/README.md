# Benchmark scorecard

Open [index.html](index.html) in a browser. It is self-contained and needs no network connection. Switch between relative time and milliseconds with the controls above the scorecard. The PNG exporter captures only the scorecard, including its legend and measurement notes.

The 32 rows cover all 16 published workloads and the completed input-size sweeps for UTS, CUB primitives and shared-graph BFS, plus the 14×14 bit-mask N-Queens case, the largest HotSpot input, the largest repeated-pricing request and the two matched host-array game-search comparisons. Columns show Bend and conventional comparisons on one CPU thread, 16 CPU threads and GPU. Missing measurements remain blank. Historical superseded implementations, invalid CUDA results and intermediate optimization variants are excluded.

`data.json` preserves times in milliseconds, source-report hashes and case identifiers where available. Complete-program figures are taken from correctness-passed JSON summaries with at least ten measured samples. Repeated-request figures are medians of the three process means in the archived reports. Published and CUB sorting runs remain separate; the game-search runs are also separate, so unmeasured cells are not backfilled across runs. HotSpot consistently uses CUDA pyramid height 1; N-Queens consistently uses OpenMP tasks through row 3. The conventional one-thread column uses the baseline named in each section, which can be serial C/C++ rather than a one-thread OpenMP run.

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
