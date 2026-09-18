"""Provenance, process execution, and exclusive local execution."""

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import struct
import tempfile
import time
import tomllib


def hash_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def append(path, data):
    data = {"utc": datetime.now(timezone.utc).isoformat(), **data}
    with Path(path).open("a") as stream:
        stream.write(json.dumps(data, sort_keys=True) + "\n")
        stream.flush()


def rows(path):
    path = Path(path)
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def environment():
    # Do not inherit arbitrary OMP/CUDA/compiler options or persist secrets.
    return {"PATH": os.environ.get("PATH", os.defpath), "HOME": os.environ.get("HOME", "/tmp"),
            "LANG": "C", "LC_ALL": "C", "TZ": "UTC"}


def execute(command, cwd=None, env=None, timeout=180, measured=False, gpu_policy=None):
    command = list(map(str, command))
    argv = ["/usr/bin/time", "-f", "BEND_BENCH_RSS_KB=%M", *command] if measured else command
    monitor = None
    if gpu_policy is not None:
        from .gpu_activity import Monitor
        monitor = Monitor(gpu_policy)
        # GNU time forks the actual workload. Save that child's identity before
        # exec, so delayed NVML records remain attributable after it exits.
        identity_file = tempfile.NamedTemporaryFile(mode="w+", prefix="bend-bench-pid-")
        workload = ["/bin/sh", "-c", 'read -r stat < /proc/$$/stat; printf "%s\\n" "$stat" > "$1"; shift; exec "$@"',
                    "bend-bench", identity_file.name, *command]
        argv = ["/usr/bin/time", "-f", "BEND_BENCH_RSS_KB=%M", *workload] if measured else workload
    start = time.perf_counter()
    try:
        proc = subprocess.Popen(argv, cwd=cwd, env=env or environment(), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, start_new_session=True)
    except BaseException:
        if monitor:
            monitor.finish()
            identity_file.close()
        raise
    if monitor:
        monitor.start(proc.pid)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate()
        if isinstance(error, KeyboardInterrupt):
            if monitor:
                monitor.finish()
            raise
        timed_out = True
    result = dict(command=command, returncode=proc.returncode, stdout=stdout, stderr=stderr,
                  timeout=timed_out, end_to_end_seconds=time.perf_counter() - start)
    if monitor:
        identity_file.seek(0)
        saved_stat = identity_file.read().strip()
        identity_file.close()
        if saved_stat:
            known = getattr(monitor.activity, "known_benchmarks", {})
            known[int(saved_stat.split(" ", 1)[0])] = int(saved_stat.rsplit(") ", 1)[1].split()[19])
            monitor.activity.known_benchmarks = known
        result["gpu_activity"] = monitor.finish()
        if result["gpu_activity"]["errors"]:
            result["contention_error"] = "; ".join(result["gpu_activity"]["errors"])
    rss = re.search(r"BEND_BENCH_RSS_KB=(\d+)", stderr)
    result["host_peak_rss_kb"] = int(rss[1]) if rss else None
    for label in ("COMPUTE", "DEVICE_SEQUENCE"):
        value = re.search(r"EVAL_" + label + r"_SECONDS=([\d.]+)", stderr)
        if value:
            result[label.lower() + "_seconds"] = float(value[1])
    return result


def output(command):
    result = execute(command)
    if result["returncode"]:
        raise ValueError(f"Command failed: {command}: {result['stderr']}")
    return result["stdout"].strip()


def repository(spec):
    path = Path(spec["path"])
    git = ["git", "-C", str(path)]
    commit = output([*git, "rev-parse", "HEAD"])
    if commit != spec["commit"]:
        raise ValueError(f"{path}: expected {spec['commit']}, found {commit}")
    untracked = output([*git, "ls-files", "--others", "--exclude-standard"])
    if untracked:
        raise ValueError(f"{path}: untracked files must be staged or excluded before benchmarking")
    patch = output([*git, "diff", "--binary", "HEAD", "--"])
    if patch and not spec.get("allow_patch", False):
        raise ValueError(f"{path}: local patch requires allow_patch = true")
    files = output([*git, "ls-files", "-z"]).split("\0")
    hashes = {name: hash_file(path / name) if (path / name).is_file() else None for name in files if name}
    return dict(path=str(path), commit=commit, patch=patch,
                remotes=output([*git, "remote", "-v"]), files=hashes)


