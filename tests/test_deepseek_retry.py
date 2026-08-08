"""Bounded transient-retry tests for both DeepSeek paths.

Covers the streaming path (``llm._deepseek_generate_stream``, used by ask
synthesis) and the non-streaming path (``llm._deepseek_generate``, used by
``generate()``/distill): a transient respons drop (urllib3 "Response ended
prematurely" / ChunkedEncodingError -> ConnectionError, timeout, or 5xx)
before any output is retried a bounded number of times, mid-stream failures
after tokens are propagated, and 4xx auth errors are never retried.
"""

from __future__ import annotations

import json
import os
import unittest
from unittest import mock

import requests

import llm


def _sse(content: str) -> str:
    return "data: " + json.dumps({"choices": [{"delta": {"content": content}}]})


class _StubResp:
    def __init__(self, *, status_code=None, transient=False, lines=None, body=None):
        self._status = status_code
        self._transient = transient
        self._lines = lines or ["data: [DONE]"]
        self._body = body or {"choices": [{"message": {"content": "OK"}}]}

    def raise_for_status(self):
        if self._status is not None:
            raise requests.exceptions.HTTPError(
                response=type("R", (), {"status_code": self._status})()
            )

    def json(self):  # noqa: D102
        if self._transient:
            raise requests.exceptions.ConnectionError(
                "Response ended prematurely (ChunkedEncodingError)"
            )
        return self._body

    def iter_lines(self, decode_unicode=True):  # noqa: U100; pylint: disable=unused-argument
        if self._transient:
            raise requests.exceptions.ConnectionError(
                "Response ended prematurely (ChunkedEncodingError)"
            )
        yield from self._lines


def _post_harness(resp_factory):
    """Return (calls, _post) where _post increments calls and returns resp_factory(n)."""
    calls = {"n": 0}

    def _post(*_args, **_kwargs):
        calls["n"] += 1
        return resp_factory(calls["n"])

    return calls, _post


class DeepSeekStreamRetryTests(unittest.TestCase):
    def setUp(self):
        os.environ["DEEPSEEK_API_KEY"] = "test-key"

    def tearDown(self):
        os.environ.pop("DEEPSEEK_API_KEY", None)

    def _stream(self, resp_factory, **kwargs):
        calls, _post = _post_harness(resp_factory)
        with mock.patch.object(requests, "post", _post):
            out = list(
                llm._deepseek_generate_stream(  # pylint: disable=protected-access
                    "prompt",
                    model="deepseek-v4-flash",
                    base_url="https://api.deepseek.com",
                    retry_backoff=0.001,
                    **kwargs,
                )
            )
        return out, calls

    def test_transient_drop_then_success_is_retried(self):
        def factory(attempt):
            if attempt == 1:
                return _StubResp(transient=True)
            return _StubResp(lines=[_sse("Hi"), "data: [DONE]"])

        out, calls = self._stream(factory)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(out, ["Hi"])

    def test_partial_tokens_not_retried(self):
        def factory(_attempt):
            def gen():
                yield _sse("A")
                yield _sse("B")
                raise requests.exceptions.ConnectionError("end")
            return _StubResp(lines=gen())

        calls, _post = _post_harness(factory)
        with mock.patch.object(requests, "post", _post):
            with self.assertRaises(requests.exceptions.ConnectionError):
                list(
                    llm._deepseek_generate_stream(  # pylint: disable=protected-access
                        "prompt", model="deepseek-v4-flash",
                        base_url="https://api.deepseek.com",
                    )
                )
        self.assertEqual(calls["n"], 1)

    def test_stream_401_not_retried(self):
        calls, _post = _post_harness(lambda _a: _StubResp(status_code=401))
        with mock.patch.object(requests, "post", _post):
            with self.assertRaises(requests.exceptions.HTTPError):
                list(
                    llm._deepseek_generate_stream(  # pylint: disable=protected-access
                        "prompt", model="deepseek-v4-flash",
                        base_url="https://api.deepseek.com",
                    )
                )
        self.assertEqual(calls["n"], 1)

    def test_stream_500_is_retried(self):
        calls, _post = _post_harness(lambda _a: _StubResp(status_code=500))
        with mock.patch.object(requests, "post", _post):
            with self.assertRaises(requests.exceptions.HTTPError):
                list(
                    llm._deepseek_generate_stream(  # pylint: disable=protected-access
                        "prompt", model="deepseek-v4-flash",
                        base_url="https://api.deepseek.com",
                        retry_backoff=0.001,
                    )
                )
        self.assertEqual(calls["n"], 2)


class DeepSeekGenerateRetryTests(unittest.TestCase):
    def setUp(self):
        os.environ["DEEPSEEK_API_KEY"] = "test-key"

    def tearDown(self):
        os.environ.pop("DEEPSEEK_API_KEY", None)

    def _generate(self, resp_factory, **kwargs):
        calls, _post = _post_harness(resp_factory)
        with mock.patch.object(requests, "post", _post):
            out = llm._deepseek_generate(  # pylint: disable=protected-access
                "prompt", "deepseek-v4-flash", "https://api.deepseek.com",
                retry_backoff=0.001, **kwargs,
            )
        return out, calls

    def test_generate_transient_drop_then_success_retried(self):
        def factory(attempt):
            return _StubResp(transient=attempt == 1)

        out, calls = self._generate(factory)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(out, "OK")

    def test_generate_401_not_retried(self):
        calls, _post = _post_harness(lambda _a: _StubResp(status_code=401))
        with mock.patch.object(requests, "post", _post):
            with self.assertRaises(requests.exceptions.HTTPError):
                llm._deepseek_generate(  # pylint: disable=protected-access
                    "prompt", "deepseek-v4-flash", "https://api.deepseek.com",
                )
        self.assertEqual(calls["n"], 1)

    def test_generate_500_is_retried(self):
        calls, _post = _post_harness(lambda _a: _StubResp(status_code=500))
        with mock.patch.object(requests, "post", _post):
            with self.assertRaises(requests.exceptions.HTTPError):
                llm._deepseek_generate(  # pylint: disable=protected-access
                    "prompt", "deepseek-v4-flash", "https://api.deepseek.com",
                    retry_backoff=0.001,
                )
        self.assertEqual(calls["n"], 2)

    def test_generate_retries_exhausted_propagates(self):
        calls, _post = _post_harness(lambda _a: _StubResp(transient=True))
        with mock.patch.object(requests, "post", _post):
            with self.assertRaises(requests.exceptions.ConnectionError):
                llm._deepseek_generate(  # pylint: disable=protected-access
                    "prompt", "deepseek-v4-flash", "https://api.deepseek.com",
                    retry_backoff=0.001, max_attempts=3,
                )
        self.assertEqual(calls["n"], 3)


if __name__ == "__main__":
    unittest.main()
