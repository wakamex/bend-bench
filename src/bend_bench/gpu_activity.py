"""Sampled NVML activity checks that distinguish residency from GPU work.

Structures and return codes follow the CUDA toolkit's nvml.h. NOT_FOUND means
no nonzero process samples; NOT_SUPPORTED and other errors fail closed.
"""
import ctypes as c
from pathlib import Path
import threading
import time


class Process(c.Structure):
    _fields_ = [("pid", c.c_uint), ("memory_bytes", c.c_ulonglong),
                ("gpu_instance", c.c_uint), ("compute_instance", c.c_uint)]


class Sample(c.Structure):
    _fields_ = [("pid", c.c_uint), ("timestamp_us", c.c_ulonglong),
                ("sm", c.c_uint), ("memory", c.c_uint), ("encoder", c.c_uint), ("decoder", c.c_uint)]


def process_identity(pid):
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
    return dict(pid=pid, start_ticks=int(fields[19]),
                boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip())


def process_cgroup(pid):
    for line in Path(f"/proc/{pid}/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            return line[3:]
    raise ValueError("Unified process cgroup unavailable")


def belongs_to(pid, root):
    """Allow only the benchmark session or its descendants during execution."""
    seen = set()
    while pid > 1 and pid not in seen:
        if pid == root:
            return True
        seen.add(pid)
        try:
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        except FileNotFoundError:
            return False
        if int(fields[3]) == root:  # session ID, after execute's setsid()
            return True
        pid = int(fields[1])
    return False


class Activity:
    def __init__(self):
        self.lib = c.CDLL("libnvidia-ml.so.1")
        self.lib.nvmlInit_v2.argtypes = []
        self.lib.nvmlShutdown.argtypes = []
        self.lib.nvmlDeviceGetHandleByIndex_v2.argtypes = [c.c_uint, c.POINTER(c.c_void_p)]
        self.lib.nvmlDeviceGetCount_v2.argtypes = [c.POINTER(c.c_uint)]
        self.lib.nvmlDeviceGetUUID.argtypes = [c.c_void_p, c.c_void_p, c.c_uint]
        self.lib.nvmlDeviceGetComputeRunningProcesses_v3.argtypes = [c.c_void_p, c.POINTER(c.c_uint), c.POINTER(Process)]
        self.lib.nvmlDeviceGetProcessUtilization.argtypes = [c.c_void_p, c.POINTER(Sample), c.POINTER(c.c_uint), c.c_ulonglong]
        self.check(self.lib.nvmlInit_v2())
        try:
            count = c.c_uint()
            self.check(self.lib.nvmlDeviceGetCount_v2(c.byref(count)))
            if count.value != 1:
                raise ValueError("Resident-aware policy currently requires exactly one GPU")
            self.device = c.c_void_p()
            self.check(self.lib.nvmlDeviceGetHandleByIndex_v2(0, c.byref(self.device)))
            uuid = c.create_string_buffer(96)
            self.check(self.lib.nvmlDeviceGetUUID(self.device, uuid, len(uuid)))
            self.uuid = uuid.value.decode()
        except BaseException:
            self.lib.nvmlShutdown()
            raise

    @staticmethod
    def check(code):
        if code:
            raise ValueError(f"NVML activity query failed (status {code}); refusing unmonitored timing")

    def close(self):
        self.check(self.lib.nvmlShutdown())

    def processes(self):
        count = c.c_uint(256)
        data = (Process * count.value)()
        self.check(self.lib.nvmlDeviceGetComputeRunningProcesses_v3(self.device, c.byref(count), data))
        return [dict(pid=p.pid, memory_bytes=p.memory_bytes) for p in data[:count.value]]

    def samples(self, since):
        count = c.c_uint(4096)
        data = (Sample * count.value)()
        code = self.lib.nvmlDeviceGetProcessUtilization(self.device, data, c.byref(count), since)
        if code == 6:  # NVML_ERROR_NOT_FOUND: no nonzero samples in this interval.
            return []
        self.check(code)
        return [{name: getattr(s, name) for name, _ in Sample._fields_} for s in data[:count.value]]

    def snapshot(self, resident, since, benchmark_pid=None):
        processes = self.processes()
        samples = self.samples(since)
        errors = []
        allowed = resident.get("pid")
        approved = {allowed} if allowed else set()
        benchmark_identities = getattr(self, "known_benchmarks", {})
        for pid in {p["pid"] for p in processes + samples}:
            if benchmark_pid and belongs_to(pid, benchmark_pid):
                try:
                    benchmark_identities[pid] = process_identity(pid)["start_ticks"]
                except FileNotFoundError:
                    pass
            if pid in benchmark_identities:
                try:
                    matches = process_identity(pid)["start_ticks"] == benchmark_identities[pid]
                except FileNotFoundError:
                    matches = True
                if matches:
                    approved.add(pid)
        self.known_benchmarks = benchmark_identities
        identities = []
        if "cgroup" in resident:
            # Retain attribution for delayed NVML samples after an observed
            # process exits. A live PID must always be checked again.
            known = getattr(self, "known_residents", {})
            for pid in {p["pid"] for p in processes + samples}:
                try:
                    identity = process_identity(pid)
                    group = process_cgroup(pid)
                    if group == resident["cgroup"] or group.startswith(resident["cgroup"] + "/"):
                        known[pid] = {**identity, "cgroup": group}
                        approved.add(pid)
                        identities.append(known[pid])
                    else:
                        known.pop(pid, None)
                except FileNotFoundError:
                    if pid in known:
                        approved.add(pid)
                        identities.append({**known[pid], "exited": True})
            self.known_residents = known
        if allowed:
            try:
                if process_identity(allowed) != resident:
                    errors.append("Resident process identity changed")
            except OSError:
                errors.append("Pinned resident process exited")
            if allowed not in {p["pid"] for p in processes}:
                errors.append("Pinned GPU residency disappeared")
        for p in processes:
            if p["pid"] not in approved and not (benchmark_pid and belongs_to(p["pid"], benchmark_pid)):
                errors.append(f"Unapproved GPU process {p['pid']}")
        # The pinned resident worker is explicitly allowed to run, including
        # its canary jobs. Only activity from an unapproved process invalidates
        # a sample; the resident process remains visible in the evidence.
        active = [s for s in samples if any(s[k] for k in ("sm", "memory", "encoder", "decoder"))
                  and s["pid"] not in approved
                  and not (benchmark_pid and belongs_to(s["pid"], benchmark_pid))]
        if active:
            errors.append("External GPU activity detected")
        return dict(gpu_uuid=self.uuid, observed_us=time.time_ns()//1000, processes=processes,
                    samples=samples, resident_processes=identities,
                    benchmark_processes=benchmark_identities.copy(), errors=errors)


def idle_snapshot(config, since=None):
    activity = Activity()
    try:
        return activity.snapshot(config.get("gpu_resident", {}), since if since is not None else time.time_ns()//1000-1_000_000)
    finally:
        activity.close()


class Monitor:
    """Observe resident activity throughout a run, outside its timing boundaries."""
    def __init__(self, config):
        self.resident = config.get("gpu_resident", {})
        self.activity = Activity()
        self.cursor = time.time_ns()//1000-1_000_000
        self.observations = []
        self.errors = []
        self.stop = threading.Event()
        self.thread = None
        # No benchmark session exists during preflight; inspect resident activity
        # and live foreign contexts without blaming a preceding benchmark's samples.
        self.pid = -1
        try:
            self.observe()
            if self.errors:
                raise ValueError("; ".join(self.errors))
        except BaseException:
            self.activity.close()
            raise

    def observe(self):
        record = self.activity.snapshot(self.resident, self.cursor, self.pid)
        if record["samples"]:
            self.cursor = max(s["timestamp_us"] for s in record["samples"])
        self.observations.append(record)
        self.errors.extend(record["errors"])

    def start(self, pid):
        self.pid = pid
        def watch():
            while not self.stop.wait(0.25):
                try:
                    self.observe()
                except Exception as error:
                    self.errors.append(str(error))
                    break
        self.thread = threading.Thread(target=watch, daemon=True)
        self.thread.start()

    def finish(self):
        self.stop.set()
        if self.thread:
            self.thread.join()
        try:
            # Give the driver's sampled counters time to publish short-run activity.
            # This delay is after the measured wall interval, never added to it.
            time.sleep(1.1)
            self.observe()
        except Exception as error:
            self.errors.append(str(error))
        finally:
            self.activity.close()
        return dict(resident=self.resident, interval_seconds=0.25, drain_seconds=1.1,
                    observations=self.observations, errors=sorted(set(self.errors)))
