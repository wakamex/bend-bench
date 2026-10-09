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
            "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
            **({"TMPDIR": os.environ["TMPDIR"]} if "TMPDIR" in os.environ else {})}


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
    launch_env = env or environment()
    if monitor:
        launch_env = {**launch_env, "BEND_BENCH_PID_FILE": identity_file.name}
    start = time.perf_counter()
    try:
        proc = subprocess.Popen(argv, cwd=cwd, env=launch_env, stdout=subprocess.PIPE,
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
            for stat in saved_stat.splitlines():
                known[int(stat.split(" ", 1)[0])] = int(stat.rsplit(") ", 1)[1].split()[19])
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
               "cuda", "gpu_heap", "gpu_arch", "uts_inputs", "uts_cutoffs", "uts_gpu", "blocked_services",
               "bend", "bots", "cccl", "rodinia", "gpu_depths", "hotspot_sizes", "hotspot_steps",
               "hotspot_pyramids", "tools", "vendor", "require_idle_gpu", "gpu_resident",
               "pricing_depths", "pricing_steps", "bfs_depths", "mnk_games", "gap", "gunrock", "moderngpu", "queens_sizes", "vendor_gpu", "cudf", "implementations",
               "bend_ml", "ml_data", "ml_workloads", "cpu_idle"}
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
    if not config.get("suites") or set(config["suites"]) - {"vendor", "uts", "cub", "hotspot", "pricing", "mnk", "bfs", "nqueens", "ml", "gpu-regression", "cpu-regression"}:
        raise ValueError("Unknown or missing suite")
    config.setdefault("vendor_gpu", [])
    selected_gpu = config["vendor_gpu"]
    if (not isinstance(selected_gpu, list) or any(x not in {"tree-radix", "tree-matmul", "editdist", "mandelbrot", "queens", "merkle", "lexer", "kmeans", "hashmap", "bfs", "nbody", "raytrace", "terrain", "symreg"} for x in selected_gpu)
            or len(set(selected_gpu)) != len(selected_gpu)):
        raise ValueError("vendor_gpu must select unique supported workloads: tree-radix, tree-matmul, editdist, mandelbrot, queens, merkle, lexer, kmeans, hashmap, bfs, nbody, raytrace, terrain, symreg")
    if selected_gpu and ("vendor" not in config["suites"] or not config.get("cuda")
                         or not set(selected_gpu) <= set(config.get("vendor", selected_gpu))):
        raise ValueError("vendor_gpu requires CUDA and matching vendor workloads")
    if "editdist" in selected_gpu or "cudf" in config:
        spec = config.get("cudf", {})
        if (set(spec) != {"path", "version", "commit", "lock"}
                or not re.fullmatch(r"[0-9a-f]{40}", spec.get("commit", ""))):
            raise ValueError("cudf requires wheel site-packages path, version, source commit and uv lock path")
        for key in ("path", "lock"):
            spec[key] = str((path.parent / spec[key]).resolve())
    if "nqueens" in config["suites"]:
        config.setdefault("queens_sizes", [8, 12, 14])
        if (not config["queens_sizes"] or any(type(n) is not int or n not in {4, 8, 12, 14} for n in config["queens_sizes"])
                or len(set(config["queens_sizes"])) != len(config["queens_sizes"])):
            raise ValueError("queens_sizes must select unique sizes from 4, 8, 12, 14")
        if config.get("cuda"):
            raise ValueError("The N-Queens baseline comparison currently supports CPU only")
    for key, default in (("repetitions", 10), ("warmups", 1), ("timeout", 180)):
        config.setdefault(key, default)
        minimum = 10 if key == 'repetitions' and config['suites'] not in (['cpu-regression'], ['gpu-regression']) else 1
        if type(config[key]) is not int or config[key] < minimum:
            raise ValueError(f"Invalid {key}; require >= {minimum}")
    if "cpu_idle" in config:
        gate = config["cpu_idle"]
        if (not isinstance(gate, dict) or set(gate) != {"max_busy", "max_wait"}
                or not isinstance(gate["max_busy"], (int, float)) or gate["max_busy"] <= 0
                or type(gate["max_wait"]) is not int or gate["max_wait"] < CPU_WINDOW):
            raise ValueError(f"cpu_idle requires max_busy, a positive number of busy CPUs, and max_wait, whole seconds >= {CPU_WINDOW}")
    config.setdefault("threads", [1])
    config.setdefault("cpus", sorted(os.sched_getaffinity(0)))
    if (not config["threads"] or any(type(n) is not int or n < 1 or n > len(config["cpus"]) for n in config["threads"])
            or len(set(config["threads"])) != len(config["threads"])):
        raise ValueError("threads must be unique positive counts within the CPU list")
    if (not config["cpus"] or len(set(config["cpus"])) != len(config["cpus"])
            or not set(config["cpus"]) <= os.sched_getaffinity(0)):
        raise ValueError("cpus must be unique CPUs available to this process")
    if "ml" in config["suites"]:
        from .ml import WORKLOADS
        if "bend_ml" not in config or set(config.get("ml_data", {})) != {"path"}:
            raise ValueError("The ml suite requires a pinned bend_ml source and ml_data.path")
        config["ml_data"]["path"] = str((path.parent / config["ml_data"]["path"]).resolve())
        config.setdefault("ml_workloads", list(WORKLOADS))
        if (not config["ml_workloads"] or set(config["ml_workloads"]) - set(WORKLOADS)
                or len(set(config["ml_workloads"])) != len(config["ml_workloads"])):
            raise ValueError("ml_workloads must select unique workloads from " + ", ".join(WORKLOADS))
    for key in ("bend", "bots", "cccl", "gap", "gunrock", "moderngpu", "bend_ml"):
        if key == "bend_ml" and key not in config:
            continue
        if key in {"gap", "gunrock", "moderngpu"} and key not in config:
            if "bfs" in config["suites"]:
                raise ValueError(f"BFS requires pinned {key} source")
            continue
        if key not in config and ((key == "bots" and "uts" not in config["suites"]) or
                                  (key == "cccl" and not set(config["suites"]) & {"cub", "bfs", "pricing"}
                                   and "tree-radix" not in selected_gpu)):
            continue
        spec = config[key]
        if spec.keys() - {"path", "commit", "allow_patch"}:
            raise ValueError(f"Unknown {key} source option")
        spec["path"] = str((path.parent / spec["path"]).resolve())
        if not re.fullmatch(r"[0-9a-f]{40}", spec["commit"]):
            raise ValueError(f"{key}.commit must be a full Git SHA")
    if set(config["suites"]) & {"hotspot", "gpu-regression", "cpu-regression"}:
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
    if tools.keys() - {"bun", "cc", "cxx", "cuda_cxx", "cuda_path", "python_ml", "python_ml_cuda"}:
        raise ValueError("Unknown tool option")
    if "ml" in config["suites"]:
        if "python_ml" not in tools:
            raise ValueError("The ml suite requires tools.python_ml, a Python with torch, numpy, safetensors, tiktoken and regex")
        if config.get("cuda") and "python_ml_cuda" not in tools:
            raise ValueError("The ml suite on CUDA requires tools.python_ml_cuda, a Python with a CUDA build of torch and numpy")
        for name in ("python_ml", "python_ml_cuda"):
            if name in tools:
                # Keep the virtual environment's own path: resolving its symlink loses the environment.
                tools[name] = os.path.abspath(path.parent / tools[name])
                if not Path(tools[name]).is_file():
                    raise ValueError(f"Missing {name}: {tools[name]}")
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
    config.setdefault("uts_gpu", False)
    if type(config["uts_gpu"]) is not bool or (config["uts_gpu"] and
            (not config["cuda"] or "uts" not in config["suites"])):
        raise ValueError("uts_gpu requires the UTS suite and CUDA")
    impls = config.get("implementations", [])
    if (not isinstance(impls, list) or any(not isinstance(x, str) or not x for x in impls)
            or len(set(impls)) != len(impls) or ("implementations" in config and not impls)):
        raise ValueError("implementations must list unique implementation names")
    config.setdefault("blocked_services", [])
    config.setdefault("label", "default")
    if "cub" in config["suites"]:
        config.setdefault("gpu_depths", [12, 18, 23])
        if (not config["cuda"] or not config["gpu_depths"] or set(config["gpu_depths"]) - {12, 18, 23}
                or len(set(config["gpu_depths"])) != len(config["gpu_depths"])):
            raise ValueError("cub requires CUDA and gpu_depths drawn from 12, 18, 23")
    if set(config["uts_inputs"]) - {"test", "tiny", "compact"}:
        raise ValueError("Supported UTS inputs: test, tiny, compact")
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
    if '_build_artifact' in config:
        from .builds import runtime_provenance
        return runtime_provenance(config)
    sources = {key: repository(config[key]) for key in ("bend", "bots", "cccl", "gap", "gunrock", "moderngpu", "bend_ml") if key in config}
    if "ml_data" in config:
        from .ml import DATA
        packages = {name: output([config["tools"][name], "-c", "import importlib.metadata as m; print(sorted(f'{d.name}=={d.version}' for d in m.distributions()))"])
                    for name in ("python_ml", "python_ml_cuda") if name in config["tools"]}
        sources["ml_data"] = dict(path=config["ml_data"]["path"], files=DATA, python_packages=packages, patch="")
    if "cudf" in config:
        spec = config["cudf"]
        root = Path(spec["path"])
        if ((root / "libcudf/VERSION").read_text().strip() != spec["version"]
                or (root / "libcudf/GIT_COMMIT").read_text().strip() != spec["commit"]):
            raise ValueError("Installed libcudf version/source commit does not match configuration")
        # Include wheel headers, shared libraries and distribution metadata; exclude interpreter caches.
        hashes = {str(p.relative_to(root)): hash_file(p) for p in sorted(root.rglob("*"))
                  if p.is_file() and "__pycache__" not in p.parts}
        sources["cudf"] = {**spec, "files": hashes, "lock_sha256": hash_file(spec["lock"]), "patch": ""}
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
    host = host_info()
    toolkit = {}
    if config["cuda"]:
        root = Path(config["tools"]["cuda_path"])
        for pattern in ("version.json", "include/*.h", "lib64/libnvrtc.so*", "lib64/libnvrtc-builtins.so*", "lib64/libcudart.so*", "lib64/libcublas.so*", "lib64/libcublasLt.so*"):
            for file in sorted(root.glob(pattern)):
                if file.is_file():
                    toolkit[str(file)] = hash_file(file)
    return dict(config=config, sources=sources, tools=tools, harness=harness_info(), host=host,
                toolkit=toolkit, environment=environment())


