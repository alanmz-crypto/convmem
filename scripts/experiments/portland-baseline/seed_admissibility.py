#!/usr/bin/env python3
"""Role-based seed admissibility for Portland baseline experiments."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

K_ROLES = {
    "K1": "housing/lifestyle preference",
    "K2": "concrete monthly budget ceiling",
    "K3": "neighborhood observation",
    "K4": "concrete housing/household must-have(s)",
    "K5": "rejected option",
    "K6": "rejection reason",
    "K7": "unresolved question",
    "K8": "earlier decision",
    "K9": "later current decision superseding K8",
    "K10": "move-relevant fact naturally stored outside relocation scope",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _search(config_path: Path, query: str, repo_cwd: Path) -> str:
    proc = subprocess.run(
        ["convmem", "search", query, "--top", "8"],
        capture_output=True,
        text=True,
        env={"CONVMEM_CONFIG": str(config_path), **__import__("os").environ},
        cwd=str(repo_cwd),
        check=False,
        timeout=120,
    )
    return (proc.stdout or "") + (proc.stderr or "")


def _has(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def _role_checks() -> dict[str, Callable[[str], bool]]:
    return {
        "K1": lambda t: _has(t, [r"walkable", r"car[- ]dependent", r"lifestyle", r"prefer.*neighborhood", r"accessibility"]),
        "K2": lambda t: _has(t, [r"\$\s?\d{3,5}", r"\d{3,5}\s?/month", r"rent.{0,20}ceiling", r"budget.{0,20}month", r"monthly.{0,20}(rent|housing|budget)"]),
        "K3": lambda t: _has(t, [r"neighborhood", r"district", r"area"]) and _has(t, [r"noise", r"transit", r"walk", r"vibe", r"feel", r"busy", r"quiet"]),
        "K4": lambda t: _has(t, [r"dog|pet", r"office|workspace", r"must[- ]have", r"requirement"]),
        "K5": lambda t: _has(t, [r"reject", r"ruled out", r"passed on", r"won't work", r"not considering", r"eliminated"]),
        "K6": lambda t: _has(t, [r"because", r"due to", r"reason", r"since", r"policy", r"layout", r"doesn'?t allow"]),
        "K7": lambda t: _has(t, [r"\bTBD\b", r"undecided", r"still open", r"unresolved", r"don'?t know yet", r"need to decide"]),
        "K8": lambda t: _has(t, [r"initially", r"first (thought|choice|priority)", r"provisional", r"earlier", r"started with", r"leaned toward"]),
        "K9": lambda t: _has(t, [r"now priorit", r"current (priority|choice|decision)", r"updated to", r"changed to", r"instead", r"supersed", r"revisit"]),
        "K10": lambda t: _has(t, [r"stipend", r"employer", r"relocation (bonus|package|assistance)", r"moving cost", r"commute time", r"transportation", r"logistics", r"financial"]),
    }


def _k10_wrong_property(corpus_blob: str) -> bool:
    # Fail if only relocation-scoped capture with no adjacent-subject signal.
    has_adjacent = _has(corpus_blob, [r"stipend", r"employer", r"moving cost", r"transportation", r"logistics", r"financial", r"commute"])
    relocation_only = _has(corpus_blob, [r"relocation"]) and not has_adjacent
    return relocation_only


def evaluate_seed(
    *,
    transcript: str,
    config_path: Path,
    repo_cwd: Path,
    attempt: int,
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
        "K8": "Portland earlier neighborhood priority provisional",
        "K9": "Portland current neighborhood priority updated decision",
        "K10": "Portland move employer stipend transportation logistics financial",
    }
    inventory: dict = {
        "attempt": attempt,
        "evaluated_at": utc_now(),
        "roles": K_ROLES,
        "k": {},
    }
    admissible = True
    for kid, role in K_ROLES.items():
        fn = checks[kid]
        transcript_hit = fn(transcript)
        corpus_blob = _search(config_path, neutral_queries[kid], repo_cwd)
        corpus_hit = fn(corpus_blob)
        if kid == "K10" and transcript_hit and _k10_wrong_property(corpus_blob):
            status = "wrong_property"
        elif transcript_hit and corpus_hit:
            status = "present_captured"
        elif transcript_hit and not corpus_hit:
            status = "present_capture_failed"
        elif not transcript_hit:
            status = "absent"
        else:
            status = "wrong_property"
        inventory["k"][kid] = {
            "role": role,
            "status": status,
            "transcript_hit": transcript_hit,
            "corpus_hit": corpus_hit,
        }
        if status != "present_captured":
            admissible = False
    inventory["admissible"] = admissible
    return inventory


def write_private_inventory(path: Path, transcript: str, admissibility: dict) -> None:
    """Extract opaque role markers for reviewer without publishing answer values in repo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "note": "private reviewer inventory — values not in git",
                "attempt": admissibility.get("attempt"),
                "admissible": admissibility.get("admissible"),
                "role_status": {k: v["status"] for k, v in admissibility.get("k", {}).items()},
                "transcript_length": len(transcript),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
