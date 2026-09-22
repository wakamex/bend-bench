"""Separate preparation, correctness, measurements, and evidence-only reporting."""

import json
import os
from pathlib import Path
import re
import statistics

from .core import append, correct, environment, exclusive, execute, fingerprint, hash_file, idle_gpu, provenance, rows, write_json
from .suites import plan, stage


def directory(config, evidence):
    if '_build_directory' in config:
        return Path(config['_build_directory'])
    return Path(config["output"]) / fingerprint(evidence)[:20]


def artifacts(work):
    folders = ("build", "baselines", "ports", "gpu")
    if (work / 'inputs/rodinia').exists():
        folders += ('inputs/rodinia',)
    return {str(p.relative_to(work)): hash_file(p) for folder in folders
            for p in sorted((work / folder).rglob("*")) if p.is_file()}


def prepare(config):
    with exclusive(config):
        if '_build_artifact' in config:
            from .builds import prepare_run
            return prepare_run(config)
        evidence = provenance(config)
        run = directory(config, evidence)
        if (run / "prepared.json").exists():
            print('Validating saved build:', run, flush=True)
            validate(config, run, evidence)
            return run
        run.mkdir(parents=True, exist_ok=True)
        write_json(run / "provenance.json", evidence)
        for name, source in evidence["sources"].items():
            (run / f"{name}.patch").write_text(source["patch"] + ("\n" if source["patch"] else ""))
        stage(config, run / "work")
        builds, cases = plan(config, run / "work")
        write_json(run / "plan.json", {"builds": builds, "cases": cases})
        print(f'Preparing {len(builds)} build steps: {run}', flush=True)
        for index, command in enumerate(builds, 1):
            output = command[command.index('-o') + 1] if '-o' in command else command[0] if '--gpu-build' in command else command[-1]
            print(f'Build {index}/{len(builds)}: {Path(str(output)).name}', flush=True)
            result = execute(command, cwd=run / "work", timeout=config["timeout"])
            append(run / "prepare.jsonl", result)
            print(f"  {'FAILED' if result['returncode'] else 'done'} ({result['end_to_end_seconds']:.2f}s)", flush=True)
            if result["returncode"]:
                raise ValueError(f"Preparation failed; retained log: {run / 'prepare.jsonl'}")
        # Verify sources/tools did not change during compilation.
        print('Validating build artifacts and loaded libraries...', flush=True)
        if provenance(config) != evidence:
            raise ValueError("Sources, tools, environment, or host changed during preparation")
        hashes = artifacts(run / "work")
        libraries = {}
        for file in (run / "work/build").iterdir():
            if file.is_file() and file.read_bytes()[:4] == b"\x7fELF":
                result = execute(["ldd", file])
                for path in re.findall(r"(/[^\s()]+)", result["stdout"]):
                    if Path(path).is_file():
                        libraries[path] = hash_file(path)
        prepared = dict(fingerprint=fingerprint({"provenance": evidence, "artifacts": hashes, "libraries": libraries}),
                        artifacts=hashes, libraries=libraries, plan_sha256=hash_file(run / "plan.json"))
        write_json(run / "prepared.json", prepared)
        return run


def validate(config, run, evidence=None):
    evidence = evidence or provenance(config)
    saved = json.loads((run / "provenance.json").read_text())
    if saved != evidence:
        raise ValueError("Experiment identity changed; prepare a new run")
    prepared = json.loads((run / "prepared.json").read_text())
    if artifacts(run / "work") != prepared["artifacts"]:
        raise ValueError("Prepared sources/binaries changed; do not reuse this run")
    if any(not Path(p).is_file() or hash_file(p) != h for p, h in prepared["libraries"].items()):
        raise ValueError("Loaded-library files changed; prepare a new experiment")
    if hash_file(run / "plan.json") != prepared["plan_sha256"]:
        raise ValueError("Prepared plan changed")
    return prepared


def locate(config):
    evidence = provenance(config)
    run = directory(config, evidence)
    if not (run / "prepared.json").exists():
        raise ValueError("No preparation for this exact identity; run prepare first")
    return run, validate(config, run, evidence)


