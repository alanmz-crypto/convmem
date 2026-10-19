"""Shadow-mode scoped mutation proof observer for incremental JSONL commits."""

# pylint: disable=too-many-instance-attributes,too-many-arguments,protected-access,broad-exception-caught,global-statement
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

SUMMARIES = "conversation_summaries"
UNITS = "knowledge_units"

DIAGNOSTIC_SCHEMA = "scoped_writes_shadow_v1"
POLICY_ID = "scoped_writes_v1"
FULL_EVIDENCE_MODE = "full_inventory_v1"
OBSERVER_VERSION = "1"
PER_ATTEMPT_BYTE_CAP = 8 * 1024 * 1024
PER_SOURCE_BYTE_CAP = 64 * 1024 * 1024
SUPPORTED_OPERATIONS = frozenset({"add", "upsert", "update", "delete"})
FORBIDDEN_KWARGS = frozenset({"where", "where_document"})

_tls = threading.local()
_coverage_spies: list[Callable[[str, str, Mapping[str, Any]], None]] = []
_spy_events: list[tuple[str, str]] = []
_TEST_FORCE_OBSERVER_IO_ERROR: Exception | None = None
_TEST_POLICY_ALLOW_ALL = False


class ObserverIOError(RuntimeError):
    """Observer-owned I/O failure (diagnostic only)."""


@dataclass(frozen=True)
class PolicyDecision:
    disposition: str  # allow | would_deny | incomplete
    reason: str = ""
    target_ids: tuple[str, ...] = ()


@dataclass
class NativeCallRecord:
    collection: str
    operation: str
    kwargs: dict[str, Any]
    policy: PolicyDecision
    api_succeeded: bool = False
    guard_finalized: bool = False


@dataclass
class ScopedProofContext:
    attempt_id: str
    transaction_id: str
    source_path: str
    source_identity: str
    generation: str
    rollback_sha256: str | None
    chroma_dir: str
    collection_names: tuple[str, str]
    owned_summary_ids: frozenset[str]
    owned_unit_ids: frozenset[str]
    authorized_summary_ids: frozenset[str]
    authorized_unit_ids: frozenset[str]
    coordinator_revision: str
    bound_pid: int
    bound_thread: int


def register_coverage_spy(spy: Callable[[str, str, Mapping[str, Any]], None]) -> None:
    _coverage_spies.append(spy)


def clear_coverage_spies() -> None:
    _coverage_spies.clear()
    _spy_events.clear()


def set_test_observer_io_error(exc: Exception | None) -> None:
    global _TEST_FORCE_OBSERVER_IO_ERROR
    _TEST_FORCE_OBSERVER_IO_ERROR = exc


def set_test_policy_allow_all(enabled: bool) -> None:
    global _TEST_POLICY_ALLOW_ALL
    _TEST_POLICY_ALLOW_ALL = bool(enabled)


