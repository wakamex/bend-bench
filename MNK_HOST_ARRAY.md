# Endgame search through host-array completion

The comparison now asks how long each implementation takes to produce every answer in a flat CPU-memory array. Timing stops before binary evidence writes, text formatting or validation. The new measurements are pending.

Earlier Bend timings labeled “search-to-host” ended after GPU synchronization, but before its completed answer tree had necessarily migrated to CPU memory. The generated runtime allocates CUDA managed memory with device-preferred placement. The output traversal can trigger further transfers. Those measurements establish synchronized search completion, not equivalence with the conventional CUDA control's completed device-to-host array copy. The earlier claim that Bend provides host-ready results faster than OpenMP is withdrawn pending this comparison. Existing raw timings remain unchanged.

## Timed work and validation

OpenMP retains its preallocated result array and completion barrier. Conventional CUDA retains its synchronous result-array copy. A measurement adapter traverses Bend's completed tree into a preallocated, first-touched uint32 host array before reading the end clock. The traversal reads every answer and includes any managed-memory migration required by those reads. The Bend search and upstream compiler/runtime checkout remain unchanged.

The adapter instruments the generated C at the emit continuation and clock effect, refusing an unexpected generated layout. Uninstrumented and instrumented C files, adapter source, build commands and binary hashes are retained. This is benchmark-side native instrumentation, not a claim that Bend source now exposes a native flat-array API.

Each implementation saves the complete host array after its end timestamp. The harness checks every uint32 against the independent rotated-corpus oracle after the process finishes. It also continues checking the text stream. Wrong values, missing or extra bytes, invalid timings and unapproved GPU activity fail the measurement. Tests cover real compiled CPU backends, the chunked-output variant, and deliberately damaged binary evidence.

Bend uses nanosecond clock readings in the adapter; conventional controls use their existing steady-clock nanosecond intervals. Buffer allocation and first-touch initialization precede the first batch. Host-ready time includes Bend's tree-to-array conversion because the specified endpoint is a flat host array. Binary evidence I/O is outside that interval, but remains inside complete process and output-phase times. Those diagnostic delivery timings must not replace or be pooled with earlier delivery benchmarks.

## Finite comparison

Five implementations run three fresh processes each in shuffled order: Bend CPU16, Bend GPU, tight-bound bulk-output OpenMP16, tight-bound bulk-output root CUDA and tight-bound bulk-output whole-position CUDA. Inputs are the same 1,024 distinct eight-empty-square positions, repeated to 524,288 positions per batch, with two warmups and 30 measured batches. Search boundaries changed, so all five implementations are remeasured rather than reusing earlier timing samples. The shared lock, idle admission, 180-second build limit, 300-second process limit and failure retention remain active.

```sh
uv run --locked python mnk_sustained.py --depths 19 --batches 30 --repeats 3 --multicore-only --telemetry --host-array --corpus-sizes 1024
journalctl --user -u bend-bench-mnk-host-array.service -f
```
