"""Bounded transient-retry tests for the DeepSeek streaming path.

Covers the fix for ``llm._deepseek_generate_stream`` via the public
``llm.generate_stream`` entrypoint: a transient streaming drop (urllib3
"Response ended prematurely" -> ConnectionError, timeout, or 5xx) before any
token is yielded is retried once; once tokens have been yielded the failure is
propagated (caller partial-answer path); 4xx auth errors are never retried.
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
    def __init__(self, *, status_code=None, transient=False, lines=None):
        self._status = status_code
        self._transient = transient
        self._lines = lines or ["data: [DONE]"]

    def raise_for_status(self):
        if self._status is not None:
            raise requests.exceptions.HTTPError(
                response=type("R", (), {"status_code": self._status})()
            )

    def iter_lines(self, decode_unicode=True):  # pylint: disable=unused-argument
        if self._transient:
            raise requests.exceptions.ConnectionError("Response ended prematurely")
        yield from self._lines


class DeepSeekStreamRetryTests(unittest.TestCase):
    def setUp(self):
        os.environ["DEEPSEEK_API_KEY"] = "test-key"

    def tearDown(self):
        os.environ.pop("DEEPSEEK_API_KEY", None)

    def _stream(self, resp_factory, **kwargs):
        calls = {"n": 0}

        def _post(*_args, **_kwargs):
            calls["n"] += 1
            return resp_factory(calls["n"])

        with mock.patch.object(requests, "post", _post):
            out = list(
                llm.generate_stream(
                    "prompt",
                    model="deepseek-v4-flash",
                    ollama_host="http://localhost:11434",
                    deepseek_base_url="https://api.deepseek.com",
                    timeout=30,
                    **kwargs,
                )
            )
        return out, calls["n"]

    def test_transient_drop_then_success_is_retried(self):
        def factory(attempt):
            if attempt == 1:
                return _StubResp(transient=True)
            return _StubResp(lines=[_sse("Hi"), "data: [DONE]"])

        out, n = self._stream(factory)
        self.assertEqual(n, 2)
        self.assertEqual(out, ["Hi"])

    def test_partial_tokens_not_retried(self):
        def factory(_attempt):
            def gen():
                yield _sse("A")
                yield _sse("B")
                raise requests.exceptions.ConnectionError("end")
            return _StubResp(lines=gen())

        calls = {"n": 0}

        def _post(*_args, **_kwargs):
            calls["n"] += 1
            return factory(calls["n"])

        with mock.patch.object(requests, "post", _post):
            with self.assertRaises(requests.exceptions.ConnectionError):
                list(
                    llm.generate_stream(
                        "prompt",
                        model="deepseek-v4-flash",
                        ollama_host="http://localhost:11434",
                        deepseek_base_url="https://api.deepseek.com",
                        timeout=30,
                    )
                )
        # A retry would have produced a second call; assert exactly one.
        self.assertEqual(calls["n"], 1)

    def test_401_not_retried(self):
        n = self._http_calls(status=401)
        self.assertEqual(n, 1)

    def test_500_is_retried(self):
        n = self._http_calls(status=500)
        self.assertEqual(n, 2)

    def _http_calls(self, status):
        calls = {"n": 0}

        def _post(*_args, **_kwargs):
            calls["n"] += 1
            return _StubResp(status_code=status)

        with mock.patch.object(requests, "post", _post):
            with self.assertRaises(requests.exceptions.HTTPError):
                list(
                    llm.generate_stream(
                        "prompt",
                        model="deepseek-v4-flash",
                        ollama_host="http://localhost:11434",
                        deepseek_base_url="https://api.deepseek.com",
                        timeout=30,
                    )
                )
        return calls["n"]

    def test_retries_exhausted_propagates(self):
        calls = {"n": 0}

        def _post(*_args, **_kwargs):
            calls["n"] += 1
            return _StubResp(transient=True)

        with mock.patch.object(requests, "post", _post):
            with self.assertRaises(requests.exceptions.ConnectionError):
                list(
                    llm.generate_stream(
                        "prompt",
                        model="deepseek-v4-flash",
                        ollama_host="http://localhost:11434",
                        deepseek_base_url="https://api.deepseek.com",
                        timeout=30,
                    )
                )
        self.assertEqual(calls["n"], 2)  # default max_attempts=2


if __name__ == "__main__":
    unittest.main()
