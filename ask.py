"""RAG answer layer — retrieve context, then synthesize an answer with citations."""

# pylint: disable=too-many-lines

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from config import load_config
from ledger_recent import (
    RECENT_DECISIONS_DAYS,
    RECENT_DECISIONS_LIMIT,
    decision_record_to_unit,
    recent_decisions_for_cfg,
)
from llm import generate_stream
from meta_format import when_from_meta, when_label
from query import query_raw, query_units

ASK_PROMPT = """You answer questions using ONLY the retrieved excerpts from past AI coding sessions below.
Be specific: mention tool names, file paths, commands, config keys, and error messages when present in the excerpts.
If the excerpts do not contain enough information to answer, say so clearly — do not invent details or guess from general knowledge.
Cite sources inline as [1], [2], etc. matching the excerpt numbers below.
Each excerpt header includes a date when known — use it when the user asks about "today", "recently", or timing.
If excerpts are only tangentially related (same tool but different topic), say the index has related material but not this specific answer.
For decisions: when one excerpt's relates_to points to another excerpt's ledger_id, the child decision replaces the parent — follow the child only; do not recommend the superseded parent approach.

Question:
{question}

Retrieved excerpts:
{context}

Answer:"""

FOLLOWUP_ASK_PROMPT = """You answer questions using ONLY the retrieved excerpts from past AI coding sessions below.
Be specific: mention tool names, file paths, commands, config keys, and error messages when present in the excerpts.
If the excerpts do not contain enough information to answer, say so clearly — do not invent details or guess from general knowledge.
Cite sources inline as [1], [2], etc. matching the excerpt numbers below.
Each excerpt header includes a date when known — use it when the user asks about "today", "recently", or timing.
If excerpts are only tangentially related (same tool but different topic), say the index has related material but not this specific answer.
For decisions: when one excerpt's relates_to points to another excerpt's ledger_id, the child decision replaces the parent — follow the child only; do not recommend the superseded parent approach.

The user is in a multi-turn session. Use the conversation so far to interpret follow-ups (e.g. "how did it improve CLS" refers to the prior topic). Still ground every claim in the excerpts — do not rely on the prior assistant reply as fact.

Conversation so far:
{history}

Current question:
{question}

Retrieved excerpts:
{context}

Answer:"""

_MAX_CONTEXT_CHARS = 12000
_MAX_HISTORY_CHARS = 4000
_LOW_CONFIDENCE = 0.55
_ASK_TOP_K = 8
EMPTY_CONTEXT_DELIVERY = {
    "max_chars": _MAX_CONTEXT_CHARS,
    "truncated": False,
    "chars_before": 0,
    "chars_after": 0,
    "last_fully_included_id": None,
    "partial_id": None,
}
# MCP / agent callers: degrade to retrieval-only before client tool timeout.
_ASK_SYNTHESIS_TIMEOUT = 45.0

# Lightweight telemetry for P1c gate detection (>=3 failures/week triggers streaming work).
_SYNTHESIS_FAIL_LOG = Path("~/.local/share/convmem/synthesis_failures.jsonl").expanduser()


def _log_synthesis_failure(question: str, error: Exception) -> None:
    """Append one JSONL line per synthesis failure. Non-blocking — never raises."""
    try:
        _SYNTHESIS_FAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "error_type": type(error).__name__,
            "error": str(error)[:200],
            "question": question[:200],
        }
        with _SYNTHESIS_FAIL_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Telemetry must never break ask


def _format_history(history: list[tuple[str, str]]) -> str:
    lines: list[str] = []
    block = ""
    for q, a in history:
        lines.append(f"User: {q}\nAssistant: {a}")
        block = "\n\n".join(lines)
        if len(block) > _MAX_HISTORY_CHARS:
            # Keep the most recent turns that fit.
            while len(block) > _MAX_HISTORY_CHARS and len(lines) > 1:
                lines.pop(0)
                block = "\n\n".join(lines)
            break
    return block


def _retrieval_query(question: str, history: list[tuple[str, str]] | None) -> str:
    """Expand a vague follow-up into a standalone search query."""
    if not history:
        return question
    # Anchor follow-ups to the last question (and optionally one before).
    prior = " ".join(q for q, _ in history[-2:])
    return f"{prior} {question}".strip()


