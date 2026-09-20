# Sustained Asian-option pricing

Bend GPU returns a price and standard error about 68× faster than Bend CPU16 and 40× faster than OpenMP16 at 262,144 paths. The project-written CUDA simulation with CUB reduction is another 7.2× faster than Bend GPU. Each program stays running across requests, which simulate an arithmetic Asian call using 256 observations per path and return the price, nominal Monte Carlo standard error and completed path count.

| Paths per request | Bend, 16 CPU threads | OpenMP, 16 CPU threads | Bend GPU | Project-written CUDA with CUB reduction |
|---:|---:|---:|---:|---:|
| 65,536 | 66.593 ms | 35.321 ms | 2.420 ms | 0.180 ms |
| 262,144 | 239.666 ms | 139.491 ms | 3.501 ms | 0.488 ms |

Times include simulation, aggregation and returning the quote to CPU memory. Each cell is the median of three fresh processes' mean request times, with two warmups and 30 measured requests per process. All four backends passed the per-path audit and all full-size quote checks. Separate conventional GPU qualification runs passed at both sizes. [Individual process results](runs/pricing-sustained-20260918-165158/report.md) and [preserved run evidence](runs/pricing-sustained-20260918-165158/) contain the measurements and source provenance.

## Pricing and arithmetic

The option has spot and strike 100, maturity one year, risk-free rate 5% and volatility 20%. Each simulated path has 256 equally spaced observations. Payoffs are discounted by exp(-0.05). Path generation retains the existing Park-Miller integer generator and Box-Muller transform with identical seeds across backends. Batch r uses hashed path indices from r*N through (r+1)*N-1. These are distinct deterministic seed inputs, not a claim of proven independent random streams or production-quality financial calibration.

For N payoffs, the reported standard error is sqrt((sum(payoff^2) - sum(payoff)^2/N) / ((N-1)*N)), with negative roundoff clamped to zero. It is the nominal independent-path standard error, not an empirical coverage guarantee. Paths use FP32. OpenMP accumulates in FP64; Bend and CUDA accumulate moments in FP32. The implementations keep their established arithmetic policies, and tolerances are fixed before timing: price 0.002 + 0.0001*abs(reference), standard error 0.000002 + 0.001*abs(reference). CUDA uses CUB to reduce paired sum/squared-sum values. This remains a project-written simulation control using an established reduction library.

## Timing boundary

Each C++ process allocates its buffers and initializes CUDA before the first request. The timer starts before simulation and stops after the final price, standard error and count are host scalars. CUDA explicitly copies the reduced moments to the host and computes the quote before stopping the clock. OpenMP's reduction barrier precedes that clock.

Bend's offloaded quote function contains path generation and the reduction. Its host-only emit continuation receives all three quote fields as scalar arguments before IO.now. Preparation checks this generated layout rather than assuming GPU synchronization migrates an arbitrary tree. A preserved generated-C clock adapter records nanosecond timestamps at the existing three IO.now calls per batch. The original and instrumented C files are retained. Formatting, validation and monitor drain are outside the quote interval; complete process wall time remains in every result record.

## Correctness and GPU qualification

Before performance runs, all four backends solve three 1,024-path batches and emit every payoff. An independent FP64 Python reference checks each payoff as well as the price, standard error and count. Performance binaries emit only the three quote fields. At full performance sizes, every batch's quote is checked against the conventional CPU result, including new seeds after warmups. Small-input per-path audit results and full-size differential checks are recorded separately.

The initial sweep uses 65,536 and 262,144 paths. At each size, separate conventional OpenMP16 and CUDA qualification processes receive two warmups and 30 measured batches, with three fresh processes each. The median CPU/GPU quote-time ratio must be at least 1.2 to proceed. If the GPU fails that gate, the run stops and preserves the result; it does not select another workload automatically.

After qualification, all four implementations run in three fresh processes in a saved shuffled order. Qualification samples are excluded from the final comparison. This yields 24 final process runs, 12 qualification processes and four per-path audit processes across the two sizes. No measured process is automatically retried. The shared benchmark lock, approved transcription-service exemption, 120-second GPU idle window, 24-hour admission deadline, 180-second build timeout and 300-second process timeout remain active.

```sh
uv run --locked python pricing_sustained.py
journalctl --user -u bend-bench-pricing-sustained.service -f
```

HotSpot's sustained simulation is a separate follow-up after the conventional GPU qualification and pricing comparison are assessed.
