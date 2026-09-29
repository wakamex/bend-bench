from pathlib import Path
import re
import subprocess
import tempfile
import tomllib
import unittest

from bend_bench import compile_stress

ROOT = Path(__file__).resolve().parents[1]


class CompileStress(unittest.TestCase):
    def test_programs_are_deterministic(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first, second = compile_stress.write(a), compile_stress.write(b)
            self.assertEqual([p.name for p in first], ['stress-flatmany.bend', 'stress-flatchain.bend', 'stress-loopchain.bend'])
            self.assertEqual([p.read_bytes() for p in first], [p.read_bytes() for p in second])

    def test_real_compiler_emits_one_native_per_function(self):
        config = tomllib.loads((ROOT / 'fast-gpu.toml').read_text())
        bun = (ROOT / config['tools']['bun']).resolve()
        main = (ROOT / config['bend']['path']).resolve() / 'bend2/main.ts'
        if not bun.exists() or not main.exists():
            self.skipTest('Bend checkout or bun unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            for path, natives in zip(compile_stress.write(tmp), (5, 10, 12)):
                out = Path(tmp) / (path.stem + '.c')
                result = subprocess.run([bun, main, path, '-o', out], cwd=tmp, capture_output=True, text=True, timeout=300)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(re.findall(r'^\w+ Term spin_\d+\(Env e', out.read_text(), re.M)), natives, path.name)


if __name__ == '__main__':
    unittest.main()
