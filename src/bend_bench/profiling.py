"""Separate Nsight kernel sums; never substitute profiled wall times."""

import json
from pathlib import Path
import re
import sqlite3

from .core import append, correct, environment, exclusive, execute, hash_file, idle_gpu, rows, write_json
from .experiment import locate, summarize, validate


def kernel_totals(database):
    with sqlite3.connect(f"file:{Path(database).resolve()}?mode=ro", uri=True) as connection:
        duration, count = connection.execute(
            "SELECT SUM(end-start), COUNT(*) FROM CUPTI_ACTIVITY_KIND_KERNEL").fetchone()
    if not count or duration is None or duration <= 0:
        raise ValueError("Profiler did not capture CUDA kernels")
    return dict(kernel_seconds=duration / 1e9, kernel_launches=count)


def profile(config, profiler):
    profiler = Path(profiler).absolute()
    with exclusive(config):
        run, prepared = locate(config)
        summary = summarize(run)
        cases = json.loads((run / "plan.json").read_text())["cases"]
        gpu_cases = [case for case in cases if case["implementation"].endswith("cuda") and not case["unsupported"]]
        if not gpu_cases:
            raise ValueError("No supported CUDA cases to profile")
        passed = {row["case"] for row in summary["cases"] if row["status"] == "passed"}
        if any(case["id"] not in passed for case in gpu_cases):
            raise ValueError("Finish correctness and unprofiled measurements before profiling")
        version = execute([profiler, "--version"])
        if version["returncode"]:
            raise ValueError("Cannot identify profiler")
        identity = dict(path=str(profiler), sha256=hash_file(profiler), version=version["stdout"])
        folder = run / "profiles"
        folder.mkdir(exist_ok=True)
        pin = folder / "profiler.json"
        if pin.exists() and json.loads(pin.read_text()) != identity:
            raise ValueError("Profiler changed; do not mix profile evidence")
        write_json(pin, identity)
        history = rows(run / "profiles.jsonl")
        if any(row["fingerprint"] != prepared["fingerprint"] for row in history):
            raise ValueError("Mixed profile fingerprints")
        failed = False
        for case in gpu_cases:
            prior = [row for row in history if row["case"] == case["id"]]
            if any(not row["correct"] for row in prior):
                failed = True
                continue
            for rep in range(-config["warmups"], config["repetitions"]):
                if any(row["rep"] == rep for row in prior):
                    continue
                stem = folder / (case["id"].replace("/", "-") + f"-{rep}")
                # Never overwrite an interrupted profile: investigate its exact files.
                if list(folder.glob(stem.name + ".*")):
                    raise ValueError(f"Unrecorded profile artifacts: {stem}")
                result = execute([profiler, "profile", "--trace=cuda", "--sample=none", "--cpuctxsw=none",
                                  "-o", stem, *case["command"]], cwd=run / "work",
                                 env={**environment(), **case["env"]}, timeout=config["timeout"], gpu_policy=config)
                # Nsight adds progress lines; benchmark output must still match a complete line.
                if 'expected_vector' in case:
                    target = result['stdout']
                    prefix = case['implementation'] in {'gap-openmp', 'gunrock-cuda'}
                    if prefix:
                        target = target.split('BEGIN_DISTANCES\n')[1] if target.count('BEGIN_DISTANCES\n') == 1 else ''
                    target = '\n'.join(line for line in target.splitlines() if re.fullmatch(r'\d+',line))
                    if prefix:
                        target = 'BEGIN_DISTANCES\n'+target
                    ok = correct(case,{**result,'stdout':target})
                elif "expected_bits" in case:
                    target = "\n".join(line for line in result["stdout"].splitlines() if re.fullmatch(r"\d+", line))
                    ok = correct(case, {**result, "stdout": target})
                else:
                    ok = not result["returncode"] and not result["timeout"] and not result.get("contention_error") and any(
                        re.fullmatch(case["expected_regex"], line) for line in result["stdout"].splitlines())
                record = dict(fingerprint=prepared["fingerprint"], case=case["id"], rep=rep,
                              phase="warmup" if rep < 0 else "measure", correct=ok, profile=result)
                if ok:
                    database = stem.with_suffix(".sqlite")
                    exported = execute([profiler, "export", "--type=sqlite", "-o", database,
                                        str(stem) + ".nsys-rep"], timeout=config["timeout"])
                    record["export"] = exported
                    try:
                        if exported["returncode"]:
                            raise ValueError("Nsight export failed")
                        record.update(kernel_totals(database))
                        record["database_sha256"] = hash_file(database)
                    except (ValueError, sqlite3.Error) as error:
                        record.update(correct=False, error=str(error))
                append(run / "profiles.jsonl", record)
                print(f"profile {case['id']} {rep}: {record['correct']}", flush=True)
                if not record["correct"]:
                    failed = True
                    break
        validate(config, run)
        return run, failed
