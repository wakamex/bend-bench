# Full packaged-suite validation

## Application queue

The active replacement request is `runs/applications-bfs-validation-20260918/request.json`, using `applications-bfs.toml`. It remeasures only the corrected BFS port and its GAP/Gunrock controls: 42 configurations and 66 profiling executions. The completed pricing and m,n,k measurements and profiles remain in `runs/486e78825d4fa285adcc/report.md`. The earlier Bend BFS timings in that report did not execute GPU kernels and must not be interpreted as GPU performance. Successful completion of the replacement writes `BFS_RESULTS.md`.

Request v6 is `runs/applications-validation-20260918-v6/request.json`. Request v5 stopped on an unidentified GPU PID after a correct CUDA pricing result. The monitor now captures the workload PID and start time before execution and retains known benchmark identities for delayed NVML records. Ten real executions of the affected workload passed; the original v5 PID attribution remains unresolved. The replacement preserves all earlier evidence.

The current request is `runs/applications-validation-20260918-v5/request.json`. It follows the approved `transcribe-worker.service` cgroup across worker exits and restarts, records observed process identities and activity, and continues to reject unrelated GPU processes. This exemption covers all GPU work in that service, including canaries. Samples separately record `output_correct` and `measurement_valid`; the existing combined verdict still gates performance results. Request v4 retained 171 passed configurations before its PID-based policy rejected a worker exit. The replacement uses a new fingerprint and reruns the suite; historical samples are retained separately.

The application extension covers [pricing, exact m,n,k search and BFS](APPLICATIONS.md): 182 configurations, 2,184 correctness/warmup/timing executions, followed by 286 separate GPU profiling executions. Small native CPU/CUDA correctness tests precede the full suite. Source checks and small JavaScript-backend comparisons against independent oracles pass. Request v2 stopped during its native smoke test because Gunrock's disabled-metrics global allocated a device vector during static initialization and raised `cudaErrorInvalidDeviceFunction`. Request v3 contained the narrow source fix and passed 58 configurations before the pinned transcription worker's canary used the GPU; its overlapping sample was preserved as failed. Request v4 uses the new resident-worker identity and allows that worker's canary activity while continuing to reject unknown GPU processes. The new request is `runs/applications-validation-20260918-v4/request.json`, managed by `bend-bench-applications.service`. The shared lock and blocked-service list remain mandatory. No retries are automatic, and any incorrect or contended sample stays failed.

The first application request, `runs/applications-validation-20260917/`, was deliberately canceled during its idle wait, before tests or benchmark preparation began. The replacement adds the missing final price reduction to the measured pricing workload. Its cancellation email and wait observations remain preserved.

```sh
journalctl --user -u bend-bench-applications.service -f
tail -F runs/applications-validation-20260918-v5/{tests,prepare,check,run,profile}.log
```

Completion writes `APPLICATION_RESULTS.md` and sends an email. Failure sends an inspection notice instead. Each notification records provider acceptance in `email-attempt.json`. The new application's success does not complete outstanding HotSpot profiles.

## HotSpot profiling interruption

The CUB/HotSpot queue stopped on September 17 at 23:04 EDT. CUB completed; all 54 HotSpot correctness configurations and their unprofiled measurements completed, but profiling stopped at `hotspot-512-10/rodinia-pyramid4-cuda/1`, repetition 4. NVML recorded the pinned transcription worker (PID 3725664) using 2% SM and 1% memory activity. Its replacement PID is 489709. The failed profile remains in `runs/c058f6b3293bda1d65dd/profiles.jsonl`; no samples were erased or retried. Provider acceptance of the failure email is in the old queue directory. The exact preceding harness is archived at `/code/bend2/sources/bend-bench-pre-applications-20260917-JNDxfg` before integrating the application extension.

## Established GPU baseline queue