def _result_key(r: dict) -> str:
    meta = r.get("metadata", {})
    return f"{meta.get('source_path','')}|{meta.get('title','')}|{meta.get('start_offset','')}"


def _merge_results(
    units: list[dict], raw_hits: list[dict], limit: int
) -> list[tuple[dict, bool]]:
    """Merge unit and raw hits; bool marks unit vs summary."""
    seen: set[str] = set()
    merged: list[tuple[dict, bool]] = []
    for r, is_unit in [(u, True) for u in units] + [(r, False) for r in raw_hits]:
        key = _result_key(r)
        if key in seen:
            continue
        seen.add(key)
        merged.append((r, is_unit))
        if len(merged) >= limit:
            break
    return merged


def _max_score(results: list[dict]) -> float | None:
    scores = [r["score"] for r in results if r.get("score") is not None]
    return max(scores) if scores else None


def _filter_superseded_decisions(results: list[dict]) -> list[dict]:
    """Drop parent decisions when a newer decision in results relates_to them."""
    parent_ids: set[str] = set()
    for r in results:
        meta = r.get("metadata") or {}
        if (meta.get("ledger_kind") or "").strip() != "decision":
            continue
        relates_to = (meta.get("relates_to") or "").strip()
        if relates_to.startswith("dec_"):
            parent_ids.add(relates_to)
    if not parent_ids:
        return results
    return [
        r
        for r in results
        if (r.get("metadata") or {}).get("ledger_id") not in parent_ids
    ]


def _dedupe_results_by_ledger_id(results: list[dict]) -> list[dict]:
    """Keep one hit per ledger_id (first wins — list should already be rank-sorted)."""
    seen: set[str] = set()
    out: list[dict] = []
    for r in results:
        lid = ((r.get("metadata") or {}).get("ledger_id") or "").strip()
        if lid:
            if lid in seen:
                continue
            seen.add(lid)
        out.append(r)
    return out


