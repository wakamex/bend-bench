# Single-job summation crossover

This experiment looks for the input size at which CUB finishes a complete summation job sooner than Bend GPU. The earlier comparison favored Bend at 8,388,608 generated integers despite much faster GPU computation in CUB. New measurements are pending; the earlier measurements remain unchanged.

The sweep starts at 8,388,608 integers and doubles the count until CUB wins or the count reaches 1,073,741,824. After a win, four intermediate sizes narrow the last Bend-win/CUB-win interval. Each size has an independent scalar correctness check, two excluded warmups and ten measured executions per implementation, with shuffled implementation order within each repetition. Results are complete-program wall times including startup, input generation, wrapping-U32 summation and scalar output. They are not kernel-only timings or a sustained-service comparison.

The source key generator and sum are unchanged. Power-of-two sizes use the original Bend reduction directly. Intermediate sizes form a prefix of the same key sequence by joining power-of-two reductions; their top-level branches can have different amounts of work. CUB continues to generate keys through its transformed counting iterator. Neither implementation reads a preallocated array of integers. Report the observed crossover interval rather than an exact, universal or necessarily monotonic threshold.

The runner reuses the harness's GPU-activity monitor, source/tool provenance and exclusive execution lock. It waits up to 24 hours for 120 seconds of GPU availability, preserving the existing transcription-worker canary exemption. Other GPU processes block admission, and activity or correctness failures stop the run without deleting samples or retrying them. A size cap, 180-second command timeouts and a one-hour measurement budget bound the experiment. Queue inputs are checked before and after the wait and after measurement. Each size preserves generated source, oracle output, build commands, binary and linked-library hashes, individual samples and its median timings.

Run the finite queue through the local Python environment:

```sh
uv run --locked python reduction_crossover.py --request runs/reduction-crossover-REQUEST/request.json --enqueue
uv run --locked python reduction_crossover.py --request runs/reduction-crossover-REQUEST/request.json
```

Use a fresh request directory for each attempt. Failed and interrupted requests remain as evidence. The runner writes `summary.jsonl` as each size completes, then `report.md` and `completed.json` after the search. It does not edit the README or overwrite earlier reports.
