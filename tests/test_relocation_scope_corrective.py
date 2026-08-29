"""Portland / relocation retrieval scope corrective — T1–T7."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ask import _prepend_recent_decisions, retrieve_for_ask
from domains import domain_matches
from ledger_recent import PROTOCOL_FALLBACK_LEDGER_ID
from query import (
    _fetch_scoped_units,
    _filter_ledger_extras_by_domain,
    _filter_results_by_scope,
    query_raw,
    query_units,
)
from read_scope import clear_read_scope, get_read_scope, resolve_retrieval_domain, set_read_scope
from tests.serving_repo_mock import patch_query_serving


def _cfg() -> dict:
    return {
        "models": {"embed_model": "nomic-embed-text", "ollama_host": "http://x"},
        "index": {"chroma_dir": "/tmp/chroma"},
        "query": {"rerank": False, "recency_weight": 0.0, "top_k_candidates": 20},
    }


def _unit(uid: str, domain: str, score: float = 0.9) -> dict:
    return {
        "id": uid,
        "distance": 1.0 - score,
        "metadata": {
            "title": uid,
            "domain": domain,
            "document": f"body {uid}",
            "tool": "cursor",
            "source_path": f"/tmp/{uid}.md",
        },
        "document": f"body {uid}",
    }


def _raw_summary(uid: str, domain: str | None, score: float = 0.4) -> dict:
    meta = {
        "tool": "cursor",
        "source_path": f"/tmp/{uid}.jsonl",
        "start_offset": 0,
        "end_offset": 1,
    }
    if domain:
        meta["domain"] = domain
    return {
        "id": uid,
        "distance": 1.0 - score,
        "metadata": meta,
        "document": f"summary {uid}",
        "score": score,
    }


class DomainMatchesSegmentTests(unittest.TestCase):
    """T3 — segment-aware recent decisions / domain_matches semantics."""

    def test_business_tax_not_business_hr(self):
        self.assertFalse(domain_matches("business.hr", "business.tax"))

    def test_business_parent_matches_child(self):
        self.assertTrue(domain_matches("business.tax", "business"))

    def test_business_not_prefix_false_positives(self):
        self.assertFalse(domain_matches("businesses", "business"))
        self.assertFalse(domain_matches("business_travel", "business"))

    def test_prepend_recent_uses_domain_matches(self):
        semantic = [{"metadata": {"ledger_id": "sem_1"}, "score": 0.9}]
        recent = [
            {"id": "dec_tax", "summary": "tax", "domain": "business.tax"},
            {"id": "dec_hr", "summary": "hr", "domain": "business.hr"},
        ]
        out = _prepend_recent_decisions(
            semantic, recent, total_limit=8, domain="business.tax"
        )
        recent_ids = [
            (u.get("metadata") or {}).get("ledger_id")
            for u in out
            if u.get("evidence_status") == "recent_decision"
        ]
        self.assertEqual(recent_ids, ["dec_tax"])


class RawFallbackScopeTests(unittest.TestCase):
    """T1 — raw hybrid fallback cannot leak outside active domain."""

    @mock.patch("ask.query_units")
    @mock.patch("ask.query_raw")
    @mock.patch("ask.load_config", return_value=_cfg())
    def test_low_confidence_hybrid_respects_domain(
        self, _cfg_mock, mock_raw, mock_units
    ):
        mock_units.return_value = [
            _unit("low", "relocation", score=0.2),
        ]
        mock_raw.return_value = [
            _raw_summary("reloc", "relocation", score=0.4),
        ]
        bundle = retrieve_for_ask(
            "Portland rental Woodstock",
            top_k=3,
            domain="relocation",
            cfg=_cfg(),
        )
        mock_raw.assert_called_once()
        self.assertEqual(mock_raw.call_args.kwargs.get("domain"), "relocation")
        for hit in bundle.selection:
            meta = hit.get("metadata") or {}
            ud = meta.get("domain")
            if ud:
                self.assertTrue(domain_matches(ud, "relocation"), ud)

    @mock.patch("query.ollama_embed", return_value=[0.1])
    @mock.patch("query.load_config", return_value=_cfg())
    def test_query_raw_filters_out_of_domain(self, _cfg, _embed):
        store = mock.MagicMock()
        store.query_summaries.return_value = [
            _raw_summary("global", "coding.tooling", score=0.95),
            _raw_summary("reloc", "relocation", score=0.4),
        ]
        with patch_query_serving(store):
            results = query_raw("q", top_k=5, domain="relocation", cfg=_cfg())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["metadata"]["domain"], "relocation")


class LedgerAnchorScopeTests(unittest.TestCase):
    """T2 — ledger / anchor priority cannot bypass domain scope."""

    def test_filter_ledger_extras_drops_out_of_domain(self):
        hits = [
            {
                "id": "anchor",
                "metadata": {"ledger_id": PROTOCOL_FALLBACK_LEDGER_ID, "domain": "coding.tooling"},
            },
            {
                "id": "reloc",
                "metadata": {"ledger_id": "dec_reloc", "domain": "relocation"},
            },
        ]
        filtered = _filter_ledger_extras_by_domain(hits, "relocation")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["metadata"]["ledger_id"], "dec_reloc")

    @mock.patch("query._ledger_lookup_hits")
    @mock.patch("query.ollama_embed", return_value=[0.1])
    @mock.patch("query.load_config", return_value=_cfg())
    @mock.patch(
        "rerank.rerank",
        side_effect=lambda _q, candidates, _m, top_k: candidates[:top_k],
    )
    def test_scoped_query_drops_protocol_anchor(
        self, _rerank, _cfg_mock, _embed, mock_lookup
    ):
        store = mock.MagicMock()
        store.query_units.return_value = [_unit("r1", "relocation", 0.8)]
        store.count_units.return_value = 100
        mock_lookup.return_value = [
            {
                "id": "anchor",
                "metadata": {
                    "ledger_id": PROTOCOL_FALLBACK_LEDGER_ID,
                    "domain": "coding.tooling",
                },
                "document": "protocol",
                "score": 0.99,
                "ledger_lookup": True,
            }
        ]
        with patch_query_serving(store):
            results = query_units(
                "convmem record relates-to fallback root",
                top_k=5,
                domain="relocation",
            )
        ledger_ids = [(r.get("metadata") or {}).get("ledger_id") for r in results]
        self.assertNotIn(PROTOCOL_FALLBACK_LEDGER_ID, ledger_ids)

    @mock.patch("query._ledger_lookup_hits")
    @mock.patch("query.ollama_embed", return_value=[0.1])
    @mock.patch("query.load_config", return_value=_cfg())
    @mock.patch(
        "rerank.rerank",
        side_effect=lambda _q, candidates, _m, top_k: candidates[:top_k],
    )
    def test_scoped_query_drops_out_of_domain_ledger_id(
        self, _rerank, _cfg_mock, _embed, mock_lookup
    ):
        store = mock.MagicMock()
        store.query_units.return_value = [_unit("r1", "relocation", 0.8)]
        store.count_units.return_value = 100
        mock_lookup.return_value = [
            {
                "id": "coding",
                "metadata": {
                    "ledger_id": "dec_prop_20260623_161428_c311",
                    "domain": "coding.tooling",
                },
                "document": "protocol",
                "score": 0.99,
                "ledger_lookup": True,
            }
        ]
        with patch_query_serving(store):
            results = query_units(
                "details for dec_prop_20260623_161428_c311",
                top_k=5,
                domain="relocation",
            )
        for row in results:
            ud = (row.get("metadata") or {}).get("domain")
            if ud:
                self.assertTrue(domain_matches(ud, "relocation"))


class SparseRelocationRecallTests(unittest.TestCase):
    """T4 — sparse relocation domain remains retrievable under scope."""

    def _corpus_rows(self) -> list[dict]:
        rows = [
            _unit("woodstock", "relocation", 0.62),
            _unit("portland", "relocation", 0.61),
        ]
        for i in range(80):
            rows.append(_unit(f"noise_{i}", "coding.tooling", 0.99 - i * 0.005))
        return rows

    def _ranked_query(self, corpus):
        def _query(_embedding, n_results):
            ranked = sorted(corpus, key=lambda r: r.get("distance", 1.0))
            return ranked[:n_results]

        return _query

    def _legacy_fixed_fetch(self, repo, embedding, *, candidate_k, domain):
        raw = repo.query_units(embedding, candidate_k * 3)
        return _filter_results_by_scope(raw, domain=domain, site_norm=None)

    def test_legacy_fixed_fetch_misses_relocation(self):
        corpus = self._corpus_rows()

        repo = mock.MagicMock()
        repo.query_units.side_effect = self._ranked_query(corpus)
        repo.count_units.return_value = len(corpus)

        legacy = self._legacy_fixed_fetch(
            repo, [0.1], candidate_k=20, domain="relocation"
        )
        self.assertEqual(len(legacy), 0)

    def test_adaptive_fetch_finds_relocation(self):
        corpus = self._corpus_rows()

        repo = mock.MagicMock()
        repo.query_units.side_effect = self._ranked_query(corpus)
        repo.count_units.return_value = len(corpus)

        adaptive = _fetch_scoped_units(
            repo,
            [0.1],
            candidate_k=20,
            domain="relocation",
            site_norm=None,
        )
        titles = {(r.get("metadata") or {}).get("title") for r in adaptive}
        self.assertIn("woodstock", titles)
        self.assertIn("portland", titles)

    @mock.patch("query.ollama_embed", return_value=[0.1])
    @mock.patch("query.load_config", return_value=_cfg())
    @mock.patch(
        "rerank.rerank",
        side_effect=lambda _q, candidates, _m, top_k: candidates[:top_k],
    )
    def test_query_units_sparse_relocation_recall(self, _rerank, _cfg, _embed):
        corpus = self._corpus_rows()

        store = mock.MagicMock()
        store.query_units.side_effect = self._ranked_query(corpus)
        store.count_units.return_value = len(corpus)
        with patch_query_serving(store):
            results = query_units(
                "Woodstock Portland rental lease",
                top_k=5,
                domain="relocation",
            )
        self.assertGreaterEqual(len(results), 2)
        for row in results:
            self.assertTrue(
                domain_matches((row.get("metadata") or {}).get("domain", ""), "relocation")
            )


class SessionReadScopeTests(unittest.TestCase):
    """T5 — session default, explicit override, clear."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self._scope_path = Path(self._tmpdir.name) / "read_scope.json"
        self._env_patch = mock.patch.dict(
            "os.environ",
            {"CONVMEM_READ_SCOPE_FILE": str(self._scope_path)},
            clear=False,
        )
        self._env_patch.start()
        clear_read_scope()

    def tearDown(self):
        clear_read_scope()
        self._env_patch.stop()
        self._tmpdir.cleanup()

    @mock.patch("ask.query_units", return_value=[])
    @mock.patch("ask.query_raw", return_value=[])
    @mock.patch("ask.load_config", return_value=_cfg())
    def test_session_default_applies_to_bare_query(
        self, _cfg_mock, _raw, mock_units
    ):
        set_read_scope("relocation")
        retrieve_for_ask("Portland lease", cfg=_cfg())
        self.assertEqual(mock_units.call_args.kwargs.get("domain"), "relocation")

    @mock.patch("ask.query_units", return_value=[])
    @mock.patch("ask.query_raw", return_value=[])
    @mock.patch("ask.load_config", return_value=_cfg())
    def test_explicit_domain_overrides_session(
        self, _cfg_mock, _raw, mock_units
    ):
        set_read_scope("relocation")
        retrieve_for_ask("q", domain="coding.tooling", cfg=_cfg())
        self.assertEqual(mock_units.call_args.kwargs.get("domain"), "coding.tooling")

    @mock.patch("ask.query_units", return_value=[])
    @mock.patch("ask.query_raw", return_value=[])
    @mock.patch("ask.load_config", return_value=_cfg())
    def test_clear_restores_unscoped(
        self, _cfg_mock, _raw, mock_units
    ):
        set_read_scope("relocation")
        clear_read_scope()
        self.assertIsNone(get_read_scope())
        retrieve_for_ask("q", cfg=_cfg())
        self.assertIsNone(mock_units.call_args.kwargs.get("domain"))