def harness_info():
    package = Path(__file__).parent
    return {str(p.relative_to(package)): hash_file(p) for p in sorted(package.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts}


def host_info():
    gpu = execute(["nvidia-smi", "--query-gpu=name,uuid,driver_version,memory.total", "--format=csv,noheader"]) if shutil.which("nvidia-smi") else None
    cpu = json.loads(output(["lscpu", "--json"]))["lscpu"]
    # Instantaneous clock utilization changes during otherwise identical runs.
    cpu = [row for row in cpu if row["field"] not in {"CPU(s) scaling MHz:", "CPU MHz:"}]
    governors = {str(p): p.read_text().strip() for p in Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_governor")}
    host = dict(platform=platform.platform(), cpu=cpu, governors=governors,
                topology=json.loads(output(["lscpu", "--json", "--extended=CPU,CORE,SOCKET,NODE"])),
                gpu=gpu["stdout"] if gpu else None, affinity=sorted(os.sched_getaffinity(0)))
    return host


@contextmanager
def exclusive(config):
    for service in config.get("blocked_services", []):
        if (service_state(service) in {"active", "activating", "reloading", "deactivating"}
                and not service_contains_current_process(service)):
            raise ValueError(f"Wait for {service} to finish; no overlapping preparation or measurement")
    # Keep the historical shared location even when compiler TMPDIR is changed.
    lock = Path('/tmp') / f"bend-bench-{os.getuid()}.lock"
    with lock.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another bend-bench process is preparing or measuring") from error
        yield


def service_contains_current_process(service):
    # A queue's own preflight is part of that job, not a competing service.
    # Use systemd's actual cgroup rather than an inherited environment claim.
    env = {**environment(), **{k: os.environ[k] for k in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS") if k in os.environ}}
    result = execute(["systemctl", "--user", "show", service, "-p", "ControlGroup", "--value"], env=env)
    group = result["stdout"].strip()
    if result["returncode"] or not group.startswith("/") or group == "/":
        return False
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            current = line[3:]
            return current == group or current.startswith(group + "/")
    return False


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


CPU_WINDOW = 5  # seconds over which the CPU gate measures foreign load


def busy_cpus(cpus, seconds=CPU_WINDOW):
    """How many of `cpus` were busy over the next `seconds`, from /proc/stat: the sum over each CPU
    of its non-idle share, so 2.5 means two and a half CPUs' worth of work."""
    def snapshot():
        out = {}
        with open("/proc/stat") as f:
            for line in f:
                name, *fields = line.split()
                if name.startswith("cpu") and name[3:].isdigit() and int(name[3:]) in cpus:
                    user, nice, system, idle, iowait, irq, softirq, steal = map(int, fields[:8])
                    out[name] = (user + nice + system + irq + softirq + steal, user + nice + system + idle + iowait + irq + softirq + steal)
        return out
    before = snapshot()
    time.sleep(seconds)
    after = snapshot()
    return sum((after[k][0] - before[k][0]) / max(1, after[k][1] - before[k][1]) for k in before)


def quiet_cpus(config):
    """With cpu_idle configured, waits until the configured CPUs carry at most max_busy CPUs of
    other work, so no sample starts on a busy host. Load that arrives during a sample is not seen."""
    gate = config.get("cpu_idle")
    if not gate:
        return None
    start = time.monotonic()
    while True:
        busy = busy_cpus(set(config["cpus"]))
        waited = time.monotonic() - start
        if busy <= gate["max_busy"]:
            return dict(busy_cpus=round(busy, 2), waited_seconds=round(waited, 1))
        if waited >= gate["max_wait"]:
            raise ValueError(f"{busy:.1f} of {len(config['cpus'])} CPUs stayed busy for {gate['max_wait']} s, above cpu_idle.max_busy "
                             f"{gate['max_busy']}; resume the run once the host is quiet")


def idle_gpu(config=None):
    from .gpu_activity import idle_snapshot
    result = idle_snapshot(config or {})
    if result["errors"]:
        raise ValueError("; ".join(result["errors"]))
    return result


def correct(case, result):
    if result["returncode"] or result["timeout"] or result.get("contention_error"):
        return False
    if 'ml_kind' in case:
        from .ml import correct as ml_correct
        return ml_correct(case, result)
    if 'regression_kind' in case:
        from .fast import correct_special
        return correct_special(case, result)
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
