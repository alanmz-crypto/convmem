"""Tests for convmem add --severity (exposure-window feed requirement)."""

from __future__ import annotations

import unittest
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from convmem import app

_BASE_ARGS = [
    "add",
    "--title", "P0 corpus poisoning",
    "--summary", "Stale units served after supersede.",
    "--keyword", "corpus", "--keyword", "supersede", "--keyword", "p0",
    "--author", "test-model",
]

_CFG = {
    "index": {"chroma_dir": "/tmp/unused", "units_export": ""},
    "models": {"embed_model": "test", "ollama_host": "local"},
}


class AddSeverityTests(unittest.TestCase):
    def _run(self, extra_args: list[str]):
        runner = CliRunner()
        captured: dict = {}

        from observe import PreparedObservationIngest  # pylint: disable=no-name-in-module  # stale docs/chatgpt-pack observe/ledger names

        def _fake_prepare(record, **_kw):
            captured.update(record)
            return PreparedObservationIngest(
                record=record,
                unit={
                    **record,
                    "id": "u1",
                    "ledger_id": "obs_test",
                    "domain": record["domain"],
                },
                doc="summary text",
                embedding=[0.1, 0.2, 0.3],
                upsert=False,
            )

        session = MagicMock()
        session.store = MagicMock()
        session.live_cfg = _CFG

        with (
            patch("convmem._guard_write"),
            patch("config.load_config", return_value=_CFG),
            patch("chroma_readonly.open_readonly_unit_store", return_value=MagicMock()),
            patch(
                "observe.embed_ledger_record_for_storage",
                return_value=[0.1, 0.2, 0.3],
            ),
            patch("llm.ollama_embed", return_value=[0.1, 0.2, 0.3]),
            patch("observe.prepare_observation_ingest", side_effect=_fake_prepare),
            patch(
                "observe.commit_observation_ingest",
                side_effect=lambda *_a, **_k: {
                    "id": "u1",
                    "ledger_id": "obs_test",
                    "domain": captured.get("domain", "general"),
                    "title": captured.get("title", "title"),
                },
            ),
            patch("purge_locks.index_write_flock", nullcontext),
            patch(
                "chroma_write_store.production_chroma_write_session",
                return_value=MagicMock(
                    __enter__=MagicMock(return_value=session),
                    __exit__=MagicMock(return_value=False),
                ),
            ),
            patch("chroma_write_store.admitted_units_export_path", return_value=None),
        ):
            result = runner.invoke(app, _BASE_ARGS + extra_args)
        return result, captured

    def test_severity_flag_lands_in_record(self):
        result, record = self._run(["--severity", "critical"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(record.get("severity"), "critical")

    def test_severity_case_normalized(self):
        result, record = self._run(["--severity", "High"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(record.get("severity"), "high")

    def test_invalid_severity_rejected(self):
        result, record = self._run(["--severity", "urgent"])
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(record, {}, "prepare_observation_ingest must never run on invalid severity")
        # render_error panels to stderr; which stream the runner captures varies by
        # click version, so check both for a single stable token.
        streams = result.output
        try:
            streams += result.stderr
        except ValueError:
            pass
        self.assertIn("critical", streams)

    def test_omitted_severity_stays_none(self):
        result, record = self._run([])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIsNone(record.get("severity"))


if __name__ == "__main__":
    unittest.main()
