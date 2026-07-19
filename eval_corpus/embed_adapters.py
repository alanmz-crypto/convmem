"""Embedding adapters for shadow build / eval (fake, HTTP-fake, Ollama)."""

from __future__ import annotations

import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable
from urllib.parse import urlparse
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


class _FakeEmbedHandler(BaseHTTPRequestHandler):
    dimensions: int = 8

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
        emb = fake_embed_fn(self.dimensions)(text)
        payload = json.dumps({"embedding": emb}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def start_fake_embed_server(dimensions: int = 8) -> tuple[HTTPServer, str, threading.Thread]:
    """Start localhost fake /api/embeddings server. Returns (server, base_url, thread)."""

    class Handler(_FakeEmbedHandler):
        pass

    Handler.dimensions = dimensions
    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}", thread


def stop_fake_embed_server(server: HTTPServer) -> None:
    server.shutdown()
    server.server_close()
