"""C6 scratch-canary contract tests; no production path is opened for write."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import pytest

from shadow_canary import (
    APPROVED_BUDGETS,
    CanaryInputs,
    CanaryRefused,
    CanaryReport,
    MountIdentity,
    TimingSample,
    _private_child,
    _run_workload,
    cold_open_validation_ms,
    evaluate_cell,
    inputs_from_cli_values,
    live_rollback_required,
    redacted_report,
    run_shadow_canary,
    seed_synthetic_ledger,
    validate_scratch_target,
)
from shadow_authorization import ensure_private_directory
from shadow_ledger import create_shadow_ledger_header, open_existing_shadow_ledger_fd, read_ledger_header_and_tail


def _inputs(tmp_path: Path, *, scratch: Path | None = None) -> CanaryInputs:
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    chroma = data / "chroma"
    chroma.mkdir(exist_ok=True)
    return CanaryInputs(
        scratch_dir=scratch or data / "canary-scratch",
        intended_ledger_path=data / "shadow" / "ledger.jsonl",
        production_chroma_root=chroma,
        current_unit_count=12,
        p50_event_bytes=2_048,
        p95_event_bytes=4_096,
        maximum_event_bytes=8_192,
        peak_writers=2,
        short_lived_opens_per_day=7,
        event_size_evidence_sha256="e" * 64,
        writer_census_sha256="c" * 64,
    )


def _mountinfo(mountpoint: Path, fs: str = "ext4") -> str:
    return f"42 1 0:42 / {mountpoint} rw - {fs} device rw\n"


def _sample(append_ms: float, end_to_end_ms: float = 20.0) -> TimingSample:
    return TimingSample(
        end_to_end_ms=end_to_end_ms,
        complete_append_ms=append_ms,
        lock_wait_ms=1.0,
        ledger_append_ms=append_ms / 2,
        health_persist_ms=append_ms / 2,
    )


def test_approved_budgets_match_ryan_decision() -> None:
    assert APPROVED_BUDGETS.append_p99_ms == 100
    assert APPROVED_BUDGETS.append_max_ms == 500
    assert APPROVED_BUDGETS.degradation_p99_factor == 2
    assert APPROVED_BUDGETS.cold_open_p99_ms == 500
    assert APPROVED_BUDGETS.rollback_p99_ms == 300
    assert APPROVED_BUDGETS.rollback_factor == 3
    assert APPROVED_BUDGETS.rollback_window_seconds == 60
    assert APPROVED_BUDGETS.rollback_min_samples == 100
    assert APPROVED_BUDGETS.horizon_events == 50_000


def test_cli_input_adapter_refuses_incomplete_matrix() -> None:
    with pytest.raises(CanaryRefused, match="canary_input_missing"):
        inputs_from_cli_values({"scratch_dir": Path("/tmp/new")})


def test_scratch_must_be_new_same_mount_private_directory(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    scratch, mount = validate_scratch_target(inputs, mountinfo_text=_mountinfo(tmp_path))
    assert scratch == inputs.scratch_dir
    assert mount.filesystem == "ext4"
    assert scratch.exists()
    assert (scratch.stat().st_mode & 0o777) == 0o700


def test_scratch_refuses_existing_directory(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    inputs.scratch_dir.mkdir()
    with pytest.raises(CanaryRefused, match="canary_scratch_exists"):
        validate_scratch_target(inputs, mountinfo_text=_mountinfo(tmp_path))


def test_scratch_refuses_overlap_with_live_chroma(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path, scratch=tmp_path / "data" / "chroma" / "canary")
    with pytest.raises(CanaryRefused, match="canary_live_path"):
        validate_scratch_target(inputs, mountinfo_text=_mountinfo(tmp_path))


def test_scratch_refuses_an_intended_ledger_inside_chroma(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    inputs = replace(
        inputs, intended_ledger_path=inputs.production_chroma_root / "ledger.jsonl"
    )
    with pytest.raises(CanaryRefused, match="canary_live_path"):
        validate_scratch_target(inputs, mountinfo_text=_mountinfo(tmp_path))


def test_scratch_refuses_mount_mismatch(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path, scratch=tmp_path / "canary-scratch")
    with pytest.raises(CanaryRefused, match="canary_mount_mismatch"):
        validate_scratch_target(
            inputs,
            mountinfo_text=(
                f"42 1 0:42 / {tmp_path / 'data'} rw - ext4 device rw\n"
                f"43 1 0:43 / {tmp_path} rw - xfs device rw\n"
            ),
        )


def test_budget_evaluation_records_absolute_relative_and_cold_limits() -> None:
    passing = evaluate_cell(
        append_samples=[_sample(80.0) for _ in range(100)],
        baseline_samples=[_sample(0.0, end_to_end_ms=50.0) for _ in range(100)],
        cold_open_ms=[450.0, 450.0, 450.0],
    )
    assert passing.passed is True
    assert passing.degradation_p99_factor == pytest.approx(1.6)

    failing = evaluate_cell(
        append_samples=[_sample(101.0) for _ in range(100)],
        baseline_samples=[_sample(0.0, end_to_end_ms=20.0) for _ in range(100)],
        cold_open_ms=[501.0, 501.0, 501.0],
    )
    assert failing.passed is False
    assert set(failing.codes) == {
        "append_p99_exceeded",
        "degradation_p99_exceeded",
        "cold_open_p99_exceeded",
    }


def test_live_rollback_requires_qualified_window() -> None:
    assert "future live monitor" in (live_rollback_required.__doc__ or "")
    assert live_rollback_required([_sample(999.0) for _ in range(99)], disabled_p99_ms=10) is False
    assert live_rollback_required([_sample(301.0) for _ in range(100)], disabled_p99_ms=100) is True
    assert live_rollback_required([_sample(200.0) for _ in range(100)], disabled_p99_ms=100) is False


def test_seeded_ledger_has_bounded_tail_sequence(tmp_path: Path) -> None:
    root = ensure_private_directory(tmp_path / "scratch")
    ledger = root / "ledger.jsonl"
    create_shadow_ledger_header(
        ledger, activation_id="canary", ledger_identity="identity", starting_sequence=0
    )
    seed_synthetic_ledger(ledger, 3)
    fd, dir_fd, _st = open_existing_shadow_ledger_fd(ledger)
    try:
        tail = read_ledger_header_and_tail(fd)
    finally:
        os.close(fd)
        os.close(dir_fd)
    assert tail.next_sequence == 4
    assert tail.last_event["sequence"] == 3


def test_cold_validation_uses_shared_strict_writer_path(tmp_path: Path) -> None:
    root = ensure_private_directory(tmp_path / "scratch")
    elapsed = cold_open_validation_ms(root, 3)
    assert elapsed >= 0


def test_disposable_workload_records_complete_path_without_live_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("shadow_canary.MIN_WARMUP_APPENDS", 1)
    monkeypatch.setattr("shadow_canary.MIN_WARMUP_SECONDS", 0.0)
    root = ensure_private_directory(tmp_path / "scratch")
    result = _run_workload(
        _private_child(root, "workload"),
        event_bytes=128,
        concurrency=1,
        timed_samples=2,
        with_shadow=True,
    )
    assert not result.errors
    assert len(result.samples) == 2
    assert result.elapsed_ms >= 0
    assert all(sample.complete_append_ms is not None for sample in result.samples)
    assert all(sample.health_persist_ms is not None for sample in result.samples)
    assert all(
        sample.complete_append_ms >= sample.health_persist_ms
        for sample in result.samples
        if sample.complete_append_ms is not None and sample.health_persist_ms is not None
    )


def test_redacted_report_hides_scratch_path_and_payload() -> None:
    report = CanaryReport(
        verdict="PASS",
        budgets={"append_p99_ms": 100},
        provenance={"payloads": "synthetic lengths only"},
        evidence_path="/private/scratch/c6-canary-evidence.json",
    )
    rendered = redacted_report(report)
    assert "evidence_path" not in rendered
    assert "/private/scratch" not in str(rendered)


def test_small_hermetic_matrix_retains_private_redacted_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path)
    scratch = inputs.scratch_dir
    mount = MountIdentity("42", "ext4", "rw", "rw", os.stat(tmp_path).st_dev)

    def fake_target(_inputs: CanaryInputs):
        return ensure_private_directory(scratch), mount

    monkeypatch.setattr("shadow_canary.validate_scratch_target", fake_target)
    monkeypatch.setattr("shadow_canary.MIN_TIMED_SAMPLES", 1)
    monkeypatch.setattr("shadow_canary.MIN_WARMUP_APPENDS", 1)
    monkeypatch.setattr("shadow_canary.MIN_WARMUP_SECONDS", 0.0)
    monkeypatch.setattr(
        CanaryInputs, "event_sizes", lambda _self: (("control_1k", 128),)
    )
    monkeypatch.setattr(CanaryInputs, "volumes", lambda _self, _budgets: (("header_only", 0),))
    monkeypatch.setattr(CanaryInputs, "concurrency", lambda _self: (("one_writer", 1),))

    report = run_shadow_canary(inputs, timed_samples=1)
    assert len(report.matrix) == 1
    assert report.evidence_path is not None
    evidence = Path(report.evidence_path)
    assert (evidence.stat().st_mode & 0o777) == 0o600
    assert str(scratch) not in evidence.read_text(encoding="utf-8")


def test_cli_defaults_to_input_refusal() -> None:
    from typer.testing import CliRunner

    from convmem import app

    result = CliRunner().invoke(app, ["shadow-canary"])
    assert result.exit_code == 2
    assert "canary_input_missing" in result.stdout
