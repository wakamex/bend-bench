from pathlib import Path
import tempfile
import struct
import unittest

from bend_bench.core import correct, execute, load_config
from bend_bench.suites import plan, stage
from bend_bench.profiling import kernel_totals


class GPUContracts(unittest.TestCase):
    def test_real_nsight_export(self):
        database = Path("/code/bend2/results/profiles/editdist-bend-0.sqlite")
        if not database.exists():
            self.skipTest("Archived Nsight export unavailable")
        totals = kernel_totals(database)
        self.assertGreater(totals["kernel_seconds"], 0)
        self.assertGreater(totals["kernel_launches"], 0)

    def test_float_vector_validation(self):
        bits = lambda x: str(struct.unpack("I", struct.pack("f", x))[0])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "expected.bits"
            path.write_text("\n".join([bits(80.0)]*4))
            case = dict(expected_bits=str(path), contract={"size": 2})
            result = dict(returncode=0, timeout=False, stdout=path.read_text())
            self.assertTrue(correct(case, result))
            self.assertFalse(correct(case, {**result, "stdout": bits(80.0)}))
            self.assertFalse(correct(case, {**result, "stdout": "\n".join([bits(81.0)]*4)}))
            self.assertFalse(correct(case, {**result, "stdout": "\n".join([bits(float('nan'))]*4)}))

    def test_real_pinned_sources_and_reference(self):
        config_file = Path(__file__).resolve().parents[1] / "gpu-primitives.toml"
        if not Path("/code/bend2/upstream").exists():
            self.skipTest("Archived evaluation sources unavailable")
        config = load_config(config_file)
        self.assertTrue(config["tools"]["cuda_cxx"].endswith("clang++"))
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            stage(config, work)
            builds, cases = plan(config, work)
            self.assertEqual(len(cases), 18)
            result = execute(builds[0])
            self.assertEqual(result["returncode"], 0, result["stderr"])
            for case in cases:
                if case["implementation"] == "serial-cpp":
                    result = execute(case["command"])
                    self.assertEqual(result["stdout"].strip(), case["expected_regex"])
                if case["implementation"] == "cub-cuda":
                    self.assertEqual(case["check_args"], ["verify"])
            self.assertIn("bsort!(12n,", (work / "ports/cub-sort-12.bend").read_text())
            self.assertIn("sum!(23n,", (work / "ports/cub-reduce-23.bend").read_text())
