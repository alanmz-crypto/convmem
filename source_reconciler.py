"""Bounded CG-2 source reconciliation independent of filesystem notifications.

Compares secure source observations against legacy processed records and
generational manifest ``source_hash`` values.  Mismatches enqueue the latest
desired owner state through a bounded, per-owner coalescing queue.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atomic_files import atomic_write_json
from file_generation_contract import canonical_source_path, ownership_key
from file_generation_pointer import (
    GenerationQualificationError,
    read_unqualified_pointer,
)
from ingest import load_processed
from serving_authority import generation_root_for_cfg
from source_observation import SourceObservationError, observe_source_hash


class ReconciliationAdmissionError(RuntimeError):
    """The reconciliation queue refused additional owner work."""


@dataclass(frozen=True)
class ReconciliationBudget:
    max_pending_owners: int = 256
    max_reconciliation_staleness: float = 300.0


@dataclass(frozen=True)
class SourceDriftFinding:
    canonical_path: str
    owner_key: str
    reason: str
    recorded_hash: str | None
    observed_hash: str | None


@dataclass
class PendingOwnerWork:
    owner_key: str
    canonical_path: str
    reason: str
    queued_at: str
    observed_hash: str | None = None


@dataclass
class ReconciliationReport:
    reason: str
    findings: list[SourceDriftFinding] = field(default_factory=list)
    queued_owner_keys: list[str] = field(default_factory=list)
    dirty_scopes: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def reconciliation_state_path(cfg: Mapping[str, Any]) -> Path:
    processed = Path(str(cfg["index"]["processed_log"])).expanduser()
    return processed.parent / "source_reconciliation.json"


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "dirty_scopes": [],
            "pending_by_owner": {},
            "last_successful_sweep_at": None,
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"source reconciliation state corrupt at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"source reconciliation state is not an object: {path}")
    data.setdefault("dirty_scopes", [])
    data.setdefault("pending_by_owner", {})
    return data


def _save_state(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, dict(data))


def _processed_path_key(path: str) -> str:
    return str(Path(path).expanduser().resolve())


def _indexed_processed_paths(processed: Mapping[str, Any]) -> dict[str, str]:
    """Map canonical processed path -> recorded content hash key."""

    by_path: dict[str, str] = {}
    for hash_key, entry in processed.items():
        if not isinstance(entry, dict) or entry.get("excluded"):
            continue
        raw_path = entry.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        by_path[_processed_path_key(raw_path)] = str(hash_key)
    return by_path


def eligible_watch_source_paths(cfg: Mapping[str, Any]) -> list[str]:
    watch_cfg = cfg.get("watch") or {}
    base = watch_cfg.get("paths") or (cfg.get("sources") or {}).get("paths") or []
    extra = watch_cfg.get("extra_paths") or []
    paths = [str(p) for p in list(base) + list(extra)]
    canonical: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        try:
            resolved = canonical_source_path(raw)
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        canonical.append(resolved)
    return canonical


def discover_legacy_source_drift(
    cfg: Mapping[str, Any],
    *,
    processed: Mapping[str, Any] | None = None,
) -> list[SourceDriftFinding]:
    processed = processed or load_processed(str(cfg["index"]["processed_log"]))
    indexed = _indexed_processed_paths(processed)
    findings: list[SourceDriftFinding] = []
    for canonical in eligible_watch_source_paths(cfg):
        owner_key = ownership_key(canonical)
        recorded = indexed.get(_processed_path_key(canonical))
        try:
            observed = observe_source_hash(canonical)
        except SourceObservationError:
            if recorded is not None:
                findings.append(
                    SourceDriftFinding(
                        canonical_path=canonical,
                        owner_key=owner_key,
                        reason="source_missing",
                        recorded_hash=recorded,
                        observed_hash=None,
                    )
                )
            continue
        if recorded is None:
            findings.append(
                SourceDriftFinding(
                    canonical_path=canonical,
                    owner_key=owner_key,
                    reason="new_eligible_source",
                    recorded_hash=None,
                    observed_hash=observed,
                )
            )
        elif recorded != observed:
            findings.append(
                SourceDriftFinding(
                    canonical_path=canonical,
                    owner_key=owner_key,
                    reason="source_hash_mismatch",
                    recorded_hash=recorded,
                    observed_hash=observed,
                )
            )
    return findings


def discover_generational_source_drift(cfg: Mapping[str, Any]) -> list[SourceDriftFinding]:
    generation_root = generation_root_for_cfg(cfg)
    active_dir = generation_root / "active"
    if not active_dir.is_dir():
        return []
    findings: list[SourceDriftFinding] = []
    for pointer_file in sorted(active_dir.glob("*.json")):
        if pointer_file.name.endswith(".fence.json") or pointer_file.name.endswith(
            ".retired.json"
        ):
            continue
        owner_digest = pointer_file.stem
        try:
            pointer = read_unqualified_pointer(generation_root, owner_digest)
        except GenerationQualificationError:
            continue
        if pointer is None:
            continue
        canonical = canonical_source_path(
            str(pointer.get("owner_key", "")).removeprefix("source:")
        )
        owner_key = str(pointer["owner_key"])
        recorded = str(pointer.get("source_hash") or "")
        try:
            observed = observe_source_hash(canonical)
        except SourceObservationError:
            findings.append(
                SourceDriftFinding(
                    canonical_path=canonical,
                    owner_key=owner_key,
                    reason="generational_source_missing",
                    recorded_hash=recorded or None,
                    observed_hash=None,
                )
            )
            continue
        if recorded and recorded != observed:
            findings.append(
                SourceDriftFinding(
                    canonical_path=canonical,
                    owner_key=owner_key,
                    reason="generational_source_hash_mismatch",
                    recorded_hash=recorded,
                    observed_hash=observed,
                )
            )
    return findings


def mark_reconciliation_dirty(
    cfg: Mapping[str, Any],
    scope: str,
    *,
    reason: str,
) -> None:
    state_path = reconciliation_state_path(cfg)
    data = _load_state(state_path)
    dirty = list(data.get("dirty_scopes") or [])
    marker = f"{scope}:{reason}"
    if marker not in dirty:
        dirty.append(marker)
    data["dirty_scopes"] = dirty
    _save_state(state_path, data)


def enqueue_owner_work(
    cfg: Mapping[str, Any],
    finding: SourceDriftFinding,
    *,
    budget: ReconciliationBudget | None = None,
) -> PendingOwnerWork:
    budget = budget or ReconciliationBudget()
    state_path = reconciliation_state_path(cfg)
    data = _load_state(state_path)
    pending = dict(data.get("pending_by_owner") or {})
    owner_digest_key = finding.owner_key
    if (
        owner_digest_key not in pending
        and len(pending) >= budget.max_pending_owners
    ):
        raise ReconciliationAdmissionError(
            "reconciliation owner queue is at capacity"
        )
    work = PendingOwnerWork(
        owner_key=finding.owner_key,
        canonical_path=finding.canonical_path,
        reason=finding.reason,
        queued_at=_utc_now(),
        observed_hash=finding.observed_hash,
    )
    pending[owner_digest_key] = {
        "owner_key": work.owner_key,
        "canonical_path": work.canonical_path,
        "reason": work.reason,
        "queued_at": work.queued_at,
        "observed_hash": work.observed_hash,
    }
    data["pending_by_owner"] = pending
    _save_state(state_path, data)
    return work


def pending_owner_work(cfg: Mapping[str, Any]) -> list[PendingOwnerWork]:
    data = _load_state(reconciliation_state_path(cfg))
    pending = data.get("pending_by_owner") or {}
    rows: list[PendingOwnerWork] = []
    for payload in pending.values():
        if not isinstance(payload, dict):
            continue
        rows.append(
            PendingOwnerWork(
                owner_key=str(payload.get("owner_key", "")),
                canonical_path=str(payload.get("canonical_path", "")),
                reason=str(payload.get("reason", "")),
                queued_at=str(payload.get("queued_at", "")),
                observed_hash=payload.get("observed_hash"),
            )
        )
    return rows


def reconciliation_staleness_seconds(cfg: Mapping[str, Any]) -> float | None:
    data = _load_state(reconciliation_state_path(cfg))
    raw = data.get("last_successful_sweep_at")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        then = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - then).total_seconds()


def run_reconciliation_sweep(
    cfg: Mapping[str, Any],
    *,
    reason: str,
    budget: ReconciliationBudget | None = None,
) -> ReconciliationReport:
    budget = budget or ReconciliationBudget()
    started = time.monotonic()
    state_path = reconciliation_state_path(cfg)
    data = _load_state(state_path)
    findings = discover_legacy_source_drift(cfg) + discover_generational_source_drift(
        cfg
    )
    queued: list[str] = []
    for finding in findings:
        try:
            enqueue_owner_work(cfg, finding, budget=budget)
            queued.append(finding.owner_key)
        except ReconciliationAdmissionError:
            break
    data = _load_state(state_path)
    data["last_successful_sweep_at"] = _utc_now()
    data["dirty_scopes"] = []
    _save_state(state_path, data)
    return ReconciliationReport(
        reason=reason,
        findings=findings,
        queued_owner_keys=queued,
        dirty_scopes=list(data.get("dirty_scopes") or []),
        elapsed_seconds=time.monotonic() - started,
    )


def run_startup_reconciliation(
    cfg: Mapping[str, Any],
    *,
    budget: ReconciliationBudget | None = None,
) -> ReconciliationReport:
    return run_reconciliation_sweep(cfg, reason="startup", budget=budget)


def assert_reconciliation_fresh(
    cfg: Mapping[str, Any],
    *,
    budget: ReconciliationBudget | None = None,
) -> None:
    budget = budget or ReconciliationBudget()
    stale = reconciliation_staleness_seconds(cfg)
    if stale is None or stale > budget.max_reconciliation_staleness:
        raise RuntimeError(
            "source reconciliation is stale relative to max_reconciliation_staleness"
        )
