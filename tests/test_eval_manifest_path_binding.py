"""Tests for explicit real-manifest config and enrichment path bindings."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_script(name: str):
    path = Path(__file__).parents[1] / "scripts" / name
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_manifest_path_binding_requires_exact_key(tmp_path):
    module = _load_script("eval_shadow_embed.py")
    expected = (tmp_path / "baseline.toml").resolve()
    assert module._manifest_bound_path(  # pylint: disable=protected-access
        {"paths": {"baseline_config": str(expected)}},
        key="baseline_config",
        label="baseline config",
    ) == expected
    with pytest.raises(ValueError, match="challenger_config"):
        module._manifest_bound_path(  # pylint: disable=protected-access
            {"paths": {}}, key="challenger_config", label="challenger config"
        )


def test_compare_manifest_path_binding_requires_exact_key(tmp_path):
    module = _load_script("eval_embed_compare.py")
    expected = (tmp_path / "challenger.jsonl").resolve()
    assert module._manifest_path(  # pylint: disable=protected-access
        {"paths": {"challenger_enrichment_path": str(expected)}},
        "challenger_enrichment_path",
        label="challenger enrichment",
    ) == expected
    with pytest.raises(ValueError, match="baseline_config"):
        module._manifest_path(  # pylint: disable=protected-access
            {"paths": {}}, "baseline_config", label="baseline config"
        )
