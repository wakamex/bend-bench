"""Custom CUDA adapters preserve the pinned original workload contracts."""
import os
import re
from pathlib import Path
import tempfile
import unittest

from bend_bench.core import append, correct, execute, exclusive, idle_gpu, load_config
from bend_bench.suites import plan, stage

ROOT = Path(__file__).resolve().parents[1]
# Last input is always the full published contract; earlier inputs exercise boundaries.
INPUTS = {
    "mandelbrot": [(0, 1), (2, 7), (10, 51), (18, 51)],
    "queens": [(4, 256), (8, 4096), (12, 100), (17, 11730)],
    "merkle": [(0,), (4,), (12,), (22,)],
    "lexer": [(0,), (6,), (12,), (23,)],
    "kmeans": [(6, 6), (8, 0), (12, 2), (19, 6)],
    "hashmap": [(0, 0), (0, 1), (3, 257), (11, 16384)],
    "bfs": [(0,), (2,), (8,), (19,)],
    "nbody": [(0, 0), (6, 1), (10, 10), (17, 300)],
    "raytrace": [(0, 2), (6, 80), (8, 600), (12, 6000)],
    "terrain": [(0, 0), (0, 1), (4, 5), (16, 5)],
}


class VendorCustomGPU(unittest.TestCase):
    def test_terrain_wavefront_against_serial(self):
        config = load_config(ROOT / "vendor-gpu-custom.toml")
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "terrain-reference"
            build = execute([config["tools"]["cc"], "-std=c11", "-O3",
                             "-I" + config["bend"]["path"] + "/bench/runtime/terrain",
                             ROOT / "tests/vendor_terrain_reference.c", "-o", binary], timeout=180)
            self.assertEqual(build["returncode"], 0, build["stderr"])
            result = execute([binary], timeout=30)
            self.assertEqual(result["returncode"], 0, result["stderr"])

    def test_plan(self):
        config = load_config(ROOT / "vendor-gpu-custom.toml")
        self.assertEqual(set(config["vendor_gpu"]), set(INPUTS))
        with tempfile.TemporaryDirectory() as tmp:
            stage(config, Path(tmp))
            builds, cases = plan(config, tmp)
            for name in ("nbody", "raytrace", "terrain"):
                original = (Path(config["bend"]["path"]) / f"bench/runtime/{name}/main.c").read_text()
                original = re.sub(r"^#include[^\n]*\n", "", original.split("int main(void)")[0], flags=re.M)
                device = (Path(tmp) / f"gpu/vendor-{name}-device.cuh").read_text()
                restored = device.removeprefix("namespace gpu {\n").removesuffix("}\n").replace("__device__ static ", "static ")
                self.assertEqual(restored.replace("__device__ __constant__ const Sph SP[NS]", "static const Sph SP[NS]"), original)
            custom = [c for c in cases if c["implementation"] == "conventional-cuda"]
            self.assertEqual({c["workload"] for c in custom}, set(INPUTS))
            for case in custom:
                self.assertEqual(case["check_args"], ["verify"])
                name = case["workload"]
                command = next(b for b in builds if any(str(x).endswith(f"vendor-{name}.cu") for x in b))
                for flag in ("-O3", "-ffp-contract=off", "--cuda-gpu-arch=sm_86"):
                    self.assertIn(flag, command)

    def build_custom(self, config, folder):
        stage(config, folder)
        builds, cases = plan(config, folder)
        custom = [c for c in cases if c["implementation"] == "conventional-cuda"]
        for case in custom:
            name = case["workload"]
            command = next(b for b in builds if any(str(x).endswith(f"vendor-{name}.cu") for x in b))
            result = execute(command, timeout=180)
            append(folder / "build.jsonl", result)
            self.assertEqual(result["returncode"], 0, result["stderr"])
        return custom

    @unittest.skipUnless(os.environ.get("BEND_BENCH_VENDOR_COMPILE_TEST") == "1", "Opt-in CUDA compile checks without execution")
    def test_compile(self):
        config = load_config(ROOT / "vendor-gpu-custom.toml")
        with exclusive(config):
            folder = Path(tempfile.mkdtemp(prefix="vendor-custom-build-", dir=ROOT / "runs"))
            self.build_custom(config, folder)
            print(folder, flush=True)

    @unittest.skipUnless(os.environ.get("BEND_BENCH_VENDOR_GPU_TEST") == "1", "Opt-in real GPU correctness")
    def test_native(self):
        config = load_config(ROOT / "vendor-gpu-custom.toml")
        with exclusive(config):
            idle_gpu(config)
            folder = Path(tempfile.mkdtemp(prefix="vendor-custom-check-", dir=ROOT / "runs"))
            custom = self.build_custom(config, folder)
            for case in custom:
                name = case["workload"]
                for index, args in enumerate(INPUTS[name]):
                    with self.subTest(workload=name, args=args):
                        idle_gpu(config)
                        result = execute([*case["command"], "verify", *map(str, args)], timeout=180, gpu_policy=config)
                        append(folder / "checks.jsonl", {"workload": name, "input": args, **result})
                        self.assertEqual(result["returncode"], 0, result["stderr"])
                        self.assertNotIn("contention_error", result)
                        self.assertIn("FULL_OUTPUT_VERIFIED=", result["stderr"])
                        if name == "mandelbrot" and args == (2, 7):
                            self.assertEqual(result["stdout"].strip(), "887240761")
                        if name == "raytrace" and args == (6, 80):
                            self.assertEqual(result["stdout"].strip(), "402971")
                        if index == len(INPUTS[name]) - 1:
                            self.assertTrue(correct(case, result), result)
            print(folder, flush=True)
