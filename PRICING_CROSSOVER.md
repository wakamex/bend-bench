# Sustained pricing crossover

Does Bend GPU overtake the project-written CUDA pricing implementation as requests grow? This sweep doubles path counts from 65,536, keeping 256 observations per path. It stops at a request taking 60 seconds, an observed crossover, a correctness or resource failure, the existing API's conservative 2^30-path cap, or a four-hour experiment budget.

Each implementation returns an Asian-call price and standard error to the host. Timing excludes process startup and output formatting. Each size has three processes per implementation, each with two warmups and ten measured requests. The summary reports the median of the three process means. A separate small-input audit checks individual payoffs against an independent reference; every timed request checks the returned price, standard error and path count against CUDA. Implementation order is shuffled at each size.

The watchdog allows 180 seconds for initialization and then 60 seconds between quotes. Native request timers remain the reported measurement. Seed offsets retain the original wrapping-U32 arithmetic, so sufficiently large batches can repeat streams. This is a size sweep of the existing implementations, not a new financial model.

The service waits for 120 seconds of sampled GPU inactivity and uses the shared benchmark lock and existing GPU activity policy. Request files preserve source hashes and configuration. Raw samples, failures and partial sizes remain archived; only complete sizes enter the summary.

Follow the queued sweep with `journalctl --user -u bend-bench-pricing-crossover.service -f`. Its request, measurements and report are saved under `runs/pricing-crossover-20260920/`. See [the original repeated-request results](PRICING_SUSTAINED.md) for the pricing model and earlier measurements.
