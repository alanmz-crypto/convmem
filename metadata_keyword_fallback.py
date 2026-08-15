"""Keyword metadata fallback for mediated Chroma serving paths."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from chroma_readonly import collection_metadata_rows
from chroma_store import is_superseded
from config import load_config
from domains import domain_matches, normalize_domain
from site_filter import filter_results_by_site, normalize_site

MediatedFallbackFn = Callable[..., list[dict[str, Any]]]


def keyword_metadata_search_rows(
    chroma_dir: str,
    collection_name: str,
    text: str,
    top_k: int,
    *,
    domain: str | None = None,
    site: str | None = None,
) -> list[dict[str, Any]]:
    """Keyword scan over collection metadata rows (mediated fallback path)."""

    from query import _keyword_score, _unit_domain

    domain_norm = normalize_domain(domain) if domain else None
    site_norm = normalize_site(site) if site else None
    rows = collection_metadata_rows(chroma_dir, collection_name)
    results: list[dict[str, Any]] = []
    for meta in rows:
        if collection_name == "knowledge_units" and is_superseded(meta):
            continue
        if site_norm and not filter_results_by_site([{"metadata": meta}], site_norm):
            continue
        if domain_norm:
            unit_domain = _unit_domain(meta)
            if unit_domain is None or not domain_matches(unit_domain, domain_norm):
                continue
        score = _keyword_score(text, meta)
        if score <= 0:
            continue
        results.append(
            {
                "id": meta.get("id", ""),
                "metadata": meta,
                "document": meta.get("document") or meta.get("title") or "",
                "score": round(min(score / 6.0, 0.99), 4),
            }
        )

    results.sort(
        key=lambda r: (
            r.get("score", 0.0),
            len(str(r.get("metadata", {}).get("title", ""))),
        ),
        reverse=True,
    )
    return results[:top_k]


def run_keyword_fallback(
    collection_name: str,
    text: str,
    top_k: int,
    *,
    domain: str | None = None,
    site: str | None = None,
    cfg: Mapping[str, Any] | None = None,
    mediated: MediatedFallbackFn | None = None,
) -> list[dict[str, Any]]:
    if mediated is not None:
        return mediated(
            collection_name,
            text,
            top_k,
            domain=domain,
            site=site,
            cfg=dict(cfg or {}),
        )
    if cfg is None:
        cfg = load_config()
    return keyword_metadata_search_rows(
        str(cfg["index"]["chroma_dir"]),
        collection_name,
        text,
        top_k,
        domain=domain,
        site=site,
    )
