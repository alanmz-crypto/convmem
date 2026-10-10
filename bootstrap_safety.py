"""Durable, bootstrap-only authority and accounting for incremental JSONL.

The normal ingest path never constructs these objects.  A reviewed one-shot
grant gets an append-only invocation journal and an HTTP-attempt ledger under
the selected source's incremental state directory.
"""

# Exact built-in type checks reject booleans and subclasses in authority data.
# The journal intentionally carries explicit path/limit state for auditability.
# pylint: disable=unidiomatic-typecheck,too-many-instance-attributes

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from llm import ProviderAttemptBudgetExceeded

GRANT_FIELDS = frozenset(
    {
        "operation_id",
        "source",
        "prefix_sha256",
        "complete_boundary",
        "max_chunks",
        "embed_dimension",
        "backup_snapshot",
        "runtime_revision",
        "config_sha256",
        "transform_fingerprint",
        "chunk_size",
        "chunk_overlap",
        "min_confidence",
        "summarize_provider",
        "summarize_model",
        "summarize_base_url",
        "distill_provider",
        "distill_model",
        "distill_base_url",
        "embedding_provider",
        "embedding_model",
        "embedding_base_url",
        "max_provider_http_attempts",
        "max_recovery_invocations",
    }
)
_DIGEST_FIELDS = (
    "operation_id",
    "prefix_sha256",
    "backup_snapshot",
    "config_sha256",
    "transform_fingerprint",
)
_POSITIVE_INT_FIELDS = (
    "complete_boundary",
    "max_chunks",
    "embed_dimension",
    "chunk_size",
    "max_provider_http_attempts",
    "max_recovery_invocations",
)
_PROVIDER_ATTEMPT_EVENT_FIELDS = ("provider", "operation", "model", "base_url")
_BOOTSTRAP_HTTP_PROVIDERS = frozenset({"deepseek", "ollama"})


class BootstrapGrantError(ValueError):
    """The authority artifact is missing, noncanonical, or mismatched."""


class RecoveryAllowanceExceeded(RuntimeError):
    """The exact grant has no authorized recovery invocation remaining."""


def _validate_provider_attempt_event(event: dict[str, object]) -> None:
    if not isinstance(event, dict):
        raise BootstrapGrantError("provider attempt event must be a JSON object")
    if set(event.keys()) != set(_PROVIDER_ATTEMPT_EVENT_FIELDS):
        raise BootstrapGrantError(
            "provider attempt event must contain exactly provider, operation, model, base_url"
        )
    for field in _PROVIDER_ATTEMPT_EVENT_FIELDS:
        value = event.get(field)
        if not isinstance(value, str) or not value.strip():
            raise BootstrapGrantError(f"provider attempt event missing {field}")
    provider = event["provider"]
    if provider not in _BOOTSTRAP_HTTP_PROVIDERS:
        raise BootstrapGrantError("provider attempt event has unsupported provider")


def _provider_attempt_paid_cap_consumed(row: dict[str, Any]) -> bool:
    if (
        row.get("record_type") == "permit_consumed"
        and row.get("provider") == "ollama"
        and row.get("paid_cap_consumed") is False
    ):
        return False
    # Unknown types, missing fields, legacy rows, and falsely exempt rows count.
    return True


