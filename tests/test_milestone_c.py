"""Tests for stable ledger ids and Lighthouse export (Milestone C1)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from export_lighthouse import export_lighthouse_file, parse_lighthouse_report, should_export_audit
from ledger_ids import observation_id, site_short, wpsec_finding_key


class LedgerIdTests(unittest.TestCase):
    def test_site_short(self):
        self.assertEqual(site_short("staging2.willowyhollow.com"), "staging2")

    def test_observation_id_lighthouse(self):
        self.assertEqual(
            observation_id("staging2.willowyhollow.com", "lh", "csp-xss"),
            "obs_staging2_lh_csp-xss",
        )

    def test_observation_id_wpsec(self):
        self.assertEqual(
            observation_id("staging2.willowyhollow.com", "wp-sec-agent", "wp-version"),
            "obs_staging2_wpsec_wp-version",
        )

    def test_wpsec_finding_keys(self):
        self.assertEqual(
            wpsec_finding_key("nikto", "Missing Content Security Policy (CSP)"),
            "csp-missing",
        )
        self.assertEqual(
            wpsec_finding_key("nikto", "Cookie nevercache created without the secure flag."),
            "cookie-secure",
        )


class LighthouseExportTests(unittest.TestCase):
    def _sample_lhr(self) -> dict:
        return {
            "finalUrl": "https://staging2.willowyhollow.com/",
            "audits": {
                "csp-xss": {
                    "id": "csp-xss",
                    "title": "Ensure CSP is effective against XSS attacks",
                    "score": 0.0,
                },
                "unused-javascript": {
                    "id": "unused-javascript",
                    "title": "Reduce unused JavaScript",
                    "score": 0.5,
                },
                "first-contentful-paint": {
                    "id": "first-contentful-paint",
                    "title": "First Contentful Paint",
                    "score": 1.0,
                },
                "viewport": {
                    "id": "viewport",
                    "title": "Has a viewport tag",
                    "score": None,
                },
            },
        }

    def test_stable_ids_across_runs(self):
        data = self._sample_lhr()
        a = parse_lighthouse_report(data, site="staging2.willowyhollow.com")
        b = parse_lighthouse_report(data, site="staging2.willowyhollow.com")
        self.assertEqual([r["id"] for r in a], [r["id"] for r in b])
        self.assertIn("obs_staging2_lh_csp-xss", [r["id"] for r in a])

    def test_only_failed_audits_exported(self):
        records = parse_lighthouse_report(
            self._sample_lhr(), site="staging2.willowyhollow.com"
        )
        ids = {r["evidence"]["audit_id"] for r in records}
        self.assertEqual(ids, {"csp-xss", "unused-javascript"})
        self.assertFalse(should_export_audit({"score": 1.0}))
        self.assertTrue(should_export_audit({"score": 0.5}))

    def test_export_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lighthouse.json"
            path.write_text(json.dumps(self._sample_lhr()), encoding="utf-8")
            records = export_lighthouse_file(path, site="staging2.willowyhollow.com")
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["author_model"], "lighthouse-ci")
            self.assertEqual(records[0]["kind"], "observation")


if __name__ == "__main__":
    unittest.main()
