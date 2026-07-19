"""Query layer.

Primary: knowledge_units (Step 5+).
Fallback: conversation_summaries via --raw (Step 4).
Reranking: Step 6 (query_units only).
"""

from __future__ import annotations

import json
import sys
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from chroma_store import ChromaStore, is_superseded, open_chroma_for_read
from chroma_readonly import collection_metadata_rows
from config import load_config
from domains import domain_breadcrumb, domain_matches, is_known_domain, normalize_domain
from llm import ollama_embed
from meta_format import when_from_meta
from open_source import resolve_open_target
from site_filter import filter_results_by_site, normalize_site

# ---------------------------------------------------------------------------
# Query logic (unchanged)
# ---------------------------------------------------------------------------

_LEDGER_ID_RE = re.compile(
    r"\b(dec_prop_\d{8}_\d{6}_[0-9a-f]{4}|obs_[a-z0-9_-]+|ver_[a-z0-9_-]+)\b",
    re.IGNORECASE,
)
DEFAULT_RERANK_MODEL = "BAAI/bge-reranker-v2-m3"


@dataclass
class QueryUnitTrace:
    """Optional stage snapshots for callers that need retrieval diagnostics."""

    candidates: list[dict] = field(default_factory=list)
    reranked: list[dict] = field(default_factory=list)


def _unit_domain(meta: dict) -> str | None:
    """Return tagged domain, or None for pre-Step-8 units without domain metadata."""
    raw = meta.get("domain")
    if raw is None or raw == "":
        return None
    return str(raw)


_SEARCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "but",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "what",
    "whats",
    "where",
    "with",
}


def _search_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9._:/-]*", text.lower())
    return [tok for tok in tokens if tok not in _SEARCH_STOPWORDS]


def _search_blob(meta: dict) -> str:
    parts = [
        meta.get("title", ""),
        meta.get("document", ""),
        meta.get("ledger_id", ""),
        meta.get("domain", ""),
        meta.get("site", ""),
        meta.get("source_path", ""),
        meta.get("tool", ""),
        meta.get("type", ""),
        meta.get("status", ""),
        meta.get("result", ""),
        meta.get("notes", ""),
        meta.get("rationale", ""),
        meta.get("relates_to", ""),
        meta.get("summary", ""),
        meta.get("source_type", ""),
        meta.get("workspace_directory", ""),
        meta.get("conversation_id", ""),
    ]
    return " ".join(str(part) for part in parts if part)


def _keyword_score(query: str, meta: dict) -> float:
    q = query.lower().strip()
    blob = _search_blob(meta).lower()
    tokens = _search_tokens(q)
    if not tokens and q:
        tokens = [q]

    score = 0.0
    if q and q in blob:
        score += 3.0
    for tok in dict.fromkeys(tokens):
        if tok in blob:
            score += 1.0
            if tok in str(meta.get("title", "")).lower():
                score += 0.5
            if tok in str(meta.get("ledger_id", "")).lower():
                score += 1.5
            if tok in str(meta.get("source_path", "")).lower():
                score += 0.5
            if tok in str(meta.get("domain", "")).lower():
                score += 0.5
            if tok in str(meta.get("site", "")).lower():
                score += 0.5
    return score


def _fallback_query_rows(
    collection_name: str,
    text: str,
    top_k: int,
    *,
    domain: str | None = None,
    site: str | None = None,
    cfg: dict | None = None,
) -> list[dict]:
    if cfg is None:
        cfg = load_config()
    chroma_dir = cfg["index"]["chroma_dir"]
    domain_norm = normalize_domain(domain) if domain else None
    site_norm = normalize_site(site) if site else None

    rows = collection_metadata_rows(chroma_dir, collection_name)
    results: list[dict] = []
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


def _extract_ledger_ids(text: str) -> list[str]:
    return list(dict.fromkeys(_LEDGER_ID_RE.findall(text)))


def _result_dedupe_key(r: dict) -> str:
    meta = r.get("metadata") or {}
    lid = (meta.get("ledger_id") or "").strip()
    if lid:
        return f"ledger:{lid}"
    return f"id:{r.get('id', '')}"


def _merge_priority_hits(primary: list[dict], extras: list[dict]) -> list[dict]:
    """Prepend exact ledger / anchor hits; dedupe by ledger id or chroma id."""
    seen: set[str] = set()
    merged: list[dict] = []
    for r in extras + primary:
        key = _result_dedupe_key(r)
        if key in seen:
            continue
        seen.add(key)
        merged.append(r)
    return merged