def _notify_coverage(collection: str, operation: str, kwargs: Mapping[str, Any]) -> None:
    _spy_events.append((collection, operation))
    for spy in _coverage_spies:
        spy(collection, operation, kwargs)


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash_record(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def extract_target_ids(kwargs: Mapping[str, Any]) -> tuple[str, ...]:
    raw = kwargs.get("ids")
    if raw is None:
        return ()
    if not isinstance(raw, list):
        return ()
    return tuple(str(item) for item in raw)


def evaluate_call_policy(
    *,
    collection: str,
    operation: str,
    kwargs: Mapping[str, Any],
    context: ScopedProofContext,
    store: Any,
) -> PolicyDecision:
    if _TEST_POLICY_ALLOW_ALL:
        return PolicyDecision("allow")
    op = str(operation)
    if op not in SUPPORTED_OPERATIONS:
        return PolicyDecision("would_deny", "native_unknown")
    if any(key in kwargs for key in FORBIDDEN_KWARGS):
        return PolicyDecision("would_deny", "broad_predicate")
    if collection not in context.collection_names:
        return PolicyDecision("would_deny", "scope_binding")
    ids = extract_target_ids(kwargs)
    if not ids:
        return PolicyDecision("would_deny", "incomplete_census")
    if len(ids) != len(set(ids)):
        return PolicyDecision("would_deny", "duplicate_ids")
    owned = context.owned_summary_ids if collection == SUMMARIES else context.owned_unit_ids
    authorized = (
        context.authorized_summary_ids
        if collection == SUMMARIES
        else context.authorized_unit_ids
    )
    for target_id in ids:
        if target_id in owned:
            meta = _row_metadata(store, collection, target_id)
            if meta is None:
                return PolicyDecision("would_deny", "owner_missing", ids)
            if str(meta.get("source_path") or "") != context.source_path:
                return PolicyDecision("would_deny", "foreign_target", ids)
            continue
        if target_id not in authorized:
            return PolicyDecision("would_deny", "foreign_target", ids)
        if _row_exists(store, collection, target_id):
            return PolicyDecision("would_deny", "foreign_target", ids)
    return PolicyDecision("allow", target_ids=ids)


def _row_exists(store: Any, collection: str, row_id: str) -> bool:
    getter = getattr(store, "get_unit", None)
    if collection == UNITS and callable(getter):
        return getter(row_id) is not None
    col = store._collection(collection)
    res = col.get(ids=[row_id], include=[])
    return bool(res.get("ids"))


def _row_metadata(store: Any, collection: str, row_id: str) -> dict[str, Any] | None:
    getter = getattr(store, "get_unit", None)
    if collection == UNITS and callable(getter):
        row = getter(row_id)
        if row is None:
            return None
        return dict(row.get("metadata") or {})
    col = store._collection(collection)
    res = col.get(ids=[row_id], include=["metadatas"])
    ids = res.get("ids") or []
    if not ids:
        return None
    metas = res.get("metadatas") or []
    return dict(metas[0] or {})


def build_authorized_candidates(prepared: list[dict]) -> tuple[frozenset[str], frozenset[str]]:
    summaries: set[str] = set()
    units: set[str] = set()
    for artifact in prepared:
        summaries.add(str(artifact["doc_id"]))
        for row in artifact.get("units") or []:
            unit = row.get("unit") or row
            units.add(str(unit.get("id") or row.get("id")))
    return frozenset(summaries), frozenset(units)


def build_owned_sets(store: Any, source_path: str) -> tuple[frozenset[str], frozenset[str]]:
    return (
        frozenset(store.ids_for_source(SUMMARIES, source_path)),
        frozenset(store.ids_for_source(UNITS, source_path)),
    )


class ShadowReceiptWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._sequence = 0
        self._prev_hash = "0" * 64
        self._bytes = 0
        self._closed = False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        self._fh = os.fdopen(fd, "w", encoding="utf-8")
        self._append(
            {
                "record_kind": "header",
                "schema": DIAGNOSTIC_SCHEMA,
                "policy_id": POLICY_ID,
                "full_evidence_mode": FULL_EVIDENCE_MODE,
                "observer_version": OBSERVER_VERSION,
            }
        )

    def _append(self, payload: dict[str, Any]) -> None:
        if self._closed:
            return
        if _TEST_FORCE_OBSERVER_IO_ERROR is not None:
            raise _TEST_FORCE_OBSERVER_IO_ERROR
        body = dict(payload)
        body["sequence"] = self._sequence
        body["prev_hash"] = self._prev_hash
        encoded = _canonical_json(body)
        if self._bytes + len(encoded) > PER_ATTEMPT_BYTE_CAP:
            raise ObserverIOError("incomplete:capacity")
        self._fh.write(encoded.decode("utf-8"))
        self._fh.write("\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._prev_hash = _hash_record(body)
        self._sequence += 1
        self._bytes += len(encoded) + 1

    def append(self, payload: dict[str, Any]) -> None:
        self._append(payload)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._fh.flush()
        os.fsync(self._fh.fileno())
        os.fsync(os.open(self.path.parent, os.O_RDONLY))
        self._fh.close()


def receipt_path(state_dir: Path, transaction_id: str, attempt_id: str) -> Path:
    return state_dir / "scoped-shadow" / transaction_id / f"{attempt_id}.jsonl"


@dataclass
class ShadowProofSession:
    mode: str
    context: ScopedProofContext
    state_dir: Path
    writer: ShadowReceiptWriter | None = None
    calls: list[NativeCallRecord] = field(default_factory=list)
    observer_seconds: float = 0.0
    coverage_unqualified: bool = False
    store: Any | None = None
    terminal_emitted: bool = False

    def bind_store(self, store: Any) -> None:
        self.store = store

    def bind_rollback_sha(self, sha256: str) -> None:
        self.context.rollback_sha256 = sha256

    def _observer_span(self) -> float:
        started = time.monotonic()
        return started

    def _charge_observer(self, started: float) -> None:
        self.observer_seconds += max(0.0, time.monotonic() - started)

    def on_native_before(self, collection: str, operation: str, **kwargs: Any) -> None:
        if self.mode != "shadow":
            return
        _notify_coverage(collection, operation, kwargs)
        started = time.monotonic()
        try:
            if (
                os.getpid() != self.context.bound_pid
                or threading.get_ident() != self.context.bound_thread
            ):
                self.coverage_unqualified = True
            if self.store is None:
                self.coverage_unqualified = True
                policy = PolicyDecision("incomplete", "incomplete_census")
            else:
                policy = evaluate_call_policy(
                    collection=collection,
                    operation=operation,
                    kwargs=kwargs,
                    context=self.context,
                    store=self.store,
                )
            self.calls.append(
                NativeCallRecord(collection, operation, dict(kwargs), policy)
            )
            if self.writer is not None:
                self.writer.append(
                    {
                        "record_kind": "intent",
                        "collection": collection,
                        "operation": operation,
                        "policy": policy.disposition,
                        "reason": policy.reason,
                        "target_count": len(extract_target_ids(kwargs)),
                    }
                )
        except Exception:
            self.coverage_unqualified = True
        finally:
            self._charge_observer(started)

    def on_native_after(
        self,
        *,
        collection: str,
        operation: str,
        succeeded: bool,
        guard_finalized: bool,
    ) -> None:
        if self.mode != "shadow":
            return
        started = time.monotonic()
        try:
            for record in reversed(self.calls):
                if record.collection == collection and record.operation == operation:
                    record.api_succeeded = succeeded
                    record.guard_finalized = guard_finalized
                    break
            if self.writer is not None:
                self.writer.append(
                    {
                        "record_kind": "completion",
                        "collection": collection,
                        "operation": operation,
                        "api_succeeded": succeeded,
                        "guard_finalized": guard_finalized,
                    }
                )
        except Exception:
            self.coverage_unqualified = True
        finally:
            self._charge_observer(started)

    def candidate_summary(self) -> tuple[str, list[str]]:
        reasons: list[str] = []
        would_deny = False
        incomplete = False
        for call in self.calls:
            if call.policy.disposition == "would_deny":
                would_deny = True
                if call.policy.reason:
                    reasons.append(call.policy.reason)
            if call.policy.disposition == "incomplete":
                incomplete = True
                if call.policy.reason:
                    reasons.append(call.policy.reason)
        if incomplete:
            return "incomplete", reasons
        if would_deny:
            return "would_deny", reasons
        if len(_spy_events) > len(self.calls):
            self.coverage_unqualified = True
        if self.coverage_unqualified:
            return "incomplete", ["coverage_unqualified"]
        return "observed_compliant", reasons

    def finalize(self, *, full_result: str, phases: Mapping[str, float] | None = None) -> dict[str, Any]:
        if self.terminal_emitted:
            return {}
        self.terminal_emitted = True
        candidate_result, reasons = self.candidate_summary()
        comparison = classify_comparison(full_result, candidate_result)
        payload = {
            "record_kind": "terminal",
            "full_result": full_result,
            "candidate_result": candidate_result,
            "comparison": comparison,
            "reasons": reasons,
            "call_count": len(self.calls),
            "coverage_unqualified": self.coverage_unqualified,
            "observer_seconds": round(self.observer_seconds, 6),
        }
        started = time.monotonic()
        try:
            if self.writer is not None:
                self.writer.append(payload)
                self.writer.close()
        except Exception:
            payload["comparison"] = "incomplete"
            payload["candidate_result"] = "incomplete"
        finally:
            self._charge_observer(started)
        emit_shadow_event(payload, phases=phases)
        return payload


def classify_comparison(full_result: str, candidate_result: str) -> str:
    if full_result == "not_reached" or candidate_result == "incomplete":
        return "incomplete"
    if full_result == "equal" and candidate_result == "observed_compliant":
        return "observed_agreement"
    if full_result == "equal" and candidate_result == "would_deny":
        return "policy_disagreement"
    if full_result == "changed" and candidate_result == "observed_compliant":
        return "detection_gap"
    if full_result == "changed" and candidate_result == "would_deny":
        return "both_seen_problem"
    return "incomplete"


def emit_shadow_event(terminal: Mapping[str, Any], *, phases: Mapping[str, float] | None = None) -> None:
    import sys

    payload = {
        "event": "incremental_scoped_proof_shadow",
        "comparison": terminal.get("comparison"),
        "full_result": terminal.get("full_result"),
        "candidate_result": terminal.get("candidate_result"),
        "call_count": terminal.get("call_count"),
        "coverage_unqualified": terminal.get("coverage_unqualified"),
        "observer_seconds": terminal.get("observer_seconds"),
    }
    if phases is not None:
        payload["observer_phase_seconds"] = round(float(phases.get("scoped_proof_observer", 0.0)), 6)
    print(json.dumps(payload, sort_keys=True), file=sys.stderr)


def active_session() -> ShadowProofSession | None:
    return getattr(_tls, "session", None)


def set_active_session(session: ShadowProofSession | None) -> None:
    _tls.session = session


@contextmanager
def shadow_proof_attempt(
    *,
    mode: str,
    state_dir: Path,
    transaction_id: str,
    source_path: str,
    source_identity: str,
    generation: str,
    prepared: list[dict],
    store: Any,
    chroma_dir: str,
    coordinator_revision: str,
) -> Iterator[ShadowProofSession | None]:
    if mode == "off":
        yield None
        return
    owned_summaries, owned_units = build_owned_sets(store, source_path)
    auth_summaries, auth_units = build_authorized_candidates(prepared)
    attempt_id = str(uuid.uuid4())
    context = ScopedProofContext(
        attempt_id=attempt_id,
        transaction_id=transaction_id,
        source_path=source_path,
        source_identity=source_identity,
        generation=generation,
        rollback_sha256=None,
        chroma_dir=chroma_dir,
        collection_names=(SUMMARIES, UNITS),
        owned_summary_ids=owned_summaries,
        owned_unit_ids=owned_units,
        authorized_summary_ids=auth_summaries,
        authorized_unit_ids=auth_units,
        coordinator_revision=coordinator_revision,
        bound_pid=os.getpid(),
        bound_thread=threading.get_ident(),
    )
    path = receipt_path(state_dir, transaction_id, attempt_id)
    writer: ShadowReceiptWriter | None
    try:
        writer = ShadowReceiptWriter(path)
    except Exception:
        writer = None
    session = ShadowProofSession(
        mode=mode,
        context=context,
        state_dir=state_dir,
        writer=writer,
        store=store,
    )
    prior = active_session()
    set_active_session(session)
    try:
        yield session
    finally:
        set_active_session(prior)


def load_terminal_record(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    terminal: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("record_kind") == "terminal":
            terminal = payload
    return terminal


def receipts_complete(path: Path) -> bool:
    terminal = load_terminal_record(path)
    return bool(terminal and terminal.get("comparison") not in {None, "incomplete"})
