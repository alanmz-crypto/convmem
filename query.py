"""Query layer.

Primary: knowledge_units (Step 5+).
Fallback: conversation_summaries via --raw (Step 4).
Reranking: Step 6 (query_units only).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from chroma_store import ChromaStore
from config import load_config
from domains import domain_breadcrumb, domain_matches, is_known_domain, normalize_domain
from llm import ollama_embed
from meta_format import when_from_meta
from open_source import resolve_open_target

# ---------------------------------------------------------------------------
# Query logic (unchanged)
# ---------------------------------------------------------------------------


def _unit_domain(meta: dict) -> str | None:
    """Return tagged domain, or None for pre-Step-8 units without domain metadata."""
    raw = meta.get("domain")
    if raw is None or raw == "":
        return None
    return str(raw)


def query_units(text: str, top_k: int = 5, domain: str | None = None) -> list[dict]:
    cfg = load_config()
    models = cfg["models"]
    qcfg = cfg.get("query", {})
    store = ChromaStore(cfg["index"]["chroma_dir"])

    embedding = ollama_embed(
        text, model=models["embed_model"], host=models["ollama_host"]
    )

    use_rerank = bool(qcfg.get("rerank", False))
    n_fetch = qcfg.get("top_k_candidates", 20) if use_rerank else top_k
    domain = normalize_domain(domain) if domain else None
    if domain:
        # Domain filtering is hierarchical (parent matches children), which
        # Chroma's exact-match `where` can't express, so over-fetch and
        # filter client-side before reranking/truncating.
        n_fetch = max(n_fetch, qcfg.get("top_k_candidates", 20)) * 3
    results = store.query_units(embedding, n_fetch)
    if domain:
        results = [
            r for r in results
            if (ud := _unit_domain(r.get("metadata", {}))) is not None
            and domain_matches(ud, domain)
        ]
    for r in results:
        d = r.get("distance")
        r["score"] = round(1.0 - d, 4) if d is not None else None

    fetch_for_rerank = qcfg.get("top_k_candidates", 20) if use_rerank else top_k
    if use_rerank and results:
        from rerank import rerank as rerank_fn

        results = rerank_fn(text, results[:fetch_for_rerank], models["rerank_model"], top_k)

    return results[:top_k]


def query_raw(text: str, top_k: int = 5) -> list[dict]:
    cfg = load_config()
    models = cfg["models"]
    store = ChromaStore(cfg["index"]["chroma_dir"])

    embedding = ollama_embed(
        text, model=models["embed_model"], host=models["ollama_host"]
    )
    results = store.query_summaries(embedding, top_k)
    for r in results:
        d = r.get("distance")
        r["score"] = round(1.0 - d, 4) if d is not None else None
    return results


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
    n: int, score: float | None, meta: dict, *, units: bool
) -> Text:
    t = Text()
    t.append(f"[{n}]  ", style="bold")
    t.append_text(_score_text(score))
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
            title=_panel_title(i, r.get("score"), meta, units=units),
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
    indexed_paths = {v.get("path") for v in processed.values()}

    deferred = not_indexed = 0
    for rec in records:
        path = rec["path"]
        fmt = detect_format(path)
        if fmt and get_parser(path) is None:
            deferred += 1
        elif path not in indexed_paths and fmt:
            not_indexed += 1
    return len(records), len(indexed_paths), not_indexed, deferred


def render_stats(cfg: dict | None = None) -> None:
    """Print index statistics as Rich tables."""
    if cfg is None:
        cfg = load_config()
    store = ChromaStore(cfg["index"]["chroma_dir"])

    from adapters.detect import TOOL_BY_FORMAT, detect_format

    summary_metas = store.summaries_metadata()
    unit_metas = store.units_metadata()
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
