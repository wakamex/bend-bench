import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bend_bench.regression import comparison, load_result, render, validate_result

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'benchmarks/uts-compact-20260922/summary.json'


class RegressionReport(unittest.TestCase):
    def setUp(self):
        if not ARCHIVE.exists():
            self.skipTest('Archived native UTS evidence unavailable')
        self.before = load_result(ARCHIVE)

    def test_real_result_roundtrip_and_self_comparison(self):
        with self.assertRaisesRegex(ValueError, 'with itself'):
            comparison(self.before, self.before)
        candidate = {**self.before, 'fingerprint': 'independent-test-run'}
        compared = comparison(self.before, candidate)
        self.assertEqual(compared['overall']['geometric_mean'], 1)
        self.assertEqual(compared['overall']['matched'], 1)
        self.assertFalse(compared['concerns'])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'comparison.json'
            path.write_text(json.dumps(compared))
            self.assertEqual(load_result(path), candidate)
            command = [sys.executable, '-m', 'bend_bench', 'gpu-report', str(path), '--baseline', str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('with itself', result.stderr)

    def test_regression_range_and_threshold(self):
        after = copy.deepcopy(self.before)
        after['fingerprint'] = 'independent-test-run'
        after['cases'][0]['seconds'] *= 1.2
        compared = comparison(self.before, after)
        self.assertEqual(compared['overall']['regressions'], 1)
        self.assertAlmostEqual(compared['overall']['geometric_mean'], 1/1.2)
        self.assertIn('20.0% longer', render(after, compared))
        self.assertFalse(comparison(self.before, after, 25)['concerns'])
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'before.json', Path(tmp)/'after.json'
            a.write_text(json.dumps(self.before)); b.write_text(json.dumps(after))
            command = [sys.executable, '-m', 'bend_bench', 'gpu-report', str(b), '--baseline', str(a)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn('REGRESSION', result.stdout)
            result = subprocess.run(command + ['--threshold', 'nan'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)

    def test_real_interrupted_run_is_incomplete(self):
        run = ROOT/'runs/672916fc95e4c1fefa0e'
        if not run.exists():
            self.skipTest('Interrupted fast-profile evidence unavailable')
        result = load_result(run)
        self.assertEqual(len(result['cases']), 22)
        self.assertIn('Unapproved GPU process', render(result))
        self.assertTrue(comparison(result, {**result, 'fingerprint': 'independent-test-run'})['concerns'])

    def test_reciprocal_ratios_balance(self):
        before, after = copy.deepcopy(self.before), copy.deepcopy(self.before)
        after['fingerprint'] = 'independent-test-run'
        for obj in (before, after):
            other = copy.deepcopy(obj['cases'][0]); other['case'] += '-other'; obj['cases'].append(other)
        after['cases'][0]['seconds'] *= 2
        after['cases'][1]['seconds'] /= 2
        overall = comparison(before, after)['overall']
        self.assertEqual(overall['geometric_mean'], 1)
        self.assertEqual((overall['minimum'], overall['maximum']), (.5, 2))

    def test_removed_failed_and_changed_cases_are_not_silent(self):
        after = copy.deepcopy(self.before)
        after['fingerprint'] = 'independent-test-run'
        after['cases'][0].update(status='failed', seconds=None, samples=0, checked=False)
        c = comparison(self.before, after)
        self.assertTrue(c['concerns'])
        self.assertEqual(c['overall']['matched'], 0)
        self.assertIn('candidate failed', render(after, c))
        after = copy.deepcopy(self.before)
        after['fingerprint'] = 'independent-test-run'
        after['cases'][0]['case'] += '-renamed'
        c = comparison(self.before, after)
        self.assertEqual(c['overall']['uncomparable'], 2)
        after = copy.deepcopy(self.before)
        after['fingerprint'] = 'independent-test-run'
        after['compatibility']['toolkit'] = 'changed'
        self.assertIn('changed toolkit', render(after, comparison(self.before, after)))
        after = copy.deepcopy(self.before)
        after['fingerprint'] = 'independent-test-run'
        after['cases'][0]['contract_sha256'] = 'changed'
        self.assertEqual(comparison(self.before, after)['overall']['matched'], 0)

    def test_rejects_invalid_evidence(self):
        for value in (0, -1, float('nan'), float('inf')):
            after = copy.deepcopy(self.before)
            after['fingerprint'] = 'independent-test-run'
            after['cases'][0]['seconds'] = value
            with self.assertRaises(ValueError):
                validate_result(after)
        after = copy.deepcopy(self.before)
        after['fingerprint'] = 'independent-test-run'
        after['cases'][0]['samples'] = 1
        with self.assertRaises(ValueError):
            validate_result(after)
        for threshold in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                comparison(self.before, self.before, threshold)

    def test_environment_warns_but_keeps_raw_ratios(self):
        after = copy.deepcopy(self.before)
        after['fingerprint'] = 'independent-test-run'
        after['compatibility']['environment'] = 'changed'
        after['cases'][0]['seconds'] *= 2
        compared = comparison(self.before, after)
        self.assertEqual(compared['overall']['geometric_mean'], .5)
        self.assertEqual(compared['overall']['matched'], 1)
        self.assertTrue(compared['warnings'])
        self.assertTrue(compared['concerns'])
        self.assertIn('not an isolated compiler effect', render(after, compared))
        after['cases'][0].update(status='failed', seconds=None)
        self.assertIsNone(comparison(self.before, after)['overall']['geometric_mean'])
        after = copy.deepcopy(self.before)
        after['fingerprint'] = 'independent-test-run'
        after['compatibility']['policy'] = 'changed'
        self.assertEqual(comparison(self.before, after)['overall']['matched'], 0)


class BuildTimes(unittest.TestCase):
    # Paired fast-gpu-v2 runs of Bend 68f870e3 (base) and the inline-rule branch (candidate).
    BASE, CANDIDATE = ROOT/'runs/d2f1555388c8d2e53740', ROOT/'runs/75f2699766cffa3c7e1b'

    def setUp(self):
        if not (self.BASE/'prepare.jsonl').exists() or not (self.CANDIDATE/'prepare.jsonl').exists():
            self.skipTest('Archived fast GPU preparation logs unavailable')
        from bend_bench.regression import build_times
        self.before, self.after = build_times(self.BASE), build_times(self.CANDIDATE)

    def test_real_logs_give_each_bend_programs_steps(self):
        self.assertEqual(len(self.before), 22)
        self.assertEqual(set(self.before['raytrace']), {'emit', 'CUDA clang', 'NVRTC'})
        self.assertNotIn('hotspot-reference', self.before)

    def test_only_slowdowns_past_threshold_and_floor_are_flagged(self):
        from bend_bench.regression import BUILD_FLOOR, build_section
        lines, slow = build_section(self.after, self.before)
        self.assertFalse(slow)
        self.assertIn('Total over 66 matched build steps', '\n'.join(lines))
        after = copy.deepcopy(self.after)
        after['raytrace']['NVRTC'] = self.before['raytrace']['NVRTC'] + BUILD_FLOOR + 1
        after['bfs']['emit'] = self.before['bfs']['emit'] * 3  # far past 10%, but well under a second
        lines, slow = build_section(after, self.before)
        self.assertTrue(slow)
        text = '\n'.join(lines)
        self.assertIn('| raytrace | NVRTC |', text)
        self.assertNotIn('| bfs |', text)

    def test_stress_programs_new_to_the_candidate_are_listed(self):
        from bend_bench.regression import build_section
        after = {**self.after, 'stress-flatmany': dict(self.after['raytrace'])}
        lines, slow = build_section(after, self.before)
        self.assertFalse(slow)
        self.assertIn('| stress-flatmany | NVRTC | - |', '\n'.join(lines))

    def test_stress_programs_are_listed_without_a_baseline(self):
        from bend_bench.regression import build_section
        after = {**self.after, 'stress-flatchain': dict(self.after['raytrace'])}
        lines, slow = build_section(after)
        self.assertFalse(slow)
        self.assertIn('| stress-flatchain | NVRTC |', '\n'.join(lines))
        self.assertNotIn('| raytrace |', '\n'.join(lines))