def _new_provider_attempt_paid_cap_consumed(event: dict[str, object]) -> bool:
    return event["provider"] == "deepseek"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_bytes(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def operation_identity(grant_without_operation_id: dict[str, Any]) -> str:
    """Return the canonical operation id for the immutable grant body."""

    body = dict(grant_without_operation_id)
    body.pop("operation_id", None)
    return sha256_bytes("convmem-bootstrap-operation-v1:" + canonical_json(body))


def grant_fingerprint(grant: dict[str, Any]) -> str:
    return sha256_bytes("convmem-bootstrap-grant-v1:" + canonical_json(grant))


def _require_canonical_url(value: str, field: str) -> None:
    parsed = urlsplit(value)
    invalid = (
        parsed.scheme not in {"http", "https"},
        not parsed.netloc,
        parsed.username is not None,
        parsed.password is not None,
        bool(parsed.query),
        bool(parsed.fragment),
        value != value.rstrip("/"),
    )
    if any(invalid):
        raise BootstrapGrantError(f"grant {field} must be a canonical HTTP base URL")


def validate_grant(grant: dict[str, Any]) -> dict[str, Any]:
    """Validate exact shape and canonical values without resolving credentials."""

    if not isinstance(grant, dict):
        raise BootstrapGrantError("grant must be a JSON object")
    if set(grant) != GRANT_FIELDS:
        raise BootstrapGrantError(
            "grant must contain exactly " + ", ".join(sorted(GRANT_FIELDS))
        )
    for field in (
        "source",
        "backup_snapshot",
        "runtime_revision",
        "summarize_provider",
        "summarize_model",
        "summarize_base_url",
        "distill_provider",
        "distill_model",
        "distill_base_url",
        "embedding_provider",
        "embedding_model",
        "embedding_base_url",
    ):
        if not isinstance(grant[field], str) or not grant[field].strip():
            raise BootstrapGrantError(f"grant {field} must be a non-empty string")
        if grant[field] != grant[field].strip():
            raise BootstrapGrantError(f"grant {field} must be canonical")
    for field in _DIGEST_FIELDS:
        value = grant[field]
        if (
            not isinstance(value, str)
            or len(value) != 64
            or value.lower() != value
        ):
            raise BootstrapGrantError(f"grant {field} must be a lowercase SHA-256")
        try:
            int(value, 16)
        except ValueError as exc:
            raise BootstrapGrantError(f"grant {field} must be hexadecimal") from exc
    for field in _POSITIVE_INT_FIELDS:
        if type(grant[field]) is not int or grant[field] < 1:
            raise BootstrapGrantError(f"grant {field} must be a positive integer")
    if type(grant["chunk_overlap"]) is not int or grant["chunk_overlap"] < 0:
        raise BootstrapGrantError("grant chunk_overlap must be a non-negative integer")
    confidence = grant["min_confidence"]
    if (
        type(confidence) is not float
        or not 0 <= float(confidence) <= 1
    ):
        raise BootstrapGrantError(
            "grant min_confidence must be a float between 0 and 1"
        )
    if grant["max_recovery_invocations"] != 1:
        raise BootstrapGrantError("grant max_recovery_invocations must equal 1")
    source_text = grant["source"]
    source = Path(source_text).expanduser()
    if (
        not source.is_absolute()
        or any(character in source_text for character in "*?[]")
        or source.resolve(strict=False) != source
    ):
        raise BootstrapGrantError("grant source must be one canonical absolute path")
    runtime = grant["runtime_revision"]
    if (
        len(runtime) != 40
        or runtime.lower() != runtime
        or any(character not in "0123456789abcdef" for character in runtime)
    ):
        raise BootstrapGrantError("grant runtime_revision must be a canonical Git SHA")
    for field in (
        "summarize_base_url",
        "distill_base_url",
        "embedding_base_url",
    ):
        _require_canonical_url(grant[field], field)
    for field in ("summarize_provider", "distill_provider", "embedding_provider"):
        if grant[field] not in {"deepseek", "ollama"}:
            raise BootstrapGrantError(f"grant {field} is unsupported")
    expected_operation = operation_identity(grant)
    if grant["operation_id"] != expected_operation:
        raise BootstrapGrantError("grant operation_id does not match its immutable body")
    return dict(grant)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    existed = path.exists()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(payload) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, 0o600)
    if not existed:
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BootstrapGrantError("operation journal is corrupt") from exc
            if not isinstance(row, dict):
                raise BootstrapGrantError("operation journal row is not an object")
            rows.append(row)
    return rows


@dataclass(frozen=True)
class InvocationAuthority:
    ordinal: int
    authorized: bool
    recovery: bool
    refusal_code: str | None


