# pylint: disable=redefined-outer-name
"""Hermetic unit tests for live_diagnosis phase and scratch guards."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from live_diagnosis import LiveDiagnosisRefused, active, emit_denial_event, mark

from tests.watch_oom_live_diagnosis_support import assert_denial_events_empty


@pytest.fixture()
def diag_scratch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    roots = json.dumps([str(tmp_path)])
    phase = tmp_path / "phases.jsonl"
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", roots)
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_PHASE_PATH", str(phase))
    return tmp_path, phase


def test_inactive_without_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", raising=False)
    assert not active()
    mark("noop")


def test_mark_appends_under_scratch(diag_scratch) -> None:
    tmp_path, phase = diag_scratch
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


def test_denial_event_visible_to_parent(diag_scratch, monkeypatch: pytest.MonkeyPatch) -> None:
    tmp_path, _phase = diag_scratch
    denial = tmp_path / "denials.jsonl"
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_DENIAL_PATH", str(denial))
    emit_denial_event("network", "outbound")
    assert denial.is_file()
    with pytest.raises(RuntimeError, match="denial_event_recorded"):
        assert_denial_events_empty(denial)


def test_phase_mark_uses_o1_counter(diag_scratch, monkeypatch: pytest.MonkeyPatch) -> None:
    _ = diag_scratch
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_PHASE_LINES", "0")
    mark("one")
    mark("two")
    assert os.environ["CONVMEM_LIVE_DIAG_PHASE_LINES"] == "2"


def test_source_drift_fail_closed(diag_scratch, monkeypatch: pytest.MonkeyPatch) -> None:
    _, phase = diag_scratch
    source = phase.parent / "source.jsonl"
    source.write_text('{"role":"user"}\n', encoding="utf-8")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", "0" * 64)
    from live_diagnosis import assert_source_unchanged

    with pytest.raises(LiveDiagnosisRefused, match="source_identity_drift"):
        assert_source_unchanged(source)