def _ledger_lookup_hits(cfg: dict, store, query: str) -> list[dict]:
    """Exact ledger id lookup + protocol fallback anchor from approved JSONL."""
    from ledger import find_unit_by_ledger_id
    from ledger_recent import (
        PROTOCOL_FALLBACK_LEDGER_ID,
        approved_decision_hit,
        is_protocol_anchor_query,
    )

    hits: list[dict] = []
    seen: set[str] = set()

    def _add(hit: dict | None) -> None:
        if not hit:
            return
        lid = ((hit.get("metadata") or {}).get("ledger_id") or "").strip()
        if lid and lid in seen:
            return
        if lid:
            seen.add(lid)
        hits.append(hit)

    for lid in _extract_ledger_ids(query):
        unit = find_unit_by_ledger_id(store, lid) if store is not None else None
        if unit:
            meta = unit.get("metadata") or {}
            doc = (unit.get("document") or "").strip()
            if not doc:
                enriched = approved_decision_hit(cfg, lid)
                if enriched:
                    _add(enriched)
                    continue
            _add(
                {
                    "id": unit.get("id", ""),
                    "metadata": meta,
                    "document": doc or meta.get("title") or "",
                    "score": 0.99,
                    "rank_score": 0.99,
                    "ledger_lookup": True,
                }
            )
        else:
            _add(approved_decision_hit(cfg, lid))

    if is_protocol_anchor_query(query):
        _add(approved_decision_hit(cfg, PROTOCOL_FALLBACK_LEDGER_ID))

    return hits


def _apply_keyword_rank(text: str, results: list[dict]) -> list[dict]:
    """Blend a small lexical boost into semantic ranking.

    Chroma embeddings are good at broad recall, but golden search queries in
    this repo often hinge on a crisp phrase or page title. Add a modest keyword
    component so exact lexical anchors bubble up without replacing semantic
    ranking entirely.
    """
    if not results:
        return results

    scored: list[tuple[float, int, dict]] = []
    for i, r in enumerate(results):
        meta = r.get("metadata") or {}
        base = r.get("rank_score")
        if base is None:
            base = r.get("score")
        if base is None:
            base = 0.0
        kw = _keyword_score(text, meta)
        out = dict(r)
        out["keyword_boost"] = round(kw, 4)
        out["rank_score"] = round(float(base) + (kw * 0.02), 4)
        scored.append((out["rank_score"], i, out))

    scored.sort(key=lambda t: (-t[0], t[1]))
    return [r for _, _, r in scored]


def _resolve_eval_retrieval_view(
    eval_view: str | None,
    cfg: dict,
) -> str | None:
    """Return evaluation view name or None for production default.

    Evaluation-scoped only. Production callers leave eval_view unset and omit
    cfg['eval']['retrieval_view'], preserving full ledger-priority behavior.
    """
    if eval_view is not None:
        view = str(eval_view).strip() or None
    else:
        view = str((cfg.get("eval") or {}).get("retrieval_view") or "").strip() or None
    if view is None:
        return None
    allowed = {
        "embedding_influenced",
        "operational_pipeline",
        # synonyms accepted for clarity
        "embedding-influenced",
        "operational-pipeline",
    }
    if view not in allowed:
        raise ValueError(
            f"unknown eval retrieval_view {view!r}; "
            "expected embedding_influenced or operational_pipeline"
        )
    return view.replace("-", "_")


