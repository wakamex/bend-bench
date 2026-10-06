"""Sequences-scaling sweep for nanoGPT generation: Bend on the CPU and the GPU against PyTorch on the
CPU and CUDA, per added sequence once the work dominates (STARTUP_SCALING.md's method).

uv run --locked --with numpy --with scipy python ml_scaling.py --bend ../bend-latest \
    --torch-cpu ../bend-ml/reference/.venv/bin/python --torch-cuda ../bend-ml-local/venv-cuda/bin/python

Each size generates 2^d copies of the 24-token generation after "ROMEO:" at nanoGPT's sizes: Bend
forks the batch over shared weight handles (ml.nano_batch_source), PyTorch stacks it into one batched
forward pass per step. Every run is checked against the stored reference, sizes run smallest first
and each round rotates the implementations' order. Each implementation's median compute time per size
is fitted as a + d*x + b*x^c (scaling_fit.curve, x the number of sequences); the comparison is the
marginal time per added sequence at the largest size both implementations reached.
"""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time

from bend_bench import ml

ROOT = Path(__file__).resolve().parent
CUDA = Path("/usr/local/cuda-13.1")
FLAGS = ["-O3", "-march=native", "-ffp-contract=off"]
CPUS = "0-15"


def stage(out, bend, bun):
    folder = out / ml.FAST
    ml.vendor_packages(ml.VENDORED, folder, ("tensor", "tensor-array", "nat-lemmas"))
    ml.stage_nano(ml.VENDORED / "demos/gpt2/fast.bend", folder, "../../pkg")
    source = folder / "demos/nanogpt/nano_batch.bend"
    source.write_text(ml.nano_batch_source((ml.VENDORED / "demos/gpt2/fast.bend").read_text()))
    run([bun, bend / "bend2/main.ts", source, "-o", out / "nano_batch.c"])
    run(["clang", "-std=c11", *FLAGS, out / "nano_batch.c", "-lpthread", "-lm", "-o", out / "nano_batch"])
    run(["clang", "-std=c11", *FLAGS, "-DBEND_CUDA=1", f"-I{CUDA}/include", f"-L{CUDA}/lib64", out / "nano_batch.c",
         "-lpthread", "-lm", "-lcuda", "-lnvrtc", f"-Wl,--disable-new-dtags,-rpath,{CUDA}/lib64", "-o", out / "nano_batch-cuda"])
    run([out / "nano_batch-cuda", "--gpu-build"])
    return folder


def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise SystemExit(f"failed: {' '.join(map(str, command))}\n{result.stderr[-2000:]}")
    return result


def commands(out, d, torch_cpu, torch_cuda):
    prompt, tokens = ml.NANO_PROMPT, ml.NANO_TOKENS
    ids = " ".join(str(ml.NANO_VOCAB.index(c)) for c in prompt)
    torch = [ml.ASSETS / "gpt_torch.py", "demos/nanogpt/w", ml.NANO["layers"], ml.NANO["heads"], ids, tokens, 1, 16,
             "--batch", 2 ** d]
    return {
        "bend-cpu": ["taskset", "-c", CPUS, out / "nano_batch", prompt, tokens, d, "--threads", 16, "--gpu", "off"],
        "bend-gpu": ["taskset", "-c", CPUS, out / "nano_batch-cuda", prompt, tokens, d, "--threads", 16, "--gpu", "8GB"],
        "pytorch-cpu": ["taskset", "-c", CPUS, torch_cpu, *torch],
        "pytorch-cuda": ["taskset", "-c", CPUS, torch_cuda, *torch, "--cuda"],
    }


