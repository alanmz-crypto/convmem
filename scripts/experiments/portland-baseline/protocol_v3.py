#!/usr/bin/env python3
"""Frozen Protocol v3 manifest and scope definitions for Portland Rerun3."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from domains import DEFAULT_DOMAINS

PROTOCOL_VERSION = 3
RUN_ID = "portland-baseline-2026-08-30-rerun3-v3"
RESTIC_SNAPSHOT = "d3908f4e"
MECHANICAL_CORRECTIVE_SHA = "4b8ff94"
RELOCATION_SCOPE = "relocation"

# Phase-4a subject → existing non-relocation domain (frozen before Agent A).
PHASE4_SCOPE_MAP: dict[str, str] = {
    "finance": "general",
    "employment": "coding.backend",
    "transportation": "web_stack.hosting",
    "logistics": "coding.devops",
}

PHASE4_SUBJECTS = tuple(PHASE4_SCOPE_MAP.keys())

AGENT_A_PHASES: list[dict[str, str]] = [
    {
        "phase": "opening",
        "prompt": (
            "Help plan a possible move to Portland. Choose all substantive values and options "
            "yourself. Preserve earlier conclusions so the record shows how the plan develops. "
            "Work only on the task in the current message."
        ),
    },
    {
        "phase": "phase1",
        "prompt": (
            "Set out the housing-search constraints: the upper monthly housing amount, "
            "day-to-day access or lifestyle preferences, and concrete household or workspace needs. "
            "Choose all specifics yourself."
        ),
    },
    {
        "phase": "phase2",
        "prompt": (
            "Compare plausible neighborhoods against those constraints. Designate one focal "
            "neighborhood observation, one option ruled out and its reason, and one question "
            "that remains genuinely unresolved."
        ),
    },
    {
        "phase": "phase3a",
        "prompt": (
            "Using only the record so far, state a provisional neighborhood priority and the "
            "evidence supporting it."
        ),
    },
    {
        "phase": "phase3b",
        "prompt": (
            "Choose and investigate one additional practical consideration not used in that "
            "provisional choice. Record the new evidence, then reassess the priority. State the "
            "current priority and why; retaining the earlier priority is allowed."
        ),
    },
    {
        "phase": "phase4a",
        "prompt": (
            "Choose one adjacent practical subject from finance, employment, transportation, "
            "or logistics. Name the subject only."
        ),
    },
    {
        "phase": "phase4b",
        "prompt": (
            "Create a separate ordinary note under that subject containing one concrete fact "
            "that could matter during the move."
        ),
    },
]

QUESTIONS: dict[str, str] = {
    "Q1": "What is the rent budget ceiling for the Portland move?",
    "Q2": "How much can we afford for housing there each month?",
    "Q3": "What did we think about that one neighborhood?",
    "Q4": "Given the must-haves, what kind of place should we look for?",
    "Q5": "What's the current decision on which Portland neighborhood to prioritize?",
    "Q6": "Which option did we rule out and why?",
    "Q7": "What's still open / undecided about the move?",
    "Q8": "Is there anything relevant we filed elsewhere?",
}

Q_TO_K: dict[str, list[str]] = {
    "Q1": ["K2"],
    "Q2": ["K2"],
    "Q3": ["K3"],
    "Q4": ["K1", "K2", "K4"],
    "Q5": ["K9"],
    "Q6": ["K5", "K6"],
    "Q7": ["K7"],
    "Q8": ["K10"],
}

K_ROLES: dict[str, str] = {
    "K1": "housing/lifestyle preference",
    "K2": "explicit concrete monthly housing ceiling",
    "K3": "focal neighborhood observation",
    "K4": "concrete household/workspace need(s)",
    "K5": "rejected option",
    "K6": "causally linked rejection reason",
    "K7": "genuinely unresolved question remaining at end",
    "K8": "supported provisional neighborhood decision",
    "K9": "later current decision genuinely superseding K8",
    "K10": "move-relevant fact from separately scoped adjacent source",
}

K_STATUSES = ("present_captured", "present_capture_failed", "absent", "wrong_property")

CONTAMINATION_EXCLUSIONS = [
    "portland-baseline-2026-08-29",
    "portland-baseline-2026-08-30-rerun1",
    "portland-baseline-2026-08-30-rerun2",
    "portland-baseline-2026-08-30-rerun3",
    "portland-baseline-2026-08-30-rerun3-v3/evidence",
    "PORTLAND-AGENT-A",
    "PORTLAND-RERUN",
    "portland-relocation-notes.md",
    "k_inventory.private.json",
    "seed_admissibility",
    "01a05042-8c04-7302-8baa-b7fa0039b228",
]

BLINDNESS_FORBIDDEN_READS = [
    "scripts/experiments/portland-baseline",
    "docs/experiments/PORTLAND",
    "protocol_v3_manifest",
    "k_inventory.private.json",
    "frozen_protocol.json",
    "seed_admissibility.json",
    "01a05042-8c04-7302-8baa-b7fa0039b228",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_phase4_scope_map() -> tuple[bool, str]:
    """Every Phase-4 subject must map to a known non-relocation domain."""
    known = set(DEFAULT_DOMAINS)
    scopes = set(PHASE4_SCOPE_MAP.values())
    if len(scopes) != len(PHASE4_SCOPE_MAP):
        return False, "duplicate locked scopes in phase4 map"
    for subject, scope in PHASE4_SCOPE_MAP.items():
        if scope not in known:
            return False, f"{subject} maps to unknown domain {scope!r}"
        if scope == RELOCATION_SCOPE or scope.startswith(RELOCATION_SCOPE + "."):
            return False, f"{subject} maps to relocation scope {scope!r}"
    return True, "ok"


def parse_phase4a_subject(text: str) -> str | None:
    """Extract Phase-4a subject from agent reply (subject name only turn)."""
    lower = text.lower()
    for subject in PHASE4_SUBJECTS:
        if re.search(rf"\b{re.escape(subject)}\b", lower):
            return subject
    return None


def build_protocol_manifest(*, execution_revision: str, model_settings: dict[str, Any]) -> dict:
    ok, reason = validate_phase4_scope_map()
    if not ok:
        raise RuntimeError(f"phase4 scope map invalid: {reason}")
    return {
        "schema": "portland-baseline.protocol-manifest.v3",
        "protocol_version": PROTOCOL_VERSION,
        "run_id": RUN_ID,
        "execution_revision": execution_revision,
        "mechanical_corrective_sha": MECHANICAL_CORRECTIVE_SHA,
        "background_snapshot": RESTIC_SNAPSHOT,
        "model_settings": model_settings,
        "agent_a_phases": AGENT_A_PHASES,
        "blindness": {
            "agent_a_sees_only": [
                "current phase prompt",
                "preceding natural planning turns",
            ],
            "forbidden_reads": BLINDNESS_FORBIDDEN_READS,
            "single_candidate": True,
        },
        "k_roles": K_ROLES,
        "k8_k9_rule": {
            "k9_qualifies_only_if": [
                "K8 precedes new evidence and K9",
                "K8 explicitly provisional and supported",
                "materially relevant new evidence only after K8",
                "later explicit current decision exists",
                "priority differs from K8",
                "explanation links new evidence to change",
                "record makes clear K8 no longer current",
            ],
            "phase3b_retain_k8": "RERUN3 SEED-GENERATION FAILURE",
        },
        "k10_rule": {
            "qualifies_only_if": [
                "adjacent subject chosen in Phase 4a",
                "mapping table existed before Agent A",
                "selected scope locked before Phase 4b",
                "Phase 4b creates distinct ordinary source artifact",
                "fact is move-relevant",
                "qualifying capture under locked non-relocation scope",
                "relocation transcript not accepted as K10 provenance",
            ],
        },
        "phase4_scope_map": PHASE4_SCOPE_MAP,
        "relocation_scope": RELOCATION_SCOPE,
        "questions": QUESTIONS,
        "q_to_k": Q_TO_K,
        "scoring": {
            "effort_budget_n": 5,
            "atomic_action_definition": (
                "One action = one bounded recovery attempt: a single rg/grep invocation, "
                "one file read, one gh search/fetch, or one convmem search/ask call."
            ),
            "aggregate_rule": "Authoritative verdict only after independent Luna xHigh review",
            "interpretation_boundary": (
                "Controlled-seed retrieval experiment only; does not establish natural "
                "long-term planning memory."
            ),
        },
        "agent_b": {
            "authorized": False,
            "c0_c1_symmetry": "future — randomized counterbalanced order when authorized",
            "ryan_seed_gate_required": True,
        },
        "terminal_outcomes": [
            "RERUN3 V3 SEED READY",
            "RERUN3 SEED-GENERATION FAILURE",
            "RERUN3 CAPTURE-STAGE FAILURE",
            "RERUN3 HARNESS FAILURE",
        ],
        "pre_v3_candidate": {
            "status": "PRE-V3 SEED — NON-ADMISSIBLE UNDER FINAL PROTOCOL",
            "thread_id": "01a05042-8c04-7302-8baa-b7fa0039b228",
            "note": "Protocol-development evidence only; not Protocol-v3 candidate",
        },
        "frozen_at": utc_now(),
    }


def manifest_digest(manifest: dict) -> str:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_background_identity(
    *,
    experiment_root: Path,
    config_path: Path,
    embed_model: str = "nomic-embed-text",
) -> dict:
    """Protocol v3 background corpus identity (section 13)."""
    bg = experiment_root / "store" / "background"
    chroma = bg / "chroma"
    processed = bg / "processed.json"
    units_export = bg / "knowledge_units.jsonl"

    def _file_digest(path: Path) -> str:
        if not path.exists():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    chroma_digest = hashlib.sha256()
    source_paths: list[str] = []
    for path in sorted(chroma.rglob("*")):
        if path.is_file():
            chroma_digest.update(path.read_bytes())
            source_paths.append(str(path.relative_to(bg)))

    processed_text = processed.read_text(encoding="utf-8") if processed.exists() else "{}"
    processed_data = json.loads(processed_text) if processed_text.strip() else {}

    return {
        "schema": "portland-baseline.background-identity.v3",
        "run_id": RUN_ID,
        "restic_snapshot": RESTIC_SNAPSHOT,
        "captured_at": utc_now(),
        "logical_corpus_export_digest": _file_digest(units_export) or chroma_digest.hexdigest(),
        "physical_chroma_digest": chroma_digest.hexdigest(),
        "source_paths": source_paths[:50],
        "source_path_count": len(source_paths),
        "processed_state_identity": {
            "path": str(processed),
            "sha256": _file_digest(processed),
            "entry_count": len(processed_data) if isinstance(processed_data, dict) else 0,
        },
        "schema_identity": "convmem-chroma-v1",
        "embedding_model_identity": embed_model,
        "config_identity": {
            "path": str(config_path),
            "sha256": _file_digest(config_path),
        },
        "source_allowlist": [
            "restic snapshot d3908f4e chroma",
            "restic snapshot d3908f4e processed.json",
        ],
        "exclusion_manifest": CONTAMINATION_EXCLUSIONS,
        "domains_observed_note": (
            "Background predates Agent-A; relocation domain absent until indexing."
        ),
    }


def seal_inventory(inventory: dict) -> str:
    payload = json.dumps(inventory, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
