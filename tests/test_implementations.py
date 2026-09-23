"""An implementations list remeasures a subset without building the rest."""
from pathlib import Path
import tempfile
import unittest

from bend_bench.core import load_config
from bend_bench.suites import plan, stage

ROOT = Path(__file__).resolve().parents[1]


class Implementations(unittest.TestCase):
    def test_subset_keeps_its_cases_and_their_builds(self):
        text = (ROOT / 'uts-gpu.toml').read_text()
        full = load_config(ROOT / 'uts-gpu.toml')
        # Beside the real configs, so their relative paths resolve alike.
        with tempfile.NamedTemporaryFile('w', suffix='.toml', dir=ROOT) as f, \
                tempfile.TemporaryDirectory() as tmp:
            f.write(text.replace('schema = 1', 'schema = 1\nimplementations = ["bend", "bend-cuda"]', 1))
            f.flush()
            subset = load_config(f.name)
            work = Path(tmp)
            stage(full, work)
            all_builds, all_cases = plan(full, work)
            builds, cases = plan(subset, work)
        self.assertTrue(cases)
        self.assertEqual({c['implementation'] for c in cases}, {'bend', 'bend-cuda'})
        self.assertEqual([c for c in all_cases if c['implementation'] in {'bend', 'bend-cuda'}], cases)
        self.assertLess(len(builds), len(all_builds))
        self.assertTrue(all(b in all_builds for b in builds))
        made = {b[b.index('-o') + 1] for b in builds if '-o' in b} | {b[0] for b in builds}
        self.assertTrue({c['command'][3] for c in cases} <= made)
        self.assertFalse(any('uts-sha.o' in ' '.join(b) for b in builds))

    def test_default_plans_everything(self):
        config = load_config(ROOT / 'experiment.toml')
        # Absent unless set: existing run identities stay unchanged.
        self.assertNotIn('implementations', config)

    def test_rejects_duplicates(self):
        text = (ROOT / 'experiment.toml').read_text()
        with tempfile.NamedTemporaryFile('w', suffix='.toml', dir=ROOT) as f:
            f.write(text.replace('schema = 1', 'schema = 1\nimplementations = ["bend", "bend"]', 1))
            f.flush()
            with self.assertRaises(ValueError):
                load_config(f.name)


if __name__ == '__main__':
    unittest.main()
