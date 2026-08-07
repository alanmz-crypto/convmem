"""Compare input parsing must use the exact bytes whose hashes are bound."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _compare_module():
    path = Path(__file__).parents[1] / "scripts" / "eval_embed_compare.py"
    spec = importlib.util.spec_from_file_location("eval_embed_compare_input_bytes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_jsonl_loader_returns_hash_of_parsed_bytes(tmp_path):
    module = _compare_module()
    path = tmp_path / "queries.jsonl"
    raw = b'{"query_id":"q1","query":"hello"}\r\n'
    path.write_bytes(raw)
    rows, digest = module._load_jsonl_bytes(path, label="query set")
    assert rows == [{"query_id": "q1", "query": "hello"}]
    import hashlib

    assert digest == hashlib.sha256(raw).hexdigest()


def test_real_jsonl_loader_rejects_blank_lines(tmp_path):
    module = _compare_module()
    path = tmp_path / "queries.jsonl"
    path.write_bytes(b'{"query_id":"q1"}\n\n')
    with pytest.raises(ValueError, match="blank line"):
        module._load_jsonl_bytes(path, label="query set")
