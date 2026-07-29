# pylint: disable=duplicate-code,too-many-instance-attributes,too-many-locals
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
    _hooks,
    COLLECTION_KNOWLEDGE_UNITS,
    SHADOW_SCHEMA_VERSION,
    SecureIOHooks,
    SecureLedgerError,
    SecureLedgerRefused,
    atomic_write_json_private_secure,
    open_existing_shadow_ledger_fd,
    read_ledger_header_and_tail,
    projection_state_hash,
    sha256_canonical,
    write_all_fd,
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
# Degradation marker only — not an approved activation SLO.
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
class AppendTiming:
    """Testable complete-path timing breakdown (milliseconds)."""

    lock_wait_ms: float = 0.0
    ledger_append_ms: float = 0.0
    health_persist_ms: float = 0.0
    complete_append_ms: float = 0.0
    bytes_read_for_sequence: int = 0


@dataclass
class ShadowHealth:
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
    lock_wait_ms: float | None = None
    ledger_append_ms: float | None = None
    health_persist_ms: float | None = None
    complete_append_ms: float | None = None
    bytes_read_for_sequence: int | None = None
    health_persist_failed: bool = False


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
    klass = h.get("last_failure_class")
    if klass in {
        "truncated_tail",
        "invalid_middle",
        "invalid_tail",
        "invalid_header",
        "ValueError",
    }:
        if int(h.get("consecutive_failures") or 0) >= 1:
            if klass in {
                "truncated_tail",
                "invalid_middle",
                "invalid_tail",
                "invalid_header",
            }:
                return "corrupt"
    if (  # pylint: disable=too-many-boolean-expressions
        h.get("append_degraded")
        or int(h.get("consecutive_lock_timeouts") or 0) >= 1
        or int(h.get("consecutive_failures") or 0) >= 1
        or klass == "lock_timeout"
        or klass == "uncertain_ack"
        or h.get("health_persist_failed")
    ):
        return "degraded"
    return "healthy"


