# pylint: disable=duplicate-code
"""Read-only Phase 0 inventory and readiness report (non-mutating)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from chroma_readonly import collection_inventory_snapshot, collection_metadata_rows
from shadow_ledger import resolve_path, resolve_shadow_settings
from shadow_sink import assess_shadow_status
from shadow_validation import ShadowValidationResult, ValidationMode, validate_shadow_activation

COMPARISON_RULE_VERSION = 1
COLLECTION_KNOWLEDGE_UNITS = "knowledge_units"

# Claims Phase 0 inventory must never make (VERIFY V6h).
NOT_CLAIMED = (
    "historic rebuild",
    "backup status",
    "migration readiness",
    "cutover authorization",
    "production activation approval",
)


def file_sha256(path: Path) -> str | None:
    path = Path(path)
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def current_code_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (OSError, subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def build_inventory_stamp(  # pylint: disable=too-many-arguments
    *,
    code_commit: str,
    chroma_root: str | Path,
    active_count: int | None,
    total_count: int | None,
    historical_count: int | None = None,
    chroma_only_ids: list[str] | None = None,
    input_paths: Mapping[str, str] | None = None,
    file_hashes: Mapping[str, str | None] | None = None,
    utc: str | None = None,
) -> dict[str, Any]:
    """Runtime-stamped inventory — never hardcodes audit snapshot constants."""
    return {
        "utc": utc
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_commit": code_commit,
        "chroma_root": str(Path(chroma_root).expanduser().resolve()),
        "collection": COLLECTION_KNOWLEDGE_UNITS,
        "active_unit_count": None if active_count is None else int(active_count),
        "historical_unit_count": (
            None if historical_count is None else int(historical_count)
        ),
        "total_unit_count": None if total_count is None else int(total_count),
        "chroma_only_count": (
            None if chroma_only_ids is None else len(chroma_only_ids)
        ),
        "chroma_only_ids": None if chroma_only_ids is None else list(chroma_only_ids),
        "input_paths": dict(input_paths or {}),
        "file_hashes": dict(file_hashes or {}),
        "comparison_rule_version": COMPARISON_RULE_VERSION,
    }


def classify_legacy_decision_candidate(  # pylint: disable=unused-argument
    *,
    title: str,
    summary: str,
    approved_match: bool,
    normalized_match: bool,
    looks_like_observation: bool,
) -> str:
    if approved_match:
        return "matched governed decision"
    if normalized_match:
        return "matched governed decision"
    if looks_like_observation:
        return "likely observation"
    return "ambiguous"


def classify_unit_metadata(meta: Mapping[str, Any]) -> str:
    """Deterministic local classification from metadata only (no LLM/API)."""
    lid = str(meta.get("ledger_id") or meta.get("id") or "").strip()
    title = str(meta.get("title") or "")
    summary = str(meta.get("summary") or meta.get("content_preview") or "")
    kind = str(meta.get("ledger_kind") or meta.get("kind") or "").strip().lower()
    looks_obs = lid.startswith("obs_") or kind == "observation"
    approved = lid.startswith("dec_") and bool(str(meta.get("proposal_id") or "").strip())
    normalized = (
        lid.startswith("dec_")
        and bool(title.strip())
        and bool(summary.strip())
        and not approved
    )
    return classify_legacy_decision_candidate(
        title=title,
        summary=summary,
        approved_match=approved,
        normalized_match=normalized,
        looks_like_observation=looks_obs,
    )


def readiness_verdict(
    *,
    corruption: bool,
    unexplained_missing: bool,
    unsafe_replay: bool,
    covered_touched_reconcile: bool,
    unknown_provenance_only: bool,
) -> str:
    if corruption or unexplained_missing or unsafe_replay:
        return "FAIL"
    if covered_touched_reconcile and not unknown_provenance_only:
        return "PASS — delta capture"
    return "PARTIAL"


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(report), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _shadow_entity_ids(ledger_path: Path) -> set[str]:
    """Read touched IDs only after strict validation has accepted the ledger."""
    ids: set[str] = set()
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict) and obj.get("stable_entity_id"):
            ids.add(str(obj["stable_entity_id"]))
    return ids


def _load_health_truth(path: Path, *, enabled: bool) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    """Read ancillary health honestly without replacing strict artifact truth."""
    if not enabled:
        return None, ()
    if not path.is_file():
        return None, ("health_missing",)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, ("health_corrupt",)
    if not isinstance(value, dict):
        return None, ("health_corrupt",)
    return value, ()


def collect_shadow_truth(
    cfg: Mapping[str, Any],
    *,
    chroma_dir: str | Path,
    mode: ValidationMode,
    code_revision: str | None = None,
) -> dict[str, Any]:
    """One shared strict-validation projection for doctor and inventory."""
    settings = resolve_shadow_settings(cfg)
    validation = validate_shadow_activation(
        None,
        chroma_dir,
        mode,
        cfg=cfg,
        runtime_code_revision=code_revision or current_code_commit(),
    )
    enabled = bool(validation.facts.get("enabled"))
    health, health_codes = _load_health_truth(settings.health_path, enabled=enabled)
    health_status = (
        "disabled"
        if not enabled
        else "unknown"
        if health is None
        else assess_shadow_status(enabled=True, health=health)
    )
    return {
        "validation": validation,
        "codes": tuple(validation.codes()) + health_codes,
        "health": health,
        "health_codes": health_codes,
        "health_status": health_status,
        "settings": settings,
    }


def human_summary(status: str, *, reasons: list[str]) -> str:
    """Concise human line that agrees with machine readiness status."""
    reason = "; ".join(reasons) if reasons else "no additional reasons"
    if status == "PASS — delta capture":
        return (
            f"PASS — delta capture: covered touched IDs reconcile ({reason}). "
            "Does not authorize activation, cutover, backup changes, or historic rebuild."
        )
    if status == "FAIL":
        return f"FAIL: {reason}"
    return f"PARTIAL: {reason}"


def collect_phase0_inventory(  # pylint: disable=too-many-locals
    cfg: Mapping[str, Any],
    *,
    code_commit: str | None = None,
    utc: str | None = None,
    include_candidate_sample: int = 200,
) -> dict[str, Any]:
    """Read-only inventory + readiness. Never mutates Chroma, ledger, or config."""
    index = cfg.get("index") if isinstance(cfg.get("index"), dict) else {}
    chroma_dir = resolve_path(index.get("chroma_dir") or ".")
    runtime_revision = current_code_commit()
    truth = collect_shadow_truth(
        cfg,
        chroma_dir=chroma_dir,
        mode=ValidationMode.INVENTORY,
        code_revision=runtime_revision,
    )
    validation: ShadowValidationResult = truth["validation"]
    settings = truth["settings"]
    enabled = bool(validation.facts.get("enabled"))
    codes = list(truth["codes"])

    try:
        current = collection_inventory_snapshot(chroma_dir, COLLECTION_KNOWLEDGE_UNITS)
    except (FileNotFoundError, OSError, sqlite3.Error):
        current = None
        if "collection_unavailable" not in codes:
            codes.append("collection_unavailable")

    chroma_ids = list(current["ids"]) if current is not None else None
    active = current["active_unit_count"] if current is not None else None
    historical = current["historical_unit_count"] if current is not None else None
    total = current["total_unit_count"] if current is not None else None

    shadow_ids: set[str] | None
    if validation.state == "disabled" and not validation.refusals:
        shadow_ids = set()
    elif validation.inject_eligible:
        try:
            shadow_ids = _shadow_entity_ids(settings.ledger_path)
        except (OSError, UnicodeError, json.JSONDecodeError):
            shadow_ids = None
            if "ledger_corrupt" not in codes:
                codes.append("ledger_corrupt")
    else:
        shadow_ids = None
    chroma_only = (
        sorted(set(chroma_ids) - shadow_ids)
        if chroma_ids is not None and shadow_ids is not None
        else None
    )

    input_paths = {
        "chroma_dir": str(chroma_dir),
        "ledger_path": str(settings.ledger_path),
        "activation_manifest_path": str(settings.activation_manifest_path),
        "health_path": str(settings.health_path),
    }
    file_hashes = {
        "ledger": file_sha256(settings.ledger_path),
        "activation_manifest": file_sha256(settings.activation_manifest_path),
        "health": file_sha256(settings.health_path),
    }

    stamp = build_inventory_stamp(
        code_commit=code_commit or runtime_revision,
        chroma_root=chroma_dir,
        active_count=active,
        total_count=total,
        historical_count=historical,
        chroma_only_ids=chroma_only,
        input_paths=input_paths,
        file_hashes=file_hashes,
        utc=utc,
    )

    # Candidate classes — metadata only, capped, sorted, no document payloads.
    candidates: list[dict[str, str]] = []
    try:
        rows = collection_metadata_rows(chroma_dir, COLLECTION_KNOWLEDGE_UNITS)
    except (FileNotFoundError, OSError, sqlite3.Error):
        rows = []
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        eid = str(row.get("id") or "")
        if not eid:
            continue
        # Drop document/payload fields before classification storage.
        meta = {
            k: v
            for k, v in row.items()
            if k not in {"document", "embedding", "embeddings"}
        }
        by_id[eid] = meta
    for eid in sorted(by_id)[: max(0, include_candidate_sample)]:
        klass = classify_unit_metadata(by_id[eid])
        candidates.append({"id": eid, "class": klass})

    reasons: list[str] = []
    blocking_codes = [r.code for r in validation.refusals if r.blocking]
    health_status = truth["health_status"]
    corrupt = "ledger_corrupt" in codes
    if validation.state == "disabled" and not validation.refusals:
        status = "PARTIAL"
        reasons.append("shadow_ledger disabled — observation not activated")
    elif validation.state == "prepared":
        status = "PARTIAL"
        reasons.append("prepared_not_committed")
    elif blocking_codes or "ledger_corrupt" in codes:
        status = "FAIL"
        reasons.extend(codes or ["shadow validation failed"])
    elif truth["health_codes"]:
        status = "PARTIAL"
        reasons.extend(truth["health_codes"])
    elif health_status == "degraded":
        status = "PARTIAL"
        reasons.append("shadow health degraded")
    elif shadow_ids is None:
        status = "PARTIAL"
        reasons.append("shadow touched entities unknown")
    elif not shadow_ids:
        status = "PARTIAL"
        reasons.append("no shadow events yet — insufficient delta evidence")
    else:
        status = "PARTIAL"
        reasons.append(
            "shadow events present; touched-ID reconcile not asserted in inventory pass"
        )

    report = {
        "inventory": stamp,
        "candidates": candidates,
        "candidate_class_counts": _count_classes(candidates),
        "shadow": {
            "enabled": enabled,
            "state": validation.state,
            "activation_id": validation.activation_id,
            "validation_codes": codes,
            "health_status": health_status,
            "health_codes": list(truth["health_codes"]),
            "corrupt": corrupt,
            "shadow_touched_entity_count": (
                None if shadow_ids is None else len(shadow_ids)
            ),
        },
        "validation": validation.as_dict(),
        "readiness": {
            "status": status,
            "reasons": reasons,
            "codes": codes,
        },
        "claims": {
            "label": "delta capture" if status.startswith("PASS") else status,
            "delta_capture_only": True,
            "not_claimed": list(NOT_CLAIMED),
        },
        "human_summary": human_summary(status, reasons=reasons),
    }
    return report


def _count_classes(candidates: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in candidates:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    return dict(sorted(counts.items()))


def redacted_stdout_view(report: Mapping[str, Any]) -> dict[str, Any]:
    """Default CLI/JSON view: counts, ids, categories — never documents/embeddings."""
    inv = dict(report.get("inventory") or {})
    # Drop nothing sensitive from stamp; stamp has no payloads by construction.
    return {
        "utc": inv.get("utc"),
        "code_commit": inv.get("code_commit"),
        "chroma_root": inv.get("chroma_root"),
        "active_unit_count": inv.get("active_unit_count"),
        "total_unit_count": inv.get("total_unit_count"),
        "chroma_only_count": inv.get("chroma_only_count"),
        "chroma_only_ids": inv.get("chroma_only_ids"),
        "comparison_rule_version": inv.get("comparison_rule_version"),
        "file_hashes": inv.get("file_hashes"),
        "input_paths": inv.get("input_paths"),
        "candidate_class_counts": report.get("candidate_class_counts"),
        "candidates": report.get("candidates"),
        "shadow": report.get("shadow"),
        "validation": report.get("validation"),
        "readiness": report.get("readiness"),
        "claims": report.get("claims"),
        "human_summary": report.get("human_summary"),
    }
