"""Unit tests for ab-test-analyzer. Run with: python3 -m pytest tests/ -q
(or python3 -m unittest discover -s tests)."""

import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from abtest.analyze import analyze
from abtest.data import load_dataset
from abtest.stats import (norm_cdf, required_sample_size, srm_check,
                          two_proportion_ztest)


class TestStats(unittest.TestCase):
    def test_norm_cdf(self):
        self.assertAlmostEqual(norm_cdf(0.0), 0.5)
        self.assertAlmostEqual(norm_cdf(1.96), 0.975, places=3)
        self.assertAlmostEqual(norm_cdf(-1.96), 0.025, places=3)

    def test_significant_win(self):
        # 1200/10000 vs 1350/10000: ~12.5% uplift, clearly significant.
        r = two_proportion_ztest(1200, 10000, 1350, 10000)
        self.assertAlmostEqual(r["p1"], 0.12)
        self.assertAlmostEqual(r["p2"], 0.135)
        self.assertAlmostEqual(r["uplift"], 0.125)
        self.assertTrue(3.0 < r["z"] < 3.4, r["z"])
        self.assertLess(r["p_value"], 0.01)
        lo, hi = r["diff_ci"]
        self.assertLess(lo, 0.015)
        self.assertGreater(hi, 0.015)

    def test_inconclusive(self):
        # 960/8000 vs 1010/8000: small lift, not significant at 5%.
        r = two_proportion_ztest(960, 8000, 1010, 8000)
        self.assertGreater(r["p_value"], 0.05)
        lo, hi = r["diff_ci"]
        self.assertLess(lo, 0)
        self.assertGreater(hi, 0)

    def test_srm_pass(self):
        r = srm_check(10000, 10000)
        self.assertGreater(r["p_value"], 0.5)

    def test_srm_fail(self):
        r = srm_check(10000, 6200)
        self.assertLess(r["p_value"], 0.01)

    def test_sample_size_monotonic(self):
        n_small_mde = required_sample_size(0.12, 0.02)
        n_large_mde = required_sample_size(0.12, 0.10)
        self.assertGreater(n_small_mde, n_large_mde)
        self.assertGreater(n_large_mde, 0)
        # rough magnitude: detecting a 5% lift on 12% base takes ~tens of thousands
        n = required_sample_size(0.12, 0.05)
        self.assertTrue(10_000 < n < 100_000, n)

    def test_sample_size_bad_args(self):
        with self.assertRaises(ValueError):
            required_sample_size(0.12, 0.0)
        with self.assertRaises(ValueError):
            required_sample_size(0.12, 0.05, alpha=0.03)


class TestData(unittest.TestCase):
    def test_load_csv(self):
        path = os.path.join(os.path.dirname(__file__), "..",
                            "datasets", "checkout_button.csv")
        exp = load_dataset(path)
        self.assertEqual(exp.n_control, 10000)
        self.assertEqual(exp.x_variant, 1350)

    def test_rejects_bad_rows(self):
        bad = "group,visitors,conversions\ncontrol,100,120\nvariant,100,10\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write(bad)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_dataset(path)
        finally:
            os.unlink(path)

    def test_rejects_single_group(self):
        bad = "group,visitors,conversions\ncontrol,100,10\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write(bad)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_dataset(path)
        finally:
            os.unlink(path)


class TestAnalyze(unittest.TestCase):
    def _exp(self, n1, x1, n2, x2):
        from abtest.data import Experiment
        return Experiment("t", "control", "variant", n1, x1, n2, x2)

    def test_verdicts(self):
        self.assertEqual(analyze(self._exp(10000, 1200, 10000, 1350)).verdict, "SHIP IT")
        self.assertEqual(analyze(self._exp(10000, 1350, 10000, 1200)).verdict, "DO NOT SHIP")
        r = analyze(self._exp(8000, 960, 8000, 1010))
        self.assertEqual(r.verdict, "INCONCLUSIVE")
        self.assertGreater(r.required_n_per_group, 8000)

    def test_srm_invalidates(self):
        r = analyze(self._exp(10000, 1180, 6200, 820))
        self.assertTrue(r.srm_failed)
        self.assertEqual(r.verdict, "INVALID")


if __name__ == "__main__":
    unittest.main()
