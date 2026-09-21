import copy
from pathlib import Path
import tempfile
import unittest

from bend_bench.core import load_config
from bend_bench.suites import plan, stage
from validate_vendor_cuda import check_history, select_cases

ROOT = Path(__file__).resolve().parents[1]


class VendorCudaQueue(unittest.TestCase):
    def test_real_plan_selects_only_eleven_new_cases(self):
        config = load_config(ROOT / "vendor-gpu-custom.toml")
        with tempfile.TemporaryDirectory() as tmp:
            stage(config, Path(tmp))
            _, cases = plan(config, tmp)
            selected = select_cases(config, cases)
            self.assertEqual(len(selected), 11)
            self.assertTrue(all(c["implementation"] == "conventional-cuda" for c in selected))
            with self.assertRaises(ValueError):
                select_cases(config, selected[:-1])
            with self.assertRaises(ValueError):
                select_cases(config, selected + selected[:1])
            unsupported = copy.deepcopy(selected)
            unsupported[0]["unsupported"] = "missing tool"
            with self.assertRaises(ValueError):
                select_cases(config, unsupported)

    def test_resume_keeps_passed_rows_and_rejects_failed_or_mixed_rows(self):
        row = dict(fingerprint="one", case="example", phase="measure", rep=0, correct=True)
        self.assertEqual(check_history([row], "one"), {("example", "measure", 0)})
        for history in ([row, row], [{**row, "correct": False}], [{**row, "fingerprint": "two"}]):
            with self.subTest(history=history), self.assertRaises(ValueError):
                check_history(history, "one")
