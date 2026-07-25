# pylint: disable=duplicate-code
"""UnitMutationSink: observe confirmed knowledge_units mutations into shadow JSONL."""

from __future__ import annotations

import fcntl
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

from shadow_ledger import (
    COLLECTION_KNOWLEDGE_UNITS,
    SHADOW_SCHEMA_VERSION,
    atomic_write_json_private,
    ensure_private_file_mode,
    projection_state_hash,
    sha256_canonical,
)

log = logging.getLogger("convmem.shadow_sink")

ALLOWED_OPERATIONS = frozenset(
    {
        "create",
        "replace",
        "metadata_update",
        "supersede",
        "restore",
        "delete",
    }
)

# Doctor WARN only after N consecutive lock timeouts (Claude note / Kiro should-fix).
LOCK_TIMEOUT_WARN_THRESHOLD_N = 3
LOCK_ACQUIRE_TIMEOUT_MS = 250
# Measured append latency above this is degraded (no signal interruption).
FSYNC_DEGRADED_LATENCY_MS = 500.0


class UnitMutationSink(Protocol):
    def prepare_event_id(self) -> str: ...

    def observe(  # pylint: disable=too-many-arguments
        self,
        *,
        event_id: str,
        operation: str,
        stable_entity_id: str,
        document: str | None,
        metadata: Mapping[str, Any] | None,
        deleted: bool,
        embed_model: str = "unknown",
        embed_dims: int | None = None,
        writer_route: str = "",
    ) -> None: ...


@dataclass
class ShadowHealth:  # pylint: disable=too-many-instance-attributes
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_failure_class: str | None = None
    consecutive_failures: int = 0
    consecutive_lock_timeouts: int = 0
    last_event_id: str | None = None
    last_sequence: int | None = None
    last_append_latency_ms: float | None = None
    append_degraded: bool = False
    idempotent_retries: int = 0
    status: str = "healthy"


def assess_shadow_status(
    *,
    enabled: bool,
    health: Mapping[str, Any] | None = None,
    ledger_corrupt: bool = False,
    baseline_mismatch: bool = False,
) -> str:
    """Return disabled|healthy|degraded|corrupt|baseline_mismatch."""
    if not enabled:
        return "disabled"
    if baseline_mismatch:
        return "baseline_mismatch"
    if ledger_corrupt:
        return "corrupt"
    h = dict(health or {})
    if h.get("last_failure_class") in {"truncated_tail", "invalid_middle", "ValueError"}:
        if int(h.get("consecutive_failures") or 0) >= 1:
            # Prefer explicit corrupt when failure class indicates ledger damage
            if h.get("last_failure_class") in {"truncated_tail", "invalid_middle"}:
                return "corrupt"
    if ledger_corrupt:
        return "corrupt"
    if (
        h.get("append_degraded")
        or int(h.get("consecutive_lock_timeouts") or 0) >= 1
        or int(h.get("consecutive_failures") or 0) >= 1
        or h.get("last_failure_class") == "lock_timeout"
        or h.get("last_failure_class") == "uncertain_ack"
    ):
        return "degraded"
    return "healthy"


def ledger_has_corruption(ledger_path: Path) -> bool:
    """True if truncated tail or invalid middle record is present."""
    path = Path(ledger_path)
    if not path.is_file():
        return False
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        return True
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line.decode("utf-8"))
        except Exception:  # pylint: disable=broad-exception-caught
            return True
        if not isinstance(obj, dict):
            return True
    return False


