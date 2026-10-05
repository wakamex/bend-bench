import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bend_bench.core import correct, environment, execute, exclusive, load_config
from bend_bench.suites import plan, stage
from bend_bench.regression import comparison, render, snapshot, validate_result

ROOT = Path(__file__).resolve().parents[1]


class FastCPU(unittest.TestCase):
    def setUp(self):
        self.config = load_config(ROOT / 'fast-cpu.toml')

    def test_plan_and_shared_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            builds, cases = plan(self.config, work)
            self.assertEqual(len(builds), 52)  # 23 workloads (nanogpt the CPU profile's own) and 3 build-only stress programs, each emitted and compiled
            self.assertEqual(len(cases), 46)
            self.assertEqual(sum('stress-' in b[-1] for b in builds), 6)
            self.assertTrue(all(c['implementation'] == 'bend' and c['threads'] in (1, 16) for c in cases))
            self.assertTrue(all(c['command'][-1] == 'off' for c in cases))
            self.assertFalse(any('--gpu-build' in b or '-DBEND_CUDA=1' in b for b in builds))
            stage(self.config, work)
            self.assertIn('sum!(28n,', (work/'ports/summation.bend').read_text())
            self.assertIn('repeat(1n, 0)', (work/'ports/pricing.bend').read_text())
            self.assertIn('U32.to_nat(2000)', (work/'ports/uts-compact.bend').read_text())
            for name in {c['workload'] for c in cases}:
                pair = [c for c in cases if c['workload'] == name]
                self.assertEqual(pair[0]['contract'], pair[1]['contract'])

    def test_entrypoints(self):
        for name in ('fast-cpu', 'cpu-report', 'regression-report'):
            result = subprocess.run([sys.executable, '-m', 'bend_bench', name, '--help'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--baseline', result.stdout)

    def test_repetition_override(self):
        self.assertEqual(self.config['repetitions'], 1)
        from unittest.mock import patch
        from bend_bench.cli import main
        with patch('bend_bench.fast.run', return_value=(ROOT, False)) as run:
            self.assertEqual(main(['fast-cpu', str(ROOT/'fast-cpu.toml'), '--repetitions', '3']), 0)
            self.assertEqual(run.call_args.args[0]['repetitions'], 3)
        with patch('bend_bench.fast.run') as run:
            self.assertEqual(main(['fast-cpu', str(ROOT/'fast-cpu.toml'), '--repetitions', '0']), 2)
            run.assert_not_called()

    def test_nested_commands_and_aliases(self):
        from unittest.mock import patch
        from bend_bench.cli import main
        for target in ('cpu', 'gpu'):
            calls = []
            for command in ([target, 'fast'], ['fast-'+target]):
                with patch('bend_bench.fast.run', return_value=(ROOT, False)) as run:
                    self.assertEqual(main([*command, str(ROOT/f'fast-{target}.toml'), '--repetitions', '3', '--threshold', '5']), 0)
                    calls.append(run.call_args)
            self.assertEqual(calls[0], calls[1])
            result = subprocess.run([sys.executable, '-m', 'bend_bench', target, 'fast', '--help'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--repetitions', result.stdout)

    def test_total_elapsed_on_success_and_failure(self):
        import contextlib
        import io
        from unittest.mock import patch
        from bend_bench.cli import main
        for target in ('cpu', 'gpu'):
            for error in (None, ValueError('test failure')):
                output = io.StringIO()
                with patch('bend_bench.fast.run', return_value=(ROOT, False), side_effect=error), \
                     patch('bend_bench.cli.time.perf_counter', side_effect=[100, 3761.2]), \
                     contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                    status = main([target, 'fast', str(ROOT/f'fast-{target}.toml')])
                self.assertEqual(status, 2 if error else 0)
                self.assertIn('Total elapsed time: 01:01:01 (3661.2 seconds', output.getvalue())

    def test_fresh_runs_and_explicit_resume_with_real_execution(self):
        from unittest.mock import patch
        from bend_bench.fast import run

        def evidence(config):
            return dict(config=config, sources={}, host={'test': True})

        def stage(config, work):
            (work/'build').mkdir(parents=True)
            (work/'build/main.c').write_text('#include <stdio.h>\nint main(void) { puts("42"); }\n')

        def plan(config, work):
            binary = work/'build/main'
            return [['cc', '-O3', str(work/'build/main.c'), '-o', str(binary)]], [
                dict(id='cpu-regression/constant/bend/1', contract={'expected': '42'},
                     implementation='bend', threads=1, command=[str(binary)], env={},
                     expected_regex='42', unsupported=None)]

        with tempfile.TemporaryDirectory() as tmp, \
             patch('bend_bench.fast.provenance', side_effect=evidence), \
             patch('bend_bench.experiment.provenance', side_effect=evidence), \
             patch('bend_bench.experiment.stage', side_effect=stage), \
             patch('bend_bench.experiment.plan', side_effect=plan), \
             patch('bend_bench.regression.publish', return_value=('test report', False)):
            config = {**self.config, 'output': tmp, 'blocked_services': []}
            first, failed = run(config)
            self.assertFalse(failed)
            original = (first/'samples.jsonl').read_bytes()
            second, failed = run(config)
            self.assertFalse(failed)
            self.assertNotEqual(first, second)
            self.assertEqual(len((second/'samples.jsonl').read_text().splitlines()), 3)
            resumed, failed = run(config, resume=first)
            self.assertEqual(resumed, first)
            self.assertEqual(original, (first/'samples.jsonl').read_bytes())
            with self.assertRaisesRegex(ValueError, 'configuration differs'):
                run({**config, 'repetitions': 3}, resume=first)
            saved = json.loads((first/'provenance.json').read_text())
            saved['config']['_run_id'] = 'wrong-identity'
            (first/'provenance.json').write_text(json.dumps(saved))
            with self.assertRaisesRegex(ValueError, 'identity changed'):
                run(config, resume=first)

    def test_cpu_report_from_archived_native_timings(self):
        path = ROOT/'runs/64b53b136d7cfde4ed9e/summary.json'
        if not path.exists():
            self.skipTest('Archived CPU evidence unavailable')
        data = json.loads(path.read_text())
        data['provenance']['config']['suites'] = ['cpu-regression']
        data['cases'] = [r for r in data['cases'] if r['implementation'] == 'bend' and r['threads'] in (1, 16)]
        result = validate_result(snapshot(data))
        quick = json.loads(json.dumps(result))
        quick['required_samples'] = 1
        for row in quick['cases']:
            row['samples'] = 1
        validate_result(quick)
        self.assertIn('Quick screen', render(quick))
        quick['required_samples'] = 3
        with self.assertRaises(ValueError):
            validate_result(quick)
        candidate = {**result, 'fingerprint': 'independent-test-run'}
        compared = comparison(result, candidate)
        self.assertEqual(compared['thread_groups']['1']['geometric_mean'], 1)
        self.assertEqual(compared['thread_groups']['16']['geometric_mean'], 1)
        self.assertTrue(all(r['change_percent'] == 0 for r in compared['scaling']))
        self.assertIn('Thread scaling', render(result, compared))
        other = json.loads((ROOT/'benchmarks/uts-compact-20260922/summary.json').read_text())
        with self.assertRaises(ValueError):
            comparison(result, snapshot(other))
        data['provenance']['host']['gpu'] = 'irrelevant CPU-only GPU change'
        data['provenance']['toolkit'] = {'unused': 'new CUDA'}
        self.assertEqual(snapshot(data)['compatibility'], result['compatibility'])

    @unittest.skipUnless(os.environ.get('BEND_BENCH_FAST_CPU_NATIVE') == '1', 'Opt-in real CPU variant checks')
    def test_native_cpu_variants(self):
        with exclusive(self.config), tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            stage(self.config, work)
            builds, cases = plan(self.config, work)
            names = {'summation', 'pricing', 'uts-test', 'game-search'}
            outputs = {str(work/'build'/name)+suffix for name in names for suffix in ('', '.c')}
            for command in builds:
                if command[-1] in outputs:
                    result = execute(command, timeout=60)
                    self.assertEqual(result['returncode'], 0, result['stderr'])
            for case in cases:
                if case['workload'] in names:
                    result = execute(case['command'], env={**environment(), **case['env']}, timeout=60)
                    self.assertTrue(correct(case, result), (case['id'], result['stderr']))
