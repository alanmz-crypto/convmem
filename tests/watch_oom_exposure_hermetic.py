# pylint: disable=too-many-locals
"""Hermetic fixtures for bounded exposure-window probe Execute (C0–C6)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.watch_oom_brief_hermetic import ENVELOPE_32K, write_chroma_sqlite

EXPOSURE_ROW = {
    "id": "exposure-window-tracking",
    "status": "open",
    "last_verified": "2026-07-01",
    "trigger": {"type": "probe", "probe": "exposure-window-tracking"},
}

FORBIDDEN_EXPOSURE_KEYS = (
    "document",
    "chroma:document",
    "provenance_envelope",
    "provenance_commitment",
    "provenance_assertion_id",
    "title",
    "summary",
    "source_path",
    "rationale",
)


def _meta_record(eid: str, **meta: Any) -> dict:
    payload = {
        "provenance_envelope": ENVELOPE_32K,
        "provenance_commitment": "forbidden-commit",
        "title": f"title {eid}",
        "summary": f"summary {eid}",
        "source_path": "/tmp/forbidden",
        "rationale": "forbidden rationale",
    }
    payload.update(meta)
    return {
        "id": eid,
        "document": f"document body for {eid}",
        "metadata": payload,
    }


def write_probe_chroma(chroma_dir: Path, metas: list[dict]) -> Path:
    """Minimal Chroma readable by the exposure-window projected iterator."""
    records = []
    for i, meta in enumerate(metas):
        eid = meta.pop("id", None) or f"emb-{i:04d}"
        records.append(_meta_record(eid, **meta))
    return write_chroma_sqlite(chroma_dir, {"knowledge_units": records})


def exposure_cfg(chroma_dir: Path) -> dict:
    return {"index": {"chroma_dir": str(chroma_dir)}, "models": {}}


def write_exposure_register(tmp_root: Path) -> Path:
    reg = tmp_root / "standing-checks-register.json"
    reg.write_text(
        json.dumps({"checks": [EXPOSURE_ROW]}),
        encoding="utf-8",
    )
    return reg


def _obs_meta(lid: str, severity: str, ts: str, **extra: Any) -> dict:
    return {
        "ledger_id": lid,
        "type": "observation",
        "severity": severity,
        "timestamp": ts,
        **extra,
    }


def _verif_meta(lid: str, parent: str, result: str, ts: str) -> dict:
    return {
        "ledger_id": lid,
        "ledger_kind": "verification",
        "relates_to": parent,
        "result": result,
        "timestamp": ts,
    }


def exposure_c0_scenarios() -> list[dict[str, Any]]:
    """Deterministic oracle cases: name, row overrides, metas, expected due/detail."""
    return [
        {
            "name": "invalid_last_verified",
            "row": {"last_verified": "not-a-date"},
            "metas": [],
            "due": True,
            "detail_contains": ["unparseable"],
        },
        {
            "name": "empty_collection",
            "metas": [],
            "due": False,
            "detail_contains": ["no closed critical/high"],
        },
        {
            "name": "medium_closed_not_eligible",
            "metas": [
                _obs_meta("obs_m", "medium", "2026-06-20T10:00:00"),
                _verif_meta("ver_m", "obs_m", "pass", "2026-07-05T10:00:00"),
            ],
            "due": False,
            "detail_contains": ["no closed critical/high"],
        },
        {
            "name": "critical_still_open",
            "metas": [_obs_meta("obs_p0", "critical", "2026-07-05T10:00:00")],
            "due": False,
            "detail_contains": ["no closed critical/high"],
        },
        {
            "name": "critical_closed_after_last_verified",
            "metas": [
                _obs_meta("obs_p0", "critical", "2026-06-20T10:00:00"),
                _verif_meta("obs_v1", "obs_p0", "pass", "2026-07-05T10:00:00"),
            ],
            "due": True,
            "detail_contains": ["obs_p0", "2026-07-05"],
        },
        {
            "name": "critical_closed_before_last_verified",
            "metas": [
                _obs_meta("obs_p0", "critical", "2026-06-20T10:00:00"),
                _verif_meta("obs_v1", "obs_p0", "pass", "2026-06-25T10:00:00"),
            ],
            "due": False,
            "detail_contains": ["clean-scan recorded"],
        },
        {
            "name": "high_observation_level_pass",
            "metas": [
                _obs_meta(
                    "obs_hp",
                    "high",
                    "2026-07-10T10:00:00",
                    verification_result="pass",
                ),
            ],
            "due": True,
            "detail_contains": ["obs_hp", "2026-07-10"],
        },
        {
            "name": "failed_verification_still_open",
            "metas": [
                _obs_meta("obs_f", "high", "2026-06-20T10:00:00"),
                _verif_meta("ver_f", "obs_f", "fail", "2026-07-05T10:00:00"),
            ],
            "due": False,
            "detail_contains": ["no closed critical/high"],
        },
        {
            "name": "timestamp_fallback_without_verification",
            "metas": [
                _obs_meta("obs_fb", "critical", "2026-07-08T10:00:00"),
                {
                    "ledger_id": "ver_pending",
                    "ledger_kind": "verification",
                    "relates_to": "obs_fb",
                    "result": "",
                    "timestamp": "2026-07-09T10:00:00",
                },
            ],
            "due": True,
            "detail_contains": ["obs_fb", "2026-07-09"],
        },
        {
            "name": "later_note_does_not_refire",
            "metas": [
                _obs_meta("obs_p0", "high", "2026-06-20T10:00:00"),
                _verif_meta("obs_v1", "obs_p0", "pass", "2026-06-25T10:00:00"),
                {"ledger_id": "obs_note", "ledger_kind": "note", "relates_to": "obs_p0",
                 "timestamp": "2026-07-06T10:00:00"},
            ],
            "due": False,
            "detail_contains": ["clean-scan recorded"],
        },
        {
            "name": "duplicate_ledger_id_last_wins",
            "metas": [
                _obs_meta("obs_dup", "critical", "2026-06-20T10:00:00", id="emb-a"),
                _obs_meta("obs_dup", "critical", "2026-06-20T10:00:00", id="emb-b"),
                _verif_meta("ver_dup", "obs_dup", "pass", "2026-07-05T10:00:00"),
            ],
            "due": True,
            "detail_contains": ["obs_dup"],
        },
        {
            "name": "equal_close_dates_pick_latest_lid",
            "metas": [
                _obs_meta("obs_a", "critical", "2026-06-20T10:00:00"),
                _verif_meta("ver_a", "obs_a", "pass", "2026-07-05T10:00:00"),
                _obs_meta("obs_b", "high", "2026-06-20T10:00:00"),
                _verif_meta("ver_b", "obs_b", "pass", "2026-07-05T10:00:00"),
            ],
            "due": True,
            "detail_contains": ["2026-07-05"],
        },
        {
            "name": "superseded_row_excluded",
            "metas": [
                _obs_meta(
                    "obs_sup",
                    "critical",
                    "2026-06-20T10:00:00",
                    superseded=True,
                ),
                _verif_meta("ver_sup", "obs_sup", "pass", "2026-07-05T10:00:00"),
            ],
            "due": False,
            "detail_contains": ["no closed critical/high"],
        },
        {
            "name": "deleted_not_excluded",
            "metas": [
                _obs_meta(
                    "obs_del",
                    "critical",
                    "2026-06-20T10:00:00",
                    deleted=True,
                ),
                _verif_meta("ver_del", "obs_del", "pass", "2026-07-05T10:00:00"),
            ],
            "due": True,
            "detail_contains": ["obs_del"],
        },
        {
            "name": "malformed_child_timestamp_ignored",
            "metas": [
                _obs_meta("obs_bad", "critical", "2026-06-20T10:00:00"),
                _verif_meta("ver_bad", "obs_bad", "pass", "not-a-ts"),
                _verif_meta("ver_good", "obs_bad", "pass", "2026-07-05T10:00:00"),
            ],
            "due": True,
            "detail_contains": ["obs_bad", "2026-07-05"],
        },
    ]


def write_exposure_memory_fixture(
    chroma_dir: Path,
    n: int,
    *,
    envelope: str = ENVELOPE_32K,
) -> None:
    """Bulk synthetic Chroma for C6 exposure probe / brief-chain measurement."""
    records = []
    for i in range(n):
        kind = "decision" if i % 17 == 0 else "observation"
        lid = f"obs_mem_{i}" if kind != "decision" else f"dec_prop_mem_{i}"
        meta = {
            "ledger_id": lid,
            "ledger_kind": kind,
            "type": "decision" if kind == "decision" else "observation",
            "timestamp": f"2026-09-13T{i % 24:02d}:{(i % 60):02d}:00Z",
            "provenance_envelope": envelope,
            "title": f"Unit {i}",
            "summary": f"Unit {i}",
            "rationale": f"rationale {i}",
            "source_path": "/tmp/memory-source",
        }
        if kind == "observation" and i % 23 == 0:
            meta["severity"] = "critical"
            meta["verification_result"] = "pass"
        elif kind == "observation" and i % 29 == 0:
            meta["severity"] = "high"
        records.append(_meta_record(f"m-{i:06d}", **meta))
    write_chroma_sqlite(chroma_dir, {"knowledge_units": records})
