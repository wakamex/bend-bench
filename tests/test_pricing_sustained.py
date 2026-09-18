from pathlib import Path
import tempfile
import unittest

from bend_bench.applications import pricing_reference
from bend_bench.core import exclusive, load_config
from pricing_sustained import ROOT, audit_quotes, compare_quotes, prepare, run_case


class SustainedPricingTests(unittest.TestCase):
    def test_seed_offsets_preserve_original_and_change_batches(self):
        self.assertEqual(pricing_reference(8, 4), pricing_reference(8, 4, 0))
        self.assertNotEqual(pricing_reference(8, 4), pricing_reference(8, 4, 8))
        self.assertEqual(pricing_reference(16, 4)[8:], pricing_reference(8, 4, 8))

    def test_quote_checks_reject_wrong_count_price_and_error(self):
        wanted = [[5.0, 0.1, 16]]
        compare_quotes(wanted, wanted)
        for bad in ([[6.0, 0.1, 16]], [[5.0, 0.2, 16]], [[5.0, 0.1, 15]], [[float('nan'), 0.1, 16]]):
            with self.assertRaises(ValueError):
                compare_quotes(bad, wanted)

    def test_real_cpu_audit_and_summary(self):
        config = load_config(ROOT / 'applications.toml')
        config.update(cuda=False, suites=['pricing'], threads=[16])
        vectors = [pricing_reference(256, 16, rep*256) for rep in range(3)]
        expected = audit_quotes(vectors)
        with exclusive(config), tempfile.TemporaryDirectory() as tmp:
            for audit in (True, False):
                work = Path(tmp) / str(audit)
                cases = prepare(config, work, 8, 16, 3, audit)
                for case in cases:
                    result = run_case(config, case, work / case['implementation'], 256, 3,
                                      expected, vectors if audit else None)
                    self.assertTrue(result['correct'])
                    self.assertEqual(len(result['pricing_seconds']), 3)
                    self.assertTrue(all(t > 0 for t in result['pricing_seconds']))
                if not audit:
                    source = (work/'build/pricing-8-16.original.c').read_text()
                    # The compiler materializes the quote fields in emit before IO.now.
                    self.assertIn('CID_QUOTE', source)
                    self.assertIn('FID_EMIT', source)
