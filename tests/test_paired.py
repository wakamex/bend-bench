import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import argparse
import json

from bend_bench.cli import paired_base
from bend_bench.paired import block_ratio, flagged, program, render, score

SOURCE = """%s
static const char SRC[] = "%s";
int main(int argc, char **argv) { return (argc %s 3) + SRC[argc]; }
"""


class PairedScoring(unittest.TestCase):
    def test_linear_drift_cancels_in_an_abba_block(self):
        # Base 2 s, candidate 1 s, with the host slowing 5% a slot through the block.
        drift = [1 + 0.05 * slot for slot in range(4)]
        abba = {'A': [2 * drift[0], 2 * drift[3]], 'B': [1 * drift[1], 1 * drift[2]]}
        baab = {'B': [1 * drift[0], 1 * drift[3]], 'A': [2 * drift[1], 2 * drift[2]]}
        self.assertAlmostEqual(block_ratio(abba), 2, places=12)
        self.assertAlmostEqual(block_ratio(baab), 2, places=12)
        # Simple alternation (A B) would read the drift as part of the speedup.
        self.assertGreater(abs(2 * drift[0] / (1 * drift[1]) - 2), 0.09)

    def test_verdicts_follow_the_interval(self):
        self.assertEqual(score([1.8, 1.85, 1.86, 1.81, 1.84, 1.83])['verdict'], 'faster')
        self.assertEqual(score([0.9, 0.92, 0.91, 0.93])['verdict'], 'slower')
        flat = score([0.99, 1.01, 1.0, 0.98, 1.02, 1.0])
        self.assertEqual(flat['verdict'], 'no detected change')
        self.assertLessEqual(flat['low'], flat['median'])
        self.assertLessEqual(flat['median'], flat['high'])

    def test_bad_blocks_are_rejected(self):
        with self.assertRaises(ValueError):
            block_ratio({'A': [1.0], 'B': [1.0, 1.0]})
        with self.assertRaises(ValueError):
            block_ratio({'A': [1.0, 0.0], 'B': [1.0, 1.0]})
        with self.assertRaises(ValueError):
            score([])

    def test_report_lists_untimed_identical_workloads(self):
        summary = dict(same_program=['gpu-regression/bfs/bend-cuda/32'],
                       results=[dict(case='gpu-regression/raytrace/bend-cuda/16', blocks=8, median=1.84, low=1.81,
                                     high=1.86, verdict='faster', ratios=[])])
        text = render(summary, {'A': 'base', 'B': 'cand'})
        self.assertIn('| gpu-regression/raytrace/bend-cuda/16 | 8 | 1.840x | 1.810x to 1.860x | faster |', text)
        self.assertIn('Not timed, the same compiled program on both sides (1): gpu-regression/bfs/bend-cuda/32.', text)

    def test_report_lists_failed_workloads(self):
        summary = dict(same_program=[], results=[], failed=[dict(case='gpu-regression/uts-compact/bend-cuda/16',
                                                                  reason='base gave a wrong result in check', sides=['A'], blocks=0)])
        self.assertIn('- gpu-regression/uts-compact/bend-cuda/16: base gave a wrong result in check', render(summary, {'A': 'a', 'B': 'b'}))

    def test_flags_need_a_candidate_only_failure_or_a_slowdown_past_the_threshold(self):
        result = lambda median, verdict: dict(case='c', median=median, verdict=verdict)
        fails = lambda *sides: dict(same_program=[], results=[], failed=[dict(case='c', reason='r', sides=list(sides), blocks=0)])
        self.assertTrue(flagged(fails('B'), 10))
        self.assertFalse(flagged(fails('A'), 10))
        self.assertFalse(flagged(fails('A', 'B'), 10))
        slow = lambda median, verdict: dict(same_program=[], failed=[], results=[result(median, verdict)])
        self.assertFalse(flagged(slow(0.996, 'slower'), 10))
        self.assertTrue(flagged(slow(0.85, 'slower'), 10))
        self.assertFalse(flagged(slow(0.85, 'no detected change'), 10))
        self.assertTrue(flagged(slow(0.996, 'slower'), 0))


class FastBaseline(unittest.TestCase):
    def args(self, baseline, blocks=3, build=None, resume=None):
        return argparse.Namespace(baseline=baseline, blocks=blocks, build=build, resume=resume)

    def test_a_baseline_run_directory_is_timed_alongside_the_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / 'provenance.json').write_text(json.dumps(dict(config=dict(
                _run_id='x', bend=dict(path='/base', commit='0' * 40), output='/old', suites=['cpu-regression']))))
            base = paired_base(self.args(run), dict(output='/new'))
            self.assertEqual(base, dict(bend=dict(path='/base', commit='0' * 40), output='/new', suites=['cpu-regression']))
            for args in (self.args(run, blocks=0), self.args(run, build=run), self.args(run, resume=run)):
                self.assertIsNone(paired_base(args, dict(output='/new')))
            with self.assertRaises(ValueError):
                paired_base(self.args(run, blocks=1), dict(output='/new'))

    def test_saved_results_and_missing_baselines_compare_against_saved_times(self):
        with tempfile.TemporaryDirectory() as tmp:
            saved = Path(tmp) / 'regression.json'
            saved.write_text('{}')
            self.assertIsNone(paired_base(self.args(saved), dict(output='/new')))
            self.assertIsNone(paired_base(self.args(None), dict(output='/new')))


@unittest.skipUnless(shutil.which('cc') and shutil.which('objdump'), 'needs cc and objdump')
class SameProgram(unittest.TestCase):
    def build(self, folder, name, define, text, op):
        binary = folder / 'work/build' / name
        binary.parent.mkdir(parents=True, exist_ok=True)
        source = folder / (name + '.c')
        source.write_text(SOURCE % (define, text, op))
        subprocess.run(['cc', '-O2', '-o', binary, source], check=True)
        return {'command': ['taskset', '-c', '0', str(binary), '--threads', '1']}

    def test_an_unused_define_compiles_to_the_same_program(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp, 'a'), Path(tmp, 'b')
            base = self.build(a, 'w', '', 'source', '*')
            same = self.build(b, 'w', '#define SHARE FAR', 'source with two more lines', '*')
            self.assertIsNotNone(program(base))
            self.assertEqual(program(base), program(same))
            changed = self.build(Path(tmp, 'c'), 'w', '', 'source', '+')
            self.assertNotEqual(program(base), program(changed))


if __name__ == '__main__':
    unittest.main()
