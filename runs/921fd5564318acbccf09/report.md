# Bend benchmark results

Times are medians of correctness-gated measured executions, excluding checks and warmups. End-to-end includes process startup and output. Device-sequence event time is distinct from a kernel-only sum. Unmeasured metrics remain blank.

Preparation: passed. Fingerprint: `3c20ac89baa9c4f449cffd46f755e779b34401f6e74c3fb40397b9ee118ee964`.

| Workload / implementation / threads | Gate | Profile gate | Checked | Runs | End-to-end seconds | Compute seconds | Device-sequence seconds | Kernel seconds | Speedup | Efficiency | Peak host RSS KiB |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| nqueens/nqueens-8/bitmask-serial/1 | passed | n/a | True | 10 | 0.002778 | 0.000009 |  |  | 1.000000 | 1.000000 | 4424.000000 |
| nqueens/nqueens-8/bend/1 | passed | n/a | True | 10 | 0.002419 |  |  |  | 1.000000 | 1.000000 | 2428.000000 |
| nqueens/nqueens-8/bitmask-openmp-depth-3/1 | passed | n/a | True | 10 | 0.002616 | 0.000024 |  |  | 1.000000 | 1.000000 | 4496.000000 |
| nqueens/nqueens-8/bitmask-openmp-depth-5/1 | passed | n/a | True | 10 | 0.002615 | 0.000067 |  |  | 1.000000 | 1.000000 | 4520.000000 |
| nqueens/nqueens-8/bend/2 | passed | n/a | True | 10 | 0.002404 |  |  |  | 1.006090 | 0.503045 | 2432.000000 |
| nqueens/nqueens-8/bitmask-openmp-depth-3/2 | passed | n/a | True | 10 | 0.002732 | 0.000083 |  |  | 0.957604 | 0.478802 | 4496.000000 |
| nqueens/nqueens-8/bitmask-openmp-depth-5/2 | passed | n/a | True | 10 | 0.002791 | 0.000179 |  |  | 0.936862 | 0.468431 | 4516.000000 |
| nqueens/nqueens-8/bend/4 | passed | n/a | True | 10 | 0.002391 |  |  |  | 1.011622 | 0.252905 | 2308.000000 |
| nqueens/nqueens-8/bitmask-openmp-depth-3/4 | passed | n/a | True | 10 | 0.002772 | 0.000165 |  |  | 0.943843 | 0.235961 | 4444.000000 |
| nqueens/nqueens-8/bitmask-openmp-depth-5/4 | passed | n/a | True | 10 | 0.002935 | 0.000255 |  |  | 0.890823 | 0.222706 | 4528.000000 |
| nqueens/nqueens-8/bend/8 | passed | n/a | True | 10 | 0.002667 |  |  |  | 0.906983 | 0.113373 | 2200.000000 |
| nqueens/nqueens-8/bitmask-openmp-depth-3/8 | passed | n/a | True | 10 | 0.003240 | 0.000405 |  |  | 0.807445 | 0.100931 | 4684.000000 |
| nqueens/nqueens-8/bitmask-openmp-depth-5/8 | passed | n/a | True | 10 | 0.003660 | 0.000792 |  |  | 0.714468 | 0.089308 | 4412.000000 |
| nqueens/nqueens-8/bend/16 | passed | n/a | True | 10 | 0.002909 |  |  |  | 0.831338 | 0.051959 | 2176.000000 |
| nqueens/nqueens-8/bitmask-openmp-depth-3/16 | passed | n/a | True | 10 | 0.003799 | 0.000818 |  |  | 0.688550 | 0.043034 | 4516.000000 |
| nqueens/nqueens-8/bitmask-openmp-depth-5/16 | passed | n/a | True | 10 | 0.004323 | 0.001389 |  |  | 0.604839 | 0.037802 | 4428.000000 |
| nqueens/nqueens-8/bend/32 | passed | n/a | True | 10 | 0.003669 |  |  |  | 0.659273 | 0.020602 | 2180.000000 |
| nqueens/nqueens-8/bitmask-openmp-depth-3/32 | passed | n/a | True | 10 | 0.005754 | 0.002685 |  |  | 0.454674 | 0.014209 | 4548.000000 |
| nqueens/nqueens-8/bitmask-openmp-depth-5/32 | passed | n/a | True | 10 | 0.005516 | 0.002476 |  |  | 0.474053 | 0.014814 | 4380.000000 |
| nqueens/nqueens-12/bitmask-serial/1 | passed | n/a | True | 10 | 0.007265 | 0.004597 |  |  | 1.000000 | 1.000000 | 4500.000000 |
| nqueens/nqueens-12/bend/1 | passed | n/a | True | 10 | 0.011682 |  |  |  | 1.000000 | 1.000000 | 2432.000000 |
| nqueens/nqueens-12/bitmask-openmp-depth-3/1 | passed | n/a | True | 10 | 0.007410 | 0.004730 |  |  | 1.000000 | 1.000000 | 4496.000000 |
| nqueens/nqueens-12/bitmask-openmp-depth-5/1 | passed | n/a | True | 10 | 0.008277 | 0.005604 |  |  | 1.000000 | 1.000000 | 4516.000000 |
| nqueens/nqueens-12/bend/2 | passed | n/a | True | 10 | 0.009983 |  |  |  | 1.170199 | 0.585100 | 2480.000000 |
| nqueens/nqueens-12/bitmask-openmp-depth-3/2 | passed | n/a | True | 10 | 0.005100 | 0.002498 |  |  | 1.452776 | 0.726388 | 4420.000000 |
| nqueens/nqueens-12/bitmask-openmp-depth-5/2 | passed | n/a | True | 10 | 0.007014 | 0.004353 |  |  | 1.180081 | 0.590041 | 4524.000000 |
| nqueens/nqueens-12/bend/4 | passed | n/a | True | 10 | 0.009355 |  |  |  | 1.248746 | 0.312186 | 2180.000000 |
| nqueens/nqueens-12/bitmask-openmp-depth-3/4 | passed | n/a | True | 10 | 0.004068 | 0.001396 |  |  | 1.821332 | 0.455333 | 4516.000000 |
| nqueens/nqueens-12/bitmask-openmp-depth-5/4 | passed | n/a | True | 10 | 0.008264 | 0.005607 |  |  | 1.001510 | 0.250378 | 4752.000000 |
| nqueens/nqueens-12/bend/8 | passed | n/a | True | 10 | 0.009172 |  |  |  | 1.273630 | 0.159204 | 2200.000000 |
| nqueens/nqueens-12/bitmask-openmp-depth-3/8 | passed | n/a | True | 10 | 0.003810 | 0.001007 |  |  | 1.945019 | 0.243127 | 4480.000000 |
| nqueens/nqueens-12/bitmask-openmp-depth-5/8 | passed | n/a | True | 10 | 0.014802 | 0.011862 |  |  | 0.559168 | 0.069896 | 4532.000000 |
| nqueens/nqueens-12/bend/16 | passed | n/a | True | 10 | 0.009340 |  |  |  | 1.250710 | 0.078169 | 2308.000000 |
| nqueens/nqueens-12/bitmask-openmp-depth-3/16 | passed | n/a | True | 10 | 0.004165 | 0.001231 |  |  | 1.778968 | 0.111185 | 4516.000000 |
| nqueens/nqueens-12/bitmask-openmp-depth-5/16 | passed | n/a | True | 10 | 0.021154 | 0.018220 |  |  | 0.391259 | 0.024454 | 4516.000000 |
| nqueens/nqueens-12/bend/32 | passed | n/a | True | 10 | 0.009153 |  |  |  | 1.276319 | 0.039885 | 2180.000000 |
| nqueens/nqueens-12/bitmask-openmp-depth-3/32 | passed | n/a | True | 10 | 0.005532 | 0.002347 |  |  | 1.339359 | 0.041855 | 4496.000000 |
| nqueens/nqueens-12/bitmask-openmp-depth-5/32 | passed | n/a | True | 10 | 0.021647 | 0.018556 |  |  | 0.382348 | 0.011948 | 4752.000000 |
| nqueens/nqueens-14/bitmask-serial/1 | passed | n/a | True | 10 | 0.141428 | 0.138402 |  |  | 1.000000 | 1.000000 | 4420.000000 |
| nqueens/nqueens-14/bend/1 | passed | n/a | True | 10 | 0.289066 |  |  |  | 1.000000 | 1.000000 | 2460.000000 |
| nqueens/nqueens-14/bitmask-openmp-depth-3/1 | passed | n/a | True | 10 | 0.145505 | 0.142437 |  |  | 1.000000 | 1.000000 | 4504.000000 |
| nqueens/nqueens-14/bitmask-openmp-depth-5/1 | passed | n/a | True | 10 | 0.147977 | 0.144888 |  |  | 1.000000 | 1.000000 | 4420.000000 |
| nqueens/nqueens-14/bend/2 | passed | n/a | True | 10 | 0.253477 |  |  |  | 1.140403 | 0.570201 | 2460.000000 |
| nqueens/nqueens-14/bitmask-openmp-depth-3/2 | passed | n/a | True | 10 | 0.082988 | 0.079788 |  |  | 1.753338 | 0.876669 | 4468.000000 |
| nqueens/nqueens-14/bitmask-openmp-depth-5/2 | passed | n/a | True | 10 | 0.085348 | 0.082010 |  |  | 1.733811 | 0.866905 | 4496.000000 |
| nqueens/nqueens-14/bend/4 | passed | n/a | True | 10 | 0.230074 |  |  |  | 1.256403 | 0.314101 | 2172.000000 |
| nqueens/nqueens-14/bitmask-openmp-depth-3/4 | passed | n/a | True | 10 | 0.047396 | 0.044076 |  |  | 3.069969 | 0.767492 | 4468.000000 |
| nqueens/nqueens-14/bitmask-openmp-depth-5/4 | passed | n/a | True | 10 | 0.050413 | 0.047037 |  |  | 2.935326 | 0.733832 | 4516.000000 |
| nqueens/nqueens-14/bend/8 | passed | n/a | True | 10 | 0.222132 |  |  |  | 1.301326 | 0.162666 | 2308.000000 |
| nqueens/nqueens-14/bitmask-openmp-depth-3/8 | passed | n/a | True | 10 | 0.023176 | 0.020186 |  |  | 6.278194 | 0.784774 | 4752.000000 |
| nqueens/nqueens-14/bitmask-openmp-depth-5/8 | passed | n/a | True | 10 | 0.035583 | 0.032452 |  |  | 4.158697 | 0.519837 | 4524.000000 |
| nqueens/nqueens-14/bend/16 | passed | n/a | True | 10 | 0.224008 |  |  |  | 1.290429 | 0.080652 | 2188.000000 |
| nqueens/nqueens-14/bitmask-openmp-depth-3/16 | passed | n/a | True | 10 | 0.014030 | 0.011105 |  |  | 10.370762 | 0.648173 | 4428.000000 |
| nqueens/nqueens-14/bitmask-openmp-depth-5/16 | passed | n/a | True | 10 | 0.061848 | 0.058656 |  |  | 2.392614 | 0.149538 | 4832.000000 |
| nqueens/nqueens-14/bend/32 | passed | n/a | True | 10 | 0.206267 |  |  |  | 1.401418 | 0.043794 | 2264.000000 |
| nqueens/nqueens-14/bitmask-openmp-depth-3/32 | passed | n/a | True | 10 | 0.015993 | 0.012669 |  |  | 9.098271 | 0.284321 | 4532.000000 |
| nqueens/nqueens-14/bitmask-openmp-depth-5/32 | passed | n/a | True | 10 | 0.066909 | 0.062893 |  |  | 2.211618 | 0.069113 | 4552.000000 |

## Scope

Vendor inputs retain upstream arithmetic and checksums. UTS preserves BOTS's SHA-1 tree. CUB uses library radix sort and reduction over matching wrapping-U32 inputs. HotSpot uses the archived Rodinia inputs and CUDA timestep, with a preserved OpenMP boundary correction and full-vector validation. Kernel sums, when present, come from separate correctness-checked Nsight executions; profiled wall time is not used as end-to-end time. Device peak memory, proof-system correspondence, Metal and AI-coding trials remain unmeasured.
