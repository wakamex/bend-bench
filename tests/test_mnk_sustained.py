import json
from pathlib import Path
import tempfile
import unittest

from bend_bench.core import exclusive, execute, load_config
from bend_bench.suites import plan, stage
from mnk_sustained import ROOT, bend_resident, cpp_resident, resident


class SustainedSearchTests(unittest.TestCase):
    def test_real_resident_cpu_answers(self):
        config = load_config(ROOT / 'applications-mnk.toml')
        config.update(cuda=False, threads=[1, 16], mnk_games=[[5, 5, 4, 8]])
        with exclusive(config), tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            stage(config, work)
            source = work / 'ports/mnk-5-5-4-8.bend'
            source.write_text(bend_resident(source.read_text(), 8))
            cpp = work / 'gpu/mnk.cpp'
            cpp.write_text(cpp_resident(cpp.read_text(), 256))
            builds, cases = plan(config, work)
            for command in builds:
                result = execute(command)
                self.assertEqual(result['returncode'], 0, result['stderr'])
            expected = json.loads(source.with_suffix('.json').read_text())
            for index, case in enumerate(cases):
                folder = work / str(index)
                folder.mkdir()
                result = resident(case['command'], folder, config, expected, 256, False)
                self.assertTrue(result['correct'])
                self.assertEqual(len(result['batches']), 12)

    def test_wrong_answers_are_retained_and_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, 'correctness'):
                resident(['/usr/bin/printf', 'READY\n99\nEND\n'], folder, {}, [0] * 16, 16, False)
            self.assertFalse(json.loads((folder / 'result.json').read_text())['correct'])
            self.assertIn('99', (folder / 'stdout.txt').read_text())
