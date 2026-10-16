"""Hermetic defaults so tests cannot reach the operator config or live data dirs."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _block_live_config_and_writer_defaults(tmp_path, monkeypatch):
    """Point every session-default live path at a nonexistent scratch location."""
    missing = tmp_path / "hermetic-missing"
    import chroma_write_store
    import config
    import writer_census

    if os.environ.get("SAFE_HARBOR_T3_BOOTSTRAPPED") != "1":
        # Under main's launcher, CONVMEM_CONFIG already names the fixture config.
        monkeypatch.setattr(config, "CONFIG_PATH", missing / "config.toml")
    monkeypatch.setattr(
        chroma_write_store,
        "DEFAULT_WRITER_LOCK",
        missing / "locks" / "chroma_writer_gate.lock",
    )
    monkeypatch.setattr(
        chroma_write_store,
        "DEFAULT_ATTEST_DIR",
        missing / "writer_attestations",
    )
    monkeypatch.setattr(
        writer_census,
        "DEFAULT_CENSUS_DIR",
        missing / "writer-census",
    )
    monkeypatch.setattr(
        config,
        "DEFAULT_INCREMENTAL_JSONL_STATE_DIR",
        str(missing / "incremental-jsonl"),
    )