def _prepend_recent_decisions(
    semantic: list[dict],
    recent_records: list[dict],
    *,
    max_recent: int = RECENT_DECISIONS_LIMIT,
    total_limit: int,
    domain: str | None = None,
    site: str | None = None,
) -> list[dict]:
    """Inject novel recent decisions as a minority of the context block.

    Pipeline: optional domain/site filter on raw records → convert → drop
    recent units whose ledger_id already appears in semantic (semantic wins)
    → minority-cap with ``min(max_recent, max(1, total_limit // 3))`` →
    prepend capped recent then fill from semantic to ``total_limit``.
    """
    records = list(recent_records)
    if site:
        site_key = site.strip()
        records = [r for r in records if (r.get("site") or "").strip() == site_key]
    if domain:
        prefix = domain.split(".")[0].strip()
        if prefix:
            records = [
                r
                for r in records
                if (r.get("domain") or "").startswith(prefix)
            ]

    recent_units = [decision_record_to_unit(r) for r in records[:max_recent]]
    semantic_ids = {
        ((u.get("metadata") or {}).get("ledger_id") or "").strip()
        for u in semantic
        if ((u.get("metadata") or {}).get("ledger_id") or "").strip()
    }
    recent_after_dedupe = [
        u
        for u in recent_units
        if not (
            ((u.get("metadata") or {}).get("ledger_id") or "").strip()
            and ((u.get("metadata") or {}).get("ledger_id") or "").strip()
            in semantic_ids
        )
    ]
    if total_limit <= 0:
        return []
    cap = min(max_recent, max(1, total_limit // 3))
    capped = recent_after_dedupe[:cap]
    slots = total_limit - len(capped)
    return capped + list(semantic)[:slots]



TRACE_SCHEMA = "convmem.ask.trace.v1"
TRACE_LIMIT_DEFAULT = 20
MAX_PER_SOURCE = 2
_CONTEXT_TRUNCATION_SUFFIX = "\n\n[… context truncated …]"


def _diversify_by_source(
    candidates: list[dict],
    *,
    limit: int,
    max_per_source: int = MAX_PER_SOURCE,
) -> tuple[list[dict], list[dict]]:
    """Fill ``limit`` slots with at most ``max_per_source`` hits per source_path.

    Empty ``source_path`` is always admissible (no shared empty bucket).
    ``dropped`` are same-source skips only — not mere tail truncation past limit.
    """
    kept: list[dict] = []
    dropped: list[dict] = []
    counts: dict[str, int] = {}
    for result in candidates:
        meta = result.get("metadata") or {}
        src = meta.get("source_path") or ""
        if src:
            if counts.get(src, 0) >= max_per_source:
                dropped.append(result)
                continue
            counts[src] = counts.get(src, 0) + 1
        kept.append(result)
        if len(kept) >= limit:
            break
    return kept, dropped


def _source_diversity_block(
    dropped: list[dict],
    *,
    trace_limit: int,
    max_per_source: int = MAX_PER_SOURCE,
) -> dict:
    """Bounded dropped-row metadata for final_context (body-free compact rows)."""
    total = len(dropped)
    truncated = total > trace_limit
    items = []
    for result in dropped[:trace_limit]:
        row = _compact_trace_row(result)
        row["drop_reason"] = "source_cap"
        items.append(row)
    return {
        "max_per_source": max_per_source,
        "dropped_items": items,
        "dropped_items_total": total,
        "truncated": truncated,
    }


def _compact_trace_row(result: dict, *, origin: str | None = None) -> dict:
    """Compact per-hit row for ask() retrieval traces (no document bodies)."""
    meta = result.get("metadata") or {}
    lid = (meta.get("ledger_id") or "").strip() or None
    row = {
        "id": result.get("id"),
        "score": result.get("score"),
        "rank_score": result.get("rank_score"),
        "evidence_boost": result.get("evidence_boost"),
        "recency_boost": result.get("recency_boost"),
        "evidence_status": result.get("evidence_status") or "",
        "title": meta.get("title", ""),
        "type": meta.get("type"),
        "tool": meta.get("tool"),
        "source_path": meta.get("source_path", ""),
        "domain": meta.get("domain"),
        "ledger_id": lid,
        "ledger_kind": meta.get("ledger_kind"),
    }
    if origin is not None:
        row["origin"] = origin
    return row


def _trace_stage(
    results: list[dict],
    *,
    limit: int,
    origins: list[str] | None = None,
    status: str = "ok",
    reason: str | None = None,
) -> dict:
    """Build a stage object; skipped stages never use null."""
    if status == "skipped":
        out: dict = {
            "status": "skipped",
            "reason": reason or "skipped",
            "items": [],
            "items_total": 0,
            "truncated": False,
        }
        return out
    total = len(results)
    truncated = total > limit
    capped = results[:limit]
    items = []
    for i, r in enumerate(capped):
        origin = origins[i] if origins is not None and i < len(origins) else None
        items.append(_compact_trace_row(r, origin=origin))
    out = {
        "status": status,
        "items": items,
        "items_total": total,
        "truncated": truncated,
    }
    if reason:
        out["reason"] = reason
    return out


def _skipped_stage(reason: str) -> dict:
    return _trace_stage([], limit=0, status="skipped", reason=reason)


def _format_context_item(
    result: dict, *, units: bool, n: int
) -> tuple[str, dict]:
    """Format one result with citation number ``n`` in both text and metadata."""
    block, cites = _format_context([result], units=units, start_n=n)
    return block, cites[0]


def _format_selection(
    selection: list[dict], unit_flags: list[bool]
) -> tuple[str, list[dict], list[str]]:
    """Format selection into context, citations, and per-item blocks."""
    blocks: list[str] = []
    citations: list[dict] = []
    for i, (r, is_unit) in enumerate(zip(selection, unit_flags), 1):
        block, cite = _format_context_item(r, units=is_unit, n=i)
        blocks.append(block)
        citations.append(cite)
    return "\n\n".join(blocks), citations, blocks


def _apply_context_char_limit(
    context: str,
    selection: list[dict],
    blocks: list[str],
    *,
    max_chars: int = _MAX_CONTEXT_CHARS,
) -> tuple[str, dict]:
    """Cut context at max_chars; report delivery metadata (ChatGPT A2)."""
    chars_before = len(context)
    delivery = {
        "max_chars": max_chars,
        "truncated": False,
        "chars_before": chars_before,
        "chars_after": chars_before,
        "last_fully_included_id": selection[-1].get("id") if selection else None,
        "partial_id": None,
    }
    if chars_before <= max_chars:
        return context, delivery

    delivered = context[:max_chars] + _CONTEXT_TRUNCATION_SUFFIX
    delivery["truncated"] = True
    delivery["chars_after"] = len(delivered)

    pos = 0
    last_full = None
    partial = None
    for i, block in enumerate(blocks):
        if i > 0:
            if pos >= max_chars:
                break
            if pos + 2 > max_chars:
                break
            pos += 2
        block_end = pos + len(block)
        if block_end <= max_chars:
            last_full = selection[i].get("id")
            pos = block_end
        else:
            if pos < max_chars:
                partial = selection[i].get("id")
            break
    delivery["last_fully_included_id"] = last_full
    delivery["partial_id"] = partial
    return delivered, delivery


def _build_trace_envelope(
    request: dict,
    stages: dict,
    *,
    trace_limit: int,
    context_delivery: dict,
) -> dict:
    # Envelope truncated when any stage item list is cut OR source_diversity
    # dropped_items exceed trace_limit. Stage.truncated stays about items only.
    any_trunc = False
    for stage in stages.values():
        if not isinstance(stage, dict):
            continue
        if stage.get("truncated"):
            any_trunc = True
            break
        diversity = stage.get("source_diversity")
        if isinstance(diversity, dict) and diversity.get("truncated"):
            any_trunc = True
            break
    return {
        "schema": TRACE_SCHEMA,
        "request": request,
        "stages": stages,
        "trace_limit": trace_limit,
        "truncated": any_trunc,
        "context_delivery": context_delivery,
    }


def _trace_request(
    *,
    search_q: str,
    top_k: int,
    fetch_k: int,
    raw: bool,
    evidence: bool,
    domain: str | None,
    site: str | None,
) -> dict:
    return {
        "retrieval_query": search_q,
        "top_k": top_k,
        "fetch_k": fetch_k,
        "raw": raw,
        "evidence": evidence,
        "domain": domain,
        "site": site,
    }


def _format_context(
    results: list[dict], *, units: bool, start_n: int = 1
) -> tuple[str, list[dict]]:
    """Build numbered context block and citation list."""
    lines: list[str] = []
    citations: list[dict] = []
    for i, r in enumerate(results, start_n):
        meta = r.get("metadata", {})
        doc = (r.get("document") or "").strip()
        if units:
            title = meta.get("title", "")
            utype = meta.get("type", "?")
            tool = meta.get("tool", "?")
            src = meta.get("source_path", "")
            when = when_label(meta)
            domain = meta.get("domain") or "general"
            author = meta.get("author_model") or "unknown"
            ledger_id = (meta.get("ledger_id") or "").strip()
            relates_to = (meta.get("relates_to") or "").strip()
            header_bits = [f"domain={domain}", f"by={author}"]
            if ledger_id:
                header_bits.append(f"ledger_id={ledger_id}")
            if relates_to:
                header_bits.append(f"relates_to={relates_to}")
            lines.append(
                f"[{i}] ({utype}, {tool}, {when}, {', '.join(header_bits)}) {title}\n"
                f"    {doc}\n"
                f"    Source: {src}"
            )
            citations.append(
                {
                    "n": i,
                    "id": r.get("id"),
                    "title": title,
                    "type": utype,
                    "tool": tool,
                    "source_path": src,
                    "when": when_from_meta(meta),
                    "score": r.get("score"),
                    "start_offset": meta.get("start_offset"),
                    "conversation_id": meta.get("conversation_id"),
                    "session_id": meta.get("session_id"),
                    "domain": domain,
                    "author_model": author,
                    "verifier_model": meta.get("verifier_model") or None,
                    "ledger_id": meta.get("ledger_id"),
                    "ledger_kind": meta.get("ledger_kind"),
                    "relates_to": meta.get("relates_to"),
                    "site": meta.get("site"),
                    "severity": meta.get("severity"),
                    "evidence_status": r.get("evidence_status") or "",
                    "evidence_boost": r.get("evidence_boost"),
                }
            )
        else:
            tool = meta.get("tool", "?")
            src = meta.get("source_path", "")
            start = meta.get("start_offset")
            end = meta.get("end_offset")
            when = when_label(meta)
            lines.append(
                f"[{i}] ({tool}, {when}) messages {start}–{end}\n"
                f"    {doc}\n"
                f"    Source: {src}"
            )
            citations.append(
                {
                    "n": i,
                    "tool": tool,
                    "source_path": src,
                    "start_offset": start,
                    "end_offset": end,
                    "when": when_from_meta(meta),
                    "score": r.get("score"),
                    "conversation_id": meta.get("conversation_id"),
                    "session_id": meta.get("session_id"),
                    "ledger_id": meta.get("ledger_id"),
                    "ledger_kind": meta.get("ledger_kind"),
                    "relates_to": meta.get("relates_to"),
                    "site": meta.get("site"),
                    "severity": meta.get("severity"),
                }
            )
    return "\n\n".join(lines), citations



def _apply_evidence_and_recent(
    units: list[dict],
    cfg: dict,
    *,
    domain: str | None,
    site: str | None,
    fetch_k: int,
    trace: bool,
    limit: int,
) -> tuple[list[dict], dict]:
    """Evidence rerank, ledger dedupe, recent prepend; optional stage snapshots."""
    from chroma_store import ChromaStore
    from evidence import apply_evidence_rerank

    stages: dict = {}
    qcfg = cfg.get("query", {})
    rw = float(qcfg.get("recency_weight", 0.0))
    rhl = float(qcfg.get("recency_half_life_days", 30.0))
    with ChromaStore(cfg["index"]["chroma_dir"]) as store:
        units = apply_evidence_rerank(
            units, store, recency_weight=rw, recency_half_life_days=rhl
        )
    if trace:
        stages["evidence_reranked"] = _trace_stage(
            units, limit=limit, origins=["unit"] * len(units)
        )
    units = _dedupe_results_by_ledger_id(units)
    if trace:
        stages["ledger_deduped"] = _trace_stage(
            units, limit=limit, origins=["unit"] * len(units)
        )
    recent = recent_decisions_for_cfg(
        cfg, days=RECENT_DECISIONS_DAYS, limit=RECENT_DECISIONS_LIMIT
    )
    if recent:
        units = _prepend_recent_decisions(
            units,
            recent,
            total_limit=fetch_k,
            domain=domain,
            site=site,
        )
    if trace:
        admitted = [
            u
            for u in units
            if (u.get("evidence_status") or "") == "recent_decision"
        ]
        stages["recent_injected"] = _trace_stage(
            admitted, limit=limit, origins=["unit"] * len(admitted)
        )
    return units, stages


def _select_units_or_hybrid(
    units: list[dict],
    *,
    search_q: str,
    top_k: int,
    fetch_k: int,
    site: str | None,
    evidence: bool,
) -> tuple[
    list[dict],
    list[dict],
    list[bool],
    list[str],
    str,
    list[dict],
    list[str],
    str | None,
    list[dict],
]:
    """Return results, selection, flags, origins, context, citations, blocks, warning, dropped.

    ``results`` stay pre-diversity; ``selection``/citations are diversified.
    Evidence pools may be small after minority-cap — shortfall is acceptable.
    """
    warning: str | None = None
    best = _max_score(units)
    if not evidence and (best is None or best < _LOW_CONFIDENCE):
        raw_hits = query_raw(search_q, top_k=fetch_k, site=site)
        merged = _merge_results(units, raw_hits, fetch_k)
        pair_slice = merged[:fetch_k]
        cands = [r for r, _ in pair_slice]
        flag_by_id = {r.get("id"): is_unit for r, is_unit in pair_slice}
        selection, dropped = _diversify_by_source(cands, limit=fetch_k)
        unit_flags = [bool(flag_by_id.get(r.get("id"), False)) for r in selection]
        origins = [
            "unit" if flag_by_id.get(r.get("id"), False) else "raw_summary"
            for r in selection
        ]
        context, citations, blocks = _format_selection(selection, unit_flags)
        results = [r for r, _ in merged]
        if best is not None and best < _LOW_CONFIDENCE:
            warning = (
                f"Low retrieval confidence (best score {best:.3f}). "
                "Answer may be incomplete — topic may not be in the index."
            )
        return (
            results,
            selection,
            unit_flags,
            origins,
            context,
            citations,
            blocks,
            warning,
            dropped,
        )

    # Longer pool for refill; results slice stays pre-diversity top_k.
    pool = _filter_superseded_decisions(units[:fetch_k])
    results = pool[:top_k]
    selection, dropped = _diversify_by_source(pool, limit=top_k)
    unit_flags = [True] * len(selection)
    origins = ["unit"] * len(selection)
    context, citations, blocks = _format_selection(selection, unit_flags)
    return (
        results,
        selection,
        unit_flags,
        origins,
        context,
        citations,
        blocks,
        warning,
        dropped,
    )


def _synthesize_answer(
    *,
    question: str,
    context: str,
    history: list[tuple[str, str]] | None,
    models: dict,
    citations: list[dict],
    top_k: int,
    warning: str | None,
) -> tuple[str, str | None, bool, bool]:
    """Run LLM synthesis; return answer, warning, failed, interrupted."""
    if history:
        prompt = FOLLOWUP_ASK_PROMPT.format(
            history=_format_history(history),
            question=question,
            context=context,
        )
    else:
        prompt = ASK_PROMPT.format(question=question, context=context)
    model = models.get("distill_model", "deepseek-v4-flash")
    synthesis_failed = False
    synthesis_interrupted = False
    buffer: list[str] = []
    try:
        for token in generate_stream(
            prompt,
            model=model,
            ollama_host=models["ollama_host"],
            deepseek_base_url=models.get("deepseek_base_url", "https://api.deepseek.com"),
            timeout=_ASK_SYNTHESIS_TIMEOUT,
        ):
            buffer.append(token)
        answer = "".join(buffer)
    except Exception as e:
        if buffer:
            synthesis_interrupted = True
            answer = "".join(buffer) + (
                f"\n\n[Synthesis interrupted ({type(e).__name__}). "
                f"Partial answer above.]"
            )
            synth_warn = "Synthesis interrupted; partial answer returned."
            warning = f"{warning}\n{synth_warn}" if warning else synth_warn
        else:
            synthesis_failed = True
            _log_synthesis_failure(question, e)
            cite_lines = [
                f"[{c['n']}] {c.get('title', 'Untitled')} ({c.get('tool', '?')}, score {c.get('score')})"
                for c in citations[:top_k]
            ]
            answer = (
                "[Synthesis unavailable — retrieval results below. "
                f"Reason: {type(e).__name__}: {e}]\n\n"
                + "\n".join(cite_lines)
            )
            synth_warn = (
                f"Synthesis failed ({type(e).__name__}); returning retrieval citations only."
            )
            warning = f"{warning}\n{synth_warn}" if warning else synth_warn
    return answer, warning, synthesis_failed, synthesis_interrupted


@dataclass(frozen=True)
class RetrievalBundle:  # pylint: disable=too-many-instance-attributes
    """Pre-synthesis retrieval outputs for ask() and future retrieval-eval.

    Cardinalities (Round 4 lock):
    - results: normal/evidence pre-diversity ≤ top_k; hybrid/raw pre-diversity ≤ fetch_k
    - selection / citations: full ordered context (may be fetch_k on raw/hybrid)
    - ask() still returns results[:top_k] and citations[:top_k]
    """

    search_q: str
    results: list[dict]
    selection: list[dict]
    citations: list[dict]
    context: str
    context_delivery: dict
    confidence: float | None
    warning: str | None
    trace: dict | None


def retrieve_for_ask(  # pylint: disable=too-many-locals,too-many-arguments
    question: str,
    *,
    top_k: int = 5,
    raw: bool = False,
    history: list[tuple[str, str]] | None = None,
    domain: str | None = None,
    site: str | None = None,
    evidence: bool = False,
    trace: bool = False,
    cfg: dict | None = None,
) -> RetrievalBundle:
    """Retrieval-only pipeline (no LLM). Behavior matches pre-extraction ask()."""
    if cfg is None:
        cfg = load_config()
    fetch_k = max(top_k, _ASK_TOP_K)
    warning: str | None = None
    search_q = _retrieval_query(question, history)
    limit = max(1, int(TRACE_LIMIT_DEFAULT))
    stages: dict = {}
    selection: list[dict] = []
    unit_flags: list[bool] = []
    origins: list[str] = []
    results: list[dict] = []
    context = ""
    citations: list[dict] = []
    blocks: list[str] = []
    dropped: list[dict] = []

    if raw:
        results = query_raw(search_q, top_k=fetch_k, site=site)
        if trace:
            stages["candidates"] = _trace_stage(
                results, limit=limit, origins=["raw_summary"] * len(results)
            )
            stages["evidence_reranked"] = _skipped_stage("raw_mode")
            stages["ledger_deduped"] = _skipped_stage("raw_mode")
            stages["recent_injected"] = _skipped_stage("raw_mode")
        selection, dropped = _diversify_by_source(results, limit=fetch_k)
        unit_flags = [False] * len(selection)
        origins = ["raw_summary"] * len(selection)
        context, citations, blocks = _format_selection(selection, unit_flags)
    else:
        units = query_units(search_q, top_k=fetch_k, domain=domain, site=site)
        if trace:
            stages["candidates"] = _trace_stage(
                units, limit=limit, origins=["unit"] * len(units)
            )
        if evidence:
            units, ev_stages = _apply_evidence_and_recent(
                units,
                cfg,
                domain=domain,
                site=site,
                fetch_k=fetch_k,
                trace=trace,
                limit=limit,
            )
            stages.update(ev_stages)
        elif trace:
            stages["evidence_reranked"] = _skipped_stage("evidence_disabled")
            stages["ledger_deduped"] = _skipped_stage("evidence_disabled")
            stages["recent_injected"] = _skipped_stage("evidence_disabled")

        (
            results,
            selection,
            unit_flags,
            origins,
            context,
            citations,
            blocks,
            warning,
            dropped,
        ) = _select_units_or_hybrid(
            units,
            search_q=search_q,
            top_k=top_k,
            fetch_k=fetch_k,
            site=site,
            evidence=evidence,
        )

    if trace:
        stages["final_context"] = _trace_stage(
            selection, limit=limit, origins=origins[: len(selection)]
        )
        stages["final_context"]["source_diversity"] = _source_diversity_block(
            dropped, trace_limit=limit
        )

    req = _trace_request(
        search_q=search_q,
        top_k=top_k,
        fetch_k=fetch_k,
        raw=raw,
        evidence=evidence,
        domain=domain,
        site=site,
    )

    if not results:
        empty_delivery = dict(EMPTY_CONTEXT_DELIVERY)
        envelope = None
        if trace:
            envelope = _build_trace_envelope(
                req, stages, trace_limit=limit, context_delivery=empty_delivery
            )
        return RetrievalBundle(
            search_q=search_q,
            results=[],
            selection=selection,
            citations=[],
            context="",
            context_delivery=empty_delivery,
            confidence=None,
            warning="No matches in index.",
            trace=envelope,
        )

    confidence = _max_score(results)
    if warning is None and confidence is not None and confidence < _LOW_CONFIDENCE:
        warning = (
            f"Low retrieval confidence (best score {confidence:.3f}). "
            "Answer may be incomplete — topic may not be in the index."
        )

    context, context_delivery = _apply_context_char_limit(
        context, selection, blocks, max_chars=_MAX_CONTEXT_CHARS
    )
    envelope = None
    if trace:
        envelope = _build_trace_envelope(
            req, stages, trace_limit=limit, context_delivery=context_delivery
        )
    return RetrievalBundle(
        search_q=search_q,
        results=results,
        selection=selection,
        citations=citations,
        context=context,
        context_delivery=context_delivery,
        confidence=confidence,
        warning=warning,
        trace=envelope,
    )


def ask(
    question: str,
    *,
    top_k: int = 5,
    raw: bool = False,
    history: list[tuple[str, str]] | None = None,
    domain: str | None = None,
    site: str | None = None,
    evidence: bool = False,
    trace: bool = False,
) -> dict:
    """Retrieve relevant memories and generate a cited answer.

    Args:
        history: Prior (question, answer) turns in this session for follow-ups.
        domain: Optional dotted-path scope (e.g. "web_stack.security"). Only
            applies to the units layer — raw summaries aren't domain-tagged.
        site: Optional site hostname (e.g. staging2.willowyhollow.com).
        evidence: Re-rank units by ledger graph (unresolved > failed > resolved).
        trace: When True, include versioned retrieval trace (convmem.ask.trace.v1).

    Returns:
        {"answer": str, "citations": list[dict], "results": list[dict],
         "confidence": float|None, "warning": str|None}
        With trace=True, also ``trace`` envelope (stages + context_delivery).
    """
    cfg = load_config()
    bundle = retrieve_for_ask(
        question,
        top_k=top_k,
        raw=raw,
        history=history,
        domain=domain,
        site=site,
        evidence=evidence,
        trace=trace,
        cfg=cfg,
    )
    if not bundle.results:
        empty = {
            "answer": "No relevant excerpts found in the index for that question.",
            "citations": [],
            "results": [],
            "confidence": None,
            "warning": "No matches in index.",
        }
        if bundle.trace is not None:
            empty["trace"] = bundle.trace
        return empty

    models = cfg["models"]
    answer, warning, synthesis_failed, synthesis_interrupted = _synthesize_answer(
        question=question,
        context=bundle.context,
        history=history,
        models=models,
        citations=bundle.citations,
        top_k=top_k,
        warning=bundle.warning,
    )
    out = {
        "answer": answer,
        "citations": bundle.citations[:top_k],
        "results": bundle.results[:top_k],
        "confidence": bundle.confidence,
        "warning": warning,
        "retrieval_query": bundle.search_q,
        "evidence": evidence,
    }
    if synthesis_failed:
        out["synthesis_failed"] = True
    if synthesis_interrupted:
        out["synthesis_interrupted"] = True
    if bundle.trace is not None:
        out["trace"] = bundle.trace
    return out



def run_interactive(
    *,
    top_k: int = 5,
    raw: bool = False,
    first_question: str | None = None,
    domain: str | None = None,
    site: str | None = None,
    evidence: bool = False,
) -> None:
    """REPL: multi-turn ask with session memory."""
    from query import err_console, render_ask_output, render_warning

    history: list[tuple[str, str]] = []

    def _print_banner() -> None:
        err_console.print("[dim]convmem ask — interactive mode[/dim]")
        if domain:
            err_console.print(f"[dim]  Scoped to domain: {domain}[/dim]")
        if site:
            err_console.print(f"[dim]  Scoped to site: {site}[/dim]")
        if evidence:
            err_console.print("[dim]  Evidence-aware ranking: unresolved findings preferred[/dim]")
        err_console.print("[dim]  Type a question, or: exit | /clear[/dim]")
        err_console.print()

    def _print_out(out: dict) -> None:
        render_ask_output(out, show_search=bool(history))

    def _turn(question: str) -> None:
        nonlocal history
        q = question.strip()
        if not q:
            return
        if q.lower() in ("exit", "quit", "q"):
            raise SystemExit(0)
        if q == "/clear":
            history = []
            render_warning("Session cleared.")
            return
        out = ask(
            q,
            top_k=top_k,
            raw=raw,
            history=history or None,
            domain=domain,
            site=site,
            evidence=evidence,
        )
        _print_out(out)
        history.append((q, out["answer"]))

    _print_banner()
    if first_question:
        _turn(first_question)

    while True:
        try:
            line = input("ask> ").strip()
        except (EOFError, KeyboardInterrupt):
            err_console.print()
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            break
        _turn(line)
