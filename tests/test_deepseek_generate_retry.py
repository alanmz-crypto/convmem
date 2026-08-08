"""Bounded transient-retry tests for the non-streaming DeepSeek path.

Covers the sibling fix to ``llm._deepseek_generate`` (used by ``generate()``
and the distill stage): a transient chunked-response drop (ChunkedEncodingError
-> ConnectionError, timeout, or 5xx) is retried a bounded number of times,
while 4xx auth errors are never retried. Tested against the internal function
so the retry knobs (max_attempts / retry_backoff) can be exercised directly.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

import requests

import llm


class _StubResp:
    def __init__(self, *, status_code=None, transient=False, body=None):
        self._status = status_code
        self._transient = transient
        self._body = body or {"choices": [{"message": {"content": "OK"}}]}

    def raise_for_status(self):
        if self._status is not None:
            raise requests.exceptions.HTTPError(
                response=type("R", (), {"status_code": self._status})()
            )

    def json(self):  # noqa: D102
        if self._transient:
            raise requests.exceptions.ConnectionError(
                "ChunkedEncodingError: Response ended prematurely"
            )
        return self._body


class DeepSeekGenerateRetryTests(unittest.TestCase):
    def setUp(self):
        os.environ["DEEPSEEK_API_KEY"] = "test-key"

    def tearDown(self):
        os.environ.pop("DEEPSEEK_API_KEY", None)

    def _run(self, resp_factory, **kwargs):
        calls = {"n": 0}

        def _post(*_args, **_kwargs):
            calls["n"] += 1
            return resp_factory(calls["n"])

        with mock.patch.object(requests, "post", _post):
            out = llm._deepseek_generate(   # pylint: disable=protected-access
                "prompt", "deepseek-v4-flash", "https://api.deepseek.com",
                retry_backoff=0.001, **kwargs,
            )
        return out, calls

    def test_transient_drop_then_success_retried(self):
        def factory(attempt):
            return _StubResp(transient=attempt == 1)

        out, calls = self._run(factory)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(out, "OK")

    def test_401_not_retried(self):
        calls, _post = self._caller(lambda _a: _StubResp(status_code=401))
        with mock.patch.object(requests, "post", _post):
            with self.assertRaises(requests.exceptions.HTTPError):
                llm._deepseek_generate(  # pylint: disable=protected-access
                    "prompt", "deepseek-v4-flash", "https://api.deepseek.com",
                )
        self.assertEqual(calls["n"], 1)

    def test_500_is_retried(self):
        calls, _post = self._caller(lambda _a: _StubResp(status_code=500))
        with mock.patch.object(requests, "post", _post):
            with self.assertRaises(requests.exceptions.HTTPError):
                llm._deepseek_generate(  # pylint: disable=protected-access
                    "prompt", "deepseek-v4-flash", "https://api.deepseek.com",
                    retry_backoff=0.001,
                )
        self.assertEqual(calls["n"], 2)

    def test_retries_exhausted_propagates(self):
        calls, _post = self._caller(lambda _a: _StubResp(transient=True))
        with mock.patch.object(requests, "post", _post):
            with self.assertRaises(requests.exceptions.ConnectionError):
                llm._deepseek_generate(  # pylint: disable=protected-access
                    "prompt", "deepseek-v4-flash", "https://api.deepseek.com",
                    retry_backoff=0.001, max_attempts=3,
                )
        self.assertEqual(calls["n"], 3)

    def _caller(self, resp_factory):
        calls = {"n": 0}

        def _post(*_args, **_kwargs):
            calls["n"] += 1
            return resp_factory(calls["n"])

        return calls, _post


if __name__ == "__main__":
    unittest.main()
