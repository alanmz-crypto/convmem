"""Tests for convmem add --upsert (Milestone C2/C3)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chroma_store import ChromaStore
from observe import ingest_observation, ingest_observation_file


def _fake_embed(text: str, model=None, host=None) -> list[float]:
    base = (sum(ord(c) for c in text) % 997) / 997.0
    return [base] * 768


_RECORD = {
    "id": "obs_staging2_lh_csp-missing",
    "kind": "observation",
    "domain": "web_stack.security",
    "author_model": "lighthouse-ci",
    "site": "staging2.willowyhollow.com",
    "severity": "medium",
    "summary": "Missing CSP header",
}


class UpsertTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ChromaStore(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    @patch("llm.ollama_embed", side_effect=_fake_embed)
    def test_upsert_keeps_unit_count(self, _mock):
        ingest_observation(
            _RECORD,
            store=self.store,
            embed_model="test",
            ollama_host="local",
        )
        self.assertEqual(self.store.count_units(), 1)

        updated = {**_RECORD, "summary": "Missing CSP and COOP headers"}
        ingest_observation(
            updated,
            store=self.store,
            embed_model="test",
            ollama_host="local",
            upsert=True,
        )
        self.assertEqual(self.store.count_units(), 1)

    @patch("llm.ollama_embed", side_effect=_fake_embed)
    def test_upsert_updates_document_and_embedding(self, mock_embed):
        ingest_observation(
            _RECORD,
            store=self.store,
            embed_model="test",
            ollama_host="local",
        )
        unit = self.store.get_unit(
            self.store.units_metadata()[0]["id"]
        )
        assert unit is not None
        first_doc = unit["document"]

        updated = {**_RECORD, "summary": "Missing CSP and COOP headers"}
        ingest_observation(
            updated,
            store=self.store,
            embed_model="test",
            ollama_host="local",
            upsert=True,
        )
        unit2 = self.store.get_unit(unit["id"])
        assert unit2 is not None
        self.assertIn("COOP", unit2["document"])
        self.assertNotEqual(unit2["document"], first_doc)
        self.assertEqual(mock_embed.call_count, 2)

    @patch("llm.ollama_embed", side_effect=_fake_embed)
    def test_file_ingest_twice_stats(self, _mock):
        path = Path(self.tmp.name) / "obs.jsonl"
        path.write_text(json.dumps(_RECORD) + "\n", encoding="utf-8")

        r1 = ingest_observation_file(
            str(path),
            store=self.store,
            embed_model="test",
            ollama_host="local",
            verbose=False,
        )
        self.assertEqual(r1["accepted"], 1)
        self.assertEqual(self.store.count_units(), 1)

        r2 = ingest_observation_file(
            str(path),
            store=self.store,
            embed_model="test",
            ollama_host="local",
            verbose=False,
            upsert=True,
        )
        self.assertEqual(r2["skipped"], 1)
        self.assertEqual(r2["accepted"], 0)
        self.assertEqual(r2["updated"], 0)
        self.assertEqual(self.store.count_units(), 1)

    @patch("llm.ollama_embed", side_effect=_fake_embed)
    def test_upsert_skips_unchanged_reembed(self, mock_embed):
        ingest_observation(
            _RECORD,
            store=self.store,
            embed_model="test",
            ollama_host="local",
        )
        ingest_observation(
            _RECORD,
            store=self.store,
            embed_model="test",
            ollama_host="local",
            upsert=True,
        )
        self.assertEqual(mock_embed.call_count, 1)


if __name__ == "__main__":
    unittest.main()


class AtomicJsonlTests(unittest.TestCase):
    """Crash-atomic JSONL replacement tests per T4 specification."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_unit(self, lid: str, title: str) -> dict:
        return {
            "id": f"id_{lid}",
            "ledger_id": lid,
            "ledger_kind": "observation",
            "domain": "testing",
            "title": title,
            "summary": f"Summary for {lid}",
            "rationale": "",
            "relates_to": "",
            "author_model": "test",
            "confidence": 1.0,
        }

    def test_new_file_created_atomically(self):
        from observe import _upsert_jsonl_line

        export = self.root / "export.jsonl"
        unit = self._make_unit("obs_test_001", "Test")
        _upsert_jsonl_line(export, "obs_test_001", unit)

        self.assertTrue(export.is_file())
        lines = export.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)

    def test_existing_line_replaced_atomically(self):
        from observe import _upsert_jsonl_line

        export = self.root / "export.jsonl"
        unit1 = self._make_unit("obs_test_001", "Title 1")
        unit2 = self._make_unit("obs_test_001", "Title 2")

        _upsert_jsonl_line(export, "obs_test_001", unit1)
        _upsert_jsonl_line(export, "obs_test_001", unit2)

        content = export.read_text(encoding="utf-8")
        self.assertIn("Title 2", content)
        self.assertNotIn("Title 1", content)

    def test_append_when_not_found(self):
        from observe import _upsert_jsonl_line

        export = self.root / "export.jsonl"
        unit1 = self._make_unit("obs_test_001", "First")
        unit2 = self._make_unit("obs_test_002", "Second")

        _upsert_jsonl_line(export, "obs_test_001", unit1)
        _upsert_jsonl_line(export, "obs_test_002", unit2)

        lines = [l for l in export.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)

    def test_malformed_lines_preserved(self):
        from observe import _upsert_jsonl_line

        export = self.root / "export.jsonl"
        # Write both lines together (write_text truncates)
        line1 = "not json" + chr(10)
        line2 = json.dumps(self._make_unit("obs_test_001", "First")) + chr(10)
        export.write_text(line1 + line2, encoding="utf-8")

        unit2 = self._make_unit("obs_test_002", "Second")
        _upsert_jsonl_line(export, "obs_test_002", unit2)

        content = export.read_text(encoding="utf-8")
        self.assertIn("not json", content)

    def test_no_temp_file_left_after_success(self):
        from observe import _upsert_jsonl_line

        export = self.root / "export.jsonl"
        unit = self._make_unit("obs_test_001", "Test")
        _upsert_jsonl_line(export, "obs_test_001", unit)

        temps = list(self.root.glob("*.tmp"))
        self.assertEqual(len(temps), 0)

    def test_no_glob_scavenger(self):
        import inspect, re
        from observe import _upsert_jsonl_line

        source = inspect.getsource(_upsert_jsonl_line)
        # Strip docstring to avoid false positives from documentation
        no_docstring = re.sub(r'""".*?"""', '', source, flags=re.DOTALL)
        impl_text = no_docstring.lower()
        self.assertNotIn("glob.", impl_text)
        self.assertNotIn("glob(", impl_text)
        self.assertNotIn("iglob", impl_text)

    def test_duplicate_lines_handled(self):
        from observe import _upsert_jsonl_line

        export = self.root / "export.jsonl"
        unit = self._make_unit("obs_test_001", "Test")

        _upsert_jsonl_line(export, "obs_test_001", unit)
        _upsert_jsonl_line(export, "obs_test_001", unit)

        lines = [l for l in export.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)

    def test_blank_lines_preserved(self):
        from observe import _upsert_jsonl_line

        export = self.root / "export.jsonl"
        unit1 = self._make_unit("obs_test_001", "First")
        _upsert_jsonl_line(export, "obs_test_001", unit1)
        export.write_text(
            export.read_text(encoding="utf-8") + chr(10),
            encoding="utf-8",
        )

        unit2 = self._make_unit("obs_test_002", "Second")
        _upsert_jsonl_line(export, "obs_test_002", unit2)

        lines = export.read_text(encoding="utf-8").splitlines()
        data_lines = [l for l in lines if l.strip()]
        self.assertEqual(len(data_lines), 2)


if __name__ == "__main__":
    unittest.main()
