import unittest

from pricing_single_cpu import single_thread, archived_cases, ROOT


class SingleThreadPricingTests(unittest.TestCase):
    def test_archived_commands_and_hashes(self):
        source = ROOT / 'runs/pricing-sustained-20260918-165158/262144'
        if not source.exists():
            self.skipTest('Local archived pricing evidence unavailable')
        cases = archived_cases(source)
        self.assertEqual({c['implementation'] for c in cases}, {'bend', 'local-openmp'})
        for case in cases:
            self.assertEqual(case['command'][2], '0')
            self.assertEqual(case['env']['OMP_NUM_THREADS'], '1')
            self.assertEqual(case['threads'], 1)
            self.assertTrue(case['id'].endswith('/1'))
            if case['implementation'] == 'bend':
                self.assertEqual(case['command'][-2:], ['--threads', '1'])

    def test_does_not_mutate_original(self):
        case = dict(command=['taskset', '-c', '0,1', 'binary', '--threads', '16'],
                    implementation='bend', env={'OMP_NUM_THREADS': '16'}, threads=16, id='pricing/bend/16')
        single_thread(case)
        self.assertEqual(case['command'][2], '0,1')
        self.assertEqual(case['command'][-1], '16')
        self.assertEqual(case['env']['OMP_NUM_THREADS'], '16')
