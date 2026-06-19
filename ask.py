"""RAG answer layer — retrieve context, then synthesize an answer with citations."""

from config import load_config
from llm import generate
from meta_format import when_from_meta, when_label
from query import query_raw, query_units

ASK_PROMPT = """You answer questions using ONLY the retrieved excerpts from past AI coding sessions below.
Be specific: mention tool names, file paths, commands, config keys, and error messages when present in the excerpts.
If the excerpts do not contain enough information to answer, say so clearly — do not invent details or guess from general knowledge.
Cite sources inline as [1], [2], etc. matching the excerpt numbers below.
Each excerpt header includes a date when known — use it when the user asks about "today", "recently", or timing.
If excerpts are only tangentially related (same tool but different topic), say the index has related material but not this specific answer.

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
# MCP / agent callers: degrade to retrieval-only before client tool timeout.
_ASK_SYNTHESIS_TIMEOUT = 45.0


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


def _format_context(results: list[dict], *, units: bool) -> tuple[str, list[dict]]:
    """Build numbered context block and citation list."""
    lines: list[str] = []
    citations: list[dict] = []
    for i, r in enumerate(results, 1):
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
            lines.append(
                f"[{i}] ({utype}, {tool}, {when}, domain={domain}, by={author}) {title}\n"
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


def ask(
    question: str,
    *,
    top_k: int = 5,
    raw: bool = False,
    history: list[tuple[str, str]] | None = None,
    domain: str | None = None,
    evidence: bool = False,
) -> dict:
    """Retrieve relevant memories and generate a cited answer.

    Args:
        history: Prior (question, answer) turns in this session for follow-ups.
        domain: Optional dotted-path scope (e.g. "web_stack.security"). Only
            applies to the units layer — raw summaries aren't domain-tagged.
        evidence: Re-rank units by ledger graph (unresolved > failed > resolved).

    Returns:
        {"answer": str, "citations": list[dict], "results": list[dict],
         "confidence": float|None, "warning": str|None}
    """
    cfg = load_config()
    models = cfg["models"]
    fetch_k = max(top_k, _ASK_TOP_K)
    warning: str | None = None
    search_q = _retrieval_query(question, history)

    if raw:
        results = query_raw(search_q, top_k=fetch_k)
        context, citations = _format_context(results, units=False)
    else:
        units = query_units(search_q, top_k=fetch_k, domain=domain)
        if evidence:
            from chroma_store import ChromaStore
            from evidence import apply_evidence_rerank

            store = ChromaStore(cfg["index"]["chroma_dir"])
            units = apply_evidence_rerank(units, store)
            units = _dedupe_results_by_ledger_id(units)
        best = _max_score(units)
        # If primary units are weak, supplement with raw summaries (hybrid).
        if not evidence and (best is None or best < _LOW_CONFIDENCE):
            raw_hits = query_raw(search_q, top_k=fetch_k)
            merged = _merge_results(units, raw_hits, fetch_k)
            lines: list[str] = []
            citations = []
            for i, (r, is_unit) in enumerate(merged[:fetch_k], 1):
                block, cites = _format_context([r], units=is_unit)
                lines.append(block)
                cites[0]["n"] = i
                citations.append(cites[0])
            results = [r for r, _ in merged]
            context = "\n\n".join(lines)
            if best is not None and best < _LOW_CONFIDENCE:
                warning = (
                    f"Low retrieval confidence (best score {best:.3f}). "
                    "Answer may be incomplete — topic may not be in the index."
                )
        else:
            results = units[:top_k]
            context, citations = _format_context(results, units=True)

    if not results:
        return {
            "answer": "No relevant excerpts found in the index for that question.",
            "citations": [],
            "results": [],
            "confidence": None,
            "warning": "No matches in index.",
        }

    confidence = _max_score(results)
    if warning is None and confidence is not None and confidence < _LOW_CONFIDENCE:
        warning = (
            f"Low retrieval confidence (best score {confidence:.3f}). "
            "Answer may be incomplete — topic may not be in the index."
        )

    if len(context) > _MAX_CONTEXT_CHARS:
        context = context[:_MAX_CONTEXT_CHARS] + "\n\n[… context truncated …]"

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
    try:
        answer = generate(
            prompt,
            model=model,
            ollama_host=models["ollama_host"],
            deepseek_base_url=models.get("deepseek_base_url", "https://api.deepseek.com"),
            timeout=_ASK_SYNTHESIS_TIMEOUT,
        )
    except Exception as e:
        synthesis_failed = True
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

    out = {
        "answer": answer,
        "citations": citations[:top_k],
        "results": results[:top_k],
        "confidence": confidence,
        "warning": warning,
        "retrieval_query": search_q,
        "evidence": evidence,
    }
    if synthesis_failed:
        out["synthesis_failed"] = True
    return out


def run_interactive(
    *,
    top_k: int = 5,
    raw: bool = False,
    first_question: str | None = None,
    domain: str | None = None,
    evidence: bool = False,
) -> None:
    """REPL: multi-turn ask with session memory."""
    from query import err_console, render_ask_output, render_warning

    history: list[tuple[str, str]] = []

    def _print_banner() -> None:
        err_console.print("[dim]convmem ask — interactive mode[/dim]")
        if domain:
            err_console.print(f"[dim]  Scoped to domain: {domain}[/dim]")
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
        out = ask(q, top_k=top_k, raw=raw, history=history or None, domain=domain, evidence=evidence)
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
