"""Read-only Phase 0 inventory and readiness report (non-mutating)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from chroma_readonly import collection_count, collection_ids, collection_metadata_rows
from shadow_ledger import resolve_path, resolve_shadow_settings, shadow_ledger_section
from shadow_sink import assess_shadow_status, ledger_has_corruption

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
    except Exception:
        return "unknown"


def build_inventory_stamp(
    *,
    code_commit: str,
    chroma_root: str | Path,
    active_count: int,
    total_count: int,
    chroma_only_ids: list[str],
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
        "active_unit_count": int(active_count),
        "total_unit_count": int(total_count),
        "chroma_only_count": len(chroma_only_ids),
        "chroma_only_ids": list(chroma_only_ids),
        "input_paths": dict(input_paths or {}),
        "file_hashes": dict(file_hashes or {}),
        "comparison_rule_version": COMPARISON_RULE_VERSION,
    }


def classify_legacy_decision_candidate(
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
    if not ledger_path.is_file():
        return set()
    ids: set[str] = set()
    for line in ledger_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("stable_entity_id"):
            ids.add(str(obj["stable_entity_id"]))
    return ids


def _load_health(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


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


def collect_phase0_inventory(
    cfg: Mapping[str, Any],
    *,
    code_commit: str | None = None,
    utc: str | None = None,
    include_candidate_sample: int = 200,
) -> dict[str, Any]:
    """Read-only inventory + readiness. Never mutates Chroma, ledger, or config."""
    index = cfg.get("index") if isinstance(cfg.get("index"), dict) else {}
    chroma_dir = resolve_path(index.get("chroma_dir") or ".")
    settings = resolve_shadow_settings(cfg)
    section = shadow_ledger_section(cfg)
    enabled = bool(section.get("enabled"))

    active = collection_count(chroma_dir, COLLECTION_KNOWLEDGE_UNITS)
    # Readonly path does not filter superseded cheaply; treat active≈total for stamp.
    total = active
    chroma_ids = sorted(collection_ids(chroma_dir, COLLECTION_KNOWLEDGE_UNITS))
    shadow_ids = _shadow_entity_ids(settings.ledger_path)
    chroma_only = sorted(set(chroma_ids) - shadow_ids) if shadow_ids else []

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
        code_commit=code_commit or current_code_commit(),
        chroma_root=chroma_dir,
        active_count=active,
        total_count=total,
        chroma_only_ids=chroma_only,
        input_paths=input_paths,
        file_hashes=file_hashes,
        utc=utc,
    )

    # Candidate classes — metadata only, capped, sorted, no document payloads.
    candidates: list[dict[str, str]] = []
    try:
        rows = collection_metadata_rows(chroma_dir, COLLECTION_KNOWLEDGE_UNITS)
    except FileNotFoundError:
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

    health = _load_health(settings.health_path)
    corrupt = ledger_has_corruption(settings.ledger_path) if enabled else False
    health_status = assess_shadow_status(
        enabled=enabled,
        health=health,
        ledger_corrupt=corrupt,
    )

    reasons: list[str] = []
    unexplained_missing = False
    unsafe_replay = False
    covered = False
    unknown_only = False

    if not enabled:
        reasons.append("shadow_ledger disabled — observation not activated")
    elif corrupt or health_status == "corrupt":
        reasons.append("shadow ledger corrupt")
        corrupt = True
    elif health_status == "baseline_mismatch":
        reasons.append("activation baseline mismatch")
        unsafe_replay = True
    elif health_status == "degraded":
        reasons.append("shadow health degraded")
    elif not shadow_ids:
        reasons.append("no shadow events yet — insufficient delta evidence")
    else:
        # With events present and no corruption: still PARTIAL unless explicit
        # reconcile evidence is supplied (touched-ID compare is a separate call).
        reasons.append(
            "shadow events present; touched-ID reconcile not asserted in inventory pass"
        )
        unknown_only = True

    status = readiness_verdict(
        corruption=corrupt,
        unexplained_missing=unexplained_missing,
        unsafe_replay=unsafe_replay,
        covered_touched_reconcile=covered,
        unknown_provenance_only=unknown_only or (not enabled),
    )
    # Disabled / no events → PARTIAL (already from verdict)
    if enabled and corrupt:
        status = "FAIL"

    report = {
        "inventory": stamp,
        "candidates": candidates,
        "candidate_class_counts": _count_classes(candidates),
        "shadow": {
            "enabled": enabled,
            "health_status": health_status,
            "corrupt": corrupt,
            "shadow_entity_count": len(shadow_ids),
        },
        "readiness": {
            "status": status,
            "reasons": reasons,
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
        "readiness": report.get("readiness"),
        "claims": report.get("claims"),
        "human_summary": report.get("human_summary"),
    }
