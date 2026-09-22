# Shorter CPU inputs

Quartering the Game of Life batch preserves thread scaling closely. Quartering the three-body batch reduces scaling by about 17%, and reducing HotSpot from 100 to 10 steps cuts scaling by about 55%. All six shorter configurations passed correctness checks, one warmup and three measured executions on Bend `19fa5ae3643241c70bcfbf1bde67d8eb0d4cca30`.

| Workload and change | Original CPU1 / CPU16 | Shorter CPU1 / CPU16 | Original scaling | Shorter scaling |
|---|---:|---:|---:|---:|
| Game of Life: 16,777,216 → 4,194,304 soups, still 32 generations each | 11.061 / 0.799 s | 2.747 / 0.204 s | 13.85× | 13.44× |
| Three-body ensemble: 1,048,576 → 262,144 simulations, still 300 steps each | 8.961 / 0.622 s | 2.196 / 0.184 s | 14.40× | 11.92× |
| HotSpot: 1,024² grid, 100 → 10 steps | 13.832 / 4.054 s | 2.778 / 1.799 s | 3.41× | 1.54× |

Game of Life is the strongest replacement candidate. Three-body retains useful scaling but gives a less comparable scaling ratio. Keep the original HotSpot for scaling checks: its shorter execution retains file reading and full-grid output, giving these costs more weight. The default profile remains unchanged by this experiment.

## Measurements and reproduction

The original measurements are the ten-repetition baseline in `runs/257a7afdc515d4cd801b`. The shorter-input measurements are a three-repetition screen in `runs/cpu-shortening-20260922-three-reps`; timings are complete-process medians, with CPU affinity and compiler configuration inherited from `fast-cpu.toml`. The CPU16 measured ranges were 0.201–0.224 s for Game of Life, 0.181–0.200 s for three-body and 1.728–1.843 s for HotSpot. This checks input representativeness on one compiler revision, not whether both sizes detect every future compiler regression.

The driver [validate_cpu_shortening.py](validate_cpu_shortening.py) preserves the baseline summary, effective provenance, staged source and executable hashes, independent C reference outputs, build logs, all timing samples and failed attempts. The C references use the original published implementations with only the batch depth changed; HotSpot checks every output cell against the archived 10-step reference. The original ten-repetition attempt was stopped at the user's request and remains in `runs/cpu-shortening-20260922`; it is not pooled with the restarted run. The driver refuses to overwrite its output directory.

Changed inputs require their own future regression baselines. Their shorter wall times are less work, not compiler improvements.
