"""Codex bootstrap v2 durable reservation and invocation authority (Arc #286 T2)."""

from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from bootstrap_codex_v2 import grant_fingerprint_v2, operation_identity_v2, validate_grant_v2
from contextlib import nullcontext

from bootstrap_codex_v2_owner import ENFORCE_ENV, require_owner_lock
from bootstrap_codex_v2_publication import append_jsonl_line, atomic_publish_json
from bootstrap_safety import (
    BootstrapGrantError,
    ProviderAttemptBudgetExceeded,
    _read_jsonl,
    utc_now,
)

PROGRESS_FIELDS = (
    "transaction_lineage_digest",
    "prepared_lineage_digest",
    "rollback_digest",
    "checkpoint_digest",
)


AUTHORITY_FILENAME = "bootstrap_v2_authority.json"
AUTHORITY_SCHEMA_VERSION = 1
CLAIM_LOCK_NAME = ".bootstrap_v2_claim.lock"
CRASH_POINT_ENV = "CONVMEM_BOOTSTRAP_V2_CRASH_POINT"


class CodexBootstrapV2AuthorityError(BootstrapGrantError):
    """V2 authority protocol violation."""


@dataclass(frozen=True)
class AuthorityView:
    path: Path
    record: dict[str, Any]

    @property
    def invocation_ordinal(self) -> int:
        return int(self.record["invocation_ordinal"])

    @property
    def revision(self) -> int:
        return int(self.record["revision"])

    @property
    def reservation_active(self) -> bool:
        return bool(self.record["reservation_active"])

    @property
    def terminal(self) -> bool:
        return str(self.record.get("reservation_state") or "") == "TERMINAL"


def authority_path(state_dir: Path) -> Path:
    return state_dir / AUTHORITY_FILENAME


def operation_root(state_dir: Path, grant: dict[str, Any]) -> Path:
    fingerprint = grant_fingerprint_v2(grant)
    root = state_dir / "operations" / fingerprint
    return root


def _authority_lock(state_dir: Path):
    if os.environ.get(ENFORCE_ENV, "").strip() == "1":
        require_owner_lock()
        return nullcontext()
    return claim_lock(state_dir)


def _crash_after(point: str) -> None:
    if os.environ.get(CRASH_POINT_ENV, "").strip() == point:
        os._exit(91)


def _publish_authority(path: Path, record: dict[str, Any], *, stage: str = "authority") -> None:
    atomic_publish_json(path, record, stage=stage)
    _crash_after("after_authority_fsync")


def _validate_record_shape(record: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "authority_kind",
        "revision",
        "operation_id",
        "grant_fingerprint_v2",
        "reservation_state",
        "reservation_active",
        "invocation_ordinal",
        "grant_snapshot",
        "progress",
        "published_at",
    }
    allowed = required | {"terminal_receipt_digest"}
    if not isinstance(record, dict):
        raise CodexBootstrapV2AuthorityError("authority must be a JSON object")
    if set(record) != allowed and set(record) != required:
        missing = required - set(record)
        extra = set(record) - allowed
        if missing or extra:
            raise CodexBootstrapV2AuthorityError("authority record has unexpected fields")
    if record["schema_version"] != AUTHORITY_SCHEMA_VERSION:
        raise CodexBootstrapV2AuthorityError("authority schema_version unsupported")
    if record["authority_kind"] != "codex_bootstrap_v2":
        raise CodexBootstrapV2AuthorityError("authority_kind mismatch")
    revision = record["revision"]
    ordinal = record["invocation_ordinal"]
    if type(revision) is not int or revision < 1:
        raise CodexBootstrapV2AuthorityError("authority revision invalid")
    if type(ordinal) is not int or ordinal not in {1, 2}:
        raise CodexBootstrapV2AuthorityError("authority invocation_ordinal invalid")
    if not isinstance(record["grant_snapshot"], dict):
        raise CodexBootstrapV2AuthorityError("authority grant_snapshot invalid")
    progress = record.get("progress")
    if not isinstance(progress, dict):
        raise CodexBootstrapV2AuthorityError("authority progress invalid")
    for key in PROGRESS_FIELDS:
        if key not in progress:
            raise CodexBootstrapV2AuthorityError("authority progress missing binding")
    return record


def load_authority(state_dir: Path) -> AuthorityView | None:
    path = authority_path(state_dir)
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CodexBootstrapV2AuthorityError("authority is unreadable") from exc
    record = _validate_record_shape(record)
    return AuthorityView(path=path, record=record)


