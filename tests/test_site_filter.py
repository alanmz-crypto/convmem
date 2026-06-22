"""Tests for --site filter helpers."""

from __future__ import annotations

import unittest

from site_filter import filter_results_by_site, normalize_site, unit_matches_site


class SiteFilterTests(unittest.TestCase):
    def test_normalize_site_strips_scheme(self):
        self.assertEqual(normalize_site("https://staging2.willowyhollow.com/path"), "staging2.willowyhollow.com")

    def test_matches_meta_site(self):
        meta = {"site": "staging2.willowyhollow.com", "source_path": "site:staging2.willowyhollow.com"}
        self.assertTrue(unit_matches_site(meta, "staging2.willowyhollow.com"))

    def test_matches_source_path_substring(self):
        meta = {"site": "", "source_path": "/home/lauer/wp-sec/clients/staging2.willowyhollow.com/results/report.md"}
        self.assertTrue(unit_matches_site(meta, "staging2.willowyhollow.com"))

    def test_rejects_unrelated_unit(self):
        meta = {"site": "", "source_path": "ledger:kiro-review", "domain": "coding.tooling"}
        self.assertFalse(unit_matches_site(meta, "staging2.willowyhollow.com"))

    def test_filter_results_by_site(self):
        rows = [
            {"metadata": {"site": "staging2.willowyhollow.com"}},
            {"metadata": {"domain": "coding.tooling", "source_path": "ledger:cursor"}},
        ]
        out = filter_results_by_site(rows, "staging2.willowyhollow.com")
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
