import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from bend_bench.builds import config_from_build, create, inspect, runtime_provenance
from bend_bench.core import environment, host_info
from bend_bench.fast import run


class BuildArtifacts(unittest.TestCase):
    def test_real_binary_relocation_fresh_runs_and_integrity(self):
        host = host_info()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = dict(output=str(root/'runs'), suites=['cpu-regression'], threads=[1, 16],
                          repetitions=1, warmups=1, timeout=10, cuda=False, require_idle_gpu=False,
                          cpus=host['affinity'], blocked_services=[], tools={'cc': '/missing/compiler'},
                          bend={'path': '/missing/checkout', 'commit': 'a'*40})

            def evidence(c):
                return dict(config=c, host=host, sources={'bend': {'commit': 'a'*40, 'patch': ''}},
                            tools={}, toolkit={}, harness={}, environment=environment())

            def stage(c, work):
                (work/'build').mkdir(parents=True)
                (work/'inputs/rodinia').mkdir(parents=True)
                (work/'inputs/rodinia/value').write_text('42\n')
                (work/'build/main.c').write_text('#include <stdio.h>\nint main(void) { int n; FILE *f=fopen("inputs/rodinia/value","r"); if(!f) return 1; fscanf(f,"%d",&n); fclose(f); printf("%d\\n",n); }\n')

            def plan(c, work):
                binary = str(work/'build/main')
                return [['cc', str(work/'build/main.c'), '-o', binary]], [dict(
                    id='cpu-regression/summation/bend/1', implementation='bend', threads=1,
                    contract={'expected': 42}, expected_regex='42', unsupported=None,
                    command=[binary], env={})]

            with patch('bend_bench.experiment.provenance', side_effect=evidence), \
                 patch('bend_bench.experiment.stage', side_effect=stage), \
                 patch('bend_bench.experiment.plan', side_effect=plan):
                artifact = create(config, root/'original')
                with self.assertRaisesRegex(ValueError, 'already exists'):
                    create(config, artifact)
            relocated = root/'relocated'
            shutil.move(artifact, relocated)
            self.assertFalse(artifact.exists())
            loaded = config_from_build(relocated, 'cpu')
            loaded['output'] = str(root/'runs')
            # Actual compilation/execution, then reuse with no accessible checkout
            # or compiler: only initial build staging/provenance were test fixtures.
            with patch('bend_bench.core.repository', side_effect=AssertionError('source checkout queried')):
                first, failed = run(loaded)
                self.assertFalse(failed)
                second, failed = run(loaded, baseline=first, threshold=1_000_000)
                self.assertFalse(failed)
            self.assertNotEqual(first, second)
            self.assertFalse((first/'prepare.jsonl').exists())
            self.assertEqual(len((second/'samples.jsonl').read_text().splitlines()), 3)
            self.assertFalse((relocated/'samples.jsonl').exists())
            with self.assertRaisesRegex(ValueError, 'Cannot use a cpu build'):
                config_from_build(relocated, 'gpu')
            changed = copy.deepcopy(host)
            changed['platform'] = 'different'
            with patch('bend_bench.builds.host_info', return_value=changed):
                with self.assertRaisesRegex(ValueError, 'host is incompatible'):
                    runtime_provenance(loaded)
            (relocated/'work/inputs/rodinia/value').write_text('43\n')
            with self.assertRaisesRegex(ValueError, 'integrity'):
                inspect(relocated)

    def test_cli_build_reuse_does_not_load_source_config(self):
        from bend_bench.cli import main
        config = dict(suites=['cpu-regression'])
        with patch('bend_bench.builds.config_from_build', return_value=config), \
             patch('bend_bench.cli.load_config', side_effect=AssertionError('source config loaded')), \
             patch('bend_bench.fast.run', return_value=(Path('/test'), False)) as runner:
            self.assertEqual(main(['cpu', 'fast', '--build', '/artifact', '--repetitions', '3']), 0)
            self.assertEqual(runner.call_args.args[0]['repetitions'], 3)

    def test_cli_rejects_ambiguous_build_options(self):
        from bend_bench.cli import main
        for argv in (['--build-only'], ['--output', 'foo'], ['--build', 'foo', 'config.toml'],
                     ['--build-only', '--output', 'foo', '--resume', 'bar']):
            self.assertEqual(main(['cpu', 'fast', *argv]), 2)
