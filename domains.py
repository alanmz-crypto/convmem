"""Domain taxonomy for knowledge units.

Domains let retrieval be scoped to a slice of the index ("just security
findings", "just hosting issues") instead of relying on free-text keyword
overlap alone. Stored as a single dotted-path string in Chroma metadata
(e.g. "web_stack.wordpress.plugins") so it stays a scalar metadata value —
Chroma metadata cannot hold lists.

This is intentionally a flat, editable list rather than a rigid enum class:
new domains are just new strings in DEFAULT_DOMAINS or the user's config.
Unknown domains are not rejected — they are recorded as-is so a slightly
different label from a model or tool doesn't silently vanish — but they are
flagged with `is_known_domain()` so `stats` can surface drift for cleanup.
"""

from __future__ import annotations

# Bootstrap taxonomy. Extend via [domains] allow_extra in config.toml, or
# just let new dotted paths flow through — they're tracked, not blocked.
DEFAULT_DOMAINS: list[str] = [
    "general",
    # --- coding / dev tooling (the original convmem corpus) ---
    "coding.frontend",
    "coding.backend",
    "coding.devops",
    "coding.ml",
    "coding.ml.hybrid_rag",
    "coding.ml.ollama",
    "coding.ml.rag",
    "coding.tooling",
    # --- website maintenance (the new use case) ---
    "web_stack.wordpress",
    "web_stack.wordpress.plugins",
    "web_stack.wordpress.themes",
    "web_stack.hosting",
    "web_stack.dns",
    "web_stack.ssl",
    "web_stack.security",
    "web_stack.js_runtime",
    "web_stack.api",
    "web_stack.performance",
    "web_stack.seo",
]

_SEP = "."


def normalize_domain(raw: str | None) -> str:
    """Lowercase, dot-joined, no leading/trailing/double dots. Empty -> 'general'."""
    if not raw or not isinstance(raw, str):
        return "general"
    cleaned = raw.strip().lower().replace("/", _SEP).replace(" ", "_")
    parts = [p for p in cleaned.split(_SEP) if p]
    return _SEP.join(parts) if parts else "general"


def is_known_domain(domain: str, extra: list[str] | None = None) -> bool:
    known = set(DEFAULT_DOMAINS) | set(extra or [])
    return domain in known


def domain_matches(unit_domain: str, query_domain: str) -> bool:
    """True if `unit_domain` is the query domain or a child of it.

    'web_stack.wordpress' matches units tagged exactly that, or
    'web_stack.wordpress.plugins', 'web_stack.wordpress.themes', etc.
    """
    if not query_domain:
        return True
    if unit_domain == query_domain:
        return True
    return unit_domain.startswith(query_domain + _SEP)


def domain_breadcrumb(domain: str) -> str:
    """Human-friendly rendering: 'web_stack.wordpress.plugins' -> 'web_stack › wordpress › plugins'."""
    if not domain:
        return "general"
    return " › ".join(domain.split(_SEP))
