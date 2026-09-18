import os
from pathlib import Path
import tempfile
import unittest

from bend_bench.core import execute, load_config
from bend_bench.experiment import prepare, measure


def count_boards(size, columns=()):
    if len(columns) == size:
        return 1
    return sum(count_boards(size, columns + (column,)) for column in range(size)
               if all(column != previous and abs(column - previous) != len(columns) - row
                      for row, previous in enumerate(columns)))


class NQueensTests(unittest.TestCase):
    def test_native_backends(self):
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "nqueens.toml")
        with tempfile.TemporaryDirectory() as tmp:
            config.update(output=tmp, queens_sizes=[4, 8], threads=[1, 4])
            prepare(config)
            run, failed = measure(config, checking=True)
            self.assertFalse(failed, str(run))
            for size in range(1, 9):
                expected = str(count_boards(size))
                for levels in (0, 3, 5):
                    result = execute([run / "work/build/nqueens-bitmask", size, levels],
                                     env={**os.environ, "OMP_NUM_THREADS": "4"})
                    self.assertEqual(result["returncode"], 0, result["stderr"])
                    self.assertEqual(result["stdout"].strip(), expected)


if __name__ == "__main__":
    unittest.main()