def _progress_binding(existing: dict[str, Any] | None = None) -> dict[str, Any]:
    base = {key: None for key in PROGRESS_FIELDS}
    if existing:
        for key in PROGRESS_FIELDS:
            if key in existing:
                base[key] = existing[key]
    return base


def _grant_snapshot(grant: dict[str, Any]) -> dict[str, Any]:
    validated = validate_grant_v2(grant)
    return dict(validated)


def _assert_identical_grant(authority: AuthorityView, grant: dict[str, Any]) -> dict[str, Any]:
    validated = _grant_snapshot(grant)
    fingerprint = grant_fingerprint_v2(validated)
    if authority.record["grant_fingerprint_v2"] != fingerprint:
        raise CodexBootstrapV2AuthorityError("replacement_grant_refused")
    if authority.record["operation_id"] != validated["operation_id"]:
        raise CodexBootstrapV2AuthorityError("replacement_grant_refused")
    snapshot = authority.record["grant_snapshot"]
    if snapshot != validated:
        raise CodexBootstrapV2AuthorityError("replacement_grant_refused")
    return validated


def inspect_initial_claim_blockers(state_dir: Path, grant: dict[str, Any]) -> list[str]:
    validated = validate_grant_v2(grant)
    fingerprint = grant_fingerprint_v2(validated)
    blockers: list[str] = []
    existing = load_authority(state_dir)
    if existing is not None:
        blockers.append("authority_present")
    op_root = operation_root(state_dir, validated)
    invocations = op_root / "invocations.jsonl"
    if invocations.is_file() and existing is None:
        blockers.append("orphan_invocation_journal")
    manifest = op_root / "manifest.json"
    if manifest.is_file() and existing is None:
        blockers.append("orphan_operation_manifest")
    tmp = authority_path(state_dir).with_name(authority_path(state_dir).name + ".tmp")
    if tmp.exists():
        blockers.append("ambiguous_authority_temp")
    return blockers


@contextmanager
def claim_lock(state_dir: Path) -> Iterator[None]:
    state_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(state_dir, 0o700)
    lock_path = state_dir / CLAIM_LOCK_NAME
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _authority_record(
    grant: dict[str, Any],
    *,
    revision: int,
    invocation_ordinal: int,
    reservation_state: str,
    reservation_active: bool,
    progress: dict[str, Any] | None = None,
    terminal_receipt_digest: str | None = None,
) -> dict[str, Any]:
    validated = _grant_snapshot(grant)
    record: dict[str, Any] = {
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        "authority_kind": "codex_bootstrap_v2",
        "revision": revision,
        "operation_id": validated["operation_id"],
        "grant_fingerprint_v2": grant_fingerprint_v2(validated),
        "reservation_state": reservation_state,
        "reservation_active": reservation_active,
        "invocation_ordinal": invocation_ordinal,
        "grant_snapshot": validated,
        "progress": _progress_binding(progress),
        "published_at": utc_now(),
    }
    if terminal_receipt_digest is not None:
        record["terminal_receipt_digest"] = terminal_receipt_digest
    return record


def claim_initial_authority(state_dir: Path, grant: dict[str, Any]) -> AuthorityView:
    validated = validate_grant_v2(grant)
    if validated["operation_id"] != operation_identity_v2(validated):
        raise CodexBootstrapV2AuthorityError("grant operation_id mismatch")
    with _authority_lock(state_dir):
        blockers = inspect_initial_claim_blockers(state_dir, validated)
        if blockers:
            raise CodexBootstrapV2AuthorityError("initial_claim_refused:" + ",".join(blockers))
        record = _authority_record(
            validated,
            revision=1,
            invocation_ordinal=1,
            reservation_state="RESERVED",
            reservation_active=True,
        )
        path = authority_path(state_dir)
        _publish_authority(path, record, stage="initial_authority")
        _crash_after("after_initial_claim_lock_release")
        return AuthorityView(path=path, record=record)


def claim_recovery_authority(state_dir: Path, grant: dict[str, Any]) -> AuthorityView:
    validated = validate_grant_v2(grant)
    with _authority_lock(state_dir):
        existing = load_authority(state_dir)
        if existing is None:
            raise CodexBootstrapV2AuthorityError("recovery_without_authority")
        if existing.terminal:
            raise CodexBootstrapV2AuthorityError("already_terminal")
        validated = _assert_identical_grant(existing, validated)
        ordinal = existing.invocation_ordinal
        if ordinal >= 2:
            raise CodexBootstrapV2AuthorityError("recovery_exhausted")
        if int(validated["max_recovery_invocations"]) < 1:
            raise CodexBootstrapV2AuthorityError("recovery_not_granted")
        record = _authority_record(
            validated,
            revision=existing.revision + 1,
            invocation_ordinal=2,
            reservation_state=str(existing.record.get("reservation_state") or "RESERVED"),
            reservation_active=True,
            progress=dict(existing.record.get("progress") or {}),
        )
        _publish_authority(existing.path, record, stage="recovery_authority")
        return AuthorityView(path=existing.path, record=record)



