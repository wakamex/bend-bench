import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from bend_bench.core import environment, exclusive


class TemporaryEnvironment(unittest.TestCase):
    def test_explicit_temp_directory_is_recorded(self):
        with patch.dict(os.environ, {'TMPDIR': '/var/tmp'}):
            self.assertEqual(environment()['TMPDIR'], '/var/tmp')

    def test_temp_directory_does_not_split_shared_lock(self):
        with exclusive({'blocked_services': []}):
            result = subprocess.run([sys.executable, '-c',
                "from bend_bench.core import exclusive\nwith exclusive({'blocked_services': []}): pass"],
                env={**os.environ, 'TMPDIR': '/var/tmp'}, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Another bend-bench process', result.stderr)
