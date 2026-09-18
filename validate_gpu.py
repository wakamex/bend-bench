"""Finite local GPU validation queue; waits without agent polling."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from bend_bench.core import append, fingerprint, hash_file, load_config, provenance, write_json
from bend_bench.gpu_activity import idle_snapshot
from bend_bench.experiment import locate, summarize

ROOT = Path(__file__).resolve().parent
CONFIGS = [ROOT / "gpu-primitives.toml", ROOT / "gpu-hotspot.toml"]
NSYS = Path("/usr/local/cuda-13.1/bin/nsys")


def pins():
    files = [ROOT / name for name in ("validate_gpu.py", "gpu-primitives.toml", "gpu-hotspot.toml",
                                      "pyproject.toml", "uv.lock", ".python-version")]
    files += [p for folder in ("src", "tests", "patches") for p in (ROOT / folder).rglob("*")
              if p.is_file() and "__pycache__" not in p.parts]
    external = []
    for config in CONFIGS:
        evidence = provenance(load_config(config))
        external.append({key: evidence[key] for key in ("sources", "tools", "toolkit")})
    return dict(files={str(p.relative_to(ROOT)): hash_file(p) for p in files},
                external=fingerprint(external), profiler=hash_file(NSYS))


def execute(command, log, timeout):
    print("STAGE", " ".join(map(str, command)), flush=True)
    with log.open("a") as stream:
        subprocess.run(list(map(str, command)), cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout)


def result_summary(runs):
    lines = ["# Established GPU baseline results", "",
             "These comparisons use matching inputs, correctness checks, one warmup and ten measured executions. End-to-end time includes startup, transfers and output. Kernel sums come from ten separate correctness-checked Nsight executions. A Bend/baseline ratio above one means the conventional baseline is faster.", ""]
    faster = {}
    for name, run in runs.items():
        summary = summarize(run)
        evidence = ROOT / "benchmarks/gpu-2026-09-17" / name
        evidence.mkdir(parents=True, exist_ok=True)
        for filename in ("report.md", "summary.json", "provenance.json", "prepared.json"):
            shutil.copyfile(run / filename, evidence / filename)
        rows = summary["cases"]
        lines += [f"## {'CUB primitives' if name == 'cub' else 'Rodinia HotSpot'}", "",
                  "| Workload | Bend end-to-end seconds | Conventional end-to-end seconds | Conventional variant | Bend/baseline wall ratio | Bend kernel seconds | Conventional kernel seconds | Conventional kernel variant |",
                  "|---|---:|---:|---|---:|---:|---:|---|"]
        wins = 0
        for bend in [r for r in rows if r["implementation"] == "bend-cuda"]:
            workload = bend["case"].split("/")[1]
            candidates = [r for r in rows if r["case"].split("/")[1] == workload and
                          r["implementation"] != "bend-cuda" and r["implementation"].endswith("cuda")]
            wall = min(candidates, key=lambda r: r["end_to_end_seconds"])
            kernel = min(candidates, key=lambda r: r["kernel_seconds"])
            ratio = bend["end_to_end_seconds"] / wall["end_to_end_seconds"]
            wins += ratio > 1
            lines.append(f"| {workload} | {bend['end_to_end_seconds']:.6f} | {wall['end_to_end_seconds']:.6f} | {wall['implementation']} | {ratio:.2f}x | {bend['kernel_seconds']:.6f} | {kernel['kernel_seconds']:.6f} | {kernel['implementation']} |")
        faster[name] = wins
        relative = evidence.relative_to(ROOT)
        lines += ["", f"[Every configuration, including CPU baselines and all CUDA variants]({relative}/report.md). Raw execution and profile evidence: `{run.relative_to(ROOT)}`.", ""]
    lines += ["HotSpot's conventional columns select the fastest measured pyramid setting separately for wall and kernel time; the settings may differ. All three settings are retained in the detailed report. These are measured best-of-three variants, not a claim of globally optimal tuning.", "",
              "See [input contracts, numerical corrections, timing definitions and pinned sources](GPU_COMPARISON.md).", ""]
    (ROOT / "GPU_RESULTS.md").write_text("\n".join(lines))
    readme = ROOT / "README.md"
    old = "The stronger GPU comparison uses [NVIDIA CUB sorting/reduction and Rodinia HotSpot](GPU_COMPARISON.md). Its CPU correctness checks pass; GPU results are pending an uncontended measurement window."
    new = f"[Established GPU baselines](GPU_RESULTS.md): CUB is faster end-to-end in {faster['cub']} of six primitive configurations; the best tested Rodinia CUDA setting is faster in {faster['hotspot']} of six HotSpot configurations. The linked results separate kernel time from startup, transfers and output."
    content = readme.read_text()
    if content.count(old) != 1:
        raise ValueError("README summary target changed; review generated results before updating it")
    readme.write_text(content.replace(old, new))


def run(request):
    saved = json.loads(request.read_text())
    out = request.parent
    if (out / "started.json").exists():
        raise ValueError("Queue already started; inspect before creating another request")
    deadline = time.monotonic() + 24*3600
    configs = [load_config(file) for file in CONFIGS]
    if configs[0].get("gpu_resident") != configs[1].get("gpu_resident"):
        raise ValueError("Queued suites must use the same resident policy")
    quiet_since = None
    cursor = time.time_ns()//1000
    print("WAITING for 120 seconds of sampled GPU inactivity; pinned idle residency allowed; deadline 24 hours", flush=True)
    while True:
        try:
            observation = idle_snapshot(configs[0], cursor)
            if observation["samples"]:
                cursor = max(s["timestamp_us"] for s in observation["samples"])
            append(out / "gpu-wait.jsonl", observation)
            if observation["errors"]:
                quiet_since = None
            elif quiet_since is None:
                quiet_since = time.monotonic()
        except (ValueError, OSError) as error:
            append(out / "gpu-wait.jsonl", dict(error=str(error)))
            quiet_since = None
        if quiet_since is not None and time.monotonic()-quiet_since >= 120:
            break
        if time.monotonic() > deadline:
            raise TimeoutError("No uncontended GPU window within 24 hours")
        time.sleep(1)
    if pins() != saved["pins"]:
        raise ValueError("Queued inputs changed; cancel and requeue")
    write_json(out / "started.json", dict(utc=datetime.now(timezone.utc).isoformat()))
    execute([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], out / "tests.log", 300)
    execute(["/home/mihai/.local/bin/uv", "--no-config", "build", "--no-sources"], out / "build.log", 300)
    cli = [sys.executable, "-m", "bend_bench"]
    runs = {}
    for file in CONFIGS:
        name = "cub" if "primitives" in file.name else "hotspot"
        if pins() != saved["pins"]:
            raise ValueError("Queued inputs changed")
        config = load_config(file)
        execute([*cli, "prepare", file], out / f"{name}-prepare.log", 1800)
        run_dir, _ = locate(config)
        runs[name] = run_dir
        write_json(out / "runs.json", {k: str(v) for k,v in runs.items()})
        try:
            for stage in ("check", "run", "profile"):
                extra = ["--nsys", NSYS] if stage == "profile" else []
                execute([*cli, stage, file, *extra], out / f"{name}-{stage}.log", 14400)
            before = hash_file(run_dir / "samples.jsonl")
            execute([*cli, "run", file], out / f"{name}-resume.log", 300)
            if hash_file(run_dir / "samples.jsonl") != before:
                raise ValueError("Completed run changed on resume")
        finally:
            execute([*cli, "report", run_dir], out / f"{name}-report.log", 300)
        for row in summarize(run_dir)["cases"]:
            if row["status"] != "passed" or (row["implementation"].endswith("cuda") and row["profile_status"] != "passed"):
                raise ValueError(f"Incomplete gate: {row['case']}")
    result_summary(runs)
    write_json(out / "completed.json", dict(utc=datetime.now(timezone.utc).isoformat(), runs={k:str(v) for k,v in runs.items()}))
    print("GPU VALIDATION COMPLETE", flush=True)


def notify(request):
    out = request.parent
    success = (out / "completed.json").exists()
    subject = "Bend GPU comparisons complete" if success else "Bend GPU comparisons stopped before completion"
    body = subject + f"\n\nQueue logs: {out}\n"
    if success:
        body += f"Results: {ROOT / 'GPU_RESULTS.md'}\n"
    if not success:
        body += "No automatic retry was attempted. Inspect the journal and per-stage logs.\n"
    attempt = out / "email-attempt.json"
    with attempt.open("x") as stream:
        json.dump(dict(status="attempting", subject=subject), stream)
    sys.path.insert(0, "/code/email")
    from send_boot_email import send_email
    try:
        email_id = send_email(sender="Bend benchmark <startup@waka.mx>", subject=subject, text_body=body)
    except Exception:
        write_json(attempt, dict(status="unconfirmed; inspect provider before retrying"))
        raise
    write_json(attempt, dict(status="accepted", email_id=email_id))
    print(f"SMTP2GO accepted notification: {email_id}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--enqueue", action="store_true")
    actions.add_argument("--notify", action="store_true")
    args = parser.parse_args()
    if args.enqueue:
        args.request.parent.mkdir(parents=True, exist_ok=True)
        record = dict(utc=datetime.now(timezone.utc).isoformat(), pins=pins())
        with args.request.open("x") as stream:
            json.dump(record, stream, indent=2)
        print(args.request)
    elif args.notify:
        notify(args.request)
    else:
        run(args.request)


if __name__ == "__main__":
    main()
