import json
from pathlib import Path
import tempfile
import unittest

from bend_bench.core import exclusive, execute, load_config
from bend_bench.suites import plan, stage
from mnk_sustained import ROOT, bend_resident, cpp_resident, resident


class SustainedSearchTests(unittest.TestCase):
    def test_cuda_control_has_distinct_compiler_and_binary(self):
        config = load_config(ROOT / 'applications-mnk.toml')
        with tempfile.TemporaryDirectory() as tmp:
            stage(config, Path(tmp))
            builds, cases = plan(config, Path(tmp))
            for game in config['mnk_games']:
                name = 'mnk-' + '-'.join(map(str, game))
                pair = [c for c in cases if c['workload'] == name and c['implementation'].endswith('cuda')]
                self.assertEqual(len(pair), 2)
                self.assertNotEqual(pair[0]['command'][3], pair[1]['command'][3])
                control = next(c for c in pair if c['implementation'] == 'local-alpha-beta-cuda')
                command = next(b for b in builds if '-o' in b and b[b.index('-o') + 1] == control['command'][3])
                self.assertEqual(command[0], config['tools']['cuda_cxx'])
                self.assertTrue(any(arg.endswith('/gpu/mnk.cpp') for arg in command))

    def test_real_resident_cpu_answers(self):
        config = load_config(ROOT / 'applications-mnk.toml')
        config.update(cuda=False, threads=[1, 16], mnk_games=[[5, 5, 4, 8]])
        with exclusive(config), tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            stage(config, work)
            source = work / 'ports/mnk-5-5-4-8.bend'
            source.write_text(bend_resident(source.read_text(), 8, 32))
            cpp = work / 'gpu/mnk.cpp'
            cpp.write_text(cpp_resident(cpp.read_text(), 256, 32))
            builds, cases = plan(config, work)
            for command in builds:
                result = execute(command)
                self.assertEqual(result['returncode'], 0, result['stderr'])
            expected = json.loads(source.with_suffix('.json').read_text())
            for index, case in enumerate(cases):
                folder = work / str(index)
                folder.mkdir()
                result = resident(case['command'], folder, config, expected, 256, False, 32)
                self.assertTrue(result['correct'])
                self.assertEqual(len(result['batches']), 32)
                self.assertAlmostEqual(result['batches'][-1]['cumulative_measured_positions_per_second'],
                                       30 * 256 / sum(b['seconds'] for b in result['batches'][2:]))
                self.assertAlmostEqual(result['positions_per_second_including_startup'],
                                       32 * 256 / result['process_seconds'])

    def test_wrong_answers_are_retained_and_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, 'correctness'):
                resident(['/usr/bin/printf', 'READY\n99\nEND\n'], folder, {}, [0] * 16, 16, False)
            self.assertFalse(json.loads((folder / 'result.json').read_text())['correct'])
            self.assertIn('99', (folder / 'stdout.txt').read_text())
