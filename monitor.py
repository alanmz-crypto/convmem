"""HTTP security header monitor (F2b).

Probes staging2 (or any site) for header/TLS posture, then emits ledger
observations or low-confidence verifications per F2b-MONITOR-POLICY.md.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import requests

from ledger import build_ledger_index, find_related_units
from ledger_ids import observation_id, site_short

AUTHOR_MODEL = "convmem-monitor"
MONITOR_CONFIDENCE = 0.4
KIRO_MODEL = "kiro-review"
_LEGACY_SKIP = frozenset({"obs001"})


@dataclass(frozen=True)
class ProbeDef:
    key: str
    finding_key: str
    label: str
    match_terms: tuple[str, ...]
    check: Callable[[dict[str, str]], bool]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_site(site: str) -> str:
    return site.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]


def _header(headers: dict[str, str], name: str) -> str:
    for k, v in headers.items():
        if k.lower() == name.lower():
            return v
    return ""


def _check_csp(headers: dict[str, str]) -> bool:
    return bool(_header(headers, "Content-Security-Policy").strip())


def _check_hsts(headers: dict[str, str]) -> bool:
    return bool(_header(headers, "Strict-Transport-Security").strip())


def _check_xcto(headers: dict[str, str]) -> bool:
    return "nosniff" in _header(headers, "X-Content-Type-Options").lower()


def _check_referrer(headers: dict[str, str]) -> bool:
    return bool(_header(headers, "Referrer-Policy").strip())


PROBES: tuple[ProbeDef, ...] = (
    ProbeDef(
        "csp",
        "csp-missing",
        "Content-Security-Policy",
        ("content security policy", "csp"),
        _check_csp,
    ),
    ProbeDef(
        "hsts",
        "header-hsts",
        "Strict-Transport-Security",
        ("strict-transport-security", "hsts"),
        _check_hsts,
    ),
    ProbeDef(
        "x-content-type-options",
        "header-x-content-type-options",
        "X-Content-Type-Options",
        ("x-content-type-options", "nosniff"),
        _check_xcto,
    ),
    ProbeDef(
        "referrer-policy",
        "header-referrer-policy",
        "Referrer-Policy",
        ("referrer-policy",),
        _check_referrer,
    ),
)


def _kind(meta: dict) -> str:
    return (meta.get("ledger_kind") or meta.get("type") or "").strip().lower()


def _site_matches(meta: dict, site: str) -> bool:
    normalized = _normalize_site(site)
    short = site_short(site)
    meta_site = (meta.get("site") or "").strip().lower()
    lid = (meta.get("ledger_id") or "").lower()
    if meta_site and (meta_site == normalized or meta_site.startswith(short)):
        return True
    if lid.startswith(f"obs_{short}_"):
        return True
    slug = normalized.replace(".", "_")
    if slug and f"obs_{slug}_" in lid:
        return True
    return False


def find_anchor_observation(
    by_ledger_id: dict[str, dict],
    *,
    site: str,
    probe: ProbeDef,
) -> str | None:
    """Resolve scanner-owned observation ledger_id for a probe (never obs001)."""
    canonical = observation_id(site, "wpsec", probe.finding_key)
    meta = by_ledger_id.get(canonical)
    if meta is not None and _kind(meta) == "observation":
        return canonical

    if probe.key == "csp":
        lh = observation_id(site, "lh", "csp-xss")
        lh_meta = by_ledger_id.get(lh)
        if lh_meta is not None and _kind(lh_meta) == "observation":
            return lh

    candidates: list[tuple[str, dict]] = []
    for lid, row in by_ledger_id.items():
        if lid in _LEGACY_SKIP:
            continue
        if _kind(row) != "observation":
            continue
        if not _site_matches(row, site):
            continue
        hay = f"{row.get('title', '')} {row.get('summary', '')} {lid}".lower()
        if any(term in hay for term in probe.match_terms):
            candidates.append((lid, row))

    if not candidates:
        return None

    def rank(item: tuple[str, dict]) -> tuple:
        lid, _ = item
        return (
            0 if "wpsec" in lid else 1,
            0 if "willowyhollow_com" in lid else 1,
            lid,
        )

    candidates.sort(key=rank)
    return candidates[0][0]


def has_kiro_verification(
    store,
    relates_to: str,
    *,
    by_relates_to: dict[str, list[dict]] | None = None,
) -> bool:
    """True if Kiro already verified this observation (never supersede).

    Pass ``by_relates_to`` from ``build_ledger_index`` when calling in a loop
    to avoid a full metadata re-scan per probe (timer/cron at scale).
    """
    if by_relates_to is not None:
        related = by_relates_to.get(relates_to, [])
    else:
        related = find_related_units(store, relates_to)
    for meta in related:
        if _kind(meta) != "verification":
            continue
        if meta.get("author_model") == KIRO_MODEL:
            return True
        if meta.get("verifier_model") == KIRO_MODEL:
            return True
    return False


def fetch_https_headers(
    site: str,
    *,
    session: requests.Session | None = None,
    timeout: float = 20.0,
) -> tuple[dict[str, str], str | None]:
    url = f"https://{_normalize_site(site)}/"
    sess = session or requests.Session()
    try:
        resp = sess.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": "convmem-monitor/1.0"},
        )
        return dict(resp.headers), None
    except requests.RequestException as exc:
        return {}, str(exc)


def check_tls_redirect(
    site: str,
    *,
    session: requests.Session | None = None,
    timeout: float = 20.0,
) -> bool:
    url = f"http://{_normalize_site(site)}/"
    sess = session or requests.Session()
    try:
        resp = sess.get(
            url,
            timeout=timeout,
            allow_redirects=False,
            headers={"User-Agent": "convmem-monitor/1.0"},
        )
    except requests.RequestException:
        return False
    if resp.status_code not in (301, 302, 303, 307, 308):
        return False
    location = (resp.headers.get("Location") or "").strip()
    return location.lower().startswith("https://")


def _observation_record(
    *,
    site: str,
    probe: ProbeDef,
    passed: bool,
    headers: dict[str, str],
    fetch_error: str | None,
) -> dict:
    normalized = _normalize_site(site)
    ledger_id = observation_id(site, "monitor", probe.finding_key)
    if passed:
        summary = (
            f"{probe.label} present on {normalized} "
            f"(convmem-monitor probe {probe.key})"
        )
        severity = "info"
    else:
        summary = (
            f"{probe.label} absent or failed on {normalized} "
            f"(convmem-monitor probe {probe.key})"
        )
        severity = "medium"
    if fetch_error:
        summary = f"{summary}; fetch error: {fetch_error}"

    evidence: dict[str, Any] = {"probe": probe.key, "passed": passed}
    if fetch_error:
        evidence["fetch_error"] = fetch_error
    else:
        evidence["header_value"] = _header(headers, probe.label) or None

    return {
        "id": ledger_id,
        "kind": "observation",
        "domain": "web_stack.security",
        "author_model": AUTHOR_MODEL,
        "site": normalized,
        "severity": severity,
        "summary": summary,
        "tool": AUTHOR_MODEL,
        "source_path": f"https://{normalized}/",
        "timestamp": _now_iso(),
        "confidence": MONITOR_CONFIDENCE,
        "evidence": evidence,
    }


def _verification_record(
    *,
    site: str,
    probe: ProbeDef,
    relates_to: str,
    passed: bool,
    headers: dict[str, str],
    fetch_error: str | None,
) -> dict:
    normalized = _normalize_site(site)
    result = "pass" if passed else "fail"
    state = "present" if passed else "still absent"
    summary = (
        f"{probe.label} {state} on {normalized} "
        f"(monitor re-check of {relates_to})"
    )
    if fetch_error:
        summary = f"{summary}; fetch error: {fetch_error}"

    ver_id = f"ver_{site_short(site)}_mon_{probe.key}"
    evidence: dict[str, Any] = {"probe": probe.key, "passed": passed}
    if fetch_error:
        evidence["fetch_error"] = fetch_error

    return {
        "id": ver_id,
        "kind": "verification",
        "domain": "web_stack.security",
        "author_model": AUTHOR_MODEL,
        "relates_to": relates_to,
        "result": result,
        "site": normalized,
        "summary": summary,
        "tool": AUTHOR_MODEL,
        "source_path": f"https://{normalized}/",
        "timestamp": _now_iso(),
        "confidence": MONITOR_CONFIDENCE,
        "evidence": evidence,
    }


def _tls_observation(site: str, passed: bool) -> dict:
    normalized = _normalize_site(site)
    ledger_id = observation_id(site, "monitor", "tls-redirect")
    summary = (
        f"HTTP→HTTPS redirect {'working' if passed else 'missing'} on {normalized}"
    )
    return {
        "id": ledger_id,
        "kind": "observation",
        "domain": "web_stack.security",
        "author_model": AUTHOR_MODEL,
        "site": normalized,
        "severity": "info" if passed else "medium",
        "summary": summary,
        "tool": AUTHOR_MODEL,
        "source_path": f"http://{normalized}/",
        "timestamp": _now_iso(),
        "confidence": MONITOR_CONFIDENCE,
        "evidence": {"probe": "tls-redirect", "passed": passed},
    }


def _tls_verification(site: str, relates_to: str, passed: bool) -> dict:
    normalized = _normalize_site(site)
    result = "pass" if passed else "fail"
    return {
        "id": f"ver_{site_short(site)}_mon_tls-redirect",
        "kind": "verification",
        "domain": "web_stack.security",
        "author_model": AUTHOR_MODEL,
        "relates_to": relates_to,
        "result": result,
        "site": normalized,
        "summary": (
            f"TLS redirect re-check on {normalized}: {result} "
            f"(monitor → {relates_to})"
        ),
        "tool": AUTHOR_MODEL,
        "source_path": f"http://{normalized}/",
        "timestamp": _now_iso(),
        "confidence": MONITOR_CONFIDENCE,
        "evidence": {"probe": "tls-redirect", "passed": passed},
    }


def run_monitor(
    store,
    *,
    site: str,
    embed_model: str,
    ollama_host: str,
    units_export=None,
    dry_run: bool = False,
    verbose: bool = True,
    session: requests.Session | None = None,
) -> dict:
    from observe import ingest_observation

    stats = {
        "observations": 0,
        "verifications": 0,
        "skipped_kiro": 0,
        "errors": 0,
        "dry_run": dry_run,
    }

    headers, fetch_error = fetch_https_headers(site, session=session)
    if fetch_error and verbose:
        print(f"[monitor] warning: HTTPS fetch failed: {fetch_error}", file=sys.stderr)

    by_ledger_id, by_relates_to = build_ledger_index(store)
    by_ledger_id_after = dict(by_ledger_id)

    for probe in PROBES:
        passed = probe.check(headers) if not fetch_error else False
        anchor = find_anchor_observation(by_ledger_id_after, site=site, probe=probe)

        if anchor:
            if has_kiro_verification(store, anchor, by_relates_to=by_relates_to):
                stats["skipped_kiro"] += 1
                if verbose:
                    print(
                        f"[monitor] skipping — Kiro verification exists for {anchor}",
                        file=sys.stderr,
                    )
                continue
            record = _verification_record(
                site=site,
                probe=probe,
                relates_to=anchor,
                passed=passed,
                headers=headers,
                fetch_error=fetch_error,
            )
            if dry_run:
                stats["verifications"] += 1
                if verbose:
                    print(f"[monitor] dry-run verification → {anchor} {record['result']}")
                continue
            unit = ingest_observation(
                record,
                store=store,
                embed_model=embed_model,
                ollama_host=ollama_host,
                min_confidence=0.0,
                units_export=units_export,
                upsert=True,
                by_ledger_id=by_ledger_id_after,
            )
            if unit:
                stats["verifications"] += 1
                lid = record["id"]
                by_ledger_id_after[lid] = {
                    **unit,
                    "id": unit["id"],
                    "ledger_id": lid,
                    "ledger_kind": "verification",
                }
                if verbose:
                    print(
                        f"[monitor] verification {record['result']} → {anchor} ({probe.key})",
                        file=sys.stderr,
                    )
            else:
                stats["errors"] += 1
        else:
            record = _observation_record(
                site=site,
                probe=probe,
                passed=passed,
                headers=headers,
                fetch_error=fetch_error,
            )
            if dry_run:
                stats["observations"] += 1
                if verbose:
                    print(f"[monitor] dry-run observation {record['id']}")
                continue
            unit = ingest_observation(
                record,
                store=store,
                embed_model=embed_model,
                ollama_host=ollama_host,
                min_confidence=0.0,
                units_export=units_export,
                upsert=True,
                by_ledger_id=by_ledger_id_after,
            )
            if unit:
                stats["observations"] += 1
                lid = record["id"]
                by_ledger_id_after[lid] = {
                    **unit,
                    "id": unit["id"],
                    "ledger_id": lid,
                    "ledger_kind": "observation",
                }
                if verbose:
                    print(f"[monitor] observation {record['id']} ({probe.key})")
            else:
                stats["errors"] += 1

    tls_probe = ProbeDef(
        "tls-redirect",
        "tls-redirect",
        "TLS redirect",
        ("tls", "redirect", "https"),
        lambda _h: False,
    )
    tls_passed = check_tls_redirect(site, session=session)
    tls_anchor = find_anchor_observation(by_ledger_id_after, site=site, probe=tls_probe)

    if tls_anchor:
        if has_kiro_verification(store, tls_anchor, by_relates_to=by_relates_to):
            stats["skipped_kiro"] += 1
            if verbose:
                print(
                    f"[monitor] skipping — Kiro verification exists for {tls_anchor}",
                    file=sys.stderr,
                )
        else:
            record = _tls_verification(site, tls_anchor, tls_passed)
            if dry_run:
                stats["verifications"] += 1
            else:
                unit = ingest_observation(
                    record,
                    store=store,
                    embed_model=embed_model,
                    ollama_host=ollama_host,
                    min_confidence=0.0,
                    units_export=units_export,
                    upsert=True,
                    by_ledger_id=by_ledger_id_after,
                )
                if unit:
                    stats["verifications"] += 1
                    if verbose:
                        print(
                            f"[monitor] verification {record['result']} → {tls_anchor} (tls)"
                        )
                else:
                    stats["errors"] += 1
    else:
        record = _tls_observation(site, tls_passed)
        if dry_run:
            stats["observations"] += 1
        else:
            unit = ingest_observation(
                record,
                store=store,
                embed_model=embed_model,
                ollama_host=ollama_host,
                min_confidence=0.0,
                units_export=units_export,
                upsert=True,
                by_ledger_id=by_ledger_id_after,
            )
            if unit:
                stats["observations"] += 1
                if verbose:
                    print(f"[monitor] observation {record['id']} (tls)")
            else:
                stats["errors"] += 1

    return stats
