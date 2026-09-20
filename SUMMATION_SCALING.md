# CPU and GPU summation scaling

OpenMP on 16 CPU threads finishes sooner than either GPU implementation at all four sizes. At 2.15 billion integers, it is 4.8× faster than CUB and 8.3× faster than Bend GPU. Both GPUs beat serial C++ at that largest size. Bend gains 12.8× from one to 16 CPU threads, then another 2.1× moving to GPU.

Bend GPU finishes sooner than CUB at 268 million and 537 million integers; CUB finishes sooner at 1.07 billion and 2.15 billion. These are complete-program comparisons, including GPU startup.

The matched sweep tests 268,435,456, 536,870,912, 1,073,741,824 and 2,147,483,648 generated integers. Each size compares Bend at one CPU thread, 16 CPU threads and GPU against serial C++, OpenMP at 16 threads and CUB on GPU. Completed results are in [the run report](runs/summation-scaling-20260920/report.md).

All implementations generate the same deterministic U32 values during summation and return the wrapping-U32 total. The conventional CPU controls use fused loops without allocating an input array; the earlier serial control populated an array. Bend uses its unchanged balanced recursion. CUB receives a 64-bit item count to safely represent the largest input. An independent scalar reference checks every configuration before timing, and every warmup and measured output must match it.

Each cell uses ten complete-program measurements after two warmups, with shuffled implementation order per repetition. Time includes startup, generation, summation and scalar output. The runner preserves sources, compiler commands, binaries, library hashes, host configuration, memory measurements and failed samples. All six configurations are measured together; previous GPU results are not combined with new CPU results.

The systemd user service `bend-bench-summation-scaling.service` waits for the existing GPU-availability gate and acquires the shared benchmark lock. The sweep has a two-hour measurement budget and a 180-second execution timeout. Only after all four sizes pass does it replace the scorecard's summation rows and rebuild the HTML; the service then exports both PNGs. Historical evidence stays unchanged.

```sh
journalctl --user -u bend-bench-summation-scaling.service -f
```
