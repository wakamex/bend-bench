import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from bend_bench.paired import block_ratio, program, render, score

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
