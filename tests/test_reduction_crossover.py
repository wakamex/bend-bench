import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reduction_crossover', ROOT / 'reduction_crossover.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReductionCrossover(unittest.TestCase):
    def test_bracket_and_cap(self):
        threshold = 23_000_000
        points, bracket = module.search(lambda n: dict(count=n, cub_wins=n >= threshold))
        self.assertLess(bracket[0], threshold)
        self.assertGreaterEqual(bracket[1], threshold)
        self.assertEqual(len(points), 7)
        self.assertEqual(module.search(lambda n: dict(cub_wins=False), maximum=1 << 24)[1], None)
        self.assertEqual(module.search(lambda n: dict(cub_wins=True))[1], [None, 1 << 23])

    def test_source_limits_and_original(self):
        base = (ROOT / 'src/bend_bench/assets/gpu/reduce.bend').read_text()
        self.assertEqual(module.source(1 << 18), base)
        self.assertIn('sum!(31n, 0)', module.source(1 << 31))
        for n in (0, (1 << 31) + 1):
            with self.assertRaises(ValueError):
                module.source(n)

    def test_real_cuda_adapter_compiles_without_gpu_execution(self):
        if not Path('/code/bend2/upstream').exists():
            self.skipTest('Pinned evaluation sources unavailable')
        config = module.load_config(ROOT / 'gpu-primitives.toml')
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            builds, cases = module.recipes(config, folder, 13)
            for command in builds:
                if command[-1] == '--gpu-build':
                    continue  # Requires the GPU; correctness is gated after admission.
                result = module.execute(command, timeout=180)
                self.assertEqual(result['returncode'], 0, result['stdout'] + result['stderr'])
            oracle = module.execute([folder / 'build/cub-reference'])
            bend = module.execute([folder / 'build/cub-reduce-23', '--threads', '1'])
            self.assertEqual(oracle['returncode'], 0)
            self.assertEqual(bend['returncode'], 0, bend['stderr'])
            self.assertEqual(bend['stdout'], oracle['stdout'])
            cub = next(c for c in cases if c['implementation'] == 'cub-cuda')
            self.assertEqual(cub['command'][-2:], ['reduce', '13'])

    def test_matched_cpu_recipes_and_real_outputs(self):
        config = module.load_config(ROOT / 'gpu-primitives.toml')
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            builds, cases = module.recipes(config, folder, 4097, cpu=True)
            self.assertEqual(len(cases), 6)
            for command in builds:
                if command[-1] == '--gpu-build':
                    continue
                result = module.execute(command, timeout=180)
                self.assertEqual(result['returncode'], 0, result['stdout'] + result['stderr'])
            oracle = module.execute([folder / 'build/cub-reference'])
            self.assertEqual(oracle['returncode'], 0)
            for case in cases:
                if case['implementation'].endswith('cuda'):
                    continue
                result = module.execute(case['command'], env={**module.environment(), **case['env']})
                self.assertEqual(result['returncode'], 0, result['stderr'])
                self.assertEqual(result['stdout'], oracle['stdout'])
            self.assertIn('keys,sum,uint64_t(n)', (folder / 'gpu/cub.cu').read_text())
            for value in ('0', '2147483649', 'junk'):
                result = module.execute([folder / 'build/serial-cpp', value])
                self.assertNotEqual(result['returncode'], 0)

    def test_real_bend_prefixes_on_cpu(self):
        if not Path('/code/bend2/upstream').exists():
            self.skipTest('Pinned Bend evaluation checkout unavailable')
        config = module.load_config(ROOT / 'gpu-primitives.toml')
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for count in (1, 3, 8, 13, 4097):
                bend, c, binary = folder / 'test.bend', folder / 'test.c', folder / 'test'
                bend.write_text(module.source(count).replace('sum!(', 'sum(').replace('chunk0!()', 'chunk0()'))
                for command in ([config['tools']['bun'], Path(config['bend']['path']) / 'bend2/main.ts', bend, '-o', c],
                                [config['tools']['cc'], '-O3', c, '-lpthread', '-lm', '-o', binary]):
                    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                result = subprocess.run([binary, '--threads', '1'], capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = 0
                for i in range(count):
                    x = ((i + 1) * 2654435761) & 0xffffffff
                    x ^= (x << 13) & 0xffffffff
                    x ^= x >> 17
                    x ^= (x << 5) & 0xffffffff
                    expected = (expected + x) & 0xffffffff
                self.assertEqual(int(result.stdout), expected)
