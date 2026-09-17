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
from unittest import mock

import requests

from ingest import (
    ProviderUnavailableError,
    UnsupportedSourceError,
    _provider_fatal,
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
