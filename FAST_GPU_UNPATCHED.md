# Unpatched Bend GPU screen

The unpatched Bend revision completed 21 of 22 fast GPU workloads on September 22, 2026. Compact Unbalanced Tree Search failed its correctness execution with `bend: memory fault (machine stack overflow?)`. No UTS timing was accepted. All other workloads passed correctness, one warmup and one measured execution. Total command time was 185.4 seconds.

The run used original revision `b9d1352c9f45632447f40a2e927355c92f2be58c` in a detached checkout at `/code/bend-unpatched`. The patched checkout at `/code/bend`, revision `19fa5ae3643241c70bcfbf1bde67d8eb0d4cca30`, was preserved unchanged. Both shared-graph BFS and the published batched maze BFS passed without the stack-growth patch.

## Reproduction and evidence

```sh
TMPDIR=/var/tmp uv run --locked bend-bench gpu fast fast-gpu-unpatched.toml
```

The [preset](fast-gpu-unpatched.toml) retains the same workloads and shared-GPU policy as the preceding patched run. Full results, sources, executable hashes and raw samples are in `runs/962dd7cf5c25f3220dc6`; the comparison is `runs/962dd7cf5c25f3220dc6/comparison.md`. The command exits nonzero because UTS failed and the comparison environment differs.

The initial preparation in `runs/e3372bea1c7e824b3a90` failed because the 16 GiB `/tmp` filesystem was full. A retry in `runs/1efa7bd7e7be67afe643` was stopped during preparation after identifying that overriding `TMPDIR` also moved the shared lock. The harness now preserves the historical lock location independently of compiler scratch space, verified with a real cross-process contention test. All attempts remain saved; no temporary data belonging to other work was deleted.

Across the 21 successful workloads, the unpatched run took 47.3% more time by geometric mean than patched run `b3b8e6ae043009e8938b`: a 0.679× speed ratio, ranging from 0.446× to 1.143×, with two faster and 19 slower workloads. Failed UTS is excluded. The completed run explicitly used `/var/tmp`; the report now shows that environment difference as a warning alongside raw ratios. These shared-GPU, single-measurement runs do not establish a patch performance effect; a matched-environment comparison would require another patched run. The original strict-environment reports are preserved as `comparison-strict-environment.json` and `.md` in the run directory.
