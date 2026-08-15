"""Shared config helpers for CG-2 serving tests."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

import pytest

from serving_index_repository import open_serving_index_repository


def serving_test_cfg(tmp_path: Path, chroma: Path) -> dict:
    return {
        "models": {
            "embed_model": "nomic-embed-text",
            "ollama_host": "http://localhost:11434",
            "rerank_model": "rerank",
        },
        "query": {
            "rerank": False,
            "recency_weight": 0.0,
            "top_k_candidates": 5,
        },
        "index": {
            "chroma_dir": str(chroma),
            "generation_root": str(tmp_path / "file_generations"),
            "processed_log": str(tmp_path / "processed.json"),
        },
    }


def assert_serving_open_raises(
    cfg: dict,
    exc_type: type[BaseException],
    *,
    patch_target: str | None = None,
    patch_side_effect: Callable[..., object] | BaseException | None = None,
) -> None:
    ctx = (
        patch(patch_target, side_effect=patch_side_effect)
        if patch_target is not None
        else nullcontext()
    )
    with pytest.raises(exc_type):
        with ctx:
            with open_serving_index_repository(cfg):
                pass
