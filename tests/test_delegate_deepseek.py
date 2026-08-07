"""Regression coverage for the bounded DeepSeek delegation helper."""

from __future__ import annotations

import json
import os
import subprocess
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "delegate-deepseek.sh"


@contextmanager
def _mock_deepseek(response: dict) -> Iterator[str]:
    """Serve one deterministic OpenAI-compatible response locally."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - HTTP handler API name
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _run(base_url: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "DEEPSEEK_API_KEY": "test-key-not-a-secret",
            "DEEPSEEK_BASE_URL": base_url,
            "DEEPSEEK_MODEL": "deepseek-v4-flash",
        }
    )
    return subprocess.run(
        [str(SCRIPT), "bounded test prompt"],
        capture_output=True,
        check=False,
        text=True,
        env=env,
        timeout=15,
    )


def _receipt(stderr: str) -> dict:
    receipts = [
        json.loads(line)
        for line in stderr.splitlines()
        if line.startswith("{") and '"event": "delegate_receipt"' in line
    ]
    assert len(receipts) == 1, stderr
    return receipts[0]


def test_normal_text_response_prints_text_and_usage_receipt():
    response = {
        "model": "deepseek-v4-flash",
        "choices": [{"message": {"content": "review complete"}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 2},
    }
    with _mock_deepseek(response) as base_url:
        result = _run(base_url)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "review complete\n"
    receipt = _receipt(result.stderr)
    assert receipt["model"] == "deepseek-v4-flash"
    assert receipt["status"] == "api_response"
    assert isinstance(receipt["elapsed_ms"], int)
    assert receipt["usage"] == response["usage"]


def test_empty_response_fails_but_emits_unavailable_usage_receipt():
    response = {
        "model": "deepseek-v4-flash",
        "choices": [{"message": {"content": "", "reasoning_content": ""}}],
    }
    with _mock_deepseek(response) as base_url:
        result = _run(base_url)

    assert result.returncode == 3
    assert result.stdout == ""
    assert "contained neither content nor reasoning_content" in result.stderr
    receipt = _receipt(result.stderr)
    assert receipt["model"] == "deepseek-v4-flash"
    assert receipt["status"] == "api_response"
    assert receipt["usage"] == "unavailable"
