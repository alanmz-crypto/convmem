"""Embedding adapters for shadow build / eval (fake, HTTP-fake, Ollama)."""

from __future__ import annotations

import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable
from urllib.request import Request, urlopen

EmbedFn = Callable[[str], list[float]]


def fake_embed_fn(dimensions: int) -> EmbedFn:
    def _embed(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vals = []
        for i in range(dimensions):
            vals.append((digest[i % len(digest)] / 255.0) * 0.5 + (i * 0.0001))
        return vals

    return _embed


def http_embed_fn(host: str, model: str, dimensions: int) -> EmbedFn:
    """Call Ollama-compatible /api/embeddings on host (may be fake HTTP server)."""

    def _embed(text: str) -> list[float]:
        url = host.rstrip("/") + "/api/embeddings"
        payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        emb = data.get("embedding")
        if not isinstance(emb, list) or len(emb) != dimensions:
            raise ValueError(
                f"embed host returned dim {0 if not isinstance(emb, list) else len(emb)}; "
                f"expected {dimensions}"
            )
        return [float(x) for x in emb]

    return _embed


def ollama_embed_fn(host: str, model: str) -> EmbedFn:
    """Production Ollama adapter — Gate 1 tests must not invoke a live host."""

    def _embed(text: str) -> list[float]:
        from llm import ollama_embed

        return list(ollama_embed(text, model=model, host=host))

    return _embed


class FakeEmbedServerState:
    """Shared mutable state for fake / canary embed HTTP servers."""

    def __init__(
        self,
        *,
        dimensions: int,
        wrong_dimensions: int | None = None,
        force_wrong_dim: bool = False,
    ) -> None:
        self.dimensions = dimensions
        self.wrong_dimensions = wrong_dimensions
        self.force_wrong_dim = force_wrong_dim
        self.request_count = 0
        self.lock = threading.Lock()
        self.prompts: list[str] = []

    def record(self, prompt: str) -> None:
        with self.lock:
            self.request_count += 1
            self.prompts.append(prompt)

    def snapshot_count(self) -> int:
        with self.lock:
            return self.request_count


def _make_handler(state: FakeEmbedServerState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:  # noqa: A003
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length)
            try:
                body = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                return
            text = str(body.get("prompt") or "")
            state.record(text)
            dims = state.dimensions
            if state.force_wrong_dim and state.wrong_dimensions is not None:
                dims = state.wrong_dimensions
            emb = fake_embed_fn(dims)(text)
            payload = json.dumps({"embedding": emb}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler


def start_fake_embed_server(
    dimensions: int = 8,
    *,
    wrong_dimensions: int | None = None,
    force_wrong_dim: bool = False,
) -> tuple[HTTPServer, str, threading.Thread, FakeEmbedServerState]:
    """Start localhost fake /api/embeddings. Returns server, url, thread, state."""
    state = FakeEmbedServerState(
        dimensions=dimensions,
        wrong_dimensions=wrong_dimensions,
        force_wrong_dim=force_wrong_dim,
    )
    handler = _make_handler(state)
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}", thread, state


def start_canary_embed_server() -> tuple[HTTPServer, str, threading.Thread, FakeEmbedServerState]:
    """Live-canary endpoint: records requests; isolation tests require count==0."""
    return start_fake_embed_server(dimensions=8)


def stop_fake_embed_server(server: HTTPServer) -> None:
    server.shutdown()
    server.server_close()