def sample(command, cwd, d, timeout):
    started = time.perf_counter()
    try:
        result = subprocess.run(list(map(str, command)), cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return dict(timeout=True, correct=False)
    wall = time.perf_counter() - started
    case = dict(ml_kind="nanogpt", ml_reference=str(ml.ASSETS / "nanogpt-reference.json"),
                contract=dict(logit_tolerance=1e-3, repetitions=2 ** d))
    marker = [line for line in result.stderr.splitlines() if line.startswith("EVAL_COMPUTE_SECONDS=")]
    return dict(returncode=result.returncode, wall_seconds=wall, timeout=False,
                compute_seconds=float(marker[-1].split("=")[1]) if marker else None,
                correct=result.returncode == 0 and bool(marker) and ml.correct(case, dict(stdout=result.stdout)),
                stderr_tail=result.stderr[-300:])


def analyse(rows):
    from scaling_fit import curve
    medians = {}
    for r in rows:
        if r["correct"]:
            medians.setdefault(r["implementation"], {}).setdefault(r["sequences"], []).append(r["compute_seconds"])
    series = {impl: [(n, statistics.median(ts)) for n, ts in sorted(by_n.items())] for impl, by_n in medians.items()}
    fits = {}
    for impl, pts in series.items():
        if len(pts) >= 4:
            c = curve([n for n, _ in pts], [t for _, t in pts])
            fits[impl] = dict(fixed=c["a"], per_sequence=c["marginal"](pts[-1][0]), largest=pts[-1][0], rms=c["rms"],
                              marginal=c["marginal"])
    pairs = {}
    for bend, other in (("bend-cpu", "pytorch-cpu"), ("bend-gpu", "pytorch-cuda"), ("bend-gpu", "bend-cpu")):
        if bend in fits and other in fits:
            n = min(fits[bend]["largest"], fits[other]["largest"])
            pairs[f"{bend} / {other}"] = dict(at_sequences=n, ratio=fits[bend]["marginal"](n) / fits[other]["marginal"](n))
    return series, {k: {x: y for x, y in v.items() if x != "marginal"} for k, v in fits.items()}, pairs


def report(out, series, fits, pairs):
    lines = ["# nanoGPT generation: time per added sequence", "",
             "Median compute seconds per size (correct runs only); a fit's per-sequence time is its marginal cost at the largest size.", "",
             "| Implementation | " + " | ".join(str(n) for n in sorted({n for pts in series.values() for n, _ in pts})) + " |",
             "|---|" + "---:|" * len({n for pts in series.values() for n, _ in pts})]
    sizes = sorted({n for pts in series.values() for n, _ in pts})
    for impl, pts in series.items():
        got = dict(pts)
        lines.append(f"| {impl} | " + " | ".join(f"{got[n]:.3g}" if n in got else "" for n in sizes) + " |")
    lines += ["", "| Implementation | Fixed cost | Seconds per added sequence | At sequences | Fit rms |", "|---|---:|---:|---:|---:|"]
    for impl, f in fits.items():
        lines.append(f"| {impl} | {f['fixed']:.3g} s | {f['per_sequence']:.3g} s | {f['largest']} | {f['rms']:.1%} |")
    lines += ["", "| Ratio of per-sequence times | Value | At sequences |", "|---|---:|---:|"]
    for name, p in pairs.items():
        lines.append(f"| {name} | {p['ratio']:.3g}x | {p['at_sequences']} |")
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bend", type=Path, required=True)
    parser.add_argument("--bun", type=Path, default=ROOT.parent / "bend2/tools/bun-linux-x64/bun")
    parser.add_argument("--torch-cpu", type=Path, required=True)
    parser.add_argument("--torch-cuda", type=Path, required=True)
    parser.add_argument("--max", type=int, default=10, help="largest log2 sequences (default 10: 1,024)")
    parser.add_argument("--gpu-max", type=int, default=8, help="largest log2 sequences for Bend's GPU (default 8)")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--analyse", type=Path, help="Only fit and report an earlier sweep's samples")
    args = parser.parse_args()
    if args.analyse:
        rows = [json.loads(line) for line in (args.analyse / "samples.jsonl").read_text().splitlines()]
        print(report(args.analyse, *analyse(rows)))
        return
    out = (args.out or ROOT / "runs" / time.strftime("ml-scaling-%Y%m%d-%H%M%S")).resolve()
    out.mkdir(parents=True)
    bend = args.bend.resolve()
    meta = dict(bend=str(bend), bend_commit=run(["git", "-C", bend, "rev-parse", "HEAD"]).stdout.strip(),
                bend_bench=run(["git", "-C", ROOT, "rev-parse", "HEAD"]).stdout.strip(),
                dirty=bool(run(["git", "-C", ROOT, "status", "--porcelain"]).stdout.strip()),
                torch_cpu=run([args.torch_cpu, "-c", "import torch; print(torch.__version__)"]).stdout.strip(),
                torch_cuda=run([args.torch_cuda, "-c", "import torch; print(torch.__version__, torch.cuda.get_device_name(0))"]).stdout.strip(),
                cpus=CPUS, rounds=args.rounds, max=args.max, gpu_max=args.gpu_max, started=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    folder = stage(out, bend, args.bun)
    rows = []
    impls = ["bend-cpu", "bend-gpu", "pytorch-cpu", "pytorch-cuda"]
    with (out / "samples.jsonl").open("a") as log:
        for rnd in range(args.rounds):
            for d in range(args.max + 1):
                order = impls[rnd % 4:] + impls[:rnd % 4]
                for impl in order:
                    if impl == "bend-gpu" and d > args.gpu_max:
                        continue
                    r = dict(implementation=impl, sequences=2 ** d, round=rnd,
                             **sample(commands(out, d, args.torch_cpu, args.torch_cuda)[impl], folder, d, args.timeout))
                    rows.append(r)
                    log.write(json.dumps(r) + "\n")
                    log.flush()
                    print(f"round {rnd} {impl} {2 ** d}: {r.get('compute_seconds')} s, correct={r['correct']}", flush=True)
    print(report(out, *analyse(rows)))


if __name__ == "__main__":
    main()