def sample(config, run, identity, case, phase, rep):
    env = {**environment(), **case["env"]}
    load = os.getloadavg()
    command = [*case["command"], *(case.get("check_args", []) if phase == "check" else [])]
    result = execute(command, cwd=run / "work", env=env, timeout=config["timeout"], measured=True,
                     gpu_policy=config if config.get("require_idle_gpu") else None)
    output_correct = correct(case, {k: v for k, v in result.items() if k != "contention_error"})
    record = dict(fingerprint=identity, case=case["id"], phase=phase, rep=rep, env=env, load_average_before=load,
                  output_correct=output_correct, measurement_valid=not bool(result.get("contention_error")),
                  correct=correct(case, result), **result)
    append(run / "samples.jsonl", record)
    print(f"{phase} {case['id']} {rep}: {'passed' if record['correct'] else 'FAILED'}", flush=True)
    return record


def measure(config, checking=False):
    with exclusive(config):
        run, prepared = locate(config)
        identity = prepared["fingerprint"]
        cases = json.loads((run / "plan.json").read_text())["cases"]
        history = rows(run / "samples.jsonl")
        if any(row["fingerprint"] != identity for row in history):
            raise ValueError("Mixed experiment fingerprints in sample log")
        failures = False
        for case in cases:
            if case["unsupported"]:
                continue
            previous = [r for r in history if r["case"] == case["id"]]
            if any(not r["correct"] for r in previous):
                failures = True
                continue
            checked = any(r["phase"] == "check" and r["correct"] for r in previous)
            if not checked:
                if not checking:
                    raise ValueError(f"Missing correctness check: {case['id']}; run check first")
                result = sample(config, run, identity, case, "check", 0)
                failures |= not result["correct"]
            if checking:
                continue
            done = {(r["phase"], r["rep"]) for r in previous}
            failed = False
            for phase, count in (("warmup", config["warmups"]), ("measure", config["repetitions"])):
                for rep in range(count):
                    if (phase, rep) in done:
                        continue
                    if not sample(config, run, identity, case, phase, rep)["correct"]:
                        failures = failed = True
                        break
                if failed:
                    break
        validate(config, run)
        return run, failures


def summarize(run):
    run = Path(run)
    evidence = json.loads((run / "provenance.json").read_text())
    config = evidence["config"]
    prepared_path = run / "prepared.json"
    prepared = json.loads(prepared_path.read_text()) if prepared_path.exists() else None
    if prepared and hash_file(run / "plan.json") != prepared["plan_sha256"]:
        raise ValueError("Prepared plan changed; report refused")
    history = rows(run / "samples.jsonl")
    profiles = rows(run / "profiles.jsonl")
    if prepared and any(r["fingerprint"] != prepared["fingerprint"] for r in history):
        raise ValueError("Mixed fingerprints; report refused")
    if prepared and any(r["fingerprint"] != prepared["fingerprint"] for r in profiles):
        raise ValueError("Mixed profile fingerprints; report refused")
    cases = json.loads((run / "plan.json").read_text())["cases"]
    result = []
    for case in cases:
        samples = [r for r in history if r["case"] == case["id"]]
        keys = [(r["phase"], r["rep"]) for r in samples]
        if len(keys) != len(set(keys)):
            raise ValueError(f"Duplicate sample identifiers: {case['id']}")
        measured = [r for r in samples if r["phase"] == "measure" and r["correct"]]
        checked = any(r["phase"] == "check" and r["correct"] for r in samples)
        warmed = sum(r["phase"] == "warmup" and r["correct"] for r in samples) >= config["warmups"]
        status = ("unsupported" if case["unsupported"] else "failed" if any(not r["correct"] for r in samples)
                  else "passed" if prepared and checked and warmed and len(measured) >= config["repetitions"] else "pending")
        row = dict(case=case["id"], contract=case["contract"], status=status, checked=checked, samples=len(measured),
                   reason=case["unsupported"], threads=case["threads"], implementation=case["implementation"],
                   end_to_end_seconds=None, compute_seconds=None, device_sequence_seconds=None, kernel_seconds=None,
                   host_peak_rss_kb=None)
        if status == "passed":
            for metric in ("end_to_end_seconds", "compute_seconds", "device_sequence_seconds"):
                values = [r[metric] for r in measured if r.get(metric) is not None]
                if len(values) == len(measured):
                    row[metric] = statistics.median(values)
            rss = [r["host_peak_rss_kb"] for r in measured if r["host_peak_rss_kb"] is not None]
            row["host_peak_rss_kb"] = max(rss) if rss else None
        profile_rows = [r for r in profiles if r["case"] == case["id"]]
        if len({r["rep"] for r in profile_rows}) != len(profile_rows):
            raise ValueError(f"Duplicate profile identifiers: {case['id']}")
        profile_measurements = [r for r in profile_rows if r["phase"] == "measure" and r["correct"]]
        profile_warmups = [r for r in profile_rows if r["phase"] == "warmup" and r["correct"]]
        row["profile_status"] = ("failed" if any(not r["correct"] for r in profile_rows) else
                                  "passed" if len(profile_measurements) >= config["repetitions"] and
                                  len(profile_warmups) >= config["warmups"] else "pending")
        if row["profile_status"] == "passed":
            row["kernel_seconds"] = statistics.median(r["kernel_seconds"] for r in profile_measurements)
        result.append(row)
    # A comparable one-thread implementation is required for a scaling ratio.
    by_id = {row["case"]: row for row in result}
    for row in result:
        base = by_id.get(row["case"].rsplit("/", 1)[0] + "/1")
        row["speedup"] = (base["end_to_end_seconds"] / row["end_to_end_seconds"]
                          if base and base["end_to_end_seconds"] and row["end_to_end_seconds"] else None)
        row["efficiency"] = row["speedup"] / row["threads"] if row["speedup"] else None
    build_failures = any(r["returncode"] for r in rows(run / "prepare.jsonl"))
    return dict(fingerprint=prepared["fingerprint"] if prepared else None, provenance=evidence, cases=result,
                preparation_status="passed" if prepared else "failed" if build_failures else "pending")


