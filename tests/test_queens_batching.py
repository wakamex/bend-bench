import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('queens_batching', ROOT / 'queens_batching.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def board_reference(n, limit, board=()):
    if len(board) == 4:
        index = 0
        for col in board:
            index = index*n + col
        if index >= limit:
            return 0, 0
    if len(board) == n:
        return 1, 0
    sols = nodes = 0
    for col in range(n):
        if all(col != previous and abs(col-previous) != len(board)-row for row, previous in enumerate(board)):
            s, w = board_reference(n, limit, (*board, col))
            sols += s
            nodes += w + (len(board) >= 4)
    return sols, nodes


class QueensBatching(unittest.TestCase):
    def test_real_variants_against_board_reference(self):
        config = module.load_config(ROOT / 'nqueens.toml')
        with tempfile.TemporaryDirectory() as tmp:
            for n, limit in [(5, 625), (8, 1173), (8, 4096)]:
                folder = Path(tmp) / f'{n}-{limit}'
                module.build(config, folder, n, limit)
                expected = '%d %d' % board_reference(n, limit)
                for name in [*module.VARIANTS, 'serial', 'openmp']:
                    for threads in ([1] if name == 'serial' else [1, 4]):
                        argv, env = module.command(config, folder, name, threads)
                        result = module.execute(argv, env=env)
                        self.assertEqual(result['returncode'], 0, result['stderr'])
                        self.assertEqual(result['stdout'].strip(), expected, (name, n, limit, threads))

    def test_full_corpus_source_contract(self):
        config = module.load_config(ROOT / 'nqueens.toml')
        variants, serial, omp = module.sources(config, 17, 11730)
        self.assertIn('batch!(17n, 0, 131071, 17, 131071, 11730)', variants['published-batch'])
        self.assertEqual(variants['recursive'].split('def main()')[0], variants['recursive-batch'].split('def main()')[0])
        self.assertIn('prefix!(289n, 4n, 17, 11730', variants['recursive'])
        self.assertEqual(omp.replace('  #pragma omp parallel for schedule(dynamic,16) reduction(+:sols,nodes)\n', ''), serial)
        self.assertEqual(board_reference(8, 4096)[0], 92)


if __name__ == '__main__':
    unittest.main()