class JsonlUnitMutationSink:
    """Append-only shadow sink for knowledge_units only (never summaries)."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        ledger_path: Path,
        health_path: Path,
        lock_timeout_ms: int = LOCK_ACQUIRE_TIMEOUT_MS,
        lock_timeout_warn_n: int = LOCK_TIMEOUT_WARN_THRESHOLD_N,
        degraded_latency_ms: float = FSYNC_DEGRADED_LATENCY_MS,
    ) -> None:
        self.ledger_path = Path(ledger_path)
        self.health_path = Path(health_path)
        self.lock_timeout_ms = lock_timeout_ms
        self.lock_timeout_warn_n = lock_timeout_warn_n
        self.degraded_latency_ms = degraded_latency_ms
        self._health = ShadowHealth()
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def prepare_event_id(self) -> str:
        return str(uuid.uuid4())

    def observe(  # pylint: disable=too-many-arguments
        self,
        *,
        event_id: str,
        operation: str,
        stable_entity_id: str,
        document: str | None,
        metadata: Mapping[str, Any] | None,
        deleted: bool,
        embed_model: str = "unknown",
        embed_dims: int | None = None,
        writer_route: str = "",
    ) -> None:
        if operation not in ALLOWED_OPERATIONS:
            self._record_failure("invalid_operation", event_id=event_id)
            log.error("shadow reject unknown operation=%s", operation)
            return
        meta = dict(metadata or {}) if not deleted else dict(metadata or {})
        ledger_id = str(meta.get("ledger_id") or "") or None
        doc = None if deleted else document
        event = {
            "shadow_schema_version": SHADOW_SCHEMA_VERSION,
            "event_id": event_id,
            "sequence": None,  # assigned under lock
            "collection": COLLECTION_KNOWLEDGE_UNITS,
            "operation": operation,
            "stable_entity_id": stable_entity_id,
            "ledger_id": ledger_id,
            "recorded_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "post_state": {
                "document": doc,
                "metadata": meta if meta else {},
                "deleted": bool(deleted),
            },
            "document_hash": (
                None if deleted or doc is None else sha256_canonical(doc)
            ),
            "metadata_hash": sha256_canonical(meta),
            "state_hash": projection_state_hash(
                stable_entity_id=stable_entity_id,
                deleted=deleted,
                document=doc,
                metadata=meta,
            ),
            "embed_model": embed_model or "unknown",
            "authority": "shadow",
            "writer_route": writer_route or "",
            "embed_dims": embed_dims,
        }
        try:
            self._append_event(event)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            klass = type(exc).__name__
            msg = str(exc)
            if "truncated tail" in msg:
                klass = "truncated_tail"
            elif "invalid middle" in msg:
                klass = "invalid_middle"
            self._record_failure(klass, event_id=event_id)
            log.error(
                "shadow append failed event_id=%s entity=%s: %s",
                event_id,
                stable_entity_id,
                exc,
            )

    def _append_event(self, event: dict[str, Any]) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        created = not self.ledger_path.exists()
        start = time.monotonic()
        uncertain = False
        idempotent = False
        with open(self.ledger_path, "a+b") as handle:
            if not self._acquire_lock(handle, event.get("event_id")):
                return
            try:
                # Tail check before any full-file scan so truncation is not
                # misreported as an invalid middle record.
                self._validate_tail(handle)
                existing = self._find_event(handle, str(event.get("event_id") or ""))
                if existing is not None:
                    idempotent = True
                    event["sequence"] = existing.get("sequence")
                else:
                    sequence = self._next_sequence(handle)
                    event["sequence"] = sequence
                    line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
                    data = line.encode("utf-8")
                    handle.seek(0, os.SEEK_END)
                    handle.write(data)  # one encoded-byte write
                    handle.flush()
                    try:
                        os.fsync(handle.fileno())
                    except OSError:
                        uncertain = True
                    if created and not uncertain:
                        ensure_private_file_mode(self.ledger_path)
                        dir_fd = os.open(str(self.ledger_path.parent), os.O_RDONLY)
                        try:
                            os.fsync(dir_fd)
                        finally:
                            os.close(dir_fd)
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

        latency_ms = (time.monotonic() - start) * 1000.0
        if uncertain:
            self._health.last_append_latency_ms = latency_ms
            self._record_failure("uncertain_ack", event_id=event.get("event_id"))
            log.warning(
                "shadow append uncertain_ack event_id=%s (fsync failed; retry may reuse id)",
                event.get("event_id"),
            )
            return

        self._health.last_success_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        self._health.consecutive_failures = 0
        self._health.consecutive_lock_timeouts = 0
        self._health.last_failure_class = None
        self._health.last_event_id = event.get("event_id")
        self._health.last_sequence = event.get("sequence")
        self._health.last_append_latency_ms = latency_ms
        self._health.append_degraded = latency_ms > self.degraded_latency_ms
        if idempotent:
            self._health.idempotent_retries += 1
        if self._health.append_degraded:
            log.warning(
                "shadow append latency degraded event_id=%s latency_ms=%.1f threshold=%.1f",
                event.get("event_id"),
                latency_ms,
                self.degraded_latency_ms,
            )
        self._health.status = assess_shadow_status(
            enabled=True,
            health=self._health_payload(),
            ledger_corrupt=False,
        )
        self._persist_health()

    def _validate_tail(self, handle: Any) -> None:
        handle.seek(0, os.SEEK_END)
        if handle.tell() > 0:
            handle.seek(handle.tell() - 1)
            if handle.read(1) != b"\n":
                raise ValueError("shadow ledger truncated tail")

    def _find_event(self, handle: Any, event_id: str) -> dict[str, Any] | None:
        if not event_id:
            return None
        handle.seek(0)
        for raw in handle:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:  # pylint: disable=broad-exception-caught
                raise ValueError("shadow ledger invalid middle record") from None
            if isinstance(obj, dict) and str(obj.get("event_id") or "") == event_id:
                return obj
        return None

    def _acquire_lock(self, handle: Any, event_id: str | None) -> bool:
        deadline = time.monotonic() + (self.lock_timeout_ms / 1000.0)
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    self._health.consecutive_lock_timeouts += 1
                    self._record_failure("lock_timeout", event_id=event_id)
                    log.warning(
                        "shadow lock timeout (%sms) event_id=%s consecutive=%s",
                        self.lock_timeout_ms,
                        event_id,
                        self._health.consecutive_lock_timeouts,
                    )
                    if (
                        self._health.consecutive_lock_timeouts
                        >= self.lock_timeout_warn_n
                    ):
                        log.warning(
                            "shadow lock timeouts reached doctor WARN threshold N=%s",
                            self.lock_timeout_warn_n,
                        )
                    return False
                time.sleep(0.005)

    def _next_sequence(self, handle: Any) -> int:
        handle.seek(0)
        last_seq = 0
        for raw in handle:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                seq = obj.get("sequence")
                if isinstance(seq, int) and seq > last_seq:
                    last_seq = seq
            except Exception:  # pylint: disable=broad-exception-caught
                raise ValueError("shadow ledger invalid middle record") from None
        return last_seq + 1

    def _health_payload(self) -> dict[str, Any]:
        return {
            "last_success_at": self._health.last_success_at,
            "last_failure_at": self._health.last_failure_at,
            "last_failure_class": self._health.last_failure_class,
            "consecutive_failures": self._health.consecutive_failures,
            "consecutive_lock_timeouts": self._health.consecutive_lock_timeouts,
            "lock_timeout_warn_threshold_n": self.lock_timeout_warn_n,
            "last_event_id": self._health.last_event_id,
            "last_sequence": self._health.last_sequence,
            "last_append_latency_ms": self._health.last_append_latency_ms,
            "append_degraded": self._health.append_degraded,
            "idempotent_retries": self._health.idempotent_retries,
            "status": self._health.status,
            "degraded_latency_threshold_ms": self.degraded_latency_ms,
        }

    def _record_failure(self, klass: str, *, event_id: str | None) -> None:
        self._health.last_failure_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        self._health.last_failure_class = klass
        self._health.consecutive_failures += 1
        self._health.last_event_id = event_id
        corrupt = klass in {"truncated_tail", "invalid_middle"}
        self._health.status = assess_shadow_status(
            enabled=True,
            health=self._health_payload(),
            ledger_corrupt=corrupt,
        )
        try:
            self._persist_health()
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    def _persist_health(self) -> None:
        atomic_write_json_private(self.health_path, self._health_payload())


def classify_metadata_operation(
    before: Mapping[str, Any] | None, after: Mapping[str, Any]
) -> str:
    """Distinguish metadata_update / supersede / restore from tombstone fields."""
    b = dict(before or {})
    a = dict(after or {})
    b_sup = bool(b.get("superseded") is True)
    a_sup = bool(a.get("superseded") is True)
    if not b_sup and a_sup:
        return "supersede"
    if b_sup and not a_sup:
        return "restore"
    return "metadata_update"
