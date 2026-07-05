"""P1c Phase 1 — partial synthesis on stream timeout."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ask import ask


def _fake_unit(score: float = 0.9) -> dict:
    return {
        "id": "u1",
        "document": "convmem ask uses a 45s synthesis timeout.",
        "score": score,
        "metadata": {
            "title": "Ask timeout",
            "type": "decision",
            "tool": "cursor",
            "source_path": "/tmp/x",
            "ledger_id": "dec_prop_test_001",
            "domain": "coding.tooling",
            "author_model": "test",
        },
    }


class TestAskStreaming(unittest.TestCase):
    @patch("ask.query_units", return_value=[_fake_unit()])
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_partial_answer_on_timeout(self, mock_stream, mock_cfg, _units):
        mock_cfg.return_value = {
            "models": {
                "distill_model": "deepseek-v4-flash",
                "ollama_host": "http://127.0.0.1:11434",
                "deepseek_base_url": "https://api.deepseek.com",
            }
        }

        def _tokens():
            yield "Partial "
            yield "answer."
            raise TimeoutError("synthesis exceeded 45.0s wall clock")

        mock_stream.return_value = _tokens()

        out = ask("What happens on ask timeout?", top_k=3)

        self.assertIn("Partial answer.", out["answer"])
        self.assertIn("[Synthesis interrupted (TimeoutError)", out["answer"])
        self.assertNotIn("synthesis_failed", out)
        self.assertTrue(out.get("synthesis_interrupted"))
        self.assertIn("partial answer returned", (out.get("warning") or "").lower())

    @patch("ask.query_units", return_value=[_fake_unit()])
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    @patch("ask._log_synthesis_failure")
    def test_empty_buffer_still_falls_back_to_citations(
        self, mock_log, mock_stream, mock_cfg, _units
    ):
        mock_cfg.return_value = {
            "models": {
                "distill_model": "deepseek-v4-flash",
                "ollama_host": "http://127.0.0.1:11434",
                "deepseek_base_url": "https://api.deepseek.com",
            }
        }

        def _fail_immediately():
            raise TimeoutError("synthesis exceeded 45.0s wall clock")
            yield ""  # pragma: no cover

        mock_stream.return_value = _fail_immediately()

        out = ask("What happens on ask timeout?", top_k=3)

        self.assertTrue(out.get("synthesis_failed"))
        self.assertIn("[Synthesis unavailable", out["answer"])
        self.assertIn("Ask timeout", out["answer"])
        mock_log.assert_called_once()

    @patch("ask.query_units", return_value=[_fake_unit()])
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_complete_stream_unchanged(self, mock_stream, mock_cfg, _units):
        mock_cfg.return_value = {
            "models": {
                "distill_model": "deepseek-v4-flash",
                "ollama_host": "http://127.0.0.1:11434",
                "deepseek_base_url": "https://api.deepseek.com",
            }
        }
        mock_stream.return_value = iter(["Full ", "answer."])

        out = ask("test question", top_k=3)

        self.assertEqual(out["answer"], "Full answer.")
        self.assertNotIn("synthesis_failed", out)
        self.assertNotIn("interrupted", (out.get("warning") or "").lower())


class TestGenerateStreamParsing(unittest.TestCase):
    def test_ollama_ndjson_yields_tokens(self):
        from llm import _ollama_generate_stream

        class FakeResp:
            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True):
                yield '{"response":"Hello","done":false}'
                yield '{"response":" world","done":true}'

        with patch("llm.requests.post", return_value=FakeResp()):
            tokens = list(_ollama_generate_stream("p", "m", "http://localhost:11434"))
        self.assertEqual(tokens, ["Hello", " world"])

    def test_deepseek_sse_yields_tokens(self):
        from llm import _deepseek_generate_stream

        class FakeResp:
            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True):
                yield 'data: {"choices":[{"delta":{"content":"Hi"}}]}'
                yield "data: [DONE]"

        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "test-key"}):
            with patch("llm.requests.post", return_value=FakeResp()):
                tokens = list(
                    _deepseek_generate_stream("p", "m", "https://api.deepseek.com")
                )
        self.assertEqual(tokens, ["Hi"])


if __name__ == "__main__":
    unittest.main()
