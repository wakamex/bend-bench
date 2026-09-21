"""Run only the eleven new CUDA baselines after the existing idle-GPU gate."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

from bend_bench.core import exclusive, hash_file, load_config, rows, write_json
from bend_bench.experiment import locate, prepare, report, sample, summarize, validate
from validate_applications import command, pins as application_pins, wait_idle

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "vendor-gpu-custom.toml"


def pins():
    value = application_pins(CONFIG)
    value["files"]["validate_vendor_cuda.py"] = hash_file(__file__)
    return value


def select_cases(config, cases):
    wanted = {f"vendor/{name}/conventional-cuda/1" for name in config["vendor_gpu"]}
    selected = [case for case in cases if case["id"] in wanted]
    if len(selected) != len(wanted) or {c["id"] for c in selected} != wanted:
        raise ValueError("Missing or duplicate custom CUDA cases")
    if any(c["unsupported"] for c in selected):
        raise ValueError("Requested CUDA baseline unsupported")
    return selected


def check_history(history, identity):
    if any(r["fingerprint"] != identity for r in history):
        raise ValueError("Foreign fingerprint in retained samples")
    keys = [(r["case"], r["phase"], r["rep"]) for r in history]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate retained samples")
    if any(not r["correct"] for r in history):
        raise ValueError("Failed samples retained; inspect before a new run")
    return set(keys)


def run(request):
    saved = json.loads(request.read_text())
    out = request.parent
    config = load_config(CONFIG)
    if (out / "completed.json").exists() or (out / "failed.json").exists():
        raise ValueError("Terminal queue evidence already exists; inspect before requeueing")
    if pins() != saved["pins"]:
        raise ValueError("Queued inputs changed")
    wait_idle(config, out)
    if pins() != saved["pins"]:
        raise ValueError("Queued inputs changed while waiting")
    write_json(out / "started.json", {"utc": datetime.now(timezone.utc).isoformat()})
    # This test runs boundary cases and compares complete published-input outputs.
    command(["/usr/bin/env", "BEND_BENCH_VENDOR_GPU_TEST=1", sys.executable,
             "-m", "unittest", "discover", "-s", "tests", "-p", "test_vendor_custom_gpu.py", "-v"],
            out / "native-checks.log", 3600)
    if pins() != saved["pins"]:
        raise ValueError("Queued inputs changed during native checks")
    print("STAGE prepare", flush=True)
    run_dir = prepare(config)
    write_json(out / "run.json", {"run": str(run_dir)})
    with exclusive(config):
        located, prepared = locate(config)
        if located != run_dir:
            raise ValueError("Prepared run identity changed")
        cases = select_cases(config, json.loads((run_dir / "plan.json").read_text())["cases"])
        done = check_history(rows(run_dir / "samples.jsonl"), prepared["fingerprint"])
        write_json(out / "selection.json", {"cases": [c["id"] for c in cases], "fingerprint": prepared["fingerprint"]})
        try:
            for case in cases:
                for phase, count in (("check", 1), ("warmup", config["warmups"]), ("measure", config["repetitions"])):
                    for rep in range(count):
                        key = (case["id"], phase, rep)
                        if key in done:
                            continue
                        if not sample(config, run_dir, prepared["fingerprint"], case, phase, rep)["correct"]:
                            raise RuntimeError(f"Failed {key}; evidence retained, no automatic retry")
                        done.add(key)
            validate(config, run_dir)
        finally:
            report(run_dir)
        selected = {c["id"] for c in cases}
        results = [r for r in summarize(run_dir)["cases"] if r["case"] in selected]
        if len(results) != len(selected) or any(r["status"] != "passed" for r in results):
            raise ValueError("Incomplete selected measurements")
        if pins() != saved["pins"]:
            raise ValueError("Queued inputs changed during measurement")
        write_json(out / "results.json", {"run": str(run_dir), "cases": results})
    write_json(out / "completed.json", {"utc": datetime.now(timezone.utc).isoformat(), "run": str(run_dir)})
    print(f"COMPLETE {out / 'results.json'}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--enqueue", action="store_true")
    args = parser.parse_args()
    request = args.request.resolve()
    os.chdir(ROOT)
    if args.enqueue:
        request.parent.mkdir(parents=True, exist_ok=True)
        saved = {"utc": datetime.now(timezone.utc).isoformat(), "pins": pins()}
        with request.open("x") as stream:
            json.dump(saved, stream, indent=2)
        print(request)
    else:
        try:
            run(request)
        except Exception as error:
            failure = request.parent / "failed.json"
            if not failure.exists():
                write_json(failure, {"utc": datetime.now(timezone.utc).isoformat(), "error": str(error)})
            raise


if __name__ == "__main__":
    main()