def load_config(path):
    path = Path(path).resolve()
    config = tomllib.loads(path.read_text())
    allowed = {"schema", "label", "output", "suites", "threads", "cpus", "repetitions", "warmups", "timeout",
               "cuda", "gpu_heap", "gpu_arch", "uts_inputs", "uts_cutoffs", "blocked_services",
               "bend", "bots", "cccl", "rodinia", "gpu_depths", "hotspot_sizes", "hotspot_steps",
               "hotspot_pyramids", "tools", "vendor", "require_idle_gpu", "gpu_resident",
               "pricing_depths", "pricing_steps", "bfs_depths", "mnk_games", "gap", "gunrock", "moderngpu"}
    if unknown := config.keys() - allowed:
        raise ValueError(f"Unknown configuration keys: {sorted(unknown)}")
    if config.get("schema") != 1:
        raise ValueError("Expected schema = 1")
    if "gpu_resident" in config:
        resident = config["gpu_resident"]
        if set(resident) == {"cgroup"}:
            group = resident["cgroup"]
            prefix = f"/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/"
            if (not isinstance(group, str) or not group.startswith(prefix)
                    or not group.endswith(".service") or ".." in group.split("/")):
                raise ValueError("gpu_resident.cgroup must name a user service cgroup")
        elif (set(resident) != {"pid", "start_ticks", "boot_id"} or
                type(resident["pid"]) is not int or resident["pid"] <= 0 or
                type(resident["start_ticks"]) is not int or resident["start_ticks"] <= 0 or
                not re.fullmatch(r"[0-9a-f-]{36}", resident["boot_id"])):
            raise ValueError("gpu_resident requires a pinned pid, start_ticks and boot_id")
        if not config.get("require_idle_gpu"):
            raise ValueError("gpu_resident requires require_idle_gpu")
    if not config.get("suites") or set(config["suites"]) - {"vendor", "uts", "cub", "hotspot", "pricing", "mnk", "bfs"}:
        raise ValueError("Unknown or missing suite")
    for key, default in (("repetitions", 10), ("warmups", 1), ("timeout", 180)):
        config.setdefault(key, default)
        if type(config[key]) is not int or config[key] < (10 if key == "repetitions" else 1):
            raise ValueError(f"Invalid {key}; require >= {10 if key == 'repetitions' else 1}")
    config.setdefault("threads", [1])
    config.setdefault("cpus", sorted(os.sched_getaffinity(0)))
    if (not config["threads"] or any(type(n) is not int or n < 1 or n > len(config["cpus"]) for n in config["threads"])
            or len(set(config["threads"])) != len(config["threads"])):
        raise ValueError("threads must be unique positive counts within the CPU list")
    if (not config["cpus"] or len(set(config["cpus"])) != len(config["cpus"])
            or not set(config["cpus"]) <= os.sched_getaffinity(0)):
        raise ValueError("cpus must be unique CPUs available to this process")
    for key in ("bend", "bots", "cccl", "gap", "gunrock", "moderngpu"):
        if key in {"gap", "gunrock", "moderngpu"} and key not in config:
            if "bfs" in config["suites"]:
                raise ValueError(f"BFS requires pinned {key} source")
            continue
        if key not in config and ((key == "bots" and "uts" not in config["suites"]) or
                                  (key == "cccl" and not set(config["suites"]) & {"cub", "bfs", "pricing"})):
            continue
        spec = config[key]
        if spec.keys() - {"path", "commit", "allow_patch"}:
            raise ValueError(f"Unknown {key} source option")
        spec["path"] = str((path.parent / spec["path"]).resolve())
        if not re.fullmatch(r"[0-9a-f]{40}", spec["commit"]):
            raise ValueError(f"{key}.commit must be a full Git SHA")
    if "hotspot" in config["suites"]:
        spec = config["rodinia"]
        if set(spec) != {"path", "archive", "sha256"} or not re.fullmatch(r"[0-9a-f]{64}", spec["sha256"]):
            raise ValueError("rodinia requires path, archive and sha256")
        for key in ("path", "archive"):
            spec[key] = str((path.parent / spec[key]).resolve())
        for key, default, allowed_values in (("hotspot_sizes", [64, 512, 1024], {64, 512, 1024}),
                                            ("hotspot_steps", [10, 100], {10, 100}),
                                            ("hotspot_pyramids", [1, 2, 4], {1, 2, 4})):
            config.setdefault(key, default)
            if not config[key] or set(config[key]) - allowed_values or len(set(config[key])) != len(config[key]):
                raise ValueError(f"Invalid {key}")
    tools = config.setdefault("tools", {})
    if tools.keys() - {"bun", "cc", "cxx", "cuda_cxx", "cuda_path"}:
        raise ValueError("Unknown tool option")
    for name, default in (("bun", "bun"), ("cc", "clang"), ("cxx", "g++"), ("cuda_cxx", "clang++")):
        value = tools.get(name, default)
        # Keep argv[0]: resolving clang++ to clang changes its linker defaults.
        resolved = os.path.abspath(path.parent / value) if "/" in value else shutil.which(value)
        if not resolved or not Path(resolved).is_file():
            raise ValueError(f"Missing {name}: {value}")
        tools[name] = resolved
    tools["cuda_path"] = str((path.parent / tools.get("cuda_path", "/usr/local/cuda")).resolve())
    config["output"] = str((path.parent / config.get("output", "runs")).resolve())
    config.setdefault("cuda", False)
    config.setdefault("gpu_heap", "4GB")
    config.setdefault("gpu_arch", "sm_86")
    config.setdefault("uts_inputs", ["test"])
    config.setdefault("uts_cutoffs", [4, 16, 64])
    config.setdefault("blocked_services", [])
    config.setdefault("label", "default")
    if "cub" in config["suites"]:
        config.setdefault("gpu_depths", [12, 18, 23])
        if (not config["cuda"] or not config["gpu_depths"] or set(config["gpu_depths"]) - {12, 18, 23}
                or len(set(config["gpu_depths"])) != len(config["gpu_depths"])):
            raise ValueError("cub requires CUDA and gpu_depths drawn from 12, 18, 23")
    if set(config["uts_inputs"]) - {"test", "tiny"}:
        raise ValueError("Supported UTS inputs: test, tiny")
    if any(type(n) is not int or n < 0 for n in config["uts_cutoffs"]):
        raise ValueError("UTS cutoffs must be nonnegative integers")
    for key, default, valid in (("pricing_depths", [12,15,18], {8,12,15,18}),
                                ("pricing_steps", [64,256], {16,64,256}),
                                ("bfs_depths", [10,14,18], {6,10,12,14,18})):
        config.setdefault(key, default)
        if not config[key] or len(set(config[key])) != len(config[key]) or set(config[key])-valid:
            raise ValueError(f"Invalid {key}")
    config.setdefault("mnk_games", [[4,4,3,6],[4,4,3,8],[5,5,4,6],[5,5,4,8]])
    games = config['mnk_games']
    if (not games or len({tuple(g) for g in games}) != len(games) or
            any(len(g)!=4 or any(type(x) is not int for x in g) or
                not (2<=g[0]<=5 and 2<=g[1]<=5 and 2<=g[2]<=min(g[:2]) and 1<=g[3]<=min(9,g[0]*g[1])) for g in games)):
        raise ValueError('Invalid mnk_games')
    return config