def publish_authority_progress(
    state_dir: Path,
    grant: dict[str, Any],
    *,
    progress: dict[str, Any],
) -> AuthorityView:
    validated = validate_grant_v2(grant)
    with _authority_lock(state_dir):
        existing = load_authority(state_dir)
        if existing is None:
            raise CodexBootstrapV2AuthorityError("progress_without_authority")
        validated = _assert_identical_grant(existing, validated)
        if existing.terminal:
            raise CodexBootstrapV2AuthorityError("already_terminal")
        merged = _progress_binding(dict(existing.record.get("progress") or {}))
        for key in PROGRESS_FIELDS:
            if key in progress:
                merged[key] = progress[key]
        record = _authority_record(
            validated,
            revision=existing.revision + 1,
            invocation_ordinal=existing.invocation_ordinal,
            reservation_state=str(existing.record.get("reservation_state") or "RESERVED"),
            reservation_active=True,
            progress=merged,
        )
        _publish_authority(existing.path, record, stage="progress_authority")
        return AuthorityView(path=existing.path, record=record)


def publish_terminal_authority(
    state_dir: Path,
    grant: dict[str, Any],
    *,
    receipt_digest: str,
    receipt_path: Path | None = None,
) -> AuthorityView:
    validated = validate_grant_v2(grant)
    with _authority_lock(state_dir):
        existing = load_authority(state_dir)
        if existing is None:
            raise CodexBootstrapV2AuthorityError("terminal_without_authority")
        validated = _assert_identical_grant(existing, validated)
        if existing.terminal:
            return existing
        if receipt_path is not None:
            atomic_publish_json(
                receipt_path,
                {"receipt_digest": receipt_digest, "operation_id": validated["operation_id"]},
                stage="terminal_receipt",
            )
            _crash_after("after_receipt_fsync")
        record = _authority_record(
            validated,
            revision=existing.revision + 1,
            invocation_ordinal=existing.invocation_ordinal,
            reservation_state="TERMINAL",
            reservation_active=False,
            progress=dict(existing.record.get("progress") or {}),
            terminal_receipt_digest=receipt_digest,
        )
        _publish_authority(existing.path, record, stage="terminal_authority")
        return AuthorityView(path=existing.path, record=record)


def refuse_third_invocation(state_dir: Path, grant: dict[str, Any]) -> str:
    existing = load_authority(state_dir)
    if existing is None:
        return "no_authority"
    if existing.terminal:
        return "already_terminal"
    if existing.invocation_ordinal >= 2:
        return "recovery_exhausted"
    return "recovery_available"


def mirror_invocation_start(state_dir: Path, grant: dict[str, Any]) -> None:
    validated = validate_grant_v2(grant)
    authority = load_authority(state_dir)
    if authority is None:
        raise CodexBootstrapV2AuthorityError("mirror_without_authority")
    _assert_identical_grant(authority, validated)
    root = operation_root(state_dir, validated)
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    invocations = root / "invocations.jsonl"
    rows = _read_jsonl(invocations)
    if any(
        row.get("record_type") == "start"
        and int(row.get("invocation_ordinal") or 0) == authority.invocation_ordinal
        for row in rows
    ):
        return
    append_jsonl_line(
        invocations,
        {
            "record_type": "start",
            "recorded_at": utc_now(),
            "operation_id": validated["operation_id"],
            "grant_fingerprint": grant_fingerprint_v2(validated),
            "invocation_ordinal": authority.invocation_ordinal,
            "authority_revision": authority.revision,
            "mirror": True,
        },
        stage="journal_mirror",
    )
    _crash_after("after_journal_mirror_fsync")


def detect_authority_corruption(state_dir: Path, grant: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    authority = load_authority(state_dir)
    if authority is None:
        return issues
    validated = validate_grant_v2(grant)
    fingerprint = grant_fingerprint_v2(validated)
    rows = _read_jsonl(operation_root(state_dir, validated) / "invocations.jsonl")
    max_journal_ordinal = max(
        [int(row.get("invocation_ordinal") or 0) for row in rows if row.get("record_type") == "start"]
        or [0]
    )
    if max_journal_ordinal > authority.invocation_ordinal:
        issues.append("journal_ahead_of_authority")
    if authority.record["grant_fingerprint_v2"] != fingerprint:
        issues.append("fingerprint_mismatch")
    return issues
