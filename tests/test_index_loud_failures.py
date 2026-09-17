"""`index --file` must fail loudly instead of silently ingesting nothing.

Both regressions here reported success while doing no work: an unrecognized
transcript returned files_processed=0 with exit 0, and an exhausted provider
balance ground through every remaining chunk (2-3 doomed calls plus 15s of
retry sleep each) until the watch subprocess hit its 900s timeout.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import ClassVar
from unittest import mock

import requests

from ingest import (
    ProviderUnavailableError,
    UnsupportedSourceError,
    _provider_fatal,
    build_chunk_artifact,
    index,
)


def _http_error(status: int) -> requests.exceptions.HTTPError:
    response = requests.Response()
    response.status_code = status
    return requests.exceptions.HTTPError(f"{status} error", response=response)


class ProviderFatalTests(unittest.TestCase):
    def test_billing_and_auth_refusals_are_fatal(self):
        for status in (401, 402, 403):
            with self.subTest(status=status):
                self.assertEqual(_provider_fatal(_http_error(status)), status)

    def test_transient_and_rate_limit_are_not_fatal(self):
        for status in (429, 500, 502, 503):
            with self.subTest(status=status):
                self.assertIsNone(_provider_fatal(_http_error(status)))

    def test_non_http_errors_are_not_fatal(self):
        self.assertIsNone(_provider_fatal(TimeoutError("slow")))
        self.assertIsNone(_provider_fatal(ValueError("nope")))

    def test_error_types_are_distinct(self):
        self.assertFalse(issubclass(ProviderUnavailableError, UnsupportedSourceError))


class UnsupportedSourceTests(unittest.TestCase):
    def test_named_file_without_adapter_raises(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "claude-transcript.jsonl"
            path.write_text('{"type":"user","message":{"content":"hi"}}\n')
            with mock.patch("ingest.get_parser", return_value=None), self.assertRaises(
                UnsupportedSourceError
            ) as ctx:
                index(force_file=str(path), verbose=False)
            self.assertIn(str(path), str(ctx.exception))

    def test_bulk_scan_still_ignores_unsupported_files(self):
        """Only an explicitly named file is an error; inventory sweeps skip."""
        with mock.patch("ingest.get_parser", return_value=None), mock.patch(
            "ingest._files_from_inventory",
            return_value=[{"path": "/nope/unsupported.bin"}],
        ):
            stats = index(verbose=False)
        self.assertEqual(stats["files_processed"], 0)


if __name__ == "__main__":
    unittest.main()


class AbortOnProviderRefusalTests(unittest.TestCase):
    """build_chunk_artifact performs no Chroma writes, so aborting there is safe."""

    CHUNK: ClassVar[dict] = {
        "messages": [{"role": "user", "content": "hello", "timestamp": None}],
        "start_offset": 0,
        "end_offset": 0,
    }
    MODELS: ClassVar[dict] = {
        "summarize_model": "deepseek-v4-flash",
        "distill_model": "deepseek-v4-flash",
        "embed_model": "nomic-embed-text:latest",
        "ollama_host": "http://localhost:11434",
    }

    def _build(self):
        return build_chunk_artifact(
            chunk=self.CHUNK,
            path="/tmp/session.jsonl",
            path_key="/tmp/session.jsonl",
            models=self.MODELS,
            tool="codex",
            chunk_size=60,
            overlap=10,
            min_confidence=0.6,
            verbose=False,
            retry_sleep=False,
        )

    def test_billing_refusal_aborts_immediately(self):
        with mock.patch(
            "ingest.summarize", side_effect=_http_error(402)
        ) as sm, self.assertRaises(ProviderUnavailableError) as ctx:
            self._build()
        self.assertEqual(sm.call_count, 1, "must not retry a doomed call")
        self.assertIn("402", str(ctx.exception))

    def test_server_error_still_retries_then_gives_up_quietly(self):
        with mock.patch("ingest.summarize", side_effect=_http_error(503)) as sm:
            self.assertIsNone(self._build())
        self.assertGreater(sm.call_count, 1, "5xx stays retryable")