def provenance(config):
    sources = {key: repository(config[key]) for key in ("bend", "bots", "cccl", "gap", "gunrock", "moderngpu") if key in config}
    if "rodinia" in config:
        spec = config["rodinia"]
        if hash_file(spec["archive"]) != spec["sha256"]:
            raise ValueError("Rodinia archive hash mismatch")
        root = Path(spec["path"])
        hashes = {str(p.relative_to(root)): hash_file(p) for p in root.rglob("*") if p.is_file()}
        # Preserve both the downloaded archive and every actual extracted input.
        # Changed extracted files create a new identity even with the same archive.
        sources["rodinia"] = {**spec, "files": hashes, "patch": ""}
    tools = {key: dict(path=value, sha256=hash_file(value), version=output([value, "--version"]))
             for key, value in config["tools"].items() if key != "cuda_path"}
    package = Path(__file__).parent
    harness = {str(p.relative_to(package)): hash_file(p) for p in sorted(package.rglob("*"))
               if p.is_file() and "__pycache__" not in p.parts}
    gpu = execute(["nvidia-smi", "--query-gpu=name,uuid,driver_version,memory.total", "--format=csv,noheader"]) if shutil.which("nvidia-smi") else None
    cpu = json.loads(output(["lscpu", "--json"]))["lscpu"]
    # Instantaneous clock utilization changes during otherwise identical runs.
    cpu = [row for row in cpu if row["field"] not in {"CPU(s) scaling MHz:", "CPU MHz:"}]
    governors = {str(p): p.read_text().strip() for p in Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_governor")}
    host = dict(platform=platform.platform(), cpu=cpu, governors=governors,
                topology=json.loads(output(["lscpu", "--json", "--extended=CPU,CORE,SOCKET,NODE"])),
                gpu=gpu["stdout"] if gpu else None, affinity=sorted(os.sched_getaffinity(0)))
    toolkit = {}
    if config["cuda"]:
        root = Path(config["tools"]["cuda_path"])
        for pattern in ("version.json", "include/*.h", "lib64/libnvrtc.so*", "lib64/libnvrtc-builtins.so*", "lib64/libcudart.so*"):
            for file in sorted(root.glob(pattern)):
                if file.is_file():
                    toolkit[str(file)] = hash_file(file)
    return dict(config=config, sources=sources, tools=tools, harness=harness, host=host,
                toolkit=toolkit, environment=environment())


@contextmanager
def exclusive(config):
    for service in config.get("blocked_services", []):
        if service_state(service) in {"active", "activating", "reloading", "deactivating"}:
            raise ValueError(f"Wait for {service} to finish; no overlapping preparation or measurement")
    lock = Path(tempfile.gettempdir()) / f"bend-bench-{os.getuid()}.lock"
    with lock.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another bend-bench process is preparing or measuring") from error
        yield


def service_state(service):
    if not shutil.which("systemctl"):
        raise ValueError("Cannot check blocked_services without systemctl")
    # User-bus routing is needed for this control query, not for benchmarks.
    env = {**environment(), **{k: os.environ[k] for k in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS") if k in os.environ}}
    result = execute(["systemctl", "--user", "is-active", service], env=env)
    state = result["stdout"].strip()
    if state not in {"active", "activating", "reloading", "deactivating", "inactive", "failed", "unknown"}:
        raise ValueError(f"Cannot inspect blocked service {service}: {result['stderr'].strip()}")
    return state


def idle_gpu(config=None):
    from .gpu_activity import idle_snapshot
    result = idle_snapshot(config or {})
    if result["errors"]:
        raise ValueError("; ".join(result["errors"]))
    return result


def correct(case, result):
    if result["returncode"] or result["timeout"] or result.get("contention_error"):
        return False
    if 'expected_vector' in case:
        try:
            expected = json.loads(Path(case['expected_vector']).read_text())
            output = result['stdout']
            if case['implementation'] in {'gap-openmp', 'gunrock-cuda'}:
                if output.count('BEGIN_DISTANCES\n') != 1:
                    return False
                output = output.split('BEGIN_DISTANCES\n')[1]
            actual = output.split()
            if len(actual) != len(expected):
                return False
            contract = case['contract']
            if contract['vector_kind'] == 'u32':
                return all(re.fullmatch(r'\d+', a) and int(a) == b for a,b in zip(actual,expected))
            for a,b in zip(actual,expected):
                x = struct.unpack('<f',struct.pack('<I',int(a)))[0]
                if not math.isfinite(x) or abs(x-b)>contract['abs_tolerance']+contract['rel_tolerance']*abs(b):
                    return False
            return True
        except (OSError, ValueError, struct.error, KeyError):
            return False
    if "expected_bits" in case:
        try:
            expected = Path(case["expected_bits"]).read_text().split()
            actual = result["stdout"].split()
            if len(actual) != len(expected) or len(actual) != case["contract"]["size"]**2:
                return False
            for a, b in zip(expected, actual):
                x = struct.unpack("f", struct.pack("I", int(a)))[0]
                y = struct.unpack("f", struct.pack("I", int(b)))[0]
                if not math.isfinite(x) or not math.isfinite(y) or abs(x-y) > 0.0001+1e-6*abs(x):
                    return False
            return True
        except (ValueError, struct.error, OSError):
            return False
    return bool(re.fullmatch(case["expected_regex"], result["stdout"].strip(), re.DOTALL))
