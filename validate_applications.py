"""Finite correctness-first application queue, serialized behind the GPU suite."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

from bend_bench.core import (
    append,
    fingerprint,
    hash_file,
    load_config,
    provenance,
    write_json,
)
from bend_bench.experiment import locate, summarize
from bend_bench.gpu_activity import idle_snapshot

ROOT = Path(__file__).resolve().parent
NSYS = Path("/usr/local/cuda-13.1/bin/nsys")
PREDECESSOR = Path(
    "/code/bend-bench/runs/gpu-validation-20260917-resident/completed.json"
)


def pins(config_path=ROOT / "applications.toml"):
    files = [
        ROOT / name
        for name in (
            "validate_applications.py",
            "applications.toml",
            "pyproject.toml",
            "uv.lock",
            ".python-version",
        )
    ]
    files.append(config_path)
    files += [
        p
        for directory in ("src", "tests", "patches")
        for p in (ROOT / directory).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    ]
    external = provenance(load_config(config_path))
    return dict(
        files={str(p.relative_to(ROOT)): hash_file(p) for p in files},
        external=fingerprint({k: external[k] for k in ("sources", "tools", "toolkit")}),
        profiler=hash_file(NSYS),
    )


def command(argv, log, timeout):
    print("STAGE", " ".join(map(str, argv)), flush=True)
    with log.open("a") as stream:
        subprocess.run(
            list(map(str, argv)),
            cwd=ROOT,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=timeout,
        )


def wait_predecessor(saved):
    print(
        "WAITING for preceding CUB/HotSpot invocation",
        saved["predecessor_invocation"],
        flush=True,
    )
    deadline = time.monotonic() + 86400
    while True:
        raw = subprocess.check_output(
            [
                "systemctl",
                "--user",
                "show",
                "bend-bench-gpu.service",
                "-p",
                "ActiveState",
                "-p",
                "InvocationID",
            ],
            text=True,
        )
        state = dict(line.split("=", 1) for line in raw.splitlines())
        if state["ActiveState"] in {
            "active",
            "activating",
            "deactivating",
            "reloading",
        }:
            if state["InvocationID"] != saved["predecessor_invocation"]:
                raise RuntimeError("Predecessor invocation changed")
        elif state["ActiveState"] in {"inactive", "failed"}:
            # The applications are independent of HotSpot's result. Preserve
            # its terminal state, but never overlap an active predecessor.
            return state
        else:
            raise RuntimeError("Cannot establish predecessor state")
        if time.monotonic() > deadline:
            raise TimeoutError("Predecessor wait exceeded 24 hours")
        time.sleep(30)


def wait_idle(config, out):
    deadline = time.monotonic() + 86400
    quiet = None
    cursor = time.time_ns() // 1000
    print("WAITING for 120 seconds of sampled GPU inactivity", flush=True)
    while True:
        try:
            observation = idle_snapshot(config, cursor)
            if observation["samples"]:
                cursor = max(s["timestamp_us"] for s in observation["samples"])
            append(out / "gpu-wait.jsonl", observation)
            if observation["errors"]:
                quiet = None
            elif quiet is None:
                quiet = time.monotonic()
        except (ValueError, OSError) as error:
            append(out / "gpu-wait.jsonl", dict(error=str(error)))
            quiet = None
        if quiet is not None and time.monotonic() - quiet >= 120:
            return
        if time.monotonic() > deadline:
            raise TimeoutError("No idle GPU window within 24 hours")
        time.sleep(1)


def run(request):
    saved = json.loads(request.read_text())
    config_path = Path(saved.get("config", ROOT / "applications.toml"))
    out = request.parent
    if (out / "started.json").exists():
        raise RuntimeError("Request already started; inspect preserved evidence")
    predecessor_state = wait_predecessor(saved)
    if pins(config_path) != saved["pins"]:
        raise RuntimeError("Queued inputs changed")
    config = load_config(config_path)
    wait_idle(config, out)
    if pins(config_path) != saved["pins"]:
        raise RuntimeError("Queued inputs changed")
    write_json(
        out / "started.json",
        dict(
            utc=datetime.now(timezone.utc).isoformat(),
            predecessor_state=predecessor_state,
            predecessor_completion_sha256=hash_file(PREDECESSOR)
            if PREDECESSOR.exists()
            else None,
        ),
    )
    command(
        [
            "/usr/bin/env",
            "BEND_BENCH_APP_NATIVE=1",
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-v",
        ],
        out / "tests.log",
        1800,
    )
    command(
        ["/home/mihai/.local/bin/uv", "--no-config", "build", "--no-sources"],
        out / "build.log",
        600,
    )
    cli = [sys.executable, "-m", "bend_bench"]
    run_dir = None
    try:
        command(
            [*cli, "prepare", config_path], out / "prepare.log", 3600
        )
        run_dir, _ = locate(config)
        write_json(out / "run.json", dict(directory=str(run_dir)))
        for stage in ("check", "run", "profile"):
            if pins(config_path) != saved["pins"]:
                raise RuntimeError("Queued inputs changed")
            extra = ["--nsys", NSYS] if stage == "profile" else []
            command(
                [*cli, stage, config_path, *extra],
                out / f"{stage}.log",
                43200,
            )
        before = hash_file(run_dir / "samples.jsonl")
        command([*cli, "run", config_path], out / "resume.log", 600)
        if before != hash_file(run_dir / "samples.jsonl"):
            raise RuntimeError("Resume appended samples")
        summary = summarize(run_dir)
        for row in summary["cases"]:
            if row["status"] != "passed" or (
                row["implementation"].endswith("cuda")
                and row["profile_status"] != "passed"
            ):
                raise RuntimeError(f"Incomplete gate: {row['case']}")
    finally:
        if run_dir:
            command([*cli, "report", run_dir], out / "report.log", 600)
    application_summary(run_dir)
    write_json(
        out / "completed.json",
        dict(
            utc=datetime.now(timezone.utc).isoformat(),
            run=str(run_dir),
            cases=len(summary["cases"]),
        ),
    )
    print("APPLICATION VALIDATION COMPLETE", run_dir, flush=True)


def application_summary(run_dir):
    rows = summarize(run_dir)["cases"]
    lines = [
        "# Application comparison results",
        "",
        "These results compare time to checked answers across pricing, exact game search and graph traversal. Each cell uses ten measurements after a correctness check and warmup. Wall time includes startup, input construction or loading, transfers and full output. CPU columns use 16 threads; kernel columns come from separate Nsight executions.",
        "",
        "| Workload | Bend CPU wall seconds | Conventional CPU wall seconds | CPU baseline | Bend GPU wall seconds | Conventional GPU wall seconds | GPU baseline | Bend kernel seconds | Conventional kernel seconds |",
        "|---|---:|---:|---|---:|---:|---|---:|---:|",
    ]
    for workload in sorted({r["case"].split("/")[1] for r in rows}):
        cells = [r for r in rows if r["case"].split("/")[1] == workload]
        bend = next(
            r for r in cells if r["implementation"] == "bend" and r["threads"] == 16
        )
        cpu = next(
            r
            for r in cells
            if r["implementation"] not in {"bend", "bend-cuda"}
            and not r["implementation"].endswith("cuda")
            and r["threads"] == 16
        )
        bgpu = next(r for r in cells if r["implementation"] == "bend-cuda")
        gpu = next(
            r
            for r in cells
            if r["implementation"] != "bend-cuda"
            and r["implementation"].endswith("cuda")
        )
        lines.append(
            f"| {workload} | {bend['end_to_end_seconds']:.6f} | {cpu['end_to_end_seconds']:.6f} | {cpu['implementation']} | {bgpu['end_to_end_seconds']:.6f} | {gpu['end_to_end_seconds']:.6f} | {gpu['implementation']} | {bgpu['kernel_seconds']:.6f} | {gpu['kernel_seconds']:.6f} |"
        )
    lines += [
        "",
        f"[Full thread-scaling, memory and timing report]({run_dir.relative_to(ROOT)}/report.md).",
        "[Input contracts, baseline maturity and algorithm differences](APPLICATIONS.md). Pricing and m,n,k baselines are local controls; BFS uses GAP and Gunrock.",
        "",
    ]
    bfs_only = all(r["case"].startswith("bfs/") for r in rows)
    mnk_only = all(r["case"].startswith("mnk/") for r in rows)
    destination = "APPLICATION_RESULTS.md"
    if bfs_only:
        destination = "BFS_RESULTS.md"
        lines[0] = "# BFS comparison results"
        lines[2] = lines[2].replace("across pricing, exact game search and graph traversal", "for graph traversal")
    elif mnk_only:
        destination = "MNK_GPU_RESULTS.md"
        lines[0] = "# Alpha-beta game-search CPU and GPU results"
        lines[2] = lines[2].replace("across pricing, exact game search and graph traversal", "for exact game search")
    (ROOT / destination).write_text("\n".join(lines))


def notify(request):
    out = request.parent
    success = (out / "completed.json").exists()
    subject = (
        "Bend application benchmarks complete"
        if success
        else "Bend application benchmarks stopped before completion"
    )
    body = subject + f"\n\nLogs: {out}\n"
    if success:
        body += (
            "Results: "
            + json.loads((out / "completed.json").read_text())["run"]
            + "/report.md\n"
        )
    else:
        body += (
            "Inspect the journal and stage logs. No automatic retries were attempted.\n"
        )
    attempt = out / "email-attempt.json"
    with attempt.open("x") as stream:
        json.dump(dict(status="attempting", subject=subject), stream)
    sys.path.insert(0, "/code/email")
    from send_boot_email import send_email

    try:
        email_id = send_email(
            sender="Bend benchmark <startup@waka.mx>", subject=subject, text_body=body
        )
    except Exception:
        write_json(
            attempt, dict(status="unconfirmed; inspect provider before retrying")
        )
        raise
    write_json(attempt, dict(status="accepted", email_id=email_id))
    print("SMTP2GO accepted notification:", email_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--enqueue", action="store_true")
    parser.add_argument("--config", type=Path, default=ROOT / "applications.toml")
    parser.add_argument("--notify", action="store_true")
    parser.add_argument(
        "--predecessor-invocation",
        help="Required at enqueue if the completed unit has cleared InvocationID",
    )
    args = parser.parse_args()
    if args.enqueue:
        invocation = (
            args.predecessor_invocation
            or subprocess.check_output(
                [
                    "systemctl",
                    "--user",
                    "show",
                    "bend-bench-gpu.service",
                    "-p",
                    "InvocationID",
                    "--value",
                ],
                text=True,
            ).strip()
        )
        if not invocation:
            raise RuntimeError("Cannot pin predecessor invocation")
        args.request.parent.mkdir(parents=True, exist_ok=True)
        with args.request.open("x") as stream:
            json.dump(
                dict(
                    utc=datetime.now(timezone.utc).isoformat(),
                    config=str(args.config.resolve()),
                    pins=pins(args.config.resolve()),
                    predecessor_invocation=invocation,
                ),
                stream,
                indent=2,
            )
        print(args.request)
    elif args.notify:
        notify(args.request)
    else:
        run(args.request)


if __name__ == "__main__":
    main()