def ledger_has_corruption(ledger_path: Path) -> bool:
    """True if truncated tail or invalid JSONL record is present (diagnostic)."""
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
    """Append-only shadow sink for knowledge_units only (never summaries).

    Does not create a missing ledger. Fixtures/C5 must create a header-bearing
    private ledger before observe() can succeed.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        ledger_path: Path,
        health_path: Path,
        lock_timeout_ms: int = LOCK_ACQUIRE_TIMEOUT_MS,
        lock_timeout_warn_n: int = LOCK_TIMEOUT_WARN_THRESHOLD_N,
        degraded_latency_ms: float = FSYNC_DEGRADED_LATENCY_MS,
        io_hooks: SecureIOHooks | None = None,
    ) -> None:
        self.ledger_path = Path(ledger_path)
        self.health_path = Path(health_path)
        self.lock_timeout_ms = lock_timeout_ms
        self.lock_timeout_warn_n = lock_timeout_warn_n
        self.degraded_latency_ms = degraded_latency_ms
        self._hooks = io_hooks
        self._health = ShadowHealth()
        self.last_timing = AppendTiming()
        # Do not mkdir/create ledger as a side effect of construction.

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
            klass = self._classify_failure(exc)
            self._record_failure(klass, event_id=event_id)
            log.error(
                "shadow append failed event_id=%s entity=%s: %s",
                event_id,
                stable_entity_id,
                exc,
            )

    @staticmethod
    def _classify_failure(exc: BaseException) -> str:
        msg = str(exc).lower()
        if isinstance(exc, SecureLedgerRefused):
            if "header" in msg:
                return "invalid_header"
            return "secure_refused"
        if "truncated tail" in msg:
            return "truncated_tail"
        if "invalid tail" in msg or "invalid final" in msg:
            return "invalid_tail"
        if "invalid middle" in msg:
            return "invalid_middle"
        return type(exc).__name__

    def _append_event(self, event: dict[str, Any]) -> None:
        """Complete path: lock → header/tail → append/fsync → unlock → health."""
        complete_start = time.monotonic()
        timing = AppendTiming()
        uncertain = False
        fd = -1
        dir_fd = -1
        pre_lock_st = None

        lock_start = time.monotonic()
        try:
            fd, dir_fd, pre_lock_st = open_existing_shadow_ledger_fd(
                self.ledger_path, hooks=self._hooks
            )
        except SecureLedgerError:
            timing.complete_append_ms = (time.monotonic() - complete_start) * 1000.0
            self.last_timing = timing
            raise

        try:
            if not self._acquire_lock_fd(fd, event.get("event_id")):
                timing.lock_wait_ms = (time.monotonic() - lock_start) * 1000.0
                timing.complete_append_ms = (time.monotonic() - complete_start) * 1000.0
                self.last_timing = timing
                return
            timing.lock_wait_ms = (time.monotonic() - lock_start) * 1000.0

            ledger_start = time.monotonic()
            try:
                # Identity recheck after lock.
                hooks = _hooks(self._hooks)
                st = hooks.fstat(fd)
                if (st.st_dev, st.st_ino) != (pre_lock_st.st_dev, pre_lock_st.st_ino):
                    raise SecureLedgerRefused("ledger identity changed under lock")

                head_tail = read_ledger_header_and_tail(fd, hooks=self._hooks)
                timing.bytes_read_for_sequence = head_tail.bytes_read
                event["sequence"] = head_tail.next_sequence

                line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
                data = line.encode("utf-8")
                hooks.lseek(fd, 0, os.SEEK_END)
                try:
                    write_all_fd(fd, data, hooks=self._hooks)
                except OSError as exc:
                    # Partial write: do not truncate or pad; refuse later via tail.
                    raise OSError(exc.errno, f"short event write: {exc}") from exc
                # Flush is implicit for raw fd writes; fsync for durability.
                try:
                    hooks.fsync(fd)
                except OSError:
                    uncertain = True
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                timing.ledger_append_ms = (time.monotonic() - ledger_start) * 1000.0
        finally:
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if dir_fd >= 0:
                try:
                    os.close(dir_fd)
                except OSError:
                    pass

        if uncertain:
            timing.complete_append_ms = (time.monotonic() - complete_start) * 1000.0
            self.last_timing = timing
            self._health.last_append_latency_ms = timing.complete_append_ms
            self._apply_timing(timing)
            self._record_failure("uncertain_ack", event_id=event.get("event_id"))
            log.warning(
                "shadow append uncertain_ack event_id=%s "
                "(fsync failed; retry may reuse id with new sequence)",
                event.get("event_id"),
            )
            return

        # Success path health update (before persistence; timing includes persist).
        self._health.last_success_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        self._health.consecutive_failures = 0
        self._health.consecutive_lock_timeouts = 0
        self._health.last_failure_class = None
        self._health.last_event_id = event.get("event_id")
        self._health.last_sequence = event.get("sequence")
        self._health.health_persist_failed = False
        self._apply_timing(timing)
        # Degraded marker may still flip after health timing is included.
        self._health.status = "healthy"

        health_start = time.monotonic()
        health_error: Exception | None = None
        try:
            # Tentative complete latency before persist for degraded check inputs.
            tentative = (time.monotonic() - complete_start) * 1000.0
            self._health.last_append_latency_ms = tentative
            self._persist_health()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            health_error = exc
            self._health.health_persist_failed = True
            log.warning(
                "shadow health persistence failed event_id=%s: %s",
                event.get("event_id"),
                exc,
            )
        timing.health_persist_ms = (time.monotonic() - health_start) * 1000.0
        timing.complete_append_ms = (time.monotonic() - complete_start) * 1000.0
        self.last_timing = timing
        self._apply_timing(timing)
        self._health.last_append_latency_ms = timing.complete_append_ms
        self._health.append_degraded = (
            timing.complete_append_ms > self.degraded_latency_ms
        )
        if self._health.append_degraded:
            log.warning(
                "shadow append latency degraded event_id=%s latency_ms=%.1f threshold=%.1f",
                event.get("event_id"),
                timing.complete_append_ms,
                self.degraded_latency_ms,
            )
        self._health.status = assess_shadow_status(
            enabled=True,
            health=self._health_payload(),
            ledger_corrupt=False,
        )
        # One bounded corrective publication of final status/timing — not a loop.
        if health_error is None:
            try:
                self._persist_health()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self._health.health_persist_failed = True
                log.warning(
                    "shadow health final publication failed event_id=%s: %s",
                    event.get("event_id"),
                    exc,
                )

    def _apply_timing(self, timing: AppendTiming) -> None:
        self._health.lock_wait_ms = timing.lock_wait_ms
        self._health.ledger_append_ms = timing.ledger_append_ms
        self._health.health_persist_ms = timing.health_persist_ms
        self._health.complete_append_ms = timing.complete_append_ms
        self._health.bytes_read_for_sequence = timing.bytes_read_for_sequence

    def _acquire_lock_fd(self, fd: int, event_id: str | None) -> bool:
        deadline = time.monotonic() + (self.lock_timeout_ms / 1000.0)
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
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
            "lock_wait_ms": self._health.lock_wait_ms,
            "ledger_append_ms": self._health.ledger_append_ms,
            "health_persist_ms": self._health.health_persist_ms,
            "complete_append_ms": self._health.complete_append_ms,
            "bytes_read_for_sequence": self._health.bytes_read_for_sequence,
            "health_persist_failed": self._health.health_persist_failed,
        }

    def _record_failure(self, klass: str, *, event_id: str | None) -> None:
        self._health.last_failure_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        self._health.last_failure_class = klass
        self._health.consecutive_failures += 1
        self._health.last_event_id = event_id
        corrupt = klass in {
            "truncated_tail",
            "invalid_middle",
            "invalid_tail",
            "invalid_header",
        }
        self._health.status = assess_shadow_status(
            enabled=True,
            health=self._health_payload(),
            ledger_corrupt=corrupt,
        )
        try:
            self._persist_health()
        except Exception:  # pylint: disable=broad-exception-caught
            self._health.health_persist_failed = True
            log.warning(
                "shadow health persistence failed while recording failure class=%s",
                klass,
            )

    def _persist_health(self) -> None:
        atomic_write_json_private_secure(
            self.health_path, self._health_payload(), hooks=self._hooks
        )


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
