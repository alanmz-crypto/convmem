"""Hermetic subprocess hooks for repository-knowledge acceptance tests only."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


if os.environ.get("CONVMEM_RK_SUBPROCESS_TEST") == "1":
    import chroma_write_store
    import llm

    def _fake_embed(text, model=None, host=None):
        del model, host
        vector = [0.0] * 48
        for token in str(text or "").lower().replace("/", " ").replace("-", " ").split():
            digest = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            vector[digest % len(vector)] += 1.0
        norm = sum(value * value for value in vector) ** 0.5 or 1.0
        return [value / norm for value in vector]

    llm.ollama_embed = _fake_embed
    chroma_write_store.DEFAULT_WRITER_LOCK = Path(
        os.environ["CONVMEM_RK_WRITER_LOCK"]
    )
    chroma_write_store.DEFAULT_ATTEST_DIR = Path(
        os.environ["CONVMEM_RK_ATTEST_DIR"]
    )
