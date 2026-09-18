import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from bend_bench.core import append, correct, execute, load_config
from bend_bench.gpu_activity import Activity, belongs_to, idle_snapshot, process_identity, process_cgroup


class ActivityTests(unittest.TestCase):
    def test_delayed_benchmark_sample_and_pid_reuse(self):
        activity = object.__new__(Activity)
        activity.uuid = "fixture"
        activity.known_benchmarks = {42: 123}
        activity.processes = lambda: [dict(pid=42, memory_bytes=1)]
        activity.samples = lambda since: [dict(pid=42, timestamp_us=100, sm=5, memory=0, encoder=0, decoder=0)]
        with patch("bend_bench.gpu_activity.process_identity", side_effect=FileNotFoundError):
            self.assertEqual(activity.snapshot({}, 0)["errors"], [])
        with patch("bend_bench.gpu_activity.process_identity", return_value=dict(start_ticks=124)):
            self.assertIn("Unapproved GPU process 42", activity.snapshot({}, 0)["errors"])

    def test_service_restart_and_foreign_process(self):
        group = process_cgroup(os.getpid())
        self.assertTrue(group.startswith("/"))
        activity = object.__new__(Activity)
        activity.uuid = "fixture"
        current = [10]
        activity.processes = lambda: [dict(pid=p, memory_bytes=1) for p in current]
        activity.samples = lambda since: []
        with patch("bend_bench.gpu_activity.process_identity", side_effect=lambda p: dict(pid=p, start_ticks=p, boot_id="test")), patch("bend_bench.gpu_activity.process_cgroup", return_value=group):
            for pids in ([10], [], [20]):
                current[:] = pids
                record = activity.snapshot(dict(cgroup=group), 0)
                self.assertEqual(record["errors"], [])
                self.assertEqual([p["pid"] for p in record["resident_processes"]], pids)
        with patch("bend_bench.gpu_activity.process_identity", return_value=dict(pid=20, start_ticks=30)), patch("bend_bench.gpu_activity.process_cgroup", return_value=group + "-impostor"):
            self.assertIn("Unapproved GPU process 20", activity.snapshot(dict(cgroup=group), 0)["errors"])

    def test_identity_and_ancestry(self):
        self.assertEqual(process_identity(os.getpid())["pid"], os.getpid())
        self.assertTrue(belongs_to(os.getpid(), os.getpid()))
        self.assertFalse(belongs_to(os.getpid(), -1))

    def test_resident_work_fails_even_with_correct_output(self):
        self.assertFalse(correct({"expected_regex": "42"}, dict(returncode=0, timeout=False,
                               stdout="42", contention_error="External GPU activity detected")))

    def snapshot(self, active_pid, expected_start=20, actual_start=20):
        resident = dict(pid=10, start_ticks=expected_start, boot_id="fixture")
        activity = object.__new__(Activity)
        activity.uuid = "fixture"
        activity.processes = lambda: [dict(pid=10, memory_bytes=3000)]
        activity.samples = lambda since: [dict(pid=active_pid, timestamp_us=100, sm=10, memory=0, encoder=0, decoder=0)]
        with patch("bend_bench.gpu_activity.process_identity", return_value={**resident, "start_ticks": actual_start}):
            return activity.snapshot(resident, 0, benchmark_pid=99)

    def test_resident_activation_and_benchmark_activity_distinguished(self):
        self.assertEqual(self.snapshot(10)["errors"], [])
        self.assertEqual(self.snapshot(99)["errors"], [])
        self.assertIn("Resident process identity changed", self.snapshot(99, actual_start=21)["errors"])

    @unittest.skipUnless(os.environ.get("BEND_BENCH_GPU_TEST") == "1", "Explicit idle-GPU hardware smoke test")
    def test_real_driver_and_monitored_cuda(self):
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "gpu-primitives.toml")
        idle = idle_snapshot(config)
        self.assertEqual(idle["errors"], [])
        self.assertGreater(idle["processes"][0]["memory_bytes"], 0)
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "probe"
            built = execute([config["tools"]["cuda_cxx"], "-O3", "--cuda-path="+config["tools"]["cuda_path"],
                             "--cuda-gpu-arch=sm_86", "-Wno-unknown-cuda-version",
                             root / "tests/gpu_activity_probe.cu", "-L"+config["tools"]["cuda_path"]+"/lib64", "-lcudart", "-o", binary])
            self.assertEqual(built["returncode"], 0, built["stderr"])
            result = execute([binary], gpu_policy=config, timeout=30)
            log = root / "runs/gpu-residency-monitor-smoke.jsonl"
            append(log, result)
            self.assertTrue(correct({"expected_regex": "42"}, result), result)
            observations = result["gpu_activity"]["observations"]
            self.assertTrue(any(s["sm"] > 0 for o in observations for s in o["samples"]), observations)
            # Activity from the pinned resident is allowed and remains recorded.
            sample = next(s for o in observations for s in o["samples"] if s["sm"] > 0)
            activity = object.__new__(Activity)
            activity.uuid = idle["gpu_uuid"]
            resident = dict(pid=sample["pid"], start_ticks=1, boot_id="fixture")
            activity.processes = lambda: [dict(pid=sample["pid"], memory_bytes=1)]
            activity.samples = lambda since: [sample]
            with patch("bend_bench.gpu_activity.process_identity", return_value=resident):
                self.assertEqual(activity.snapshot(resident, 0, benchmark_pid=-1)["errors"], [])
            # Start and finish a real foreign CUDA process entirely inside the
            # measured interval: endpoint-only occupancy checks would miss it.
            foreign = []
            worker = threading.Timer(0.5, lambda: foreign.append(execute([binary], timeout=30)))
            worker.start()
            try:
                overlapped = execute([sys.executable, "-c", "import time; time.sleep(5); print(42)"], gpu_policy=config)
            finally:
                worker.join()
            append(log, overlapped)
            self.assertEqual(foreign[0]["returncode"], 0)
            self.assertIn("Unapproved GPU process", overlapped.get("contention_error", ""))
            self.assertFalse(correct({"expected_regex": "42"}, overlapped))
