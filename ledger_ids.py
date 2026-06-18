"""Stable semantic ledger ids for tool-sourced observations.

Pattern: obs_<site>_<producer>_<audit_key>

Examples:
  obs_staging2_lh_csp-missing
  obs_staging2_wpsec_wp-version
  obs_staging2_wpsec_cookie-secure

No counters — ids are deterministic from site + producer + finding key.
"""

from __future__ import annotations

import re

_PRODUCERS = ("lh", "wpsec", "lighthouse", "wpscan", "nikto")


def site_short(site: str) -> str:
    """Short site slug for ledger ids (e.g. staging2.willowyhollow.com → staging2)."""
    site = site.strip().lower()
    site = site.replace("https://", "").replace("http://", "").split("/")[0]
    if not site:
        return "unknown"
    parts = site.split(".")
    if len(parts) >= 3:
        return parts[0]
    return site.replace(".", "_")


def audit_key(raw: str, *, max_len: int = 48) -> str:
    """Normalize an audit or finding name into a stable key segment."""
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s[:max_len] or "finding").strip("-")


def observation_id(site: str, producer: str, key: str) -> str:
    """Build a stable observation ledger id."""
    prod = producer.strip().lower()
    if prod in ("lighthouse", "lighthouse-ci", "lhci"):
        prod = "lh"
    elif prod in ("wp-sec-agent", "wpsec", "wpscan", "nikto", "nuclei"):
        prod = "wpsec"
    key_slug = audit_key(key)
    return f"obs_{site_short(site)}_{prod}_{key_slug}"


def wpsec_finding_key(tool: str, summary: str) -> str:
    """Map a wp-sec report line to a stable finding key."""
    s = summary.lower()
    tool = tool.lower().strip()

    if "wordpress version" in s or "wp version" in s:
        return "wp-version"
    if "directory listing" in s:
        return "directory-listing"
    if "content security policy" in s or "missing content security" in s:
        return "csp-missing"
    if "httponly" in s:
        return "cookie-httponly"
    if "secure flag" in s or "without the secure" in s:
        return "cookie-secure"
    if "x-content-type-options" in s:
        return "header-x-content-type-options"
    if "permissions-policy" in s:
        return "header-permissions-policy"
    if "strict-transport-security" in s or "hsts" in s:
        return "header-hsts"
    if "referrer-policy" in s:
        return "header-referrer-policy"
    if "security header" in s or "headers missing" in s:
        return "headers"
    if "waf detection" in s:
        return "waf-detection"
    if "cloudflare" in s:
        return "cloudflare-detected"
    if "alt-svc" in s or "http/3" in s:
        return "alt-svc-http3"

    return audit_key(f"{tool}-{summary}", max_len=48)
