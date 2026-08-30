#!/usr/bin/env python3
"""Protocol v3 seed admissibility with K8/K9 relational and K10 scope rules."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from typing import Callable

from pathlib import Path

from protocol_v3 import K_ROLES, RELOCATION_SCOPE, seal_inventory

STATUS_PRESENT = "present_captured"
STATUS_CAPTURE_FAIL = "present_capture_failed"
STATUS_ABSENT = "absent"
STATUS_WRONG = "wrong_property"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _has(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def _search(config_path: Path, query: str, repo_cwd: Path, domain: str | None = None) -> str:
    cmd = ["convmem", "search", query, "--top", "8"]
    if domain:
        cmd.extend(["--domain", domain])
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env={"CONVMEM_CONFIG": str(config_path), **__import__("os").environ},
        cwd=str(repo_cwd),
        check=False,
        timeout=120,
    )
    return (proc.stdout or "") + (proc.stderr or "")


def _role_checks() -> dict[str, Callable[[str], bool]]:
    return {
        "K1": lambda t: _has(t, [r"walkable", r"car[- ]dependent", r"lifestyle", r"prefer", r"access"]),
        "K2": lambda t: _has(
            t,
            [
                r"\$\s?\d{3,5}",
                r"\d{3,5}\s?/month",
                r"rent.{0,20}ceiling",
                r"budget.{0,20}month",
                r"monthly.{0,20}(rent|housing|budget)",
                r"upper.{0,20}monthly",
            ],
        ),
        "K3": lambda t: _has(t, [r"neighborhood", r"district"]) and _has(
            t, [r"noise", r"transit", r"walk", r"vibe", r"feel", r"busy", r"quiet", r"focal"]
        ),
        "K4": lambda t: _has(t, [r"dog|pet", r"office|workspace", r"must[- ]have", r"requirement", r"household"]),
        "K5": lambda t: _has(t, [r"reject", r"ruled out", r"passed on", r"won't work", r"eliminated"]),
        "K6": lambda t: _has(t, [r"because", r"due to", r"reason", r"since"]) and _has(
            t, [r"reject", r"ruled out", r"passed", r"won't", r"eliminated"]
        ),
        "K7": lambda t: _has(t, [r"\bTBD\b", r"undecided", r"still open", r"unresolved", r"don'?t know yet"]),
        "K8": lambda t: _has(
            t,
            [r"provisional", r"lean", r"initial priority", r"for now", r"tentative", r"starting with"],
        )
        and _has(t, [r"neighborhood", r"area", r"district", r"priority"]),
        "K9": lambda t: _has(
            t,
            [r"current priority", r"now priorit", r"updated to", r"changed to", r"instead", r"supersed"],
        )
        and _has(t, [r"neighborhood", r"area", r"district"]),
        "K10": lambda t: _has(
            t,
            [
                r"stipend",
                r"employer",
                r"moving cost",
                r"commute",
                r"transportation",
                r"logistics",
                r"financial",
                r"relocation (bonus|package|assistance)",
            ],
        ),
    }


def evaluate_k8_k9_relational(transcript: str) -> dict:
    """K9 must genuinely supersede K8; Phase 3b retain = failure."""
    lower = transcript.lower()
    k8_markers = [
        r"provisional",
        r"for now",
        r"tentative",
        r"lean(?:ing)? toward",
        r"initial(?:ly)?",
    ]
    k9_change = [
        r"changed (?:to|my)",
        r"updated (?:to|my)",
        r"now priorit",
        r"current priority",
        r"instead",
        r"supersed",
        r"shifted to",
    ]
    retain = [
        r"retain(?:ing)? (?:the )?(?:earlier|previous|same)",
        r"keeping (?:the )?(?:earlier|previous|same)",
        r"still (?:lean|priorit)",
        r"no change",
        r"unchanged",
    ]
    has_k8 = any(re.search(p, lower) for p in k8_markers)
    has_k9_change = any(re.search(p, lower) for p in k9_change)
    retained = any(re.search(p, lower) for p in retain)
    qualifies = has_k8 and has_k9_change and not retained
    return {
        "k8_present": has_k8,
        "k9_supersedes": has_k9_change,
        "retained_k8": retained,
        "qualifies": qualifies,
    }


def evaluate_k10_provenance(
    *,
    transcript: str,
    config_path: Path,
    repo_cwd: Path,
    locked_scope: str,
    phase4_artifact_path: str | None,
) -> dict:
    checks = _role_checks()
    transcript_hit = checks["K10"](transcript)
    scoped_blob = _search(
        config_path,
        "Portland move employer stipend transportation logistics financial",
        repo_cwd,
        domain=locked_scope,
    )
    relocation_blob = _search(
        config_path,
        "Portland move employer stipend transportation logistics financial",
        repo_cwd,
        domain=RELOCATION_SCOPE,
    )
    scoped_hit = checks["K10"](scoped_blob)
    relocation_only = checks["K10"](relocation_blob) and not scoped_hit
    distinct_artifact = bool(phase4_artifact_path and Path(phase4_artifact_path).exists())
    qualifies = (
        transcript_hit
        and scoped_hit
        and not relocation_only
        and locked_scope != RELOCATION_SCOPE
        and distinct_artifact
    )
    return {
        "transcript_hit": transcript_hit,
        "scoped_corpus_hit": scoped_hit,
        "relocation_only_capture": relocation_only,
        "locked_scope": locked_scope,
        "phase4_artifact_path": phase4_artifact_path,
        "distinct_artifact_exists": distinct_artifact,
        "qualifies": qualifies,
    }


def evaluate_seed_v3(
    *,
    transcript: str,
    config_path: Path,
    repo_cwd: Path,
    locked_phase4_scope: str,
    phase4_artifact_path: str | None = None,
) -> dict:
    checks = _role_checks()
    neutral_queries = {
        "K1": "Portland housing lifestyle walkability preference",
        "K2": "Portland monthly housing budget rent ceiling",
        "K3": "Portland neighborhood observation noise transit",
        "K4": "Portland rental must-have dog office requirements",
        "K5": "Portland rejected rental neighborhood option",
        "K6": "Portland rejection reason ruled out",
        "K7": "Portland move unresolved undecided open question",
        "K8": "Portland provisional neighborhood priority",
        "K9": "Portland current neighborhood priority updated decision",
        "K10": "Portland move employer stipend transportation logistics financial",
    }
    k8_k9 = evaluate_k8_k9_relational(transcript)
    inventory: dict = {
        "protocol_version": 3,
        "evaluated_at": utc_now(),
        "roles": K_ROLES,
        "k": {},
        "k8_k9_relational": k8_k9,
    }
    admissible = True
    failure_mode = ""

    for kid, role in K_ROLES.items():
        fn = checks[kid]
        transcript_hit = fn(transcript)
        if kid == "K10":
            k10 = evaluate_k10_provenance(
                transcript=transcript,
                config_path=config_path,
                repo_cwd=repo_cwd,
                locked_scope=locked_phase4_scope,
                phase4_artifact_path=phase4_artifact_path,
            )
            inventory["k10_provenance"] = k10
            if not transcript_hit:
                status = STATUS_ABSENT
            elif not k10["qualifies"]:
                status = STATUS_WRONG if k10["scoped_corpus_hit"] else STATUS_CAPTURE_FAIL
            else:
                status = STATUS_PRESENT
        else:
            corpus_blob = _search(config_path, neutral_queries[kid], repo_cwd)
            corpus_hit = fn(corpus_blob)
            if not transcript_hit:
                status = STATUS_ABSENT
            elif transcript_hit and not corpus_hit:
                status = STATUS_CAPTURE_FAIL
            else:
                status = STATUS_PRESENT

        inventory["k"][kid] = {
            "role": role,
            "status": status,
            "transcript_hit": transcript_hit,
        }
        if status != STATUS_PRESENT:
            admissible = False
            if not failure_mode:
                failure_mode = (
                    "RERUN3 CAPTURE-STAGE FAILURE"
                    if status == STATUS_CAPTURE_FAIL
                    else "RERUN3 SEED-GENERATION FAILURE"
                )

    if not k8_k9["qualifies"]:
        admissible = False
        failure_mode = "RERUN3 SEED-GENERATION FAILURE"
        inventory["k"]["K9"]["status"] = STATUS_WRONG
        inventory["k8_k9_relational"]["failure"] = "K8 not genuinely superseded by K9"

    inventory["admissible"] = admissible
    inventory["failure_mode"] = failure_mode if not admissible else ""
    inventory["inventory_seal"] = seal_inventory(inventory)
    return inventory


def write_private_inventory_v3(path: Path, admissibility: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    private = {
        "note": "private Protocol-v3 inventory — values not in git",
        "protocol_version": 3,
        "admissible": admissibility.get("admissible"),
        "failure_mode": admissibility.get("failure_mode"),
        "role_status": {k: v["status"] for k, v in admissibility.get("k", {}).items()},
        "k8_k9_relational": admissibility.get("k8_k9_relational"),
        "k10_provenance": admissibility.get("k10_provenance"),
        "inventory_seal": admissibility.get("inventory_seal"),
    }
    path.write_text(json.dumps(private, indent=2) + "\n", encoding="utf-8")
    return admissibility["inventory_seal"]
