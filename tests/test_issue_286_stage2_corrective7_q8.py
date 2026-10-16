"""Q8 tamper durability tests (issue #286 corrective 7)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone  # pylint: disable=unused-import

import pytest  # pylint: disable=unused-import

from doctor import _check_incremental_rollback_tamper


def test_rollback_tamper_record_warns_within_seven_days(tmp_path, monkeypatch) -> None:  # pylint: disable=unused-argument
    import doctor  # pylint: disable=unused-import

    state_dir = tmp_path / "incremental"
    state_dir.mkdir()
    tamper = state_dir / "rollback_export_tamper.jsonl"
    tamper.write_text(
        '{"recorded_at": "2026-10-13T12:00:00Z", "source_path": "/x", '
        '"transaction_id": "tx", "dropped_unexpected_export_lines": 1}\n',
        encoding="utf-8",
    )
    cfg = {"index": {"incremental_jsonl": {"enabled": True, "state_dir": str(state_dir)}}}
    check = _check_incremental_rollback_tamper(cfg)
    assert check.status == "warn"
    assert "rollback tamper" in check.detail


def test_rollback_tamper_record_silent_after_seven_days(tmp_path, monkeypatch) -> None:  # pylint: disable=unused-argument
    import doctor  # pylint: disable=unused-import
    import os  # pylint: disable=unused-import

    state_dir = tmp_path / "incremental"
    state_dir.mkdir()
    tamper = state_dir / "rollback_export_tamper.jsonl"
    tamper.write_text(
        '{"recorded_at": "2026-10-01T12:00:00Z", "source_path": "/x", '
        '"transaction_id": "tx", "dropped_unexpected_export_lines": 1}\n',
        encoding="utf-8",
    )
    cfg = {"index": {"incremental_jsonl": {"enabled": True, "state_dir": str(state_dir)}}}
    check = _check_incremental_rollback_tamper(cfg)
    assert "0 rollback tamper records (7d)" in check.detail
