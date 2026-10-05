from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

from bend_bench.compiler_check import check, render, run

ROOT = Path(__file__).resolve().parents[1]
TEST = '''import Base

def main() -> IO(Unit):
  IO.print(U32.show(U32.add(40, 2)))

#|{}
'''


class CompilerCheck(unittest.TestCase):
    def setUp(self):
        config = tomllib.loads((ROOT / 'fast-gpu.toml').read_text())
        self.bun = (ROOT / config['tools']['bun']).resolve()
        self.bend = (ROOT / config['bend']['path']).resolve()
        if not self.bun.exists() or not (self.bend / 'bend2/main.ts').exists():
            self.skipTest('Bend checkout or bun unavailable')
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def checkout(self, name, answer='42', header='// Imports'):
        # A checkout reduced to the real compiler plus one test with a `#|` expectation.
        root = self.tmp / name
        shutil.copytree(self.bend / 'bend2', root / 'bend2')
        comp = root / 'bend2/comp.ts'
        text = comp.read_text()
        self.assertEqual(text.count('\n// Imports\n'), 1, 'marker moved in the pinned compiler')
        comp.write_text(text.replace('\n// Imports\n', f'\n{header}\n'))
        (root / 'tests/t').mkdir(parents=True)
        (root / 'tests/t/add.bend').write_text(TEST.format(answer))
        return root

    def test_a_slower_compiler_is_listed_by_compile_time(self):
        # A candidate whose C emitter spends 400 ms more per program, on a demo.
        roots = [self.checkout('a'), self.checkout('b')]
        comp = roots[1] / 'bend2/comp.ts'
        head = 'export function compile_book(book: Bend.Book): string {\n'
        self.assertEqual(comp.read_text().count(head), 1, 'compile_book moved in the pinned compiler')
        comp.write_text(comp.read_text().replace(head, head + '  { const t0 = Date.now(); while (Date.now() - t0 < 400) {} }\n'))
        for root in roots:
            (root / 'demos/d').mkdir(parents=True)
            (root / 'demos/d/main.bend').write_text(TEST.format('42'))
        result = check(*roots, self.bun, only='^demos/')
        self.assertEqual(result['compile']['slower'], ['demos/d/main.bend'], result['compile'])
        self.assertIn('| demos/d/main.bend |', render(result))

    def test_same_compiler_emits_the_same_output(self):
        result = check(self.checkout('a'), self.checkout('b'), self.bun, only='^tests/')
        self.assertEqual(result['changed'], {})
        self.assertEqual(result['tests'], {'pass': 1})
        self.assertEqual(result['regressions'], [])
        self.assertIn('The candidate emits the same output as the base.', render(result))

    def test_changed_c_output_and_test_regression_are_reported(self):
        base = self.checkout('a')
        candidate = self.checkout('b', answer='41', header='// Imports (changed)')
        result = check(base, candidate, self.bun, only='^tests/')
        self.assertEqual(result['changed'], {'tests/t/add.bend': ['c']})
        self.assertEqual(result['test_changes'], {'tests/t/add.bend': {'base': 'pass', 'candidate': 'wrong'}})
        self.assertEqual(result['regressions'], ['tests/t/add.bend'])
        text, failed = run(base, candidate, self.bun, self.tmp / 'check.json', only='^tests/')
        self.assertTrue(failed)
        self.assertIn('| tests/t/add.bend | pass | wrong |', text)
        self.assertTrue((self.tmp / 'check.json').exists())

    def test_identical_flag_fails_on_any_output_change(self):
        base, candidate = self.checkout('a'), self.checkout('b', header='// Imports (changed)')
        self.assertFalse(run(base, candidate, self.bun, only='^tests/')[1])
        self.assertTrue(run(base, candidate, self.bun, only='^tests/', identical=True)[1])

    def test_cli_rejects_a_directory_without_a_compiler(self):
        command = [sys.executable, '-m', 'bend_bench', 'compiler-check', str(self.tmp), str(self.tmp), '--bun', str(self.bun)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Not a Bend checkout', result.stderr)


if __name__ == '__main__':
    unittest.main()