The new `bend-bench-gpu.service` queue covers 72 configurations: CUB sorting/reduction at three sizes, and Rodinia HotSpot at three sizes and two timestep counts with Bend CPU/CUDA, a scalar reference, corrected OpenMP and three CUDA pyramid settings. Each configuration has one correctness check, one warmup and ten measurements. The 36 CUDA configurations additionally receive one profiling warmup and ten Nsight executions. See [contracts and source corrections](GPU_COMPARISON.md).

The service waits for 120 seconds of sampled GPU inactivity, checking once per second, with a 24-hour waiting deadline. The configured resident model may remain loaded: its PID, process start time and host boot ID are pinned, and its memory reservation is recorded. Activity from that pinned worker, including canary inference, is allowed and remains in the evidence. Unknown compute processes still block admission and invalidate overlapping samples. NVML process-activity samples distinguish residency from unapproved work; an unsupported or failed monitoring query blocks execution. A 1.1-second counter-drain delay follows each process and is excluded from its measured wall time. Driver sampling resolution limits detection of very brief bursts, so results share the GPU with the resident worker. No other workload is stopped and no failed configuration is automatically retried.

The current request, stage logs and eventual completion marker live in `runs/gpu-validation-20260917-resident/`. The canceled zero-process queue remains preserved in `runs/gpu-validation-20260917/`. Sources, compiler/toolkit identities, harness files and configuration are pinned when queued and rechecked before execution. Do not edit queued inputs; stop the service and explicitly requeue first. After every requested timing and profiling gate passes, the job generates `GPU_RESULTS.md`, updates the README summary and sends the configured completion email. A stopped job instead sends a failure notification. Provider acceptance is recorded in `email-attempt.json`; an ambiguous email send is not retried.

```sh
systemctl --user status bend-bench-gpu.service
journalctl --user -u bend-bench-gpu.service -n 30 --no-pager
```

## Completed vendor and UTS queue

Completed successfully on 2026-09-17 at 20:50 EDT. All 287 configurations passed; `runs/validation-20260917/completed.json` records completion. The following describes the executed queue. See [performance results](PERFORMANCE.md).

The `bend-bench-validation.service` systemd user job waits for the exact invocation of `bend2-evaluation.service` recorded in `runs/validation-20260917/request.json`. It checks for the legacy pipeline's completion marker before starting. If that job fails or is replaced, this job stops for inspection. A completion marker does not erase correctness failures in the legacy evidence.

The queued experiment enables all 16 vendor workloads, serial C and OpenMP baselines, Bend CPU at 1, 2, 4, 8, 16 and 32 threads, Bend CUDA for every vendor workload, the conventional CUDA Game of Life baseline, and both CPU UTS inputs with canonical and cutoff OpenMP implementations. This is 287 configurations, each with one correctness check, one warmup and ten measured runs: 3,444 program executions if all gates pass.

Execution order: tests, package build, preparation, correctness checks, measurements, no-op resume verification, identity comparison and report generation. The self-comparison checks the reporting machinery; it is not an independent performance reproduction. Logs live beside the queue request. `run.json` records the fingerprinted result directory once preparation completes, and `completed.json` is written only after all requested configurations pass. Unsupported requested configurations leave validation incomplete.

The job retains source/configuration hashes at enqueue time and refuses changed inputs. There are no automatic retries. A failed correctness stage stops before timed measurements. Per-program timeout is 180 seconds; queue waiting is limited to 24 hours; the service has a two-day total limit. Stop and requeue deliberately if changes are needed.

```sh
systemctl --user status bend-bench-validation.service
journalctl --user -u bend-bench-validation.service -n 30 --no-pager
```

The original job already queues BOTS Sort and N-Queens, backend differential checks and GPU kernel profiling. The packaged suite does not yet include those stages. Floorplan, SparseLU, Strassen, GAP, PBBS, Rodinia, additional conventional GPU baselines, Metal, expanded proof checks and AI-coding trials need implementation or hardware before they can be scheduled. Nothing is pushed or published by this queue.