def query_units(
    text: str,
    top_k: int = 5,
    domain: str | None = None,
    site: str | None = None,
    chroma_dir: str | None = None,
    *,
    cfg: dict | None = None,
    eval_view: str | None = None,
    retrieval_trace: QueryUnitTrace | None = None,
) -> list[dict]:
    if cfg is None:
        cfg = load_config()
    models = cfg["models"]
    qcfg = cfg.get("query", {})
    chroma_path = chroma_dir or cfg["index"]["chroma_dir"]
    view = _resolve_eval_retrieval_view(eval_view, cfg)
    # embedding_influenced: keyword/recency/rerank remain; ledger-priority path off
    skip_ledger_priority = view == "embedding_influenced"

    embedding = ollama_embed(
        text, model=models["embed_model"], host=models["ollama_host"]
    )

    candidate_k = max(top_k, int(qcfg.get("top_k_candidates", 20) or 20))
    n_fetch = candidate_k
    domain = normalize_domain(domain) if domain else None
    site_norm = normalize_site(site) if site else None
    if domain or site_norm:
        # Domain filtering is hierarchical (parent matches children), which
        # Chroma's exact-match `where` can't express, so over-fetch and
        # filter client-side before reranking/truncating.
        n_fetch = candidate_k * 3

    ledger_extras: list[dict] = []
    try:
        store = open_chroma_for_read(chroma_path)
        try:
            results = store.query_units(embedding, n_fetch)
            if not skip_ledger_priority:
                ledger_extras = _ledger_lookup_hits(cfg, store, text)
        finally:
            store.close()
        if site_norm:
            results = filter_results_by_site(results, site_norm)
        if domain:
            results = [
                r for r in results
                if (ud := _unit_domain(r.get("metadata", {}))) is not None
                and domain_matches(ud, domain)
            ]
    except Exception:
        results = _fallback_query_rows(
            "knowledge_units",
            text,
            n_fetch,
            domain=domain,
            site=site,
            cfg=cfg,
        )
        if not skip_ledger_priority:
            ledger_extras = _ledger_lookup_hits(cfg, None, text)
    for r in results:
        d = r.get("distance")
        if d is not None:
            r["score"] = round(1.0 - d, 4)
    for rank, result in enumerate(results, 1):
        result["semantic_rank"] = rank

    if retrieval_trace is not None:
        retrieval_trace.candidates = [dict(result) for result in results[:candidate_k]]

    rw = float(qcfg.get("recency_weight", 0.0) or 0.0)
    rhl = float(qcfg.get("recency_half_life_days", 30.0))
    if rw > 0 and results:
        from evidence import apply_recency_rerank

        results = apply_recency_rerank(
            results, recency_weight=rw, recency_half_life_days=rhl
        )

    results = _apply_keyword_rank(text, results)
    if results:
        from rerank import rerank as rerank_fn

        model_name = str(models.get("rerank_model") or DEFAULT_RERANK_MODEL).strip()
        results = rerank_fn(text, results[:candidate_k], model_name, top_k)
    if retrieval_trace is not None:
        retrieval_trace.reranked = [dict(result) for result in results]

    if not skip_ledger_priority:
        results = _merge_priority_hits(results, ledger_extras)
    return results[:top_k]


def query_raw(
    text: str,
    top_k: int = 5,
    site: str | None = None,
    *,
    cfg: dict | None = None,
) -> list[dict]:
    if cfg is None:
        cfg = load_config()
    models = cfg["models"]

    embedding = ollama_embed(
        text, model=models["embed_model"], host=models["ollama_host"]
    )
    site_norm = normalize_site(site) if site else None
    n_fetch = top_k * 3 if site_norm else top_k
    try:
        store = open_chroma_for_read(cfg["index"]["chroma_dir"])
        try:
            results = store.query_summaries(embedding, n_fetch)
        finally:
            store.close()
        if site_norm:
            results = filter_results_by_site(results, site_norm)
    except Exception:
        results = _fallback_query_rows(
            "conversation_summaries",
            text,
            n_fetch,
            site=site,
            cfg=cfg,
        )
    for r in results:
        d = r.get("distance")
        if d is not None:
            r["score"] = round(1.0 - d, 4)
    return results[:top_k]


# ---------------------------------------------------------------------------
# Rich display (Step 7) — formatting only, no retrieval logic
# ---------------------------------------------------------------------------

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console()
err_console = Console(stderr=True)


