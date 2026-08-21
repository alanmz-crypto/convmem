"""Agent Run Ledger — durable, append-only run identity events (Arc Runway Ledger).

Deep module: envelope validation, sibling-lock append, deterministic reducer,
and query views. No LLM calls. No Chroma/ledger authority changes.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import secrets
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SUPPORTED_SCHEMA_VERSIONS = frozenset({1})

VALID_CLIENTS = frozenset(
    {
        "kiro",
        "codex",
        "cursor",
        "crush",
        "copilot",
        "continue",
        "aider",
        "openwebui",
        "unknown",
    }
)
VALID_EVENT_TYPES = frozenset(
    {"run_started", "run_enriched", "run_stopped", "capture_diagnostic"}
)
VALID_STATUSES = frozenset({"active", "completed", "aborted", "unknown", "diagnostic"})
VALID_RELATIONS = frozenset({"observed", "explicit"})
VALID_COMMIT_SOURCES = frozenset({"git", "caller"})
VALID_FILE_SOURCES = frozenset({"git", "caller"})
VALID_FILE_CHANGES = frozenset({"added", "modified", "deleted", "unknown"})
VALID_LEDGER_SOURCES = frozenset({"record", "caller"})

_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_LEDGER_ID_RE = re.compile(r"^(obs_|dec_|ver_|dec_prop_)[A-Za-z0-9_.-]+$")
_EVENT_ID_RE = re.compile(r"^arevt_[A-Za-z0-9_-]+$")
_RUN_ID_RE = re.compile(r"^run_[A-Za-z0-9_-]+$")

DEFAULT_DATA_DIR = Path("~/.local/share/convmem").expanduser()
AGENT_RUN_LOG_NAME = "agent_runs.jsonl"
AGENT_RUN_LOCK_NAME = "agent_runs.lock"

# Forbidden fact/source payload keys (prompt/content/secrets).
_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "assistant_response",
        "prompt",
        "USER_PROMPT",
        "tool_input",
        "tool_response",
        "content",
        "messages",
        "token",
        "password",
        "secret",
    }
)


class AgentRunLedgerError(ValueError):
    """Base error for validation / durability failures."""


class CorruptionError(AgentRunLedgerError):
    """Event log is corrupt or an event-id collision has mismatched bytes."""


class AmbiguityError(AgentRunLedgerError):
    """Lookup matched more than one active run."""


class NotFoundError(AgentRunLedgerError):
    """Lookup matched zero runs."""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_iso_ms() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def new_run_id() -> str:
    return f"run_{secrets.token_hex(16)}"


def new_event_id() -> str:
    return f"arevt_{secrets.token_hex(16)}"


def default_log_path(data_dir: Path | None = None) -> Path:
    root = (data_dir or DEFAULT_DATA_DIR).expanduser()
    return root / AGENT_RUN_LOG_NAME


def default_lock_path(data_dir: Path | None = None) -> Path:
    root = (data_dir or DEFAULT_DATA_DIR).expanduser()
    return root / AGENT_RUN_LOCK_NAME


def canonical_event_bytes(event: Mapping[str, Any]) -> bytes:
    """Stable byte form for duplicate-id comparison (excludes lock-assigned sequence)."""
    payload = {k: v for k, v in event.items() if k != "sequence"}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def event_content_digest(event: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_event_bytes(event)).hexdigest()


def delivery_event_id(
    *,
    client: str,
    hook_event_name: str,
    session_id: str | None,
    cwd: str | None,
    source_ref: str,
) -> str:
    """Deterministic event_id for identical hook deliveries (idempotent retries)."""
    material = "|".join(
        [
            "kiro-delivery-v1",
            client,
            hook_event_name,
            session_id or "",
            cwd or "",
            source_ref,
        ]
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return f"arevt_{digest}"


def _reject_forbidden_keys(obj: Mapping[str, Any], *, where: str) -> None:
    bad = _FORBIDDEN_PAYLOAD_KEYS.intersection(obj)
    if bad:
        raise AgentRunLedgerError(f"{where}: forbidden keys {sorted(bad)}")


def _require_str_or_none(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AgentRunLedgerError(f"{field_name} must be string or null")
    return value


def _validate_source(source: Any) -> dict[str, str]:
    if not isinstance(source, Mapping):
        raise AgentRunLedgerError("source must be an object")
    _reject_forbidden_keys(source, where="source")
    kind = source.get("kind")
    ref = source.get("ref")
    if not isinstance(kind, str) or not kind:
        raise AgentRunLedgerError("source.kind must be a non-empty string")
    if not isinstance(ref, str) or not ref:
        raise AgentRunLedgerError("source.ref must be a non-empty string")
    return {"kind": kind, "ref": ref}


def _validate_commit(row: Any) -> dict[str, str]:
    if not isinstance(row, Mapping):
        raise AgentRunLedgerError("facts.commits entries must be objects")
    sha = row.get("sha")
    relation = row.get("relation")
    source = row.get("source")
    if not isinstance(sha, str) or not _SHA40_RE.fullmatch(sha):
        raise AgentRunLedgerError("facts.commits.sha must be 40-hex")
    if relation not in VALID_RELATIONS:
        raise AgentRunLedgerError("facts.commits.relation invalid")
    if source not in VALID_COMMIT_SOURCES:
        raise AgentRunLedgerError("facts.commits.source invalid")
    return {"sha": sha, "relation": relation, "source": source}


def _validate_file(row: Any) -> dict[str, str]:
    if not isinstance(row, Mapping):
        raise AgentRunLedgerError("facts.files entries must be objects")
    path = row.get("path")
    relation = row.get("relation")
    source = row.get("source")
    change = row.get("change", "unknown")
    if not isinstance(path, str) or not path or path.startswith("/"):
        raise AgentRunLedgerError("facts.files.path must be repo-relative")
    if relation not in VALID_RELATIONS:
        raise AgentRunLedgerError("facts.files.relation invalid")
    if source not in VALID_FILE_SOURCES:
        raise AgentRunLedgerError("facts.files.source invalid")
    if change not in VALID_FILE_CHANGES:
        raise AgentRunLedgerError("facts.files.change invalid")
    return {"path": path, "relation": relation, "source": source, "change": change}


def _validate_ledger_record(row: Any) -> dict[str, str]:
    if not isinstance(row, Mapping):
        raise AgentRunLedgerError("facts.ledger_records entries must be objects")
    ledger_id = row.get("ledger_id")
    relation = row.get("relation", "explicit")
    source = row.get("source", "caller")
    if not isinstance(ledger_id, str) or not _LEDGER_ID_RE.fullmatch(ledger_id):
        raise AgentRunLedgerError("facts.ledger_records.ledger_id invalid")
    if relation != "explicit":
        raise AgentRunLedgerError("facts.ledger_records.relation must be explicit")
    if source not in VALID_LEDGER_SOURCES:
        raise AgentRunLedgerError("facts.ledger_records.source invalid")
    return {"ledger_id": ledger_id, "relation": relation, "source": source}


def validate_facts(facts: Any) -> dict[str, Any]:
    if facts is None:
        return {
            "head_revision": None,
            "commits": [],
            "files": [],
            "ledger_records": [],
        }
    if not isinstance(facts, Mapping):
        raise AgentRunLedgerError("facts must be an object")
    _reject_forbidden_keys(facts, where="facts")
    allowed = {"head_revision", "commits", "files", "ledger_records"}
    unknown = set(facts) - allowed
    if unknown:
        raise AgentRunLedgerError(f"facts has unknown keys: {sorted(unknown)}")
    head = facts.get("head_revision")
    if head is not None and (not isinstance(head, str) or not _SHA40_RE.fullmatch(head)):
        raise AgentRunLedgerError("facts.head_revision must be 40-hex or null")
    commits = facts.get("commits", [])
    files = facts.get("files", [])
    ledger_records = facts.get("ledger_records", [])
    if not isinstance(commits, list) or not isinstance(files, list) or not isinstance(
        ledger_records, list
    ):
        raise AgentRunLedgerError("facts list fields must be arrays")
    return {
        "head_revision": head,
        "commits": [_validate_commit(c) for c in commits],
        "files": [_validate_file(f) for f in files],
        "ledger_records": [_validate_ledger_record(r) for r in ledger_records],
    }


def validate_envelope(event: Mapping[str, Any], *, require_sequence: bool = False) -> dict[str, Any]:
    """Validate and normalize a run-ledger event. Returns a clean dict."""
    if not isinstance(event, Mapping):
        raise AgentRunLedgerError("event must be an object")
    _reject_forbidden_keys(event, where="event")

    version = event.get("schema_version")
    if not isinstance(version, int) or version not in SUPPORTED_SCHEMA_VERSIONS:
        raise AgentRunLedgerError(f"unsupported schema_version: {version!r}")

    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not _EVENT_ID_RE.fullmatch(event_id):
        raise AgentRunLedgerError("event_id invalid")

    event_type = event.get("event_type")
    if event_type not in VALID_EVENT_TYPES:
        raise AgentRunLedgerError(f"event_type invalid: {event_type!r}")

    run_id = event.get("run_id")
    if event_type == "capture_diagnostic":
        if run_id is not None and not (isinstance(run_id, str) and _RUN_ID_RE.fullmatch(run_id)):
            raise AgentRunLedgerError("diagnostic run_id must be null or valid run_id")
    else:
        if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
            raise AgentRunLedgerError("run_id required for lifecycle/enrichment")

    client = event.get("client")
    if client not in VALID_CLIENTS:
        raise AgentRunLedgerError(f"client invalid: {client!r}")

    native = _require_str_or_none(event.get("native_session_id"), field_name="native_session_id")
    repository = _require_str_or_none(event.get("repository"), field_name="repository")
    branch = _require_str_or_none(event.get("branch"), field_name="branch")
    if branch is not None and branch != "detached" and not branch:
        raise AgentRunLedgerError("branch must be non-empty, null, or detached")

    status = event.get("status")
    if event_type == "capture_diagnostic":
        if status != "diagnostic":
            raise AgentRunLedgerError("capture_diagnostic status must be diagnostic")
    elif event_type == "run_enriched":
        if status != "active":
            raise AgentRunLedgerError("run_enriched status must be active")
    elif event_type == "run_started":
        if status != "active":
            raise AgentRunLedgerError("run_started status must be active")
    elif event_type == "run_stopped":
        if status not in {"completed", "aborted", "unknown"}:
            raise AgentRunLedgerError("run_stopped status must be terminal")
    elif status not in VALID_STATUSES:
        raise AgentRunLedgerError(f"status invalid: {status!r}")

    event_time = _require_str_or_none(event.get("event_time"), field_name="event_time")
    if event_type != "capture_diagnostic" and not event_time:
        raise AgentRunLedgerError("event_time required for lifecycle/enrichment")

    recorded_at = event.get("recorded_at")
    if not isinstance(recorded_at, str) or not recorded_at:
        raise AgentRunLedgerError("recorded_at required")

    source = _validate_source(event.get("source"))
    facts = validate_facts(event.get("facts"))

    sequence = event.get("sequence")
    if require_sequence:
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            raise AgentRunLedgerError("sequence must be a positive int")
    elif sequence is not None and (
        not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1
    ):
        raise AgentRunLedgerError("sequence must be a positive int when present")

    out: dict[str, Any] = {
        "schema_version": version,
        "event_id": event_id,
        "event_type": event_type,
        "run_id": run_id,
        "event_time": event_time,
        "recorded_at": recorded_at,
        "client": client,
        "native_session_id": native,
        "repository": repository,
        "branch": branch,
        "status": status,
        "source": source,
        "facts": facts,
    }
    if sequence is not None:
        out["sequence"] = sequence
    return out


@dataclass
class EvidenceConflict:
    kind: str
    key: str
    existing: Any
    incoming: Any


@dataclass
class RunView:
    run_id: str
    client: str
    native_session_id: str | None
    repository: str | None
    branch: str | None
    status: str
    identity_completeness: str
    terminal_evidence: bool
    event_ids: list[str] = field(default_factory=list)
    source_refs: list[dict[str, str]] = field(default_factory=list)
    head_revision: str | None = None
    commits: list[dict[str, str]] = field(default_factory=list)
    files: list[dict[str, str]] = field(default_factory=list)
    ledger_records: list[dict[str, str]] = field(default_factory=list)
    conflicts: list[EvidenceConflict] = field(default_factory=list)
    started_event_time: str | None = None
    stopped_event_time: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "client": self.client,
            "native_session_id": self.native_session_id,
            "repository": self.repository,
            "branch": self.branch,
            "status": self.status,
            "identity_completeness": self.identity_completeness,
            "terminal_evidence": self.terminal_evidence,
            "event_ids": list(self.event_ids),
            "source_refs": list(self.source_refs),
            "head_revision": self.head_revision,
            "commits": list(self.commits),
            "files": list(self.files),
            "ledger_records": list(self.ledger_records),
            "conflicts": [
                {
                    "kind": c.kind,
                    "key": c.key,
                    "existing": c.existing,
                    "incoming": c.incoming,
                }
                for c in self.conflicts
            ],
            "started_event_time": self.started_event_time,
            "stopped_event_time": self.stopped_event_time,
        }


@dataclass
class ReduceResult:
    runs: dict[str, RunView]
    diagnostics: list[dict[str, Any]]
    problems: list[str]
    event_digests: dict[str, str]

    def get_run(self, run_id: str) -> RunView | None:
        return self.runs.get(run_id)


def _identity_completeness(native_session_id: str | None) -> str:
    return "complete" if native_session_id else "partial"


def _commit_key(row: Mapping[str, str]) -> str:
    return f"{row['sha']}|{row['relation']}|{row['source']}"


def _file_key(row: Mapping[str, str]) -> str:
    return f"{row['path']}|{row['relation']}|{row['source']}|{row['change']}"


def _ledger_key(row: Mapping[str, str]) -> str:
    return f"{row['ledger_id']}|{row['relation']}|{row['source']}"


def _merge_facts(view: RunView, facts: Mapping[str, Any]) -> None:
    head = facts.get("head_revision")
    if head is not None:
        if view.head_revision is None:
            view.head_revision = head
        elif view.head_revision != head:
            view.conflicts.append(
                EvidenceConflict(
                    kind="head_revision",
                    key="head_revision",
                    existing=view.head_revision,
                    incoming=head,
                )
            )

    seen_commits = {_commit_key(c) for c in view.commits}
    for row in facts.get("commits", []):
        key = _commit_key(row)
        if key in seen_commits:
            continue
        # Same sha with different relation is kept distinct (observed vs explicit).
        view.commits.append(dict(row))
        seen_commits.add(key)

    seen_files = {_file_key(f) for f in view.files}
    for row in facts.get("files", []):
        key = _file_key(row)
        if key in seen_files:
            continue
        view.files.append(dict(row))
        seen_files.add(key)

    seen_ledger = {_ledger_key(r) for r in view.ledger_records}
    for row in facts.get("ledger_records", []):
        key = _ledger_key(row)
        if key in seen_ledger:
            continue
        view.ledger_records.append(dict(row))
        seen_ledger.add(key)


def _apply_identity(view: RunView, event: Mapping[str, Any]) -> None:
    for field_name in ("native_session_id", "repository", "branch", "client"):
        incoming = event.get(field_name)
        if incoming is None:
            continue
        existing = getattr(view, field_name)
        if existing is None:
            setattr(view, field_name, incoming)
        elif existing != incoming:
            view.conflicts.append(
                EvidenceConflict(
                    kind="identity",
                    key=field_name,
                    existing=existing,
                    incoming=incoming,
                )
            )
    view.identity_completeness = _identity_completeness(view.native_session_id)


def reduce_events(events: Iterable[Mapping[str, Any]]) -> ReduceResult:
    """Replay events in append order (caller must pass sequence order)."""
    runs: dict[str, RunView] = {}
    diagnostics: list[dict[str, Any]] = []
    problems: list[str] = []
    digests: dict[str, str] = {}

    for raw in events:
        try:
            event = validate_envelope(raw, require_sequence=False)
        except AgentRunLedgerError as exc:
            problems.append(str(exc))
            continue

        eid = event["event_id"]
        digest = event_content_digest(event)
        if eid in digests:
            if digests[eid] != digest:
                problems.append(f"event_id reused with different content: {eid}")
            # Exact duplicate is idempotent — skip apply.
            continue
        digests[eid] = digest

        etype = event["event_type"]
        if etype == "capture_diagnostic":
            diagnostics.append(dict(event))
            continue

        run_id = event["run_id"]
        if etype == "run_started":
            if run_id in runs:
                problems.append(f"illegal transition: run_started for existing run {run_id}")
                continue
            view = RunView(
                run_id=run_id,
                client=event["client"],
                native_session_id=event.get("native_session_id"),
                repository=event.get("repository"),
                branch=event.get("branch"),
                status="active",
                identity_completeness=_identity_completeness(event.get("native_session_id")),
                terminal_evidence=False,
                started_event_time=event.get("event_time"),
            )
            view.event_ids.append(eid)
            view.source_refs.append(dict(event["source"]))
            _merge_facts(view, event["facts"])
            runs[run_id] = view
            continue

        view = runs.get(run_id)
        if view is None:
            problems.append(f"illegal transition: {etype} for unknown run {run_id}")
            continue

        view.event_ids.append(eid)
        view.source_refs.append(dict(event["source"]))
        _apply_identity(view, event)
        _merge_facts(view, event["facts"])

        if etype == "run_stopped":
            if view.terminal_evidence:
                # Duplicate stop with same event_id already handled; second distinct stop is illegal.
                problems.append(f"illegal transition: run already terminal {run_id}")
                continue
            view.status = event["status"]
            view.terminal_evidence = True
            view.stopped_event_time = event.get("event_time")
        # run_enriched: status unchanged (including if already terminal)

    return ReduceResult(
        runs=runs, diagnostics=diagnostics, problems=problems, event_digests=digests
    )


def find_active_runs(
    result: ReduceResult,
    *,
    client: str,
    native_session_id: str | None,
    repository: str | None,
) -> list[RunView]:
    """Exact-match active run lookup. Never uses recency."""
    matches: list[RunView] = []
    for view in result.runs.values():
        if view.status != "active":
            continue
        if view.client != client:
            continue
        if view.native_session_id != native_session_id:
            continue
        if view.repository != repository:
            continue
        matches.append(view)
    return matches


def resolve_unique_active_run(
    result: ReduceResult,
    *,
    client: str,
    native_session_id: str | None,
    repository: str | None,
) -> RunView:
    matches = find_active_runs(
        result,
        client=client,
        native_session_id=native_session_id,
        repository=repository,
    )
    if not matches:
        raise NotFoundError("no active run matches exact identity")
    if len(matches) > 1:
        raise AmbiguityError(
            f"ambiguous active runs: {[m.run_id for m in matches]}"
        )
    return matches[0]


# --- Durable writer (T2) -------------------------------------------------


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _reject_symlink(path: Path, *, label: str) -> None:
    if path.is_symlink():
        raise CorruptionError(f"{label} refuses symlink path: {path}")


def validate_log_text(text: str) -> tuple[list[dict[str, Any]], int]:
    """Parse JSONL; fail closed on interior corruption or truncated tail.

    Returns (events_in_order, next_sequence).
    """
    if not text:
        return [], 1
    if not text.endswith("\n") and text.strip():
        # Truncated final line (no terminating newline after content).
        raise CorruptionError("truncated final event line")

    lines = text.splitlines()
    events: list[dict[str, Any]] = []
    last_seq = 0
    digests: dict[str, str] = {}

    for number, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CorruptionError(f"malformed JSON at line {number}") from exc
        if not isinstance(row, dict):
            raise CorruptionError(f"non-object event at line {number}")
        try:
            event = validate_envelope(row, require_sequence=True)
        except AgentRunLedgerError as exc:
            raise CorruptionError(f"invalid envelope at line {number}: {exc}") from exc

        seq = event["sequence"]
        if seq <= last_seq:
            raise CorruptionError(f"non-increasing sequence at line {number}")
        last_seq = seq

        eid = event["event_id"]
        digest = event_content_digest(event)
        if eid in digests and digests[eid] != digest:
            raise CorruptionError(f"event_id collision with different bytes: {eid}")
        digests[eid] = digest
        events.append(event)

    return events, last_seq + 1


def load_events_from_path(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if path.is_symlink():
        raise CorruptionError(f"refuses symlink log: {path}")
    text = path.read_text(encoding="utf-8")
    events, _ = validate_log_text(text)
    return events


@dataclass
class AppendResult:
    event: dict[str, Any]
    created: bool  # False when exact idempotent retry


class AgentRunLedger:
    """Append-only agent run event store with sibling flock."""

    def __init__(
        self,
        *,
        log_path: Path | None = None,
        lock_path: Path | None = None,
        data_dir: Path | None = None,
        lock_timeout_s: float = 5.0,
    ) -> None:
        root = (data_dir or DEFAULT_DATA_DIR).expanduser()
        self.log_path = (log_path or (root / AGENT_RUN_LOG_NAME)).expanduser()
        self.lock_path = (lock_path or (root / AGENT_RUN_LOCK_NAME)).expanduser()
        self.lock_timeout_s = lock_timeout_s

    def _prepare_paths(self) -> None:
        parent = self.log_path.parent
        _reject_symlink(parent, label="data dir")
        _ensure_private_dir(parent)
        _reject_symlink(self.log_path, label="log")
        _reject_symlink(self.lock_path, label="lock")

    def _acquire_lock(self):
        self._prepare_paths()
        handle = open(self.lock_path, "a+", encoding="utf-8")
        try:
            os.chmod(self.lock_path, 0o600)
        except OSError:
            pass
        deadline = time.monotonic() + self.lock_timeout_s
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return handle
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    handle.close()
                    raise AgentRunLedgerError("agent run ledger lock timeout")
                time.sleep(0.01)

    def append_event(self, event: Mapping[str, Any]) -> AppendResult:
        """Validate, assign sequence, durable append. Exact event_id retry is idempotent."""
        normalized = validate_envelope(event, require_sequence=False)
        lock_handle = self._acquire_lock()
        try:
            if self.log_path.exists():
                text = self.log_path.read_text(encoding="utf-8")
                existing, next_seq = validate_log_text(text)
            else:
                existing, next_seq = [], 1

            for row in existing:
                if row["event_id"] == normalized["event_id"]:
                    if event_content_digest(row) != event_content_digest(normalized):
                        raise CorruptionError(
                            f"event_id reused with different content: {normalized['event_id']}"
                        )
                    return AppendResult(event=row, created=False)

            # Transition checks against reduced state of existing events.
            reduced = reduce_events(existing)
            self._assert_transition_allowed(normalized, reduced)

            to_write = dict(normalized)
            to_write["sequence"] = next_seq
            if "recorded_at" not in to_write or not to_write["recorded_at"]:
                to_write["recorded_at"] = now_iso_ms()
            to_write = validate_envelope(to_write, require_sequence=True)

            line = json.dumps(to_write, ensure_ascii=False, sort_keys=True) + "\n"
            created_new_file = not self.log_path.exists()
            with open(self.log_path, "a", encoding="utf-8") as handle:
                if created_new_file:
                    try:
                        os.chmod(self.log_path, 0o600)
                    except OSError:
                        pass
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            if created_new_file:
                dir_fd = os.open(str(self.log_path.parent), os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            return AppendResult(event=to_write, created=True)
        finally:
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
            finally:
                lock_handle.close()

    def _assert_transition_allowed(
        self, event: Mapping[str, Any], reduced: ReduceResult
    ) -> None:
        etype = event["event_type"]
        if etype == "capture_diagnostic":
            return
        run_id = event["run_id"]
        if etype == "run_started":
            if run_id in reduced.runs:
                raise AgentRunLedgerError(f"run already exists: {run_id}")
            return
        view = reduced.runs.get(run_id)
        if view is None:
            raise AgentRunLedgerError(f"unknown run_id: {run_id}")
        if etype == "run_stopped" and view.terminal_evidence:
            raise AgentRunLedgerError(f"run already terminal: {run_id}")

    def load(self) -> ReduceResult:
        return reduce_events(load_events_from_path(self.log_path))

    def validate(self) -> dict[str, Any]:
        """Report validation without repair."""
        report: dict[str, Any] = {
            "ok": True,
            "path": str(self.log_path),
            "problems": [],
            "event_count": 0,
            "run_count": 0,
        }
        try:
            if self.log_path.is_symlink():
                raise CorruptionError(f"refuses symlink log: {self.log_path}")
            if not self.log_path.exists():
                return report
            text = self.log_path.read_text(encoding="utf-8")
            events, _ = validate_log_text(text)
            reduced = reduce_events(events)
            report["event_count"] = len(events)
            report["run_count"] = len(reduced.runs)
            report["problems"] = list(reduced.problems)
            if reduced.problems:
                report["ok"] = False
        except (OSError, CorruptionError, AgentRunLedgerError) as exc:
            report["ok"] = False
            report["problems"].append(str(exc))
        return report


def build_start_event(
    *,
    client: str,
    native_session_id: str | None,
    repository: str | None = None,
    branch: str | None = None,
    source_kind: str,
    source_ref: str,
    facts: Mapping[str, Any] | None = None,
    event_id: str | None = None,
    run_id: str | None = None,
    event_time: str | None = None,
) -> dict[str, Any]:
    return validate_envelope(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": event_id or new_event_id(),
            "event_type": "run_started",
            "run_id": run_id or new_run_id(),
            "event_time": event_time or now_iso(),
            "recorded_at": now_iso_ms(),
            "client": client,
            "native_session_id": native_session_id,
            "repository": repository,
            "branch": branch,
            "status": "active",
            "source": {"kind": source_kind, "ref": source_ref},
            "facts": facts or {},
        }
    )


def build_stop_event(
    *,
    run_id: str,
    client: str,
    status: str,
    native_session_id: str | None = None,
    repository: str | None = None,
    branch: str | None = None,
    source_kind: str,
    source_ref: str,
    facts: Mapping[str, Any] | None = None,
    event_id: str | None = None,
    event_time: str | None = None,
) -> dict[str, Any]:
    return validate_envelope(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": event_id or new_event_id(),
            "event_type": "run_stopped",
            "run_id": run_id,
            "event_time": event_time or now_iso(),
            "recorded_at": now_iso_ms(),
            "client": client,
            "native_session_id": native_session_id,
            "repository": repository,
            "branch": branch,
            "status": status,
            "source": {"kind": source_kind, "ref": source_ref},
            "facts": facts or {},
        }
    )


def build_enrich_event(
    *,
    run_id: str,
    client: str,
    source_kind: str,
    source_ref: str,
    facts: Mapping[str, Any],
    native_session_id: str | None = None,
    repository: str | None = None,
    branch: str | None = None,
    event_id: str | None = None,
    event_time: str | None = None,
) -> dict[str, Any]:
    return validate_envelope(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": event_id or new_event_id(),
            "event_type": "run_enriched",
            "run_id": run_id,
            "event_time": event_time or now_iso(),
            "recorded_at": now_iso_ms(),
            "client": client,
            "native_session_id": native_session_id,
            "repository": repository,
            "branch": branch,
            "status": "active",
            "source": {"kind": source_kind, "ref": source_ref},
            "facts": facts,
        }
    )


def build_diagnostic_event(
    *,
    client: str,
    source_kind: str,
    reason: str,
    native_session_id: str | None = None,
    repository: str | None = None,
    event_id: str | None = None,
    event_time: str | None = None,
) -> dict[str, Any]:
    """Build an unmatched-capture diagnostic.

    ``reason`` is a short machine code (e.g. ``unmatched_stop``); it is encoded
    into ``source.ref`` so facts stay free of freeform text.
    """
    if not isinstance(reason, str) or not reason or len(reason) > 120:
        raise AgentRunLedgerError("diagnostic reason must be a short string")
    if any(ch in reason for ch in "\n\r\t"):
        raise AgentRunLedgerError("diagnostic reason must be single-line")
    ref = f"{reason}"
    return validate_envelope(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": event_id or new_event_id(),
            "event_type": "capture_diagnostic",
            "run_id": None,
            "event_time": event_time,
            "recorded_at": now_iso_ms(),
            "client": client,
            "native_session_id": native_session_id,
            "repository": repository,
            "branch": None,
            "status": "diagnostic",
            "source": {"kind": source_kind, "ref": ref},
            "facts": {},
        }
    )
