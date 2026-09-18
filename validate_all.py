"""One finite local validation job, waiting for the existing evaluation first."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inputs():
    files = [ROOT / name for name in ("experiment.toml", "pyproject.toml", "uv.lock", ".python-version", "validate_all.py")]
    files += [p for folder in ("src", "tests") for p in (ROOT / folder).rglob("*")
              if p.is_file() and "__pycache__" not in p.parts]
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)}


def verify_inputs(expected):
    if inputs() != expected:
        raise RuntimeError("Queued source/configuration changed; cancel and enqueue a new validation")


def predecessor_state(unit, invocation):
    result = subprocess.run(["systemctl", "--user", "show", unit, "-p", "ActiveState", "-p", "InvocationID", "-p", "LoadState"],
                            capture_output=True, text=True, check=True)
    properties = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if properties.get("ActiveState") in {"active", "activating", "deactivating", "reloading"}:
        if properties.get("InvocationID") != invocation:
            raise RuntimeError("Predecessor invocation changed; inspect before starting another suite")
        return "waiting"
    journal = subprocess.run(["journalctl", "--user", "-u", unit, f"_SYSTEMD_INVOCATION_ID={invocation}",
                              "--no-pager", "-o", "cat"], capture_output=True, text=True, check=True)
    if not any(line.startswith("PIPELINE COMPLETE:") for line in journal.stdout.splitlines()):
        raise RuntimeError("Predecessor stopped without its completion marker; inspect its journal")
    return "complete"


def execute(command, log, timeout):
    print("STAGE", " ".join(map(str, command)), flush=True)
    with log.open("a") as stream:
        subprocess.run(list(map(str, command)), cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enqueue", action="store_true", help="Write the immutable queue request; does not start execution")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--predecessor", default="bend2-evaluation.service")
    parser.add_argument("--invocation")
    args = parser.parse_args()
    if args.enqueue:
        if not args.invocation:
            parser.error("--enqueue requires --invocation")
        request = dict(created_utc=datetime.now(timezone.utc).isoformat(), inputs=inputs(),
                       predecessor=args.predecessor, invocation=args.invocation)
        args.request.parent.mkdir(parents=True, exist_ok=True)
        with args.request.open("x") as stream:
            json.dump(request, stream, indent=2)
        print(args.request)
        return
    request = json.loads(args.request.read_text())
    out = args.request.parent
    deadline = time.monotonic() + 24 * 3600
    print(f"WAITING for {request['predecessor']} invocation {request['invocation']}", flush=True)
    while True:
        verify_inputs(request["inputs"])
        if predecessor_state(request["predecessor"], request["invocation"]) == "complete":
            break
        if time.monotonic() >= deadline:
            raise TimeoutError("Predecessor did not complete within 24 hours")
        time.sleep(30)
    verify_inputs(request["inputs"])
    if (out / "run.json").exists():
        raise RuntimeError("This queue already reached preparation; use a new request directory after inspection")
    execute([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], out / "tests.log", 300)
    execute(["/home/mihai/.local/bin/uv", "--no-config", "build", "--no-sources"], out / "build.log", 600)
    config = ROOT / "experiment.toml"
    cli = [sys.executable, "-m", "bend_bench"]
    execute([*cli, "prepare", config], out / "prepare.log", 3600)
    from bend_bench.core import load_config, write_json
    from bend_bench.experiment import locate, summarize
    run, prepared = locate(load_config(config))
    write_json(out / "run.json", {"directory": str(run), "fingerprint": prepared["fingerprint"]})
    try:
        execute([*cli, "check", config], out / "check.log", 14400)
        execute([*cli, "run", config], out / "measure.log", 86400)
        verify_inputs(request["inputs"])
        before = sha(run / "samples.jsonl")
        execute([*cli, "run", config], out / "resume.log", 600)
        if sha(run / "samples.jsonl") != before:
            raise RuntimeError("Resume changed the completed sample log")
        execute([*cli, "compare", run, run], out / "compare.json", 600)
        comparison = json.loads((out / "compare.json").read_text())
        summary = summarize(run)
        if any(c["status"] != "passed" for c in summary["cases"]):
            raise RuntimeError("Not every requested configuration passed; inspect report")
        if any(c["before_over_after"] != 1 for c in comparison["comparisons"]):
            raise RuntimeError("Identity comparison failed")
        write_json(out / "completed.json", dict(run=str(run), cases=len(summary["cases"]),
                   fingerprint=prepared["fingerprint"], sample_log_sha256=before,
                   completed_utc=datetime.now(timezone.utc).isoformat()))
    finally:
        execute([*cli, "report", run], out / "report.log", 600)
    print(f"VALIDATION COMPLETE: {out / 'completed.json'}", flush=True)


if __name__ == "__main__":
    main()