def report(run):
    run = Path(run)
    summary = summarize(run)
    write_json(run / "summary.json", summary)
    lines = ["# Bend benchmark results", "", "Times are medians of correctness-gated measured executions, excluding checks and warmups. End-to-end includes process startup and output. Device-sequence event time is distinct from a kernel-only sum. Unmeasured metrics remain blank.", "",
             f"Preparation: {summary['preparation_status']}. Fingerprint: `{summary['fingerprint']}`.", "",
             "| Workload / implementation / threads | Gate | Profile gate | Checked | Runs | End-to-end seconds | Compute seconds | Device-sequence seconds | Kernel seconds | Speedup | Efficiency | Peak host RSS KiB |",
             "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in summary["cases"]:
        values = [row["case"], row["status"], row["profile_status"] if row["implementation"].endswith("cuda") else "n/a",
                  str(row["checked"]), str(row["samples"])]
        for key in ("end_to_end_seconds", "compute_seconds", "device_sequence_seconds", "kernel_seconds", "speedup", "efficiency", "host_peak_rss_kb"):
            values.append(f"{row[key]:.6f}" if row[key] is not None else "")
        lines.append("| " + " | ".join(values) + " |")
    lines += ["", "## Scope", "", "Vendor inputs retain upstream arithmetic and checksums. UTS preserves BOTS's SHA-1 tree. CUB uses library radix sort and reduction over matching wrapping-U32 inputs. HotSpot uses the archived Rodinia inputs and CUDA timestep, with a preserved OpenMP boundary correction and full-vector validation. Kernel sums, when present, come from separate correctness-checked Nsight executions; profiled wall time is not used as end-to-end time. Device peak memory, proof-system correspondence, Metal and AI-coding trials remain unmeasured.", ""]
    (run / "report.md").write_text("\n".join(lines))
    return run / "report.md"


def compare(before, after):
    old, new = summarize(before), summarize(after)
    left = {r["case"]: r for r in old["cases"]}
    same_host = old["provenance"]["host"] == new["provenance"]["host"]
    policy = ("threads", "cpus", "warmups", "repetitions", "gpu_heap", "gpu_arch", "tools")
    same_policy = all(old["provenance"]["config"].get(k) == new["provenance"]["config"].get(k) for k in policy)
    result = []
    for row in new["cases"]:
        prior = left.get(row["case"])
        reason = ("missing baseline" if not prior else "host changed" if not same_host else "measurement policy changed" if not same_policy
                  else "workload contract changed" if prior["contract"] != row["contract"]
                  else "incomplete or failed gate" if prior["status"] != "passed" or row["status"] != "passed" else None)
        result.append(dict(case=row["case"], reason=reason,
                           before_over_after=None if reason else prior["end_to_end_seconds"] / row["end_to_end_seconds"]))
    changes = {key: {"before": fingerprint(old["provenance"].get(key)), "after": fingerprint(new["provenance"].get(key))}
               for key in ("sources", "tools", "harness", "toolkit", "environment", "config", "host")
               if old["provenance"].get(key) != new["provenance"].get(key)}
    return dict(before=old["fingerprint"], after=new["fingerprint"], changed_provenance=changes, comparisons=result)
