# Reusable CPU and GPU builds

Compile once, then collect fresh measurements from the saved binaries:

```sh
uv run --locked bend-bench gpu fast --build-only --output builds/patched-gpu
uv run --locked bend-bench gpu fast --build builds/patched-gpu
uv run --locked bend-bench gpu fast --build builds/patched-gpu --repetitions 3
```

Use `cpu fast` for CPU builds. A custom compiler configuration can precede `--build-only`; the output directory must not already exist. Build-only performs compilation and GPU device-program generation, without correctness checks or timing runs. A successful build is not a benchmark result.

`--build` loads the artifact's recorded configuration without reading the original configuration file, source checkouts or compiler executables. It creates a fresh measurement directory under `./runs`, copies the artifact into it, and runs the usual correctness checks, warmups and measured executions. `--baseline` compares those new measurements with saved results. `--output` with `--build` changes the measurement output root. `--resume` continues a matching measurement run; it never changes the build artifact.

## Artifact contents and validation

The directory contains binaries, CUDA device-program sidecars when applicable, workload sources, input files, correctness references, original build commands, compiler/source provenance and a `build.json` manifest. HotSpot input paths are relative to the bundled working directory. The artifact can be moved to another directory before reuse.

Reuse verifies the manifest's metadata hashes, binary/source/input/reference hashes, runtime shared-library hashes and host compatibility. Current runtime environment and harness identity are recorded separately from the archived compiler/build identity. The initial implementation requires matching CPU platform, model/topology and affinity, plus matching GPU/driver identity for GPU artifacts. It does not claim cross-machine portability. CPU governor changes are recorded in measurement provenance rather than treated as a binary incompatibility.

Only use artifacts you trust: these contain native executable programs. Hash checks detect changes relative to the saved manifest; they are not signatures proving who created it. Existing artifacts and measurement directories are never overwritten to hide failures. Failed build directories remain available for inspection and are not reusable until a successful build creates the manifest.

There is no automatic build cache. Creating a build and selecting it for reuse are explicit operations. Normal `cpu fast` and `gpu fast` commands still compile their own fresh runs.