class BootstrapOperationJournal:
    """Append-only invocation, permit, usage, and terminal receipt authority."""

    def __init__(
        self,
        source_state_dir: Path,
        grant: dict[str, Any],
        binding: dict[str, Any],
    ) -> None:
        self.grant = validate_grant(grant)
        self.fingerprint = grant_fingerprint(self.grant)
        self.operation_id = self.grant["operation_id"]
        self.max_attempts = int(self.grant["max_provider_http_attempts"])
        self.max_recoveries = int(self.grant["max_recovery_invocations"])
        self.root = source_state_dir / "operations" / self.fingerprint
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.lock_path = self.root / "operation.lock"
        self.invocations_path = self.root / "invocations.jsonl"
        self.attempts_path = self.root / "provider_attempts.jsonl"
        self.usage_path = self.root / "provider_usage.jsonl"
        self.manifest_path = self.root / "manifest.json"
        manifest = {
            "version": 1,
            "operation_id": self.operation_id,
            "grant_fingerprint": self.fingerprint,
            "grant": self.grant,
            "binding": binding,
        }
        existing = None
        if self.manifest_path.is_file():
            try:
                existing = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise BootstrapGrantError("operation manifest is unreadable") from exc
        if existing is not None and existing != manifest:
            raise BootstrapGrantError("operation manifest binding mismatch")
        if existing is None:
            _atomic_json(self.manifest_path, manifest)
        self.current: InvocationAuthority | None = None

    def _locked(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.lock_path.open("a+", encoding="utf-8")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        return lock

    def begin_invocation(self, *, recoverable_transaction: bool) -> InvocationAuthority:
        with self._locked():
            starts = [
                row
                for row in _read_jsonl(self.invocations_path)
                if row.get("record_type") == "start"
            ]
            ordinal = len(starts) + 1
            recovery = ordinal > 1
            refusal = None
            if ordinal > 1 + self.max_recoveries:
                refusal = "recovery_exhausted"
            elif recovery and not recoverable_transaction:
                refusal = "recovery_not_available"
            authority = InvocationAuthority(
                ordinal=ordinal,
                authorized=refusal is None,
                recovery=recovery,
                refusal_code=refusal,
            )
            _append_jsonl(
                self.invocations_path,
                {
                    "record_type": "start",
                    "recorded_at": utc_now(),
                    "operation_id": self.operation_id,
                    "grant_fingerprint": self.fingerprint,
                    "invocation_ordinal": ordinal,
                    "authorized": authority.authorized,
                    "recovery": recovery,
                    "refusal_code": refusal,
                },
            )
        self.current = authority
        return authority

    def consume_provider_http_attempt(self, event: dict[str, object]) -> None:
        if self.current is None or not self.current.authorized:
            raise ProviderAttemptBudgetExceeded("bootstrap invocation is not authorized")
        _validate_provider_attempt_event(event)
        paid_cap_consumed = _new_provider_attempt_paid_cap_consumed(event)
        with self._locked():
            attempts = _read_jsonl(self.attempts_path)
            consumed_paid = sum(
                _provider_attempt_paid_cap_consumed(row) for row in attempts
            )
            if paid_cap_consumed and consumed_paid >= self.max_attempts:
                raise ProviderAttemptBudgetExceeded(
                    f"provider_http_budget_exhausted:{consumed_paid}/{self.max_attempts}"
                )
            observed = len(attempts)
            _append_jsonl(
                self.attempts_path,
                {
                    "record_type": "permit_consumed",
                    "recorded_at": utc_now(),
                    "operation_id": self.operation_id,
                    "grant_fingerprint": self.fingerprint,
                    "invocation_ordinal": self.current.ordinal,
                    "attempt_ordinal": observed + 1,
                    "paid_cap_consumed": paid_cap_consumed,
                    **event,
                },
            )

    def report_provider_usage(
        self, event: dict[str, object], usage: dict[str, object]
    ) -> None:
        if self.current is None:
            return
        def safe(value: Any) -> Any:
            if isinstance(value, dict):
                return {str(key): safe(item) for key, item in value.items()}
            if isinstance(value, list):
                return [safe(item) for item in value]
            if isinstance(value, (str, int, float, bool)) or value is None:
                return value
            return str(value)

        safe_usage = safe(usage)
        with self._locked():
            _append_jsonl(
                self.usage_path,
                {
                    "record_type": "provider_usage",
                    "recorded_at": utc_now(),
                    "operation_id": self.operation_id,
                    "grant_fingerprint": self.fingerprint,
                    "invocation_ordinal": self.current.ordinal,
                    "provider": event.get("provider"),
                    "operation": event.get("operation"),
                    "model": event.get("model"),
                    "usage": safe_usage,
                },
            )

    def accounting(self) -> dict[str, Any]:
        attempts = _read_jsonl(self.attempts_path)
        usage = _read_jsonl(self.usage_path)
        current_ordinal = self.current.ordinal if self.current else 0
        current_attempts = [
            row for row in attempts if row.get("invocation_ordinal") == current_ordinal
        ]
        paid_current = sum(
            _provider_attempt_paid_cap_consumed(row) for row in current_attempts
        )
        paid_cumulative = sum(_provider_attempt_paid_cap_consumed(row) for row in attempts)
        return {
            "permitted_http_attempts": paid_current,
            "cumulative_permitted_http_attempts": paid_cumulative,
            "paid_provider_http_attempts": paid_current,
            "cumulative_paid_provider_http_attempts": paid_cumulative,
            "observed_provider_http_attempts": len(current_attempts),
            "cumulative_observed_provider_http_attempts": len(attempts),
            "provider_usage": [
                row for row in usage if row.get("invocation_ordinal") == current_ordinal
            ],
        }

    def finish(self, receipt: dict[str, Any]) -> dict[str, Any]:
        if self.current is None:
            raise RuntimeError("invocation has not started")
        payload = {
            "record_type": "terminal",
            "recorded_at": utc_now(),
            "operation_id": self.operation_id,
            "grant_fingerprint": self.fingerprint,
            "invocation_ordinal": self.current.ordinal,
            **receipt,
        }
        with self._locked():
            _append_jsonl(self.invocations_path, payload)
        return payload
