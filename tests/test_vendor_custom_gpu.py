"""Custom CUDA adapters preserve the pinned original workload contracts."""
import os
from pathlib import Path
import tempfile
import unittest

from bend_bench.core import append, correct, execute, exclusive, idle_gpu, load_config
from bend_bench.suites import plan, stage

ROOT = Path(__file__).resolve().parents[1]


class VendorCustomGPU(unittest.TestCase):
    def test_plan(self):
        config = load_config(ROOT / "vendor-gpu-custom.toml")
        with tempfile.TemporaryDirectory() as tmp:
            stage(config, Path(tmp))
            builds, cases = plan(config, tmp)
            case = next(c for c in cases if c["implementation"] == "conventional-cuda")
            self.assertEqual(case["workload"], "mandelbrot")
            self.assertEqual(case["check_args"], ["verify"])
            command = next(b for b in builds if any(str(x).endswith("vendor-mandelbrot.cu") for x in b))
            for flag in ("-O3", "-ffp-contract=off", "--cuda-gpu-arch=sm_86"):
                self.assertIn(flag, command)

    @unittest.skipUnless(os.environ.get("BEND_BENCH_VENDOR_GPU_TEST") == "1", "Opt-in real GPU correctness")
    def test_native_queens(self):
        config = load_config(ROOT / "vendor-gpu-custom.toml")
        with exclusive(config):
            idle_gpu(config)
            folder = Path(tempfile.mkdtemp(prefix="vendor-queens-check-", dir=ROOT / "runs"))
            stage(config, folder)
            builds, cases = plan(config, folder)
            case = next(c for c in cases if c["implementation"] == "conventional-cuda" and c["workload"] == "queens")
            command = next(b for b in builds if any(str(x).endswith("vendor-queens.cu") for x in b))
            result = execute(command, timeout=180)
            append(folder / "checks.jsonl", result)
            self.assertEqual(result["returncode"], 0, result["stderr"])
            for size, limit in ((4, 256), (8, 4096), (12, 100), (17, 11730)):
                result = execute([*case["command"], "verify", str(size), str(limit)], timeout=180, gpu_policy=config)
                append(folder / "checks.jsonl", result)
                self.assertEqual(result["returncode"], 0, result["stderr"])
                self.assertNotIn("contention_error", result)
                self.assertIn("FULL_OUTPUT_VERIFIED=", result["stderr"])
                if size == 17:
                    self.assertTrue(correct(case, result), result)

    @unittest.skipUnless(os.environ.get("BEND_BENCH_VENDOR_GPU_TEST") == "1", "Opt-in real GPU correctness")
    def test_native_mandelbrot(self):
        config = load_config(ROOT / "vendor-gpu-custom.toml")
        with exclusive(config):
            idle_gpu(config)
            folder = Path(tempfile.mkdtemp(prefix="vendor-mandelbrot-check-", dir=ROOT / "runs"))
            stage(config, folder)
            builds, cases = plan(config, folder)
            case = next(c for c in cases if c["implementation"] == "conventional-cuda")
            command = next(b for b in builds if any(str(x).endswith("vendor-mandelbrot.cu") for x in b))
            result = execute(command, timeout=180)
            append(folder / "checks.jsonl", result)
            self.assertEqual(result["returncode"], 0, result["stderr"])
            for depth, steps in ((0, 1), (2, 7), (10, 51), (18, 51)):
                result = execute([*case["command"], "verify", str(depth), str(steps)], timeout=180, gpu_policy=config)
                append(folder / "checks.jsonl", result)
                self.assertEqual(result["returncode"], 0, result["stderr"])
                self.assertNotIn("contention_error", result)
                self.assertIn("FULL_OUTPUT_VERIFIED=", result["stderr"])
                if depth == 2:
                    self.assertEqual(result["stdout"].strip(), "887240761")
                if depth == 18:
                    self.assertTrue(correct(case, result), result)
