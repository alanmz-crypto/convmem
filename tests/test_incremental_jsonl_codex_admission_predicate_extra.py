"""Extra predicate-matrix tests for Codex rollout admission."""

# pylint: disable=duplicate-code

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from incremental_jsonl_codex_admission import admits_path_checks_1_4, make_uuid7
from tests.test_incremental_jsonl_codex_admission import _meta_for, _settings, _write_rollout


def test_predicate_rejects_path_outside_root(tmp_path: Path) -> None:
    root = (tmp_path / "sessions").resolve()
    root.mkdir()
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    settings = _settings(root, admitted)
    uid_obj = make_uuid7(int(admitted.timestamp() * 1000) + 1)
    uid = str(uid_obj)
    local = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0)
    outside = tmp_path / "outside"
    outside.mkdir()
    path = _write_rollout(
        outside,
        uid,
        filename_local=local,
        session_meta=_meta_for(
            uid,
            datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0, tz=timezone.utc),
        ),
    )
    assert not admits_path_checks_1_4(settings, str(path), "jsonl_codex_rollout")


def test_predicate_rejects_symlink_component(tmp_path: Path) -> None:
    root = (tmp_path / "sessions").resolve()
    root.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    settings = _settings(root, admitted)
    uid_obj = make_uuid7(int(admitted.timestamp() * 1000) + 2)
    uid = str(uid_obj)
    local = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0)
    real = _write_rollout(
        root,
        uid,
        filename_local=local,
        session_meta=_meta_for(
            uid,
            datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0, tz=timezone.utc),
        ),
    )
    alias = root / "2026" / "09" / "alias-rollout.jsonl"
    alias.parent.mkdir(parents=True, exist_ok=True)
    alias.symlink_to(real)
    assert not admits_path_checks_1_4(settings, str(alias), "jsonl_codex_rollout")


def test_predicate_rejects_uuid_v4(tmp_path: Path) -> None:
    root = (tmp_path / "sessions").resolve()
    root.mkdir()
    settings = _settings(root, datetime(2026, 6, 1, tzinfo=timezone.utc))
    uid = uuid.uuid4()
    local = datetime(2026, 6, 2, 12, 0, 0)
    path = _write_rollout(
        root,
        str(uid),
        filename_local=local,
        session_meta=_meta_for(str(uid), datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)),
    )
    assert not admits_path_checks_1_4(settings, str(path), "jsonl_codex_rollout")


def test_predicate_rejects_filename_uuid_skew_over_120_seconds(tmp_path: Path) -> None:
    root = (tmp_path / "sessions").resolve()
    root.mkdir()
    settings = _settings(root, datetime(2026, 6, 1, tzinfo=timezone.utc))
    uid_obj = make_uuid7(int(datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp() * 1000))
    uid = str(uid_obj)
    skewed_local = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0) + timedelta(hours=3)
    path = _write_rollout(
        root,
        uid,
        filename_local=skewed_local,
        session_meta=_meta_for(
            uid,
            datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0, tz=timezone.utc),
        ),
    )
    assert not admits_path_checks_1_4(settings, str(path), "jsonl_codex_rollout")
