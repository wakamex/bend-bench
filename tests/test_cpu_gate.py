import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bend_bench import core
from bend_bench.core import busy_cpus, load_config, quiet_cpus


class CpuGate(unittest.TestCase):
    def test_a_spinning_process_counts_as_one_busy_cpu(self):
        cpu = sorted(os.sched_getaffinity(0))[-1]
        idle = busy_cpus({cpu}, 1)
        spin = subprocess.Popen(["taskset", "-c", str(cpu), sys.executable, "-c", "while True: pass"])
        try:
            busy = busy_cpus({cpu}, 1)
        finally:
            spin.kill()
            spin.wait()
        self.assertGreater(busy, 0.9)
        self.assertLessEqual(busy, 1.0)
        self.assertLess(idle, busy)

    def test_waits_for_quiet_cpus_then_reports_the_wait(self):
        config = dict(cpus=[0, 1], cpu_idle=dict(max_busy=1.0, max_wait=60))
        clock = iter([0, 5, 10])
        with mock.patch.object(core, "busy_cpus", side_effect=[1.8, 0.4]), mock.patch.object(core.time, "monotonic", lambda: next(clock)):
            self.assertEqual(quiet_cpus(config), dict(busy_cpus=0.4, waited_seconds=10))

    def test_gives_up_after_max_wait(self):
        config = dict(cpus=[0, 1], cpu_idle=dict(max_busy=1.0, max_wait=10))
        clock = iter([0, 5, 10])
        with mock.patch.object(core, "busy_cpus", return_value=1.8), mock.patch.object(core.time, "monotonic", lambda: next(clock)):
            with self.assertRaisesRegex(ValueError, "stayed busy for 10 s"):
                quiet_cpus(config)

    def test_without_the_gate_nothing_is_measured(self):
        with mock.patch.object(core, "busy_cpus") as busy:
            self.assertIsNone(quiet_cpus(dict(cpus=[0])))
            busy.assert_not_called()

    def test_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.toml"
            base = 'schema = 1\nsuites = ["vendor"]\n[bend]\npath = "."\ncommit = "' + "0" * 40 + '"\n'
            for gate in ("{max_busy = 0, max_wait = 60}", "{max_busy = 2.5}", "{max_busy = 2.5, max_wait = 1}", "3"):
                path.write_text("cpu_idle = " + gate + "\n" + base)
                with self.assertRaisesRegex(ValueError, "cpu_idle"):
                    load_config(path)


if __name__ == "__main__":
    unittest.main()
