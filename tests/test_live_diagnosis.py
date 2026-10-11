"""Hermetic unit tests for live_diagnosis phase and scratch guards."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from live_diagnosis import LiveDiagnosisRefused, active, mark


@pytest.fixture()
def scratch_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    roots = json.dumps([str(tmp_path)])
    phase = tmp_path / "phases.jsonl"
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", roots)
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_PHASE_PATH", str(phase))
    return tmp_path, phase


def test_inactive_without_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", raising=False)
    assert not active()
    mark("noop")


def test_mark_appends_under_scratch(scratch_env) -> None:
    tmp_path, phase = scratch_env
    mark("index_hash_done", file_hash="abc")
    lines = phase.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["phase"] == "index_hash_done"
    assert payload["file_hash"] == "abc"
    assert tmp_path in Path(os.environ["CONVMEM_LIVE_DIAG_PHASE_PATH"]).parents


def test_phase_path_outside_scratch_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    outside = Path("/tmp/convmem-live-diag-outside-phase.jsonl")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([str(other)]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_PHASE_PATH", str(outside))
    with pytest.raises(LiveDiagnosisRefused, match="phase_path_outside_scratch"):
        mark("index_hash")


def test_source_drift_fail_closed(scratch_env, monkeypatch: pytest.MonkeyPatch) -> None:
    _, phase = scratch_env
    source = phase.parent / "source.jsonl"
    source.write_text('{"role":"user"}\n', encoding="utf-8")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", "0" * 64)
    from live_diagnosis import assert_source_unchanged

    with pytest.raises(LiveDiagnosisRefused, match="source_identity_drift"):
        assert_source_unchanged(source)
