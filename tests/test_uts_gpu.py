"""UTS GPU contracts checked against the external pinned BOTS RNG."""
import os
from pathlib import Path
import tempfile
import unittest

from bend_bench.core import append, execute, exclusive, idle_gpu, load_config
from bend_bench.suites import plan, stage

ROOT = Path(__file__).resolve().parents[1]


class UTSGPU(unittest.TestCase):
    def test_opt_in_plan(self):
        for filename, expected in (("experiment.toml", 0), ("uts-gpu.toml", 4)):
            config = load_config(ROOT / filename)
            with tempfile.TemporaryDirectory() as tmp:
                stage(config, Path(tmp))
                builds, cases = plan(config, tmp)
                gpu = [c for c in cases if c['suite'] == 'uts' and c['implementation'].endswith('cuda')]
                self.assertEqual(len(gpu), expected)
                for case in gpu:
                    cpu = next(c for c in cases if c['id'] == f"uts/{case['workload']}/bend/16")
                    self.assertEqual(case['contract'], cpu['contract'])
                    if case['implementation'] == 'bend-cuda':
                        self.assertEqual(case['expected_regex'], cpu['expected_regex'])
                    else:
                        self.assertEqual(case['check_args'], ['verify'])
                if expected:
                    self.assertTrue(any(str(c[-1]).endswith('uts-sha.o') for c in builds))
                    for dataset in config['uts_inputs']:
                        # CUDA uses exactly the same Bend source as the CPU build.
                        source = str(Path(tmp) / f'ports/uts-{dataset}.bend')
                        self.assertEqual(sum(source in b for b in builds), 1)

    @unittest.skipUnless(os.environ.get('BEND_BENCH_UTS_GPU_TEST') == '1', 'Opt-in real CUDA and BOTS checks')
    def test_native(self):
        config = load_config(ROOT / 'uts-gpu.toml')
        with exclusive(config):
            idle_gpu(config)
            folder = Path(tempfile.mkdtemp(prefix='uts-gpu-check-', dir=ROOT / 'runs'))
            stage(config, folder)
            builds, _ = plan(config, folder)
            for cmd in builds:
                if not (str(cmd[-1]).endswith('uts-sha.o') or str(cmd[-1]).endswith('uts-conventional-cuda')):
                    continue
                result = execute(cmd, timeout=180)
                append(folder / 'build.jsonl', result)
                self.assertEqual(result['returncode'], 0, result['stderr'])
            binary = folder / 'build/uts-conventional-cuda'
            inputs = []
            for root, seed in ((0, 0), (1, 42), (4096, 123)):
                path = folder / f'boundary-{root}.input'
                path.write_text(f'{root} 0 8 {seed} 1 {root + 1} 0 0\n')
                inputs.append((path, root + 1))
            for dataset in config['uts_inputs']:
                path = Path(config['bots']['path']) / f'inputs/uts/{dataset}.input'
                inputs.append((path, int(path.read_text().split()[5])))
            for path, nodes in inputs:
                with self.subTest(input=path.name):
                    idle_gpu(config)
                    result = execute([binary, path, 'verify'], timeout=180, gpu_policy=config)
                    append(folder / 'checks.jsonl', result)
                    self.assertEqual(result['returncode'], 0, result['stderr'])
                    self.assertFalse(result.get('contention_error'))
                    self.assertEqual(result['stdout'].strip(), str(nodes))
                    self.assertIn(f'BOTS_TREE_VERIFIED={nodes}', result['stderr'])
            print(folder, flush=True)
