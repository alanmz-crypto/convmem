"""Hermetic tests for Codex rollout admission predicate and config validation."""

# pylint: disable=duplicate-code

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import config
from incremental_jsonl_codex_admission import (
    CodexRolloutAdmissionSettings,
    admits_path_checks_1_4,
    make_uuid7,
    parse_rollout_basename,
    verify_session_meta_identity,
)
from tests.incremental_jsonl_helpers import codex_rollout_record


def _settings(
    root: Path,
    admitted_after: datetime,
) -> CodexRolloutAdmissionSettings:
    return CodexRolloutAdmissionSettings(
        root=root,
        admitted_after=admitted_after,
        max_transform_chunks_per_run=20,
        max_source_bytes=256 * 1024 * 1024,
    )


def _write_rollout(
    sessions_root: Path,
    uid: str,
    *,
    filename_local: datetime,
    session_meta: dict | None = None,
    extra_lines: int = 2,
) -> Path:
    day = filename_local.strftime("%Y-%m-%d")
    stamp = filename_local.strftime("%H-%M-%S")
    path = (
        sessions_root
        / "2026"
        / "09"
        / f"rollout-{day}T{stamp}-{uid}.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if session_meta is not None:
        lines.append(json.dumps(session_meta, sort_keys=True))
    for index in range(extra_lines):
        lines.append(codex_rollout_record(index).decode("utf-8").strip())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path.resolve()


def _meta_for(uid: str, ts: datetime) -> dict:
    return {
        "type": "session_meta",
        "timestamp": ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "payload": {"id": uid, "timestamp": ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
    }


def test_predicate_rejects_wrong_format(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    root.mkdir()
    other = root / "not-rollout.jsonl"
    other.write_text("{}", encoding="utf-8")
    settings = _settings(root.resolve(), datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert not admits_path_checks_1_4(settings, str(other.resolve()), "jsonl_kiro_session")


def test_predicate_admitted_after_boundary(tmp_path: Path) -> None:
    root = (tmp_path / "sessions").resolve()
    root.mkdir()
    admitted = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    settings = _settings(root, admitted)
    uid_obj = make_uuid7(int(admitted.timestamp() * 1000) + 1)
    uid = str(uid_obj)
    local = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0)
    path = _write_rollout(
        root,
        uid,
        filename_local=local,
        session_meta=_meta_for(uid, datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0, tz=timezone.utc)),
    )
    assert admits_path_checks_1_4(settings, str(path), "jsonl_codex_rollout")

    early_uid = make_uuid7(int((admitted - timedelta(milliseconds=1)).timestamp() * 1000))
    early_local = datetime.fromtimestamp((early_uid.int >> 80) / 1000.0)
    early_path = _write_rollout(
        root,
        str(early_uid),
        filename_local=early_local,
        session_meta=_meta_for(
            str(early_uid),
            datetime.fromtimestamp((early_uid.int >> 80) / 1000.0, tz=timezone.utc),
        ),
    )
    assert not admits_path_checks_1_4(settings, str(early_path), "jsonl_codex_rollout")


def test_same_session_prefix_copy_not_admitted(tmp_path: Path) -> None:
    root = (tmp_path / "sessions").resolve()
    root.mkdir()
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    settings = _settings(root, admitted)
    uid_obj = make_uuid7(int(admitted.timestamp() * 1000) + 5_000)
    uid = str(uid_obj)
    uuid_dt = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0, tz=timezone.utc)
    original_local = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0)
    original = _write_rollout(
        root,
        uid,
        filename_local=original_local,
        session_meta=_meta_for(uid, uuid_dt),
    )
    assert admits_path_checks_1_4(settings, str(original), "jsonl_codex_rollout")
    later_local = original_local + timedelta(hours=1)
    copy = _write_rollout(
        root,
        uid,
        filename_local=later_local,
        session_meta=_meta_for(uid, uuid_dt),
        extra_lines=1,
    )
    assert not admits_path_checks_1_4(settings, str(copy), "jsonl_codex_rollout")


def test_session_meta_mismatch_refuses(tmp_path: Path) -> None:
    root = (tmp_path / "sessions").resolve()
    root.mkdir()
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    uid_obj = make_uuid7(int(admitted.timestamp() * 1000) + 1_000)
    uid = str(uid_obj)
    uuid_dt = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0, tz=timezone.utc)
    local = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0)
    path = _write_rollout(
        root,
        uid,
        filename_local=local,
        session_meta=_meta_for("00000000-0000-7000-8000-000000000001", uuid_dt),
    )
    raw = path.read_bytes()
    assert verify_session_meta_identity(path, raw) == "codex_session_identity_mismatch"


@pytest.mark.parametrize(
    "table_patch,match",
    [
        (
            {
                "codex_rollout_admission": {
                    "root": "/tmp/x",
                    "admitted_after": "2026-01-01T00:00:00Z",
                }
            },
            "embed_dimension",
        ),
        (
            {
                "enabled": False,
                "codex_rollout_admission": {
                    "root": "/tmp/x",
                    "admitted_after": "2026-01-01T00:00:00Z",
                },
            },
            "enabled",
        ),
        ({"codex_rollout_admission": {"root": "relative", "admitted_after": "2026-01-01T00:00:00Z"}}, "root"),
        ({"codex_rollout_admission": {"root": "/tmp/x", "admitted_after": "2026-01-01T00:00:00"}}, "naive"),
    ],
)
def test_config_validation_fail_closed(table_patch: dict, match: str) -> None:
    base_table = {
        "enabled": True,
        "live_sources": [],
        **table_patch,
    }
    if "embed_dimension" not in table_patch and match != "embed_dimension":
        base_table["embed_dimension"] = 8
    cfg = {"index": {"incremental_jsonl": base_table}}
    with pytest.raises(config.IncrementalJsonlConfigError, match=match):
        config.incremental_jsonl_settings(cfg)


def test_filename_regex_parses_uuid_v7() -> None:
    uid = make_uuid7(1_735_689_600_000)
    local = datetime.fromtimestamp((uid.int >> 80) / 1000.0)
    path = Path(
        f"rollout-{local.strftime('%Y-%m-%d')}T{local.strftime('%H-%M-%S')}-{uid}.jsonl"
    )
    parsed_uid, parsed_local = parse_rollout_basename(path)
    assert parsed_uid.version == 7
    assert parsed_local == local
