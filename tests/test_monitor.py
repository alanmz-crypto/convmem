"""Tests for F2b HTTP monitor."""

from __future__ import annotations

import unittest
from unittest import mock

from ledger import build_ledger_index
from monitor import (
    AUTHOR_MODEL,
    PROBES,
    _check_csp,
    _check_hsts,
    _check_referrer,
    _check_xcto,
    check_tls_redirect,
    find_anchor_observation,
    has_kiro_verification,
    run_monitor,
)


class FakeStore:
    def __init__(self, metas: list[dict]):
        self._metas = [dict(m) for m in metas]
        self._units = {
            m["id"]: {"id": m["id"], "metadata": m, "document": m.get("title", "")}
            for m in self._metas
        }

    def units_metadata(self, **kwargs):
        return self._metas

    def get_unit(self, uid: str):
        return self._units.get(uid)

    def add_unit(self, unit_id, document, embedding, metadata):
        meta = dict(metadata)
        meta["id"] = unit_id
        self._metas.append(meta)
        self._units[unit_id] = {"id": unit_id, "metadata": meta, "document": document}

    def update_unit(self, unit_id, document, embedding, metadata):
        meta = dict(metadata)
        meta["id"] = unit_id
        self._units[unit_id] = {"id": unit_id, "metadata": meta, "document": document}
        for i, m in enumerate(self._metas):
            if m.get("id") == unit_id or m.get("ledger_id") == meta.get("ledger_id"):
                self._metas[i] = meta
                return


class MonitorProbeTests(unittest.TestCase):
    def test_header_checks(self):
        headers = {
            "Content-Security-Policy": "default-src 'self'",
            "Strict-Transport-Security": "max-age=31536000",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin",
        }
        self.assertTrue(_check_csp(headers))
        self.assertTrue(_check_hsts(headers))
        self.assertTrue(_check_xcto(headers))
        self.assertTrue(_check_referrer(headers))
        self.assertFalse(_check_csp({}))

    def test_tls_redirect_detected(self):
        session = mock.Mock()
        response = mock.Mock()
        response.status_code = 301
        response.headers = {"Location": "https://staging2.example.com/"}
        session.get.return_value = response
        self.assertTrue(check_tls_redirect("staging2.example.com", session=session))

    def test_find_anchor_skips_obs001(self):
        by_lid, _ = build_ledger_index(
            FakeStore(
                [
                    {
                        "id": "a",
                        "ledger_id": "obs001",
                        "ledger_kind": "observation",
                        "title": "Missing Content-Security-Policy header",
                        "site": "staging2.willowyhollow.com",
                    },
                    {
                        "id": "b",
                        "ledger_id": "obs_staging2_willowyhollow_com_006",
                        "ledger_kind": "observation",
                        "title": "Missing Content Security Policy (CSP)",
                        "site": "staging2.willowyhollow.com",
                    },
                ]
            )
        )
        anchor = find_anchor_observation(
            by_lid, site="staging2.willowyhollow.com", probe=PROBES[0]
        )
        self.assertEqual(anchor, "obs_staging2_willowyhollow_com_006")

    def test_find_anchor_prefers_wpsec_canonical(self):
        by_lid, _ = build_ledger_index(
            FakeStore(
                [
                    {
                        "id": "a",
                        "ledger_id": "obs_staging2_willowyhollow_com_006",
                        "ledger_kind": "observation",
                        "title": "Missing CSP",
                        "site": "staging2.willowyhollow.com",
                    },
                    {
                        "id": "b",
                        "ledger_id": "obs_staging2_wpsec_csp-missing",
                        "ledger_kind": "observation",
                        "title": "Missing Content Security Policy",
                        "site": "staging2.willowyhollow.com",
                    },
                ]
            )
        )
        anchor = find_anchor_observation(
            by_lid, site="staging2.willowyhollow.com", probe=PROBES[0]
        )
        self.assertEqual(anchor, "obs_staging2_wpsec_csp-missing")

    def test_has_kiro_verification(self):
        store = FakeStore(
            [
                {
                    "id": "v1",
                    "ledger_id": "ver_kiro",
                    "ledger_kind": "verification",
                    "relates_to": "obs_staging2_wpsec_csp-missing",
                    "author_model": "kiro-review",
                }
            ]
        )
        self.assertTrue(has_kiro_verification(store, "obs_staging2_wpsec_csp-missing"))
        self.assertFalse(has_kiro_verification(store, "obs_other"))

    @mock.patch("observe.ingest_observation")
    @mock.patch("monitor.fetch_https_headers")
    @mock.patch("monitor.check_tls_redirect")
    def test_run_monitor_emits_verification(
        self, mock_tls, mock_fetch, mock_ingest
    ):
        mock_fetch.return_value = ({}, None)
        mock_tls.return_value = False
        mock_ingest.return_value = {"id": "u1", "ledger_id": "ver_x"}

        store = FakeStore(
            [
                {
                    "id": "o1",
                    "ledger_id": "obs_staging2_willowyhollow_com_006",
                    "ledger_kind": "observation",
                    "title": "Missing Content Security Policy (CSP)",
                    "site": "staging2.willowyhollow.com",
                }
            ]
        )
        stats = run_monitor(
            store,
            site="staging2.willowyhollow.com",
            embed_model="test",
            ollama_host="http://localhost:11434",
            dry_run=False,
            verbose=False,
        )
        self.assertGreater(stats["verifications"], 0)
        self.assertEqual(stats["skipped_kiro"], 0)
        first_call = mock_ingest.call_args_list[0][0][0]
        self.assertEqual(first_call["kind"], "verification")
        self.assertEqual(first_call["relates_to"], "obs_staging2_willowyhollow_com_006")
        self.assertEqual(first_call["author_model"], AUTHOR_MODEL)
        self.assertEqual(first_call["confidence"], 0.4)

    @mock.patch("observe.ingest_observation")
    @mock.patch("monitor.fetch_https_headers")
    @mock.patch("monitor.check_tls_redirect")
    def test_run_monitor_skips_kiro(self, mock_tls, mock_fetch, mock_ingest):
        mock_fetch.return_value = ({"Content-Security-Policy": "x"}, None)
        mock_tls.return_value = True
        store = FakeStore(
            [
                {
                    "id": "o1",
                    "ledger_id": "obs_staging2_willowyhollow_com_006",
                    "ledger_kind": "observation",
                    "title": "Missing CSP",
                    "site": "staging2.willowyhollow.com",
                },
                {
                    "id": "v1",
                    "ledger_id": "ver_kiro",
                    "ledger_kind": "verification",
                    "relates_to": "obs_staging2_willowyhollow_com_006",
                    "author_model": "kiro-review",
                },
            ]
        )
        stats = run_monitor(
            store,
            site="staging2.willowyhollow.com",
            embed_model="test",
            ollama_host="http://localhost:11434",
            verbose=False,
        )
        self.assertGreater(stats["skipped_kiro"], 0)
        csp_verifications = [
            call[0][0]
            for call in mock_ingest.call_args_list
            if call[0][0].get("relates_to") == "obs_staging2_willowyhollow_com_006"
        ]
        self.assertEqual(csp_verifications, [])


if __name__ == "__main__":
    unittest.main()
