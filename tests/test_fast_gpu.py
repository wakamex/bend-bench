import copy
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

from bend_bench.core import correct, load_config
from bend_bench.fast import ASSETS
from bend_bench.suites import plan, stage

ROOT = Path(__file__).resolve().parents[1]


class FastGPU(unittest.TestCase):
    def setUp(self):
        self.config = load_config(ROOT / 'fast-gpu.toml')

    def test_default_repetitions(self):
        self.assertEqual(self.config['repetitions'], 1)
        self.assertEqual(self.config['warmups'], 1)

    def test_idle_wait_is_opt_in(self):
        from unittest.mock import patch
        from bend_bench.cli import main
        for flags, expected in [([], False), (['--wait-idle'], True)]:
            with patch('bend_bench.fast.run', return_value=(ROOT, False)) as run:
                self.assertEqual(main(['gpu', 'fast', str(ROOT/'fast-gpu.toml'), *flags]), 0)
                self.assertEqual(run.call_args.kwargs['wait_for_idle'], expected)

    def test_runner_only_waits_when_requested(self):
        from unittest.mock import patch
        from bend_bench.fast import run
        for requested in (False, True):
            with tempfile.TemporaryDirectory() as tmp, \
                 patch('bend_bench.fast.provenance', return_value={}), \
                 patch('bend_bench.experiment.directory', return_value=Path(tmp)), \
                 patch('bend_bench.fast.wait_gpu') as wait, \
                 patch('bend_bench.fast.idle_gpu') as check, \
                 patch('bend_bench.experiment.prepare', side_effect=ValueError('stop before builds')):
                with self.assertRaisesRegex(ValueError, 'stop before builds'):
                    run(self.config, wait_for_idle=requested)
                self.assertEqual(wait.call_count, int(requested))
                self.assertEqual(check.call_count, int(not requested))

    def test_gpu_conflict_fails_before_provenance_and_builds(self):
        from unittest.mock import patch
        from bend_bench.fast import run
        with patch('bend_bench.fast.idle_gpu', side_effect=ValueError('Unapproved GPU process 42')), \
             patch('bend_bench.fast.provenance') as provenance, \
             patch('bend_bench.experiment.prepare') as prepare:
            with self.assertRaisesRegex(ValueError, 'Unapproved GPU process 42'):
                run(self.config)
            provenance.assert_not_called()
            prepare.assert_not_called()

    def test_cli_entrypoint(self):
        result = subprocess.run([sys.executable, '-m', 'bend_bench', 'fast-gpu', '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--plan', result.stdout)

    def test_shared_runner_preserves_gpu_contracts(self):
        archived = ROOT/'runs/672916fc95e4c1fefa0e/plan.json'
        if not archived.exists():
            self.skipTest('Original fast GPU plan unavailable')
        _, cases = plan(self.config, ROOT/'runs/fast-plan-only')
        before = {c['id']: c['contract'] for c in json.loads(archived.read_text())['cases']}
        self.assertEqual(before, {c['id']: c['contract'] for c in cases})

    def test_plan_is_gpu_only_and_fixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            builds, cases = plan(self.config, work)
            self.assertEqual(len(cases), 22)
            self.assertEqual(len(builds), 66)
            self.assertTrue(all(c['implementation'] == 'bend-cuda' for c in cases))
            self.assertTrue(all(c['contract']['profile'] == 'fast-gpu-v1' for c in cases))
            self.assertTrue(all(c['threads'] in (16, 32) for c in cases))
            self.assertTrue(all('--gpu-build' in b or '-DBEND_CUDA=1' in b or b[0] == self.config['tools']['bun'] for b in builds))
            stage(self.config, work)
            self.assertIn('repeat(1n)', (work/'ports/game-search.bend').read_text())
            self.assertNotIn('@RODINIA@', (work/'ports/hotspot.bend').read_text())
            self.assertEqual(len((work/'ports/hotspot.expected').read_text().split()), 1024**2)
            self.assertEqual(len(json.loads((work/'ports/bfs-shared.expected').read_text())), 262144)

    def test_real_saved_pricing_and_game_answers(self):
        pricing = ROOT/'runs/pricing-sustained-20260918-165158/262144/bend-cuda-0/result.json'
        game = ROOT/'runs/mnk-sustained-20260918-160439/corpus-1024-524288-batches-30/bend-cuda-16-run0/stdout.txt'
        if not pricing.exists() or not game.exists():
            self.skipTest('Archived native outputs unavailable')
        _, cases = plan(self.config, ROOT/'runs/fast-plan-only')
        case = next(c for c in cases if c['workload'] == 'pricing')
        result = json.loads(pricing.read_text())
        self.assertTrue(correct(case, result))
        bad = copy.deepcopy(result)
        bad['stdout'] = bad['stdout'].replace('RESULT', 'BROKEN', 1)
        self.assertFalse(correct(case, bad))
        case = next(c for c in cases if c['workload'] == 'game-search')
        # The single-request fixture executes p=0, the last archived batch.
        last = game.read_text().split('END')[-2].strip()
        result = dict(returncode=0, timeout=False, stdout='READY\n'+last+'\nEND\n')
        self.assertTrue(correct(case, result))
        result['stdout'] = result['stdout'].replace('\n', '\n9\n', 1)
        self.assertFalse(correct(case, result))
