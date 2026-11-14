import subprocess
import unittest
from pathlib import Path

from bend_bench.metal import parse, render, summarize

ROOT = Path(__file__).resolve().parents[1]

# Lines from a Mac mini M4 run of an earlier version of metal/compare.sh, which labelled the
# sides main and pr, including the update notice Bun printed between build lines. The FAIL for
# offload_bang_g and the probe build failure are added to cover those paths.
LOG = """== bang tests
PASS main f32_from_nat_wide
BUILDFAIL main offload_bang_g
PASS pr f32_from_nat_wide
PASS pr bang_lane_spill
FAIL pr offload_bang_g
== programs
prog deep_1m main .0690 bend: memory fault (machine stack overflow?)
prog deep_1m pr .7697 257066912
BUILDFAIL main split_append_100k
prog split_append_100k pr .1860 100000
== build
build queens main 1 .7033 .1471
bend 2.0.40 is available: run bend update
build queens pr 1 .7100 .1474
build queens pr 2 .7106 .1482
build queens main 2 .7054 .1458
== runtime
same-output queens
run 1 queens main 2.8035
run 1 queens pr 2.4395
run 1 queens pr 2.5209
run 1 queens main 2.7941
run 2 queens pr 2.3172
run 2 queens main 2.4208
run 2 queens main 2.5944
run 2 queens pr 2.1995
DONE
"""


class MetalReport(unittest.TestCase):
    def test_the_first_side_named_is_the_base(self):
        log = parse(LOG)
        self.assertEqual(log['sides'], ['main', 'pr'])
        self.assertEqual(parse(LOG.replace('main', 'base').replace(' pr', ' candidate'))['sides'], ['base', 'candidate'])

    def test_sections_route_build_failures(self):
        log = parse(LOG)
        self.assertEqual(log['tests']['offload_bang_g'], {'main': 'BUILDFAIL', 'pr': 'FAIL'})
        self.assertEqual(log['probes']['split_append_100k']['main'], 'build failed')
        self.assertEqual(log['probes']['deep_1m']['pr'], (0.7697, '257066912'))

    def test_runtime_blocks_score_base_over_candidate(self):
        result, = summarize(parse(LOG))['results']
        abba = (2.8035 + 2.7941) / (2.4395 + 2.5209)
        baab = (2.4208 + 2.5944) / (2.3172 + 2.1995)
        self.assertAlmostEqual(result['median'], (abba + baab) / 2)
        self.assertEqual(result['blocks'], 2)
        self.assertEqual(result['verdict'], 'faster')

    def test_build_medians_per_side(self):
        build, = summarize(parse(LOG))['builds']
        self.assertEqual(build['runs'], 2)
        self.assertAlmostEqual(build['compile'][0], (0.7033 + 0.7054) / 2)
        self.assertAlmostEqual(build['gpu_build'][1], (0.1474 + 0.1482) / 2)

    def test_report_lists_status_changes(self):
        text = render(parse(LOG))
        self.assertIn('| bang_lane_spill | absent | PASS |', text)
        self.assertIn('| offload_bang_g | BUILDFAIL | FAIL |', text)
        self.assertNotIn('f32_from_nat_wide |', text)
        self.assertIn('identical on both sides for all 1 programs', text)

    def test_a_third_side_is_rejected(self):
        with self.assertRaises(ValueError):
            parse(LOG + 'PASS other f32_from_nat_wide\n')

    def test_script_parses_and_requires_two_checkouts(self):
        script = ROOT / 'metal/compare.sh'
        self.assertEqual(subprocess.run(['bash', '-n', script]).returncode, 0)
        self.assertEqual(subprocess.run(['bash', script], capture_output=True).returncode, 2)
        self.assertTrue(sorted((ROOT / 'metal/probes').glob('*.bend')))


if __name__ == '__main__':
    unittest.main()
