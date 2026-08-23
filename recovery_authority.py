"""Recovery Authority T2 — authority recovery and projection agreement.

Consumes the T1 durable registry validator. Distinguishes recovered authority
from projection validity and from serving readiness. Never publishes serving
pointers or mutates live authority.

Architecture: docs/plans/ARCHITECTURE-recovery-authority.md §7
Execution: docs/plans/EXECUTION-recovery-authority.md T2
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from complete_data_restore import (
    EVIDENCE_FILENAME,
    OUTCOME_BLOCKED,
    _canonical_json_hash,
    chroma_logical_snapshot,
)
from provenance_registry_restore import (
    OUTCOME_QUARANTINED,
    ProvenanceTuple,
    RegistryValidationResult,
    build_registry_fixture,
    validate_provenance_registry,
)

RECOVERY_STATE_SCHEMA = "convmem/recovery-authority-state-v1"
PROJECTION_BINDING_PROFILE = "convmem/recovery-projection-binding-v1"


class RecoveryState(str, Enum):
    """Architecture recovery states owned by T2 (non-serving)."""

    AUTHORITY_RECOVERED_PROJECTION_PENDING = "AUTHORITY_RECOVERED_PROJECTION_PENDING"
    PROJECTION_VALIDATED = "PROJECTION_VALIDATED"
    BLOCKED = "BLOCKED"
    QUARANTINED = "QUARANTINED"
    PROVENANCE_STORE_UNAVAILABLE = "PROVENANCE_STORE_UNAVAILABLE"

    @property
    def is_serving_ready(self) -> bool:
        """T2 never yields serving readiness."""
        return False

    @property
    def authority_recovered(self) -> bool:
        return self in {
            RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING,
            RecoveryState.PROJECTION_VALIDATED,
        }


@dataclass(frozen=True)
class ProjectionFingerprint:
    """Exact projection agreement surface for one source (JSONL or Chroma)."""

    present: bool
    assertion_ids: tuple[str, ...] = ()
    provenance_commitments: tuple[tuple[str, str], ...] = ()
    generation_id: str = ""
    manifest_commitment: str = ""
    projection_binding: str = ""
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "present": self.present,
            "assertion_ids": list(self.assertion_ids),
            "provenance_commitments": [
                {"assertion_id": aid, "commitment": cmt}
                for aid, cmt in self.provenance_commitments
            ],
            "generation_id": self.generation_id,
            "manifest_commitment": self.manifest_commitment,
            "projection_binding": self.projection_binding,
            "detail": self.detail,
        }


@dataclass
class RecoveryAuthorityResult:
    """Outcome of one T2 recovery evaluation (scratch/fixture only)."""

    state: RecoveryState
    detail: str = ""
    code: str = ""
    serving_ready: bool = False
    provenance_tuple: ProvenanceTuple | None = None
    reports: dict[str, Any] = field(default_factory=dict)
    transitions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def registry_validation(self) -> dict[str, Any]:
        return dict(self.reports.get("registry_validation") or {})

    @property
    def registry_report(self) -> dict[str, Any]:
        return dict(self.reports.get("registry_report") or {})

    @property
    def projection_agreement(self) -> dict[str, Any]:
        return dict(self.reports.get("projection_agreement") or {})

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RECOVERY_STATE_SCHEMA,
            "state": self.state.value,
            "detail": self.detail,
            "code": self.code,
            "serving_ready": self.serving_ready,
            "authority_recovered": self.state.authority_recovered,
            "provenance_tuple": (
                self.provenance_tuple.as_dict() if self.provenance_tuple else None
            ),
            "registry_validation": self.registry_validation,
            "registry_report": self.registry_report,
            "projection_agreement": self.projection_agreement,
            "transitions": list(self.transitions),
        }


def compute_projection_binding(
    *,
    generation_id: str,
    manifest_commitment: str,
    assertion_ids: list[str] | tuple[str, ...],
) -> str:
    """Canonical projection/profile binding for a selected registry generation."""
    return _canonical_json_hash(
        {
            "profile": PROJECTION_BINDING_PROFILE,
            "generation_id": generation_id,
            "manifest_commitment": manifest_commitment,
            "assertion_ids": sorted(assertion_ids),
        }
    )


def _registry_authority_map(
    registry: RegistryValidationResult,
    *,
    content_tree_present: bool,
) -> RecoveryAuthorityResult | None:
    """Map T1 registry outcomes to T2 fail-closed states, or None if valid."""
    if registry.ok and registry.provenance_tuple is not None:
        return None

    code = registry.code or ""
    outcome = registry.outcome
    transitions = [
        {
            "from": "CANDIDATE",
            "to": "REGISTRY_VALIDATION",
            "result": outcome,
            "code": code,
        }
    ]

    if code in {
        "BLOCKED_PROVENANCE_SELECTOR_MISSING",
        "BLOCKED_PROVENANCE_GENERATION_MISSING",
        "BLOCKED_PROVENANCE_MANIFEST_MISSING",
    } or (
        outcome == OUTCOME_BLOCKED
        and content_tree_present
        and "missing" in (registry.detail or "").lower()
    ):
        # Content may still be useful as untrusted evidence only.
        if content_tree_present and code in {
            "BLOCKED_PROVENANCE_SELECTOR_MISSING",
            "BLOCKED_PROVENANCE_GENERATION_MISSING",
            "BLOCKED_PROVENANCE_MANIFEST_MISSING",
        }:
            state = RecoveryState.PROVENANCE_STORE_UNAVAILABLE
            transitions.append(
                {
                    "from": "REGISTRY_VALIDATION",
                    "to": state.value,
                    "result": "fail_closed",
                }
            )
            return RecoveryAuthorityResult(
                state=state,
                detail=registry.detail or "provenance store unavailable",
                code=code or "PROVENANCE_STORE_UNAVAILABLE",
                serving_ready=False,
                reports={
                    "registry_validation": {
                        "outcome": registry.outcome,
                        "detail": registry.detail,
                        "code": registry.code,
                    },
                    "registry_report": {"checks": registry.checks},
                },
                transitions=transitions,
            )

    if outcome == OUTCOME_QUARANTINED or code.startswith("QUARANTINED_"):
        state = RecoveryState.QUARANTINED
    else:
        state = RecoveryState.BLOCKED

    transitions.append(
        {
            "from": "REGISTRY_VALIDATION",
            "to": state.value,
            "result": "fail_closed",
        }
    )
    return RecoveryAuthorityResult(
        state=state,
        detail=registry.detail or "registry validation failed",
        code=code or state.value,
        serving_ready=False,
        reports={
            "registry_validation": {
                "outcome": registry.outcome,
                "detail": registry.detail,
                "code": registry.code,
            },
            "registry_report": {"checks": registry.checks},
        },
        transitions=transitions,
    )


def _load_registry_assertion_commitments(
    root: Path, generation_id: str, assertion_ids: list[str]
) -> dict[str, str]:
    gen_dir = root / "provenance" / "generations" / generation_id
    commitments: dict[str, str] = {}
    for aid in assertion_ids:
        path = gen_dir / "assertions" / f"{aid}.json"
        if not path.is_file():
            continue
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(body, dict):
            cmt = str(body.get("provenance_commitment") or "").strip()
            if cmt:
                commitments[aid] = cmt
    return commitments


def _read_jsonl_projection(root: Path) -> ProjectionFingerprint:
    path = root / "knowledge_units.jsonl"
    if not path.is_file():
        return ProjectionFingerprint(present=False, detail="knowledge_units.jsonl missing")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return ProjectionFingerprint(
            present=True, detail=f"knowledge_units.jsonl unreadable: {exc}"
        )

    assertion_ids: list[str] = []
    commitments: list[tuple[str, str]] = []
    generation_ids: set[str] = set()
    for raw in lines:
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            return ProjectionFingerprint(
                present=True, detail="knowledge_units.jsonl malformed"
            )
        if not isinstance(row, dict):
            return ProjectionFingerprint(
                present=True, detail="knowledge_units.jsonl non-object row"
            )
        aid = str(
            row.get("assertion_id") or row.get("id") or row.get("unit_id") or ""
        ).strip()
        if not aid:
            continue
        assertion_ids.append(aid)
        cmt = str(row.get("provenance_commitment") or "").strip()
        if cmt:
            commitments.append((aid, cmt))
        gid = str(row.get("generation_id") or "").strip()
        if gid:
            generation_ids.add(gid)

    if len(generation_ids) > 1:
        return ProjectionFingerprint(
            present=True,
            assertion_ids=tuple(sorted(set(assertion_ids))),
            provenance_commitments=tuple(sorted(commitments)),
            detail="mixed generation in JSONL projection",
        )

    generation_id = next(iter(generation_ids), "")
    manifest_commitment = ""
    projection_binding = ""
    body_ids = tuple(sorted(set(assertion_ids)))
    body_commitments = tuple(sorted(commitments))
    bind_path = root / "knowledge_units.projection.json"
    if bind_path.is_file():
        try:
            body = json.loads(bind_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return ProjectionFingerprint(
                present=True,
                assertion_ids=body_ids,
                provenance_commitments=body_commitments,
                generation_id=generation_id,
                detail=f"jsonl projection binding unreadable: {exc}",
            )
        if isinstance(body, dict):
            generation_id = str(body.get("generation_id") or generation_id).strip()
            manifest_commitment = str(body.get("manifest_commitment") or "").strip()
            projection_binding = str(body.get("projection_binding") or "").strip()
            listed = body.get("assertion_ids")
            if isinstance(listed, list) and listed:
                listed_ids = tuple(sorted({str(x) for x in listed if str(x).strip()}))
                if listed_ids != body_ids:
                    return ProjectionFingerprint(
                        present=True,
                        assertion_ids=body_ids,
                        provenance_commitments=body_commitments,
                        generation_id=generation_id,
                        manifest_commitment=manifest_commitment,
                        projection_binding=projection_binding,
                        detail="jsonl sidecar assertion-id set disagrees with body",
                    )
            raw_cmt = body.get("provenance_commitments")
            if isinstance(raw_cmt, dict) and raw_cmt:
                side_cmt = tuple(
                    sorted(
                        (str(aid), str(cmt))
                        for aid, cmt in raw_cmt.items()
                        if str(aid).strip() and str(cmt).strip()
                    )
                )
                if body_commitments and side_cmt != body_commitments:
                    return ProjectionFingerprint(
                        present=True,
                        assertion_ids=body_ids,
                        provenance_commitments=body_commitments,
                        generation_id=generation_id,
                        manifest_commitment=manifest_commitment,
                        projection_binding=projection_binding,
                        detail="jsonl sidecar commitments disagree with body",
                    )
                if not body_commitments:
                    body_commitments = side_cmt

    return ProjectionFingerprint(
        present=True,
        assertion_ids=body_ids,
        provenance_commitments=body_commitments,
        generation_id=generation_id,
        manifest_commitment=manifest_commitment,
        projection_binding=projection_binding,
        detail="jsonl projection present",
    )


def _read_chroma_projection(root: Path) -> ProjectionFingerprint:
    chroma_dir = root / "chroma"
    if not chroma_dir.is_dir():
        return ProjectionFingerprint(present=False, detail="chroma directory missing")
    if not (chroma_dir / "chroma.sqlite3").is_file():
        # Empty or placeholder tree — unavailable/rebuildable, not a broken body.
        return ProjectionFingerprint(present=False, detail="chroma.sqlite3 missing")
    try:
        snap = chroma_logical_snapshot(chroma_dir)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return ProjectionFingerprint(
            present=True, detail=f"chroma unreadable: {exc}"
        )

    ku_ids = list(snap.get("required_ids", {}).get("knowledge_units") or [])
    body_ids = tuple(sorted(set(str(x) for x in ku_ids if str(x).strip())))
    binding_path = chroma_dir / "projection_binding.json"
    generation_id = ""
    manifest_commitment = ""
    projection_binding = ""
    commitments: list[tuple[str, str]] = []
    if binding_path.is_file():
        try:
            body = json.loads(binding_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return ProjectionFingerprint(
                present=True,
                assertion_ids=body_ids,
                detail=f"chroma projection_binding unreadable: {exc}",
            )
        if not isinstance(body, dict):
            return ProjectionFingerprint(
                present=True,
                assertion_ids=body_ids,
                detail="chroma projection_binding not an object",
            )
        generation_id = str(body.get("generation_id") or "").strip()
        manifest_commitment = str(body.get("manifest_commitment") or "").strip()
        projection_binding = str(body.get("projection_binding") or "").strip()
        listed = body.get("assertion_ids")
        if isinstance(listed, list) and listed:
            listed_ids = tuple(sorted({str(x) for x in listed if str(x).strip()}))
            if listed_ids != body_ids:
                return ProjectionFingerprint(
                    present=True,
                    assertion_ids=body_ids,
                    generation_id=generation_id,
                    manifest_commitment=manifest_commitment,
                    projection_binding=projection_binding,
                    detail="chroma sidecar assertion-id set disagrees with embedding ids",
                )
        raw_cmt = body.get("provenance_commitments") or {}
        if isinstance(raw_cmt, dict):
            commitments = [
                (str(aid), str(cmt))
                for aid, cmt in sorted(raw_cmt.items())
                if str(aid).strip() and str(cmt).strip()
            ]

    return ProjectionFingerprint(
        present=True,
        assertion_ids=body_ids,
        provenance_commitments=tuple(commitments),
        generation_id=generation_id,
        manifest_commitment=manifest_commitment,
        projection_binding=projection_binding,
        detail="chroma projection present",
    )


def _expected_fingerprint(
    tuple_: ProvenanceTuple,
    assertion_ids: list[str],
    commitments: Mapping[str, str],
) -> ProjectionFingerprint:
    binding = compute_projection_binding(
        generation_id=tuple_.generation_id,
        manifest_commitment=tuple_.manifest_commitment,
        assertion_ids=assertion_ids,
    )
    return ProjectionFingerprint(
        present=True,
        assertion_ids=tuple(sorted(assertion_ids)),
        provenance_commitments=tuple(
            sorted((aid, commitments[aid]) for aid in assertion_ids if aid in commitments)
        ),
        generation_id=tuple_.generation_id,
        manifest_commitment=tuple_.manifest_commitment,
        projection_binding=binding,
        detail="expected from registry",
    )


def _projection_matches(
    expected: ProjectionFingerprint, actual: ProjectionFingerprint
) -> tuple[bool, str]:
    if not actual.present:
        return False, "projection absent"
    if any(
        token in actual.detail
        for token in ("mixed", "malformed", "unreadable", "disagree")
    ):
        return False, actual.detail
    if not actual.generation_id or not actual.manifest_commitment or not actual.projection_binding:
        return False, "projection missing generation/manifest/binding fields"
    if actual.generation_id != expected.generation_id:
        return False, "generation mismatch"
    if actual.manifest_commitment != expected.manifest_commitment:
        return False, "manifest commitment mismatch"
    if actual.projection_binding != expected.projection_binding:
        return False, "projection binding mismatch"
    if set(actual.assertion_ids) != set(expected.assertion_ids):
        return False, "assertion-id set mismatch"
    if dict(actual.provenance_commitments) != dict(expected.provenance_commitments):
        return False, "provenance commitment mismatch"
    return True, "exact agreement"


def _is_rebuildable_projection_reason(reason: str) -> bool:
    """True when failure means rebuild/pending, not quarantine.

    Missing binding metadata means the projection is not yet an exact
    qualified projection of recovered authority — not that authority is
    contradicted by a stale or forged projection.
    """
    rebuildable = {
        "projection absent",
        "projection missing generation/manifest/binding fields",
    }
    return reason in rebuildable


def _registry_reports(registry: RegistryValidationResult, **extra: Any) -> dict[str, Any]:
    report = {
        "checks": registry.checks,
        "manifest_path": registry.manifest_path,
    }
    report.update(extra)
    return {
        "registry_validation": {
            "outcome": registry.outcome,
            "detail": registry.detail,
            "code": registry.code,
        },
        "registry_report": report,
    }


def _evaluate_projections(
    *,
    data_root: Path,
    tuple_: ProvenanceTuple,
    registry: RegistryValidationResult,
    transitions: list[dict[str, Any]],
    allow_stale_fallback: bool,
    stale_projection_root: Path | None,
) -> RecoveryAuthorityResult:
    gen_dir = data_root / "provenance" / "generations" / tuple_.generation_id
    manifest = json.loads((gen_dir / "manifest.json").read_text(encoding="utf-8"))
    assertion_ids = [str(x) for x in (manifest.get("assertion_ids") or [])]
    commitments = _load_registry_assertion_commitments(
        data_root, tuple_.generation_id, assertion_ids
    )
    expected = _expected_fingerprint(tuple_, assertion_ids, commitments)
    base_reports = _registry_reports(registry, assertion_ids=assertion_ids)

    if allow_stale_fallback and stale_projection_root is not None:
        stale_root = Path(stale_projection_root).expanduser().resolve()
        transitions.append(
            {
                "from": "REGISTRY_VALIDATED",
                "to": "STALE_FALLBACK_ATTEMPT",
                "result": "rejected",
            }
        )
        return RecoveryAuthorityResult(
            state=RecoveryState.QUARANTINED,
            detail="stale projection fallback rejected against recovered authority",
            code="QUARANTINED_STALE_PROJECTION_FALLBACK",
            serving_ready=False,
            provenance_tuple=tuple_,
            reports={
                **base_reports,
                "projection_agreement": {
                    "expected": expected.as_dict(),
                    "stale_jsonl": _read_jsonl_projection(stale_root).as_dict(),
                    "stale_chroma": _read_chroma_projection(stale_root).as_dict(),
                    "fallback_allowed": False,
                    "serving_ready": False,
                },
            },
            transitions=transitions,
        )

    jsonl_fp = _read_jsonl_projection(data_root)
    chroma_fp = _read_chroma_projection(data_root)
    agreement = {
        "expected": expected.as_dict(),
        "jsonl": jsonl_fp.as_dict(),
        "chroma": chroma_fp.as_dict(),
        "serving_ready": False,
    }

    if (not jsonl_fp.present) and (not chroma_fp.present):
        state = RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING
        transitions.append(
            {
                "from": "REGISTRY_VALIDATED",
                "to": state.value,
                "result": "projections_unavailable",
            }
        )
        agreement["status"] = "pending"
        return RecoveryAuthorityResult(
            state=state,
            detail="authority recovered; projections unavailable/rebuildable; non-serving",
            code="AUTHORITY_RECOVERED_PROJECTION_PENDING",
            serving_ready=False,
            provenance_tuple=tuple_,
            reports={**base_reports, "projection_agreement": agreement},
            transitions=transitions,
        )

    if jsonl_fp.present != chroma_fp.present:
        present_name = "jsonl" if jsonl_fp.present else "chroma"
        present_fp = jsonl_fp if jsonl_fp.present else chroma_fp
        ok, reason = _projection_matches(expected, present_fp)
        if ok or _is_rebuildable_projection_reason(reason):
            state = RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING
            transitions.append(
                {
                    "from": "REGISTRY_VALIDATED",
                    "to": state.value,
                    "result": "partial_or_rebuildable_projections",
                    "source": present_name,
                    "match_ok": ok,
                    "reason": reason if not ok else "exact_agreement",
                }
            )
            agreement["status"] = "pending"
            return RecoveryAuthorityResult(
                state=state,
                detail=(
                    "authority recovered; one projection unavailable/rebuildable; "
                    "non-serving"
                ),
                code="AUTHORITY_RECOVERED_PROJECTION_PENDING",
                serving_ready=False,
                provenance_tuple=tuple_,
                reports={**base_reports, "projection_agreement": agreement},
                transitions=transitions,
            )
        state = RecoveryState.QUARANTINED
        transitions.append(
            {
                "from": "REGISTRY_VALIDATED",
                "to": state.value,
                "result": reason,
                "source": present_name,
            }
        )
        agreement["status"] = "quarantined"
        return RecoveryAuthorityResult(
            state=state,
            detail=f"broken/stale {present_name} projection: {reason}",
            code="QUARANTINED_PROJECTION_MISMATCH",
            serving_ready=False,
            provenance_tuple=tuple_,
            reports={**base_reports, "projection_agreement": agreement},
            transitions=transitions,
        )

    jsonl_ok, jsonl_reason = _projection_matches(expected, jsonl_fp)
    chroma_ok, chroma_reason = _projection_matches(expected, chroma_fp)
    if not jsonl_ok or not chroma_ok:
        rebuildable_only = (jsonl_ok or _is_rebuildable_projection_reason(jsonl_reason)) and (
            chroma_ok or _is_rebuildable_projection_reason(chroma_reason)
        )
        if rebuildable_only:
            state = RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING
            transitions.append(
                {
                    "from": "REGISTRY_VALIDATED",
                    "to": state.value,
                    "result": "rebuildable_projections",
                }
            )
            agreement.update(
                {
                    "jsonl_ok": jsonl_ok,
                    "chroma_ok": chroma_ok,
                    "status": "pending",
                    "jsonl_reason": jsonl_reason,
                    "chroma_reason": chroma_reason,
                }
            )
            return RecoveryAuthorityResult(
                state=state,
                detail=(
                    "authority recovered; projections unavailable/rebuildable; "
                    "non-serving"
                ),
                code="AUTHORITY_RECOVERED_PROJECTION_PENDING",
                serving_ready=False,
                provenance_tuple=tuple_,
                reports={**base_reports, "projection_agreement": agreement},
                transitions=transitions,
            )
        state = RecoveryState.QUARANTINED
        transitions.append(
            {
                "from": "REGISTRY_VALIDATED",
                "to": state.value,
                "result": "quarantine",
            }
        )
        agreement.update(
            {
                "jsonl_ok": jsonl_ok,
                "chroma_ok": chroma_ok,
                "status": "quarantined",
            }
        )
        return RecoveryAuthorityResult(
            state=state,
            detail=(
                f"projection disagreement: jsonl={jsonl_reason}; chroma={chroma_reason}"
            ),
            code="QUARANTINED_PROJECTION_MISMATCH",
            serving_ready=False,
            provenance_tuple=tuple_,
            reports={**base_reports, "projection_agreement": agreement},
            transitions=transitions,
        )

    state = RecoveryState.PROJECTION_VALIDATED
    transitions.extend(
        [
            {
                "from": "REGISTRY_VALIDATED",
                "to": state.value,
                "result": "exact_agreement",
            },
            {
                "from": state.value,
                "to": "SERVING_READY",
                "result": "not_authorized_in_t2",
                "serving_ready": False,
            },
        ]
    )
    agreement["status"] = "validated"
    return RecoveryAuthorityResult(
        state=state,
        detail=(
            "authority recovered and projections validated; "
            "serving activation not authorized in T2"
        ),
        code="PROJECTION_VALIDATED",
        serving_ready=False,
        provenance_tuple=tuple_,
        reports={**base_reports, "projection_agreement": agreement},
        transitions=transitions,
    )


def evaluate_recovery_authority(
    root: Path | str,
    *,
    expected_tree_commitment: str | None = None,
    allow_stale_fallback: bool = False,
    stale_projection_root: Path | str | None = None,
) -> RecoveryAuthorityResult:
    """Evaluate recovered authority and projection agreement for a scratch root.

    Never mutates live serving state. ``allow_stale_fallback`` is accepted only
    to prove rejection: when True with a stale projection root, the result is
    always quarantined/blocked — never serving.
    """
    data_root = Path(root).expanduser().resolve()
    content_tree_present = (data_root / "decisions-approved.jsonl").is_file() or (
        data_root / "chroma"
    ).is_dir()
    evidence_present = (data_root / EVIDENCE_FILENAME).is_file()

    registry = validate_provenance_registry(
        data_root, expected_tree_commitment=expected_tree_commitment
    )
    mapped = _registry_authority_map(registry, content_tree_present=content_tree_present)
    if mapped is not None:
        if evidence_present:
            mapped.detail = (
                f"{mapped.detail}; capture evidence present but cannot repair registry"
            )
            report = dict(mapped.reports.get("registry_report") or {})
            report["evidence_sidecar_present"] = True
            report["evidence_repairs_registry"] = False
            mapped.reports["registry_report"] = report
        return mapped

    assert registry.provenance_tuple is not None
    transitions = [
        {
            "from": "CANDIDATE",
            "to": "REGISTRY_VALIDATED",
            "result": "VALID",
            "generation_id": registry.provenance_tuple.generation_id,
        }
    ]
    return _evaluate_projections(
        data_root=data_root,
        tuple_=registry.provenance_tuple,
        registry=registry,
        transitions=transitions,
        allow_stale_fallback=allow_stale_fallback,
        stale_projection_root=(
            Path(stale_projection_root) if stale_projection_root is not None else None
        ),
    )



def write_matching_projections(
    root: Path,
    provenance_tuple: ProvenanceTuple,
    *,
    assertion_ids: tuple[str, ...] | None = None,
    include_jsonl: bool = True,
    include_chroma: bool = True,
    rewrite_bodies: bool = False,
) -> str:
    """Test helper: write projection bindings (and optionally bodies) for a registry.

    Binding sidecars are T_g-excluded so they may carry M_g without cycles.
    When ``rewrite_bodies`` is False (default), only sidecars are written so a
    sealed registry tree commitment remains valid.
    """
    root = root.expanduser().resolve()
    gen_dir = root / "provenance" / "generations" / provenance_tuple.generation_id
    manifest = json.loads((gen_dir / "manifest.json").read_text(encoding="utf-8"))
    aids = list(assertion_ids or manifest.get("assertion_ids") or [])
    commitments = _load_registry_assertion_commitments(
        root, provenance_tuple.generation_id, aids
    )
    binding = compute_projection_binding(
        generation_id=provenance_tuple.generation_id,
        manifest_commitment=provenance_tuple.manifest_commitment,
        assertion_ids=aids,
    )
    bind_payload = {
        "generation_id": provenance_tuple.generation_id,
        "manifest_commitment": provenance_tuple.manifest_commitment,
        "projection_binding": binding,
        "assertion_ids": aids,
        "provenance_commitments": commitments,
    }

    if include_jsonl:
        if rewrite_bodies:
            rows = [
                {
                    "id": aid,
                    "assertion_id": aid,
                    "provenance_commitment": commitments.get(aid, ""),
                    "generation_id": provenance_tuple.generation_id,
                }
                for aid in aids
            ]
            (root / "knowledge_units.jsonl").write_text(
                "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
                encoding="utf-8",
            )
        (root / "knowledge_units.projection.json").write_text(
            json.dumps(bind_payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )

    if include_chroma:
        chroma = root / "chroma"
        chroma.mkdir(parents=True, exist_ok=True)
        if rewrite_bodies:
            db = chroma / "chroma.sqlite3"
            if db.exists():
                db.unlink()
            conn = sqlite3.connect(str(db))
            conn.executescript(
                """
                CREATE TABLE collections (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, dimension INTEGER,
                    database_id TEXT NOT NULL, config_json_str TEXT, schema_str TEXT
                );
                CREATE TABLE segments (
                    id TEXT PRIMARY KEY, type TEXT NOT NULL, scope TEXT NOT NULL,
                    collection TEXT NOT NULL
                );
                CREATE TABLE embeddings (
                    id INTEGER PRIMARY KEY, segment_id TEXT NOT NULL,
                    embedding_id TEXT NOT NULL, seq_id BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                "INSERT INTO collections VALUES ('c0', 'knowledge_units', NULL, 'db', NULL, NULL)"
            )
            conn.execute(
                "INSERT INTO segments VALUES ('s0', 'vector', 'VECTOR', 'c0')"
            )
            for i, aid in enumerate(aids):
                conn.execute(
                    "INSERT INTO embeddings VALUES (?, 's0', ?, ?, CURRENT_TIMESTAMP)",
                    (i, aid, b"\x00"),
                )
            conn.execute(
                "INSERT INTO collections VALUES ('c1', 'conversation_summaries', NULL, 'db', NULL, NULL)"
            )
            conn.execute(
                "INSERT INTO segments VALUES ('s1', 'vector', 'VECTOR', 'c1')"
            )
            conn.execute(
                "INSERT INTO embeddings VALUES (1000, 's1', 'sum-1', ?, CURRENT_TIMESTAMP)",
                (b"\x00",),
            )
            conn.commit()
            conn.close()
        (chroma / "projection_binding.json").write_text(
            json.dumps(bind_payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    return binding



__all__ = [
    "PROJECTION_BINDING_PROFILE",
    "RECOVERY_STATE_SCHEMA",
    "ProjectionFingerprint",
    "RecoveryAuthorityResult",
    "RecoveryState",
    "build_registry_fixture",
    "compute_projection_binding",
    "evaluate_recovery_authority",
    "write_matching_projections",
]
