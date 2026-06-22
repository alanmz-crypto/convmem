"""Site-scoped search helpers for --site on search/ask."""

from __future__ import annotations

from domains import domain_matches
from ledger_ids import site_short

# Domains commonly tagged on client-site ledger units (monitor, wpsec exports).
_SITE_SCOPED_DOMAINS = (
    "web_stack.security",
    "web_stack.wordpress",
)


def normalize_site(site: str) -> str:
    return site.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]


def unit_matches_site(meta: dict, site: str) -> bool:
    """True when metadata belongs to the given site hostname."""
    if not site:
        return True
    normalized = normalize_site(site)
    if not normalized:
        return True
    short = site_short(normalized)

    meta_site = (meta.get("site") or "").strip().lower()
    if meta_site:
        if meta_site == normalized or meta_site.startswith(f"{short}."):
            return True

    src = (meta.get("source_path") or "").lower()
    if src.startswith(f"site:{normalized}"):
        return True
    if normalized in src:
        return True
    if short and short in src:
        return True

    domain = (meta.get("domain") or "").strip()
    if domain and meta_site == normalized:
        return any(domain_matches(domain, d) for d in _SITE_SCOPED_DOMAINS)

    return False


def filter_results_by_site(results: list[dict], site: str | None) -> list[dict]:
    if not site:
        return results
    return [r for r in results if unit_matches_site(r.get("metadata") or {}, site)]
