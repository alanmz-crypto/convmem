"""Producer-based document reconstruction (verified against current ingest paths)."""

from __future__ import annotations

import hashlib
from typing import Any

from eval_corpus import RECONSTRUCTION_SCHEMA_VERSION
from eval_corpus.classify import classify_source_path

RECIPE_ORDINARY = "ordinary_summary_keywords@v1"
RECIPE_INTER_MODEL = "inter_model_embed@v1"
RECIPE_GOVERNED = "ledger_unit_document@v1"

_MAX_INTER_SUMMARY = 500
_MAX_INTER_DOC = 8000


def select_recipe(unit: dict) -> str:
    """Producer-based discriminator — source classification must not decide recipe.

    ledger_id or ledger_kind → governed
    tool == \"inter-model\" → inter-model
    else → ordinary
    """
    ledger_id = str(unit.get("ledger_id") or "").strip()
    ledger_kind = str(unit.get("ledger_kind") or "").strip()
    if ledger_id or ledger_kind:
        return RECIPE_GOVERNED
    if str(unit.get("tool") or "") == "inter-model":
        return RECIPE_INTER_MODEL
    return RECIPE_ORDINARY


def reconstruct_document(unit: dict) -> str:
    recipe = select_recipe(unit)
    if recipe == RECIPE_GOVERNED:
        return _ledger_document(unit)
    if recipe == RECIPE_INTER_MODEL:
        return _inter_model_document(unit)
    return _ordinary_document(unit)


def _ordinary_document(unit: dict) -> str:
    summary = str(unit.get("summary") or "").strip()
    keywords = unit.get("keywords") or []
    kw = " ".join(str(k) for k in keywords if k)
    return f"{summary} {kw}".strip()


def _ledger_document(unit: dict) -> str:
    parts: list[str] = []
    summary = str(unit.get("summary") or "").strip()
    if summary:
        parts.append(summary)
    keywords = unit.get("keywords") or []
    if keywords:
        parts.append(" ".join(str(k) for k in keywords if k))
    rationale = str(unit.get("rationale") or "").strip()
    if rationale:
        parts.append(f"Rationale: {rationale}")
    return " ".join(p for p in parts if p).strip()


def _inter_model_document(unit: dict) -> str:
    title = str(unit.get("title") or "").strip()
    summary = str(unit.get("summary") or "").strip()
    if len(summary) > _MAX_INTER_SUMMARY:
        summary = summary[: _MAX_INTER_SUMMARY - 3] + "…"
    keywords = unit.get("keywords") or []
    kw = " ".join(str(k) for k in keywords if k)
    doc = f"{title} {summary} {kw}".strip()
    if len(doc) > _MAX_INTER_DOC:
        doc = doc[: _MAX_INTER_DOC - 1] + "…"
    return doc


def document_sha256(document: str) -> str:
    return hashlib.sha256(document.encode("utf-8")).hexdigest()


# Metadata keys written into shadow unit rows / fingerprint (ranking/filter inputs).
SHADOW_META_KEYS = (
    "title",
    "type",
    "keywords",
    "timestamp",
    "domain",
    "site",
    "tool",
    "source_path",
    "ledger_id",
    "ledger_kind",
    "confidence",
    "author_model",
    "verifier_model",
    "relates_to",
    "severity",
    "status",
    "result",
    "notes",
    "rationale",
)


def normalized_shadow_metadata(unit: dict) -> dict[str, Any]:
    """Normalize metadata for shadow rows and fingerprinting (omit absent optionals)."""
    out: dict[str, Any] = {}
    for key in SHADOW_META_KEYS:
        if key not in unit:
            continue
        val = unit.get(key)
        if val is None or val == "":
            continue
        if key == "keywords":
            if not val:
                continue
            out[key] = [str(k) for k in val]
        elif key == "confidence":
            try:
                out[key] = float(val)
            except (TypeError, ValueError):
                out[key] = val
        else:
            out[key] = val if not isinstance(val, (str, int, float, bool, list)) else val
            if isinstance(val, str):
                out[key] = val
    return out


def build_canonical_unit(unit: dict) -> dict[str, Any]:
    """Full canonical package unit (sorted keys applied at serialize time)."""
    document = reconstruct_document(unit)
    recipe = select_recipe(unit)
    meta = normalized_shadow_metadata(unit)
    uid = str(unit.get("id") or "").strip()
    row: dict[str, Any] = {
        "id": uid,
        "document": document,
        "document_sha256": document_sha256(document),
        "document_recipe_version": recipe,
        "reconstruction_schema_version": RECONSTRUCTION_SCHEMA_VERSION,
        "source_classification": classify_source_path(str(unit.get("source_path") or "")),
        "summary": str(unit.get("summary") or ""),
        "title": str(unit.get("title") or ""),
        "keywords": list(unit.get("keywords") or []),
        "source_path": str(unit.get("source_path") or ""),
    }
    row.update(meta)
    return row
