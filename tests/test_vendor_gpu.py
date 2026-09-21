"""Library adapters checked against pinned published workload contracts."""
import os
from pathlib import Path
import tempfile
import unittest

from bend_bench.core import append, correct, execute, exclusive, idle_gpu, load_config
from bend_bench.suites import plan, stage

ROOT = Path(__file__).resolve().parents[1]


class VendorGPU(unittest.TestCase):
    def test_plan(self):
        config = load_config(ROOT / "vendor-gpu-libraries.toml")
        with tempfile.TemporaryDirectory() as tmp:
            stage(config, Path(tmp))
            builds, cases = plan(config, tmp)
            case = next(c for c in cases if c["implementation"] == "cub-cuda")
            self.assertEqual(case["workload"], "tree-radix")
            self.assertEqual(case["check_args"], ["verify"])
            command = next(b for b in builds if any(str(x).endswith("vendor-radix.cu") for x in b))
            self.assertIn("-O3", command)
            self.assertIn("--cuda-gpu-arch=sm_86", command)

    def test_config_rejects_invalid_selection(self):
        original = (ROOT / "vendor-gpu-libraries.toml").read_text()
        for value in ('["unknown"]', '["tree-radix", "tree-radix"]'):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".toml") as f:
                f.write(original.replace('vendor_gpu = ["tree-radix"]', f'vendor_gpu = {value}'))
                f.flush()
                with self.assertRaises(ValueError):
                    load_config(f.name)

    @unittest.skipUnless(os.environ.get("BEND_BENCH_VENDOR_GPU_TEST") == "1", "Opt-in real GPU correctness")
    def test_native(self):
        config = load_config(ROOT / "vendor-gpu-libraries.toml")
        with exclusive(config):
            idle_gpu(config)
            folder = Path(tempfile.mkdtemp(prefix="vendor-gpu-check-", dir=ROOT / "runs"))
            stage(config, folder)
            builds, cases = plan(config, folder)
            case = next(c for c in cases if c["implementation"] == "cub-cuda")
            command = next(b for b in builds if any(str(x).endswith("vendor-radix.cu") for x in b))
            result = execute(command, timeout=180)
            append(folder / "checks.jsonl", result)
            self.assertEqual(result["returncode"], 0, result["stderr"])
            for depth in (0, 6, 12, 22):
                result = execute([*case["command"], "verify", str(depth)], timeout=180, gpu_policy=config)
                append(folder / "checks.jsonl", result)
                self.assertEqual(result["returncode"], 0, result["stderr"])
                self.assertNotIn("contention_error", result)
                self.assertIn("FULL_OUTPUT_VERIFIED=", result["stderr"])
                if depth == 22:
                    self.assertTrue(correct(case, result), result)