def _parse_dt(raw: str) -> datetime | None:
    try:
        if len(raw) >= 19:
            return datetime.fromisoformat(raw.replace(" ", "T")[:19]).replace(
                tzinfo=timezone.utc
            )
        if len(raw) >= 10:
            return datetime.strptime(raw[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return None


def when_relative(meta: dict) -> str:
    """Relative date for search panels (e.g. '1 week ago')."""
    raw = when_from_meta(meta)
    if not raw:
        return "—"
    dt = _parse_dt(raw)
    if dt is None:
        return raw[:10]
    days = (datetime.now(timezone.utc) - dt).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 14:
        return "1 week ago"
    if days < 30:
        weeks = days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    if days < 365:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    return dt.strftime("%b %d")


def when_short(meta: dict) -> str:
    """Short date for citations (e.g. 'Jun 5')."""
    raw = when_from_meta(meta)
    if not raw:
        return "—"
    dt = _parse_dt(raw)
    if dt is None:
        return raw[:10]
    return dt.strftime("%b %-d") if sys.platform != "win32" else dt.strftime("%b %d")


def render_warning(message: str) -> None:
    err_console.print(
        Panel(message, title="Warning", border_style="yellow", expand=False)
    )


def render_error(message: str) -> None:
    err_console.print(Panel(message, title="Error", border_style="red", expand=False))


def _score_text(score: float | None) -> Text:
    t = Text()
    if score is None:
        t.append("n/a", style="dim")
    else:
        t.append(f"{score:.3f}", style="bold bright_green")
    return t


def _open_text(meta: dict) -> Text:
    line = resolve_open_target(meta).format_line()
    if line.startswith("Open: "):
        line = line[6:]
    t = Text()
    t.append("Open: ", style="dim")
    t.append(line, style="blue underline")
    return t


def _panel_title(
    n: int, score: float | None, meta: dict, *, units: bool, result: dict | None = None
) -> Text:
    t = Text()
    t.append(f"[{n}]  ", style="bold")
    display_score = None
    if result:
        display_score = result.get("rank_score", result.get("score"))
    else:
        display_score = score
    t.append_text(_score_text(display_score))
    rboost = (result or {}).get("recency_boost")
    if rboost:
        t.append(f" +{rboost:.3f}rec", style="dim cyan")
    t.append(" ─ ", style="dim")
    if units:
        t.append(meta.get("type", "?"), style="dim cyan")
        t.append(" · ", style="dim")
        t.append(meta.get("tool", "?"), style="dim cyan")
        t.append(" · ", style="dim")
        t.append(when_relative(meta), style="dim cyan")
    else:
        t.append(meta.get("tool", "?"), style="dim cyan")
        t.append(" · ", style="dim")
        t.append(when_relative(meta), style="dim cyan")
        start = meta.get("start_offset")
        end = meta.get("end_offset")
        if start is not None and end is not None:
            t.append(f" · msgs {start}–{end}", style="dim cyan")
    return t


def _attribution_text(meta: dict) -> Text | None:
    """Domain + author/verifier + ledger links — secondary metadata, dim styling."""
    domain = meta.get("domain")
    author = meta.get("author_model")
    kind = meta.get("ledger_kind")
    relates = meta.get("relates_to")
    site = meta.get("site")
    severity = meta.get("severity")
    if not any((domain, author, kind, relates, site, severity)):
        return None
    t = Text()
    if kind:
        t.append(kind, style="dim cyan")
        t.append("  ·  ", style="dim")
    if domain:
        t.append(domain_breadcrumb(domain), style="dim magenta")
    if site:
        t.append("  ·  ", style="dim")
        t.append(site, style="dim")
    if severity:
        t.append(f"  ·  {severity}", style="dim yellow")
    if author:
        t.append("  ·  ", style="dim")
        t.append(f"by {author}", style="dim")
        verifier = meta.get("verifier_model")
        if verifier:
            t.append(f"  (verified by {verifier})", style="dim green")
    if relates:
        t.append("  ·  ", style="dim")
        t.append(f"→ {relates}", style="dim")
    return t


def _result_body(r: dict, meta: dict, *, units: bool) -> Group:
    doc = (r.get("document") or "").strip()
    title = meta.get("title", "").strip() if units else ""
    if not title and units:
        title = doc.split(".")[0][:80] if doc else "Untitled"
    if not units and not title:
        title = "Conversation summary"

    parts: list = []
    if title:
        parts.append(Text(title, style="bold white"))
        parts.append(Text(""))
    if doc:
        parts.append(Text(doc, overflow="fold"))
        parts.append(Text(""))
    if units:
        attribution = _attribution_text(meta)
        if attribution:
            parts.append(attribution)
    src = meta.get("source_path", "")
    if src:
        parts.append(Text(src, style="dim"))
    if units and (r.get("id") or meta.get("ledger_id")):
        lid = meta.get("ledger_id") or r.get("id")
        parts.append(Text(f"ledger: {lid}", style="dim"))
        if meta.get("ledger_id") and r.get("id"):
            parts.append(Text(f"chroma: {r['id']}", style="dim"))
    parts.append(_open_text(meta))
    return Group(*parts)


def render_search_results(results: list[dict], *, units: bool = True) -> None:
    """Print search hits as numbered Rich panels."""
    if not results:
        render_warning("No results found.")
        return
    for i, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        panel = Panel(
            _result_body(r, meta, units=units),
            title=_panel_title(i, r.get("score"), meta, units=units, result=r),
            title_align="left",
            border_style="bright_black",
            padding=(0, 1),
        )
        console.print(panel)
        if i < len(results):
            console.print()


def _citation_block(c: dict) -> Group:
    score = c.get("score")
    score_s = f"{score:.3f}" if score is not None else "n/a"
    header = Text()
    header.append(f"[{c['n']}] ", style="bold")
    header.append(score_s, style="bold bright_green")
    ev = c.get("evidence_status")
    if ev:
        header.append(" · ", style="dim")
        header.append(ev.replace("_", " "), style="bold yellow")
    header.append("  ", style="")
    if c.get("title"):
        header.append(c.get("type", "?"), style="dim cyan")
        header.append(" · ", style="dim")
        header.append(c.get("tool", "?"), style="dim cyan")
        header.append(" · ", style="dim")
        header.append(when_short({"timestamp": c.get("when"), "date": c.get("when")}), style="dim cyan")
    else:
        header.append(c.get("tool", "?"), style="dim cyan")
        header.append(" · ", style="dim")
        header.append(when_short({"timestamp": c.get("when"), "date": c.get("when")}), style="dim cyan")
        if c.get("start_offset") is not None:
            header.append(
                f" · msgs {c.get('start_offset')}–{c.get('end_offset')}",
                style="dim cyan",
            )

    parts: list = [header, Text("")]
    if c.get("title"):
        parts.append(Text(c["title"], style="bold white"))
        parts.append(Text(""))
    attribution = _attribution_text(
        {
            "domain": c.get("domain"),
            "author_model": c.get("author_model"),
            "verifier_model": c.get("verifier_model"),
            "ledger_kind": c.get("ledger_kind"),
            "relates_to": c.get("relates_to"),
            "site": c.get("site"),
            "severity": c.get("severity"),
        }
    )
    if attribution:
        parts.append(attribution)
    src = c.get("source_path", "")
    if src:
        parts.append(Text(src, style="dim"))
    lid = c.get("ledger_id") or c.get("id")
    if lid:
        parts.append(Text(f"ledger: {lid}", style="dim"))
    open_meta = {
        "source_path": c.get("source_path"),
        "tool": c.get("tool"),
        "start_offset": c.get("start_offset"),
        "conversation_id": c.get("conversation_id"),
        "session_id": c.get("session_id"),
    }
    parts.append(_open_text(open_meta))
    return Group(*parts)


def render_ask_output(out: dict, *, show_search: bool = False) -> None:
    """Print ask answer + citations with visual separation."""
    if out.get("warning"):
        render_warning(out["warning"])
    rq = out.get("retrieval_query")
    if show_search and rq:
        err_console.print(Text(f"Search: {rq}", style="dim cyan"))

    answer = out.get("answer", "")
    console.print(
        Panel(
            Text(answer, overflow="fold"),
            title="Answer",
            border_style="blue",
            padding=(1, 2),
        )
    )

    citations = out.get("citations") or []
    if not citations:
        return

    console.print()
    console.print(Rule("References", style="dim"))
    console.print()
    for i, c in enumerate(citations):
        console.print(_citation_block(c))
        if i < len(citations) - 1:
            console.print()
            console.print(Rule(style="bright_black"))


def _coverage_counts(cfg: dict) -> tuple[int, int, int, int]:
    from adapters.detect import detect_format, get_parser
    from ingest import sha256_file

    inv_path = Path(
        cfg.get("sources", {}).get("inventory")
        or "~/.local/share/convmem/inventory.jsonl"
    ).expanduser()
    proc_path = Path(
        cfg.get("index", {}).get("processed_log")
        or "~/.local/share/convmem/processed.json"
    ).expanduser()
    if not inv_path.exists():
        return 0, 0, 0, 0

    records = []
    with open(inv_path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    processed = {}
    if proc_path.exists():
        try:
            processed = json.loads(proc_path.read_text())
        except Exception:
            pass
    indexed_paths = {v.get("path") for v in processed.values() if isinstance(v, dict)}
    indexed_hashes = set(processed.keys())

    deferred = not_indexed = 0
    for rec in records:
        path = rec["path"]
        fmt = detect_format(path)
        if fmt and get_parser(path) is None:
            deferred += 1
        elif path not in indexed_paths and fmt:
            try:
                file_hash = sha256_file(path)
            except OSError:
                file_hash = ""
            if file_hash and file_hash in indexed_hashes:
                continue  # same bytes indexed under another path (moved transcript)
            not_indexed += 1
    return len(records), len(indexed_paths), not_indexed, deferred


def render_stats(cfg: dict | None = None) -> None:
    """Print index statistics as Rich tables."""
    if cfg is None:
        cfg = load_config()

    from adapters.detect import TOOL_BY_FORMAT, detect_format

    chroma_dir = cfg["index"]["chroma_dir"]
    summary_metas = collection_metadata_rows(chroma_dir, "conversation_summaries")
    unit_metas = collection_metadata_rows(chroma_dir, "knowledge_units")
    chunks_by_tool = Counter(m.get("tool", "?") for m in summary_metas)
    units_by_tool = Counter(m.get("tool", "?") for m in unit_metas)

    proc_path = Path(
        cfg.get("index", {}).get("processed_log")
        or "~/.local/share/convmem/processed.json"
    ).expanduser()
    files_by_tool: Counter = Counter()
    if proc_path.exists():
        try:
            processed = json.loads(proc_path.read_text())
            for entry in processed.values():
                path = entry.get("path")
                if not path:
                    continue
                fmt = detect_format(path)
                tool = TOOL_BY_FORMAT.get(fmt, fmt or "?")
                files_by_tool[tool] += 1
        except Exception:
            pass

    all_tools = sorted(
        set(chunks_by_tool) | set(units_by_tool) | set(files_by_tool),
        key=lambda t: (-units_by_tool.get(t, 0), t),
    )

    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=box.SIMPLE_HEAVY,
        padding=(0, 1),
    )
    table.add_column("Source", style="cyan")
    table.add_column("Files", justify="right")
    table.add_column("Chunks", justify="right")
    table.add_column("Units", justify="right")

    for tool in all_tools:
        table.add_row(
            tool,
            str(files_by_tool.get(tool, 0)),
            str(chunks_by_tool.get(tool, 0)),
            str(units_by_tool.get(tool, 0)),
        )

    console.print(
        Panel.fit(table, title="Index Statistics", border_style="blue", padding=(1, 2))
    )

    units_by_domain = Counter(m.get("domain") or "untagged" for m in unit_metas)
    if units_by_domain:
        domain_table = Table(
            show_header=True,
            header_style="bold magenta",
            box=box.SIMPLE_HEAVY,
            padding=(0, 1),
        )
        domain_table.add_column("Domain", style="magenta")
        domain_table.add_column("Units", justify="right")
        for dom, count in sorted(units_by_domain.items(), key=lambda kv: -kv[1]):
            domain_table.add_row(domain_breadcrumb(dom) if dom != "untagged" else "untagged", str(count))
        console.print()
        console.print(
            Panel.fit(domain_table, title="By Domain", border_style="magenta", padding=(1, 2))
        )
        if units_by_domain.get("untagged"):
            render_warning(
                f"{units_by_domain['untagged']} unit(s) indexed before domain tagging was added.\n"
                "They'll still surface in search/ask, just not under --domain filters."
            )

        allow_extra = cfg.get("domains", {}).get("allow_extra", [])
        unknown = sorted(
            d for d in units_by_domain
            if d != "untagged" and not is_known_domain(d, allow_extra)
        )
        if unknown:
            render_warning(
                "Domains not in the taxonomy (typo, or add to [domains] allow_extra "
                "in config.toml if intentional):\n" + "\n".join(f"  • {d}" for d in unknown)
            )

    total_inv, indexed, pending, deferred = _coverage_counts(cfg)
    if total_inv:
        console.print()
        inv_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        inv_table.add_column(style="dim")
        inv_table.add_column(justify="right", style="bold")
        inv_table.add_row("Indexed", str(indexed))
        inv_table.add_row("Pending", str(pending))
        inv_table.add_row("Deferred", str(deferred))
        console.print(Text("Inventory", style="bold"))
        console.print(inv_table)

        if deferred:
            render_warning(
                "Cursor store.db chats are not searchable yet.\n"
                "Run: python ~/Projects/convmem/inventory.py && convmem index"
            )
        elif pending:
            render_warning(
                "New files pending ingest.\n"
                "Run: python ~/Projects/convmem/inventory.py && convmem index"
            )
