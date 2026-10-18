"""Hermetic defaults so tests cannot reach the operator config or live data dirs."""

from __future__ import annotations

import os

import tests.fixtures.issue_286_real_home_capture  # noqa: F401  # capture operator HOME first

_INNER_BWRAP_WORKER = os.environ.get("CONVMEM_ISSUE_286_INNER_BWRAP_WORKER") == "1"

if not _INNER_BWRAP_WORKER:
    from tests.fixtures.issue_286_host_isolation import (
        bootstrap_issue_286_host_isolation_at_import,
        configure_issue_286_isolation_for_pytest,
    )

    bootstrap_issue_286_host_isolation_at_import()


def pytest_configure(config):  # noqa: ARG001
    if _INNER_BWRAP_WORKER:
        return
    from tests.fixtures.issue_286_host_isolation import configure_issue_286_isolation_for_pytest

    configure_issue_286_isolation_for_pytest()


from pathlib import Path  # pylint: disable=unused-import

import pytest


@pytest.fixture(autouse=True)
def _block_live_config_and_writer_defaults(tmp_path, monkeypatch):
    """Point every session-default live path at a nonexistent scratch location."""
    missing = tmp_path / "hermetic-missing"
    import chroma_write_store
    import config
    import writer_census

    if os.environ.get("SAFE_HARBOR_T3_BOOTSTRAPPED") != "1":
        if os.environ.get("CONVMEM_ISSUE_286_HOST_ISOLATION_INSTALLED") == "1":
            isolated_home = os.environ.get("HOME")
            default_cfg = (
                Path(isolated_home).expanduser() / ".config" / "convmem" / "config.toml"
                if isolated_home
                else missing / "config.toml"
            )
            monkeypatch.setattr(config, "CONFIG_PATH", default_cfg)
        else:
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