class CrossDomainNonStickyTests(unittest.TestCase):
    """T6 — explicit crossover widens once; next call respects scope."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self._scope_path = Path(self._tmpdir.name) / "read_scope.json"
        self._env_patch = mock.patch.dict(
            "os.environ",
            {"CONVMEM_READ_SCOPE_FILE": str(self._scope_path)},
            clear=False,
        )
        self._env_patch.start()
        set_read_scope("relocation")

    def tearDown(self):
        clear_read_scope()
        self._env_patch.stop()
        self._tmpdir.cleanup()

    @mock.patch("ask.query_units")
    @mock.patch("ask.query_raw", return_value=[])
    @mock.patch("ask.load_config", return_value=_cfg())
    def test_cross_domain_widens_then_reverts(self, _cfg_mock, _raw, mock_units):
        mock_units.return_value = [
            _unit("coding", "coding.tooling", 0.9),
            _unit("reloc", "relocation", 0.8),
        ]
        crossover = retrieve_for_ask(
            "general question",
            cross_domain=True,
            cfg=_cfg(),
            trace=True,
        )
        self.assertIsNone(mock_units.call_args.kwargs.get("domain"))
        self.assertEqual(crossover.trace["request"]["scope"]["scope_source"], "cross_domain")

        retrieve_for_ask("follow-up", cfg=_cfg())
        self.assertEqual(mock_units.call_args.kwargs.get("domain"), "relocation")

    def test_resolve_cross_domain_observable(self):
        domain, meta = resolve_retrieval_domain(None, cross_domain=True)
        self.assertIsNone(domain)
        self.assertTrue(meta["cross_domain"])
        self.assertEqual(meta["scope_source"], "cross_domain")


class WriteClassificationAuditTests(unittest.TestCase):
    """T7 — writes stay content-classified; session scope is read-only."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self._scope_path = Path(self._tmpdir.name) / "read_scope.json"
        self._env_patch = mock.patch.dict(
            "os.environ",
            {"CONVMEM_READ_SCOPE_FILE": str(self._scope_path)},
            clear=False,
        )
        self._env_patch.start()
        set_read_scope("relocation")

    def tearDown(self):
        clear_read_scope()
        self._env_patch.stop()
        self._tmpdir.cleanup()

    def test_content_domains_not_blanket_relocation(self):
        from domains import normalize_domain

        samples = [
            {"domain": "coding.devops"},
            {"domain": "web_stack.wordpress.plugins"},
            {"domain": "relocation"},
            {"domain": "web_stack.dns"},
            {"domain": "coding.ml.ollama"},
            {"domain": "web_stack.ssl"},
            {"domain": "coding.ml.rag"},
            {"domain": "relocation.portland"},
            {"domain": "web_stack.wordpress.themes"},
            {"domain": "web_stack.hosting"},
            {"domain": "web_stack.security"},
            {"domain": "coding.backend"},
            {"domain": "coding.frontend"},
            {"domain": "coding.tooling"},
            {"domain": "web_stack.api"},
        ]
        domains = [normalize_domain(s["domain"]) for s in samples]
        self.assertEqual(get_read_scope(), "relocation")
        self.assertGreater(len(set(domains)), 3)
        self.assertNotEqual(set(domains), {"relocation"})
        relocation_n = sum(
            1 for d in domains if d == "relocation" or d.startswith("relocation.")
        )
        self.assertLess(relocation_n, len(domains))

    def test_write_paths_do_not_import_read_scope(self):
        import distill
        import ingest

        for module in (distill, ingest):
            source = Path(module.__file__).read_text(encoding="utf-8")
            self.assertNotIn("read_scope", source)
            self.assertNotIn("get_read_scope", source)


if __name__ == "__main__":
    unittest.main()
