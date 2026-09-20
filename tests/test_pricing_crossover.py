import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pricing_crossover', ROOT / 'pricing_crossover.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PricingCrossover(unittest.TestCase):
    def watch(self, code, limit=0.5):
        return subprocess.run([sys.executable, str(ROOT / 'pricing_crossover.py'), '--watchdog', str(limit),
                               sys.executable, '-u', '-c', code], capture_output=True, text=True, timeout=10)

    def test_watchdog_forwarding(self):
        result = self.watch('print("READY");print("RESULT 1 2 3")')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'READY\nRESULT 1 2 3\n')

    def test_watchdog_stops_stalled_quote(self):
        result = self.watch('import time;print("READY");time.sleep(5)', 0.05)
        self.assertEqual(result.returncode, 124)
        self.assertIn('PRICING_REQUEST_LIMIT_EXCEEDED', result.stderr)

    def test_watchdog_resets_after_each_quote(self):
        result = self.watch('import time;print("READY");\nfor i in range(6):\n time.sleep(0.1);print("RESULT 1 2 3")', 0.4)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('RESULT'), 6)

    def test_watchdog_preserves_failure(self):
        result = self.watch('raise SystemExit(7)')
        self.assertEqual(result.returncode, 7)

    def test_watchdog_records_real_child_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'identity'
            result = subprocess.run([sys.executable, str(ROOT / 'pricing_crossover.py'), '--watchdog', '1',
                                     sys.executable, '-u', '-c', 'print("READY")'],
                                    env={**module.os.environ, 'BEND_BENCH_PID_FILE': str(path)},
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            stat = path.read_text().strip()
            self.assertGreater(int(stat.split(' ', 1)[0]), 0)
            self.assertGreater(int(stat.rsplit(') ', 1)[1].split()[19]), 0)
