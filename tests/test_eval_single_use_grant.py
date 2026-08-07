"""Single-use evaluation grants reject replay, races, and unsafe identities."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from eval_corpus.secure_fs import FilesystemAuthorizationError
from eval_corpus.single_use_grant import consume_single_use_grant


def _grant(root, *, not_before=None, expires_at=None):
    path = root / "grant.json"
    body = {
        "schema_version": "single_use_grant_v1",
        "grant_id": "grant-1",
        "attempt_id": "attempt-1",
        "run_id": "run-1",
        "operation": "compare",
        "manifest_body_sha256": "a" * 64,
        "approved_paths": {"out": str(root / "out")},
        "approved_git_oid": "b" * 40,
        "not_before": not_before or "2026-08-01T00:00:00Z",
        "expires_at": expires_at,
        "max_invocations": 1,
    }
    path.write_text(json.dumps(body), encoding="utf-8")
    return path, body


def _expected(path):
    body = json.loads(path.read_text(encoding="utf-8"))
    return {
        "grant_id": body["grant_id"],
        "attempt_id": body["attempt_id"],
        "run_id": body["run_id"],
        "operation": body["operation"],
        "manifest_body_sha256": body["manifest_body_sha256"],
        "approved_paths": body["approved_paths"],
        "approved_git_oid": body["approved_git_oid"],
    }


def test_grant_is_consumed_once_with_receipt(tmp_path):
    path, body = _grant(tmp_path)
    expected = {
        "grant_id": body["grant_id"],
        "attempt_id": body["attempt_id"],
        "run_id": body["run_id"],
        "operation": body["operation"],
        "manifest_body_sha256": body["manifest_body_sha256"],
        "approved_paths": body["approved_paths"],
        "approved_git_oid": body["approved_git_oid"],
    }
    result = consume_single_use_grant(
        path,
        expected,
        now=datetime(2026, 8, 7, tzinfo=timezone.utc),
    )
    assert not path.exists()
    assert (tmp_path / ".consumed" / "grant-1.json").read_text() == json.dumps(body)
    assert result["receipt"]["grant_sha256"]
    with pytest.raises(FileNotFoundError):
        consume_single_use_grant(
            path,
            expected,
            now=datetime(2026, 8, 7, tzinfo=timezone.utc),
        )


def test_mismatched_or_future_or_expired_grant_stays_unconsumed(tmp_path):
    future = (datetime(2026, 8, 8, tzinfo=timezone.utc)).isoformat().replace("+00:00", "Z")
    path, _ = _grant(tmp_path, not_before=future)
    expected = _expected(path)
    with pytest.raises(PermissionError, match="not active"):
        consume_single_use_grant(path, expected, now=datetime(2026, 8, 7, tzinfo=timezone.utc))
    assert path.exists()

    expired_dir = tmp_path / "expired"
    expired_dir.mkdir()
    expired = (datetime(2026, 8, 6, tzinfo=timezone.utc)).isoformat().replace("+00:00", "Z")
    expired_path, _ = _grant(expired_dir, expires_at=expired)
    expired_expected = _expected(expired_path)
    with pytest.raises(PermissionError, match="expired"):
        consume_single_use_grant(expired_path, expired_expected, now=datetime(2026, 8, 7, tzinfo=timezone.utc))


def test_symlink_grant_is_rejected(tmp_path):
    real, _ = _grant(tmp_path)
    link = tmp_path / "link.json"
    link.symlink_to(real)
    with pytest.raises(FilesystemAuthorizationError):
        consume_single_use_grant(link, {})


def test_unsafe_id_and_existing_consumed_state_reject(tmp_path):
    path, body = _grant(tmp_path)
    body["grant_id"] = "../escape"
    path.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(PermissionError, match="unsafe path"):
        consume_single_use_grant(path, _expected(path), now=datetime(2026, 8, 7, tzinfo=timezone.utc))

    second = tmp_path / "second"
    second.mkdir()
    path, _ = _grant(second)
    consumed = second / ".consumed"
    consumed.mkdir()
    (consumed / "grant-1.json").write_text("already consumed", encoding="utf-8")
    with pytest.raises(PermissionError, match="already consumed"):
        consume_single_use_grant(
            path,
            _expected(path),
            now=datetime(2026, 8, 7, tzinfo=timezone.utc),
        )
