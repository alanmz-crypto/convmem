"""convmem CLI (typer).

Usage:
  convmem "query"            search (raw summaries in Step 4)
  convmem "query" --raw      explicit fallback over conversation summaries
  convmem "query" --top 10   more results
  convmem "query" --domain web_stack.security   scope to a domain (+children)
  convmem "query" --site staging2.example.com   scope to a client site
  convmem "query" --open 1        search and open result #1 in source app
  convmem index              ingest all sources, skip unchanged
  convmem index --file PATH  force re-ingest one file
  convmem ask "question"           answer from retrieved memories
  convmem ask "question" --evidence     prefer unresolved ledger findings
  convmem ask -i                   interactive multi-turn session
  convmem ask -i "first question"  start interactive with one turn
  convmem open PATH               open a hit in its native chat app
  convmem add --file observations.jsonl   batch-ingest tool-sourced findings
  convmem add --file observations.jsonl --upsert   update by stable ledger id
  convmem add --title ... --summary ... --author MODEL   ingest one finding
  convmem verify UNIT_ID --model MODEL [--confidence 0.9]  cross-model check
  convmem related LEDGER_ID        show observation/decision/verification chain
  convmem exclude PATH --reason "noise"  mark a conversation as excluded
  convmem exclude --list             show excluded conversations
  convmem exclude --undo PATH        re-include a previously excluded file
  convmem watch                    watch transcript dirs → incremental index
  convmem refine                   background index refinement (F1)
  convmem refine --once --job JOB  run one refine job
  convmem monitor                  HTTP security probes (F2b)
  convmem brief                    shared context block for all agents
  convmem brief --print            stdout only (paste into ChatGPT sessions)
  convmem doctor                   health checks (v0); --v1 for watch/systemd
  convmem tldr                     one-page cheat sheet (cwd-aware)
  convmem doctor --verify          also run scripts/verify-continue.sh
  convmem record -i                record a durable fact (interactive)
  convmem record --approve-last    approve newest pending + index (searchable)
  convmem propose_decision         same as record (legacy name)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import typer

from chroma_readonly import collection_count
from open_source import run_open

app = typer.Typer(add_completion=False, help="Search your past AI conversations.")

_SUBCOMMANDS = {
    "index", "stats", "search", "ask", "open", "add", "verify", "related",
    "watch", "refine", "monitor", "exclude", "brief", "doctor", "propose_decision", "record",
    "unresolved", "tldr",
}
# Primary search is misleading until distillation backfill catches up to summaries.
_MIN_UNITS_FOR_PRIMARY = 50


def _unit_count() -> int:
    from config import load_config

    cfg = load_config()
    return collection_count(cfg["index"]["chroma_dir"], "knowledge_units")


def _primary_search_ready() -> bool:
    return _unit_count() >= _MIN_UNITS_FOR_PRIMARY


# Lightweight telemetry for delayed-index detection (ledger-approved, Chroma-failed).
_INDEX_FAIL_LOG = Path("~/.local/share/convmem/index_failures.jsonl").expanduser()


def _log_index_failure(proposal_id: str, error: Exception) -> None:
    """Append one JSONL line when approval succeeds but Chroma indexing fails. Never raises."""
    try:
        _INDEX_FAIL_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "proposal_id": proposal_id,
            "error_type": type(error).__name__,
            "error": str(error)[:200],
        }
        with _INDEX_FAIL_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Telemetry must never break record


def _guard_write() -> None:
    """Refuse prod/lab cross-lane writes unless CONVMEM_CONFIRM_* is set."""
    from config import load_config
    from query import render_error
    from runtime_guard import require_write_consent

    cfg = load_config()
    try:
        require_write_consent(cfg["index"]["chroma_dir"])
    except RuntimeError as exc:
        render_error(str(exc))
        raise typer.Exit(2) from exc


@app.command()
def search(
    query: str = typer.Argument(..., help="What you're trying to recall"),
    raw: bool = typer.Option(False, "--raw", help="Search conversation summaries (fallback layer)"),
    top: int = typer.Option(5, "--top", help="Number of results"),
    domain: str | None = typer.Option(
        None, "--domain", help="Scope to a domain and its children, e.g. web_stack.security"
    ),
    site: str | None = typer.Option(
        None, "--site", help="Scope to a site hostname, e.g. staging2.willowyhollow.com"
    ),
    open_at: int | None = typer.Option(
        None, "--open", min=1, help="Open result # in its source chat app"
    ),
):
    """Search past conversations."""
    from query import query_raw, query_units, render_search_results, render_warning

    if raw:
        if domain:
            render_warning("--domain has no effect with --raw (summaries aren't domain-tagged).")
        results = query_raw(query, top_k=top, site=site)
        render_search_results(results, units=False)
    else:
        if not _primary_search_ready():
            from chroma_store import ChromaStore
            from config import load_config

            store = ChromaStore(load_config()["index"]["chroma_dir"])
            n, summary_n = store.count_units(), store.count_summaries()
            render_warning(
                f"Only {n} knowledge unit(s) vs {summary_n} summaries — "
                "primary search is thin. Use --raw until backfill completes, or:\n"
                "rm ~/.local/share/convmem/processed.json && convmem index"
            )
        results = query_units(query, top_k=top, domain=domain, site=site)
        render_search_results(results, units=True)

    from next_steps import after_search

    after_search(query=query, site=site, n_results=len(results or []))

    if open_at and results:
        idx = open_at - 1
        if 0 <= idx < len(results):
            meta = results[idx].get("metadata", {})
            target = run_open(meta)
            if target.command:
                typer.echo(f"\n{target.format_line()}", err=True)
            elif target.hint:
                typer.echo(f"\n{target.format_line()}", err=True)
        else:
            from query import render_error

            render_error(f"No result #{open_at}.")


@app.command("open")
def open_hit(
    source_path: str = typer.Argument(..., help="source_path from a search/ask result"),
    at: int | None = typer.Option(
        None, "--at", help="Message offset (helps locate Kiro sessions)"
    ),
    tool: str | None = typer.Option(None, "--tool", help="Tool name from result metadata"),
):
    """Open a hit's source chat in the native app (Kiro, Cursor, etc.)."""
    meta = {
        "source_path": source_path,
        "start_offset": at,
        "tool": tool or "",
    }
    target = run_open(meta)
    typer.echo(target.format_line())
    if not target.command and target.hint:
        raise typer.Exit(0)


@app.command("ask")
def ask_command(
    question: str | None = typer.Argument(
        None, help="Question (omit with -i for interactive mode)"
    ),
    interactive: bool = typer.Option(
        False, "-i", "--interactive", help="Multi-turn session with follow-ups"
    ),
    raw: bool = typer.Option(False, "--raw", help="Retrieve from conversation summaries"),
    top: int = typer.Option(5, "--top", help="Number of excerpts to use as context"),
    domain: str | None = typer.Option(
        None, "--domain", help="Scope to a domain and its children, e.g. web_stack.wordpress"
    ),
    site: str | None = typer.Option(
        None, "--site", help="Scope to a site hostname, e.g. staging2.willowyhollow.com"
    ),
    evidence: bool = typer.Option(
        False,
        "--evidence",
        help="Prefer unresolved observations and failed verifications (ledger graph)",
    ),
    open_at: int | None = typer.Option(
        None, "--open", min=1, help="After answering, open source citation #"
    ),
):
    """Answer questions using retrieved memories from past sessions."""
    from ask import ask, run_interactive
    from query import render_ask_output, render_error

    if interactive:
        run_interactive(top_k=top, raw=raw, first_question=question, domain=domain, site=site, evidence=evidence)
        return
    if not question:
        render_error("Provide a question, or use -i for interactive mode.")
        raise typer.Exit(1)

    out = ask(question, top_k=top, raw=raw, domain=domain, site=site, evidence=evidence)
    render_ask_output(out)
    from next_steps import after_ask

    after_ask(
        question=question,
        site=site,
        n_citations=len(out.get("citations") or []),
        synthesis_failed=bool(out.get("synthesis_failed")),
        synthesis_interrupted=bool(out.get("synthesis_interrupted")),
    )
    if open_at and out.get("citations"):
        idx = open_at - 1
        if 0 <= idx < len(out["citations"]):
            c = out["citations"][idx]
            run_open(
                {
                    "source_path": c.get("source_path"),
                    "tool": c.get("tool"),
                    "start_offset": c.get("start_offset"),
                    "conversation_id": c.get("conversation_id"),
                    "session_id": c.get("session_id"),
                }
            )
        else:
            render_error(f"No citation #{open_at}.")


@app.command()
def index(
    file: str = typer.Option(None, "--file", help="Ingest a single file"),
    limit: int = typer.Option(None, "--limit", help="Max files to process (debug)"),
    force: bool = typer.Option(
        False,
        "--force",
        help="With --file: bypass path/hash skip and re-ingest (clears processed entry)",
    ),
):
    """Ingest all sources (skip unchanged), or one file (--file; add --force to re-ingest)."""
    _guard_write()
    from ingest import index as run_index

    stats = run_index(force_file=file, limit_files=limit, force_reindex=force)
    typer.echo("")
    typer.echo(
        f"Done. files_processed={stats['files_processed']} "
        f"files_skipped={stats['files_skipped']} "
        f"chunks_indexed={stats['chunks_indexed']} "
        f"units_indexed={stats.get('units_indexed', 0)}"
    )
    from next_steps import after_index

    after_index(
        files_processed=stats["files_processed"],
        units_indexed=stats.get("units_indexed", 0),
    )


@app.command()
def stats():
    """Show collection counts and source breakdown."""
    from config import load_config
    from query import render_stats, render_warning

    cfg = load_config()
    render_stats(cfg)

    if not _primary_search_ready():
        render_warning(
            "Primary search (--raw off) needs distillation backfill.\n"
            "Use --raw now, or: rm ~/.local/share/convmem/processed.json && convmem index"
        )


@app.command()
def add(
    file: str | None = typer.Option(
        None, "--file", help="JSONL file of observation records to batch-ingest"
    ),
    title: str | None = typer.Option(None, "--title", help="Short, specific title"),
    summary: str | None = typer.Option(None, "--summary", help="1-2 self-contained sentences"),
    keyword: list[str] = typer.Option(
        [], "--keyword", help="Repeatable; needs >=3 total, e.g. --keyword wp-rocket --keyword cache"
    ),
    domain: str = typer.Option(
        "general", "--domain", help="e.g. web_stack.wordpress.plugins, web_stack.security"
    ),
    author: str | None = typer.Option(
        None, "--author", help="Which model/tool produced this (required)"
    ),
    unit_type: str = typer.Option(
        "observation", "--type", help="observation | solution | decision | explanation | pattern"
    ),
    confidence: float = typer.Option(0.8, "--confidence"),
    tool: str = typer.Option("observation", "--tool", help="Tool name, e.g. openclaw"),
    source_path: str | None = typer.Option(
        None, "--source-path", help="URL, log path, or 'runtime:checkout-page'"
    ),
    upsert: bool = typer.Option(
        False,
        "--upsert",
        help="Update existing units by ledger id (document + embedding + metadata)",
    ),
):
    """Write a tool/model-sourced finding directly into the index — no chat needed.

    This is the path for non-conversational sources: security scanners, log
    parsers, HTTP probes, OpenClaw browser sessions, etc. Either pass a
    single record via flags, or --file a JSONL batch (one record per line).
    """
    _guard_write()
    from config import load_config
    from chroma_store import ChromaStore
    from observe import ingest_observation, ingest_observation_file
    from query import render_error, render_warning
    from pathlib import Path

    cfg = load_config()
    models = cfg["models"]

    if upsert:
        from restic_gate import ensure_chroma_snapshot_for_live_write

        ensure_chroma_snapshot_for_live_write()

    store = ChromaStore(cfg["index"]["chroma_dir"])
    units_export = cfg["index"].get("units_export")
    units_export_path = Path(units_export).expanduser() if units_export else None

    if file:
        result = ingest_observation_file(
            file,
            store=store,
            embed_model=models["embed_model"],
            ollama_host=models["ollama_host"],
            units_export=units_export_path,
            upsert=upsert,
        )
        parts = [
            f"accepted={result['accepted']}",
            f"rejected={result['rejected']}",
        ]
        if upsert:
            parts.append(f"updated={result['updated']}")
        typer.echo(f"\nDone. {' '.join(parts)}")
        return

    if not title or not summary or not author:
        render_error("Provide --title, --summary, and --author (or use --file for batch ingest).")
        raise typer.Exit(1)
    if len(keyword) < 3:
        render_error("Need at least 3 --keyword values.")
        raise typer.Exit(1)

    record = {
        "title": title,
        "summary": summary,
        "keywords": keyword,
        "type": unit_type,
        "domain": domain,
        "author_model": author,
        "confidence": confidence,
        "tool": tool,
        "source_path": source_path,
    }
    unit = ingest_observation(
        record,
        store=store,
        embed_model=models["embed_model"],
        ollama_host=models["ollama_host"],
        units_export=units_export_path,
    )
    if unit is None:
        render_error("Record rejected — check required fields.")
        raise typer.Exit(1)
    typer.echo(f"Added [{unit['domain']}] {unit['title']}  (ledger: {unit.get('ledger_id', unit['id'])})")


@app.command("verify")
def verify_command(
    unit_id: str = typer.Argument(
        ..., help="Chroma unit id or ledger id (e.g. obs_20260617_001)"
    ),
    model: str = typer.Option(..., "--model", help="Verifying model/tool name"),
    confidence: float | None = typer.Option(
        None, "--confidence", help="Verifier's confidence; defaults to the existing value"
    ),
    notes: str | None = typer.Option(
        None, "--notes", help="Verification notes (also used as ledger summary)"
    ),
    result: str = typer.Option(
        "pass", "--result", help="pass | fail — outcome of the verification check"
    ),
    no_record: bool = typer.Option(
        False, "--no-record", help="Only update metadata; skip verification ledger ingest"
    ),
    emit_file: str | None = typer.Option(
        None,
        "--emit-file",
        help="Append verification JSONL to this path (in addition to ingest)",
    ),
):
    """Record a verifier's check on an existing observation (metadata + ledger record)."""
    _guard_write()
    import json
    from pathlib import Path

    from config import load_config
    from chroma_store import ChromaStore
    from query import render_error
    from verify import verify_unit

    cfg = load_config()
    models = cfg["models"]
    store = ChromaStore(cfg["index"]["chroma_dir"])
    units_export = cfg["index"].get("units_export")
    units_export_path = Path(units_export).expanduser() if units_export else None

    meta = verify_unit(
        store,
        unit_id,
        verifier_model=model,
        confidence=confidence,
        notes=notes,
        result=result,
        record_ledger=not no_record,
        embed_model=models["embed_model"],
        ollama_host=models["ollama_host"],
        units_export=units_export_path,
    )
    if meta is None:
        render_error(f"No unit found with id {unit_id}.")
        raise typer.Exit(1)

    if emit_file:
        relates_to = meta.get("ledger_id") or unit_id
        record = {
            "id": f"ver_{relates_to}",
            "kind": "verification",
            "author_model": model,
            "relates_to": relates_to,
            "result": result,
            "summary": notes or f"Verified {meta.get('title', relates_to)}: {result}",
            "notes": notes or "",
            "domain": meta.get("domain") or "web_stack.security",
            "site": meta.get("site") or "",
            "timestamp": meta.get("verified_at"),
        }
        path = Path(emit_file).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        typer.echo(f"Appended verification → {path}")

    typer.echo(
        f"Verified '{meta.get('title', unit_id)}' — "
        f"ledger={meta.get('ledger_id') or unit_id} "
        f"verifier={model} result={result} confidence={meta.get('verified_confidence')}"
    )


@app.command()
def watch(
    debounce: float | None = typer.Option(
        None, "--debounce", help="Seconds after last write before indexing (default from config)"
    ),
    path: list[str] = typer.Option(
        [],
        "--path",
        help="Watch roots only (repeatable); replaces [sources]/[watch] paths when set",
    ),
    no_lock: bool = typer.Option(False, "--no-lock", help="Skip PID lock (debug only)"),
):
    """Watch transcript paths and run incremental index when files change."""
    _guard_write()
    from watch import run_watch

    extra = path if path else None
    run_watch(
        debounce_seconds=debounce,
        paths=extra,
        use_lock=not no_lock,
        verbose=True,
    )


@app.command()
def refine(
    once: bool = typer.Option(False, "--once", help="Run one job batch and exit"),
    job: str | None = typer.Option(None, "--job", help=f"Job name: {', '.join(__import__('refine').JOB_NAMES)}"),
    limit: int | None = typer.Option(None, "--limit", help="Max items per job run"),
    stats_only: bool = typer.Option(False, "--stats", help="Print refine_stats.json and exit"),
    approve_dedupe: str | None = typer.Option(
        None,
        "--approve-dedupe",
        help="Apply approved dedupe_queue row (1-based line) or 'all'",
    ),
    no_lock: bool = typer.Option(False, "--no-lock", help="Skip PID lock (daemon only)"),
):
    """Background index refinement — dedupe, domain backfill, audit queue (F1)."""
    if not stats_only:
        _guard_write()
    from refine import (
        JOB_NAMES,
        apply_approved_dedupe,
        print_stats,
        run_job,
        run_refine_daemon,
    )

    if approve_dedupe is not None:
        try:
            result = apply_approved_dedupe(approve_dedupe, verbose=True)
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc
        typer.echo(json.dumps(result, indent=2))
        return
    if stats_only:
        print_stats()
        return
    if once:
        if not job:
            typer.echo(f"--once requires --job. Choices: {', '.join(JOB_NAMES)}")
            raise typer.Exit(1)
        result = run_job(job, limit=limit, verbose=True)
        typer.echo(json.dumps(result, indent=2))
        return
    run_refine_daemon(verbose=True, use_lock=not no_lock)


@app.command("monitor")
def monitor_command(
    site: str = typer.Option(
        "staging2.willowyhollow.com",
        "--site",
        help="Hostname to probe (default: staging2)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run probes and print actions without writing to the ledger",
    ),
):
    """HTTP security probes — observations or advisory verifications (F2b)."""
    if not dry_run:
        _guard_write()
    import json
    from pathlib import Path

    from config import load_config
    from chroma_store import ChromaStore
    from monitor import run_monitor

    cfg = load_config()
    models = cfg["models"]
    store = ChromaStore(cfg["index"]["chroma_dir"])
    units_export = cfg["index"].get("units_export")
    units_export_path = Path(units_export).expanduser() if units_export else None

    stats = run_monitor(
        store,
        site=site,
        embed_model=models["embed_model"],
        ollama_host=models["ollama_host"],
        units_export=units_export_path,
        dry_run=dry_run,
        verbose=True,
    )
    typer.echo(json.dumps(stats, indent=2))
    from brief import refresh_brief_after_change

    refresh_brief_after_change(cfg)


@app.command()
def tldr(
    lane: str | None = typer.Option(
        None,
        "--lane",
        help="Force lane: willowyhollow-practice | convmem (default: infer from cwd)",
    ),
    list_lanes: bool = typer.Option(False, "--list", help="List available TLDR lanes"),
):
    """Print a one-page cheat sheet for the current workspace (or --lane)."""
    from query import render_error
    from tldr import list_lanes as lanes, read_tldr, resolve_tldr_path

    if list_lanes:
        typer.echo("TLDR lanes:")
        for name in lanes():
            path = resolve_tldr_path(lane=name)
            typer.echo(f"  {name}  →  {path}")
        return

    try:
        path = resolve_tldr_path(lane=lane)
        text = read_tldr(lane=lane)
    except FileNotFoundError as exc:
        render_error(str(exc))
        raise typer.Exit(1) from exc

    typer.echo(text.rstrip())
    typer.echo("")
    typer.echo(f"(from {path})")
    from next_steps import emit_next_steps

    ctx_lane = lane or __import__("next_steps").workspace_context().get("lane", "")
    if "willowyhollow" in str(ctx_lane):
        emit_next_steps(
            [
                "Full: ~/Projects/convmem/docs/WILLOWYHOLLOW-WEBDEV-GUIDE.md",
                "convmem brief --stdout-only",
            ]
        )
    else:
        emit_next_steps(
            [
                "Full: ~/Projects/convmem/docs/MODEL-WORKFLOW.md",
                "convmem brief --stdout-only",
            ]
        )


@app.command()
def brief(
    print_: bool = typer.Option(False, "--print", help="Also print brief to stdout"),
    out: str | None = typer.Option(None, "--out", help="Output path (default ~/.local/share/convmem/brief.md)"),
    with_tests: bool = typer.Option(False, "--with-tests", help="Run unit tests and include count in brief"),
    stdout_only: bool = typer.Option(False, "--stdout-only", help="Print only; do not write brief.md"),
):
    """Generate a read-only shared context block for multi-agent sessions."""
    from config import load_config
    from brief import gather_brief_data, render_brief_markdown, write_brief

    cfg = load_config()
    data = gather_brief_data(cfg, with_tests=with_tests)
    text = render_brief_markdown(data)

    if stdout_only:
        typer.echo(text)
        from next_steps import after_brief

        stale = (data.get("handoff_staleness") or {}).get("stale", False)
        after_brief(
            unresolved_count=int(data.get("unresolved_count") or 0),
            stale_handoff=bool(stale),
        )
        return

    path = write_brief(cfg, out_path=out, with_tests=with_tests, quiet=True)
    if print_:
        typer.echo(text)
    typer.echo(f"Written → {path}")
    from next_steps import after_brief

    stale = (data.get("handoff_staleness") or {}).get("stale", False)
    after_brief(
        unresolved_count=int(data.get("unresolved_count") or 0),
        stale_handoff=bool(stale),
    )


@app.command()
def doctor(
    v1: bool = typer.Option(False, "--v1", help="Include watch RSS, systemd, and lock checks"),
    verify: bool = typer.Option(False, "--verify", help="Run scripts/verify-continue.sh smoke test"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of text"),
):
    """Health checks for the canonical host (reuse brief probes; exit 0 = PASS)."""
    import json

    from doctor import doctor_exit_code, doctor_payload, render_doctor_text, run_doctor

    try:
        checks = run_doctor(v1=v1, run_verify=verify)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    if json_out:
        typer.echo(json.dumps(doctor_payload(checks), indent=2))
    else:
        typer.echo(render_doctor_text(checks))
        from next_steps import after_doctor

        after_doctor(passed=doctor_exit_code(checks) == 0, v1=v1)
    raise typer.Exit(doctor_exit_code(checks))


def _resolve_approve_signer(signer: str | None) -> str:
    return (signer or os.environ.get("CONVMEM_SIGNER") or "ryan").strip()


def _finish_record_messages(
    proposal: dict,
    ledger: dict,
    *,
    indexed: bool,
    ingest: dict | None = None,
    approved_file: str | None = None,
) -> None:
    summary = (proposal.get("summary") or "").strip()
    lid = ledger.get("id", proposal.get("id", "?"))
    site = (proposal.get("site") or "").strip()
    q = summary[:72] if summary else lid
    if site:
        q = f"{site} {q}"[:80]
    typer.echo(f"✓ Recorded: {summary or lid}")
    typer.echo(f"  Ledger id: {lid}")
    if indexed:
        if ingest:
            typer.echo(
                f"  Indexed (accepted={ingest.get('accepted', 0)}, "
                f"updated={ingest.get('updated', 0)}, "
                f"skipped={ingest.get('skipped', 0)})"
            )
        else:
            typer.echo("  Indexed — searchable via convmem search / MCP ask.")
    elif approved_file:
        typer.echo(
            f"  Skipped index (--no-index). Run: convmem add --file {approved_file} --upsert"
        )
    typer.echo(f'  Try: convmem search "{q}"')
    from next_steps import after_record_approved

    after_record_approved(summary=summary, ledger_id=lid, site=site)


def _pending_record_hint() -> None:
    from next_steps import after_record_pending

    typer.echo("  Finish recording: convmem record --approve-last")
    after_record_pending()


@app.command("propose_decision")
def propose_decision_command(
    list_: bool = typer.Option(False, "--list", help="Show pending drafts"),
    all_: bool = typer.Option(False, "--all", help="With --list: include approved/rejected"),
    json_out: bool = typer.Option(False, "--json", help="With --list: emit raw JSONL records"),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Record a fact interactively (prompts for each field)",
    ),
    approve: str | None = typer.Option(None, "--approve", help="Approve a specific draft id"),
    approve_last: bool = typer.Option(
        False,
        "--approve-last",
        help="Approve the newest pending draft (no id to remember)",
    ),
    no_index: bool = typer.Option(
        False,
        "--no-index",
        help="On approve: skip auto-index (default indexes into search)",
    ),
    reject: str | None = typer.Option(None, "--reject", help="Reject a draft id"),
    signer: str | None = typer.Option(
        None,
        "--signer",
        help="Signer on approve/reject (default on approve: ryan or CONVMEM_SIGNER)",
    ),
    reason: str | None = typer.Option(None, "--reason", help="Required for --reject"),
    ledger_id: str | None = typer.Option(
        None, "--ledger-id", help="Canonical ledger id on approve (default: proposal id)"
    ),
    parse_doc: str | None = typer.Option(
        None, "--parse-doc", help="Scan inter-model doc for DECISION PROPOSED blocks (v2)"
    ),
    relates_to: str | None = typer.Option(None, "--relates-to", help="Parent observation/decision id"),
    summary: str | None = typer.Option(None, "--summary", help="One-sentence choice"),
    rationale: str | None = typer.Option(None, "--rationale", help="Why this choice"),
    author: str | None = typer.Option(None, "--author", help="Proposing model or human id"),
    alternative: list[str] | None = typer.Option(
        None, "--alternative", help="Rejected alternative (repeatable)"
    ),
    alternatives_rejected: list[str] | None = typer.Option(
        None, "--alternatives-rejected", help="Rejected alternative (repeatable)"
    ),
    constraint: list[str] | None = typer.Option(
        None, "--constraint", help="Hard constraint (repeatable)"
    ),
    constraints: list[str] | None = typer.Option(
        None, "--constraints", help="Hard constraint (repeatable)"
    ),
    domain: str = typer.Option("coding.tooling", "--domain", help="Domain tag"),
    site: str = typer.Option("", "--site", help="Site tag (optional)"),
    confidence: float = typer.Option(0.8, "--confidence", help="Confidence 0–1"),
    proposal_id: str | None = typer.Option(None, "--id", help="Explicit proposal id"),
):
    """Record a durable fact (alias: `convmem record`).

    Draft: `record -i` or flags. Finish: `record --approve-last` (indexes automatically).
    """
    from config import load_config
    from propose_decision import (
        InteractiveLockError,
        approve as do_approve,
        approved_path,
        collect_interactive_fields,
        confirm_interactive_submit,
        ingest_approved_file,
        ingest_approved_ledger,
        interactive_session_lock,
        latest_pending,
        list_proposals,
        propose as do_propose,
        reject as do_reject,
    )
    from query import render_error

    if parse_doc:
        render_error("--parse-doc is not yet implemented (reserved for v2)")
        raise typer.Exit(1)

    if approve and approve_last:
        render_error("Use --approve or --approve-last, not both")
        raise typer.Exit(1)

    cfg = load_config()

    if list_:
        rows = list_proposals(cfg, show_all=all_)
        if json_out:
            for row in rows:
                typer.echo(json.dumps(row, ensure_ascii=False))
            return
        if not rows:
            typer.echo(
                "No pending drafts." if not all_ else "No drafts."
            )
            if not all_:
                typer.echo("  Start one: convmem record -i")
            return
        typer.echo(f"{'PENDING' if not all_ else 'ALL'} ({len(rows)})")
        for row in rows:
            pid = row.get("id", "?")
            status = row.get("status", "PENDING")
            site_s = row.get("site") or "(no site)"
            typer.echo(f"  {pid}  [{status}]  {site_s}  {row.get('domain', '')}")
            typer.echo(f"    {row.get('summary', '')}")
            typer.echo(
                f"    proposed by {row.get('proposed_by', '?')} · "
                f"relates_to {row.get('relates_to', '?')} · {row.get('proposed_at', '?')}"
            )
            if row.get("rejection_reason"):
                typer.echo(f"    rejected: {row['rejection_reason']}")
        if not all_ and rows:
            typer.echo("")
            typer.echo("  Finish newest: convmem record --approve-last")
        return

    _guard_write()

    approve_id = approve
    if approve_last:
        pending = latest_pending(cfg)
        if pending is None:
            render_error("No pending drafts to approve. Record one with: convmem record -i")
            raise typer.Exit(1)
        approve_id = pending["id"]

    if approve_id:
        resolved_signer = _resolve_approve_signer(signer)
        try:
            proposal, ledger = do_approve(
                cfg, approve_id, signer=resolved_signer, ledger_id=ledger_id
            )
        except ValueError as e:
            render_error(str(e))
            raise typer.Exit(1) from e
        ingest_result = None
        apath = str(approved_path(cfg))
        if not no_index:
            from restic_gate import ensure_chroma_snapshot_for_live_write

            ensure_chroma_snapshot_for_live_write()
            try:
                ingest_result = ingest_approved_ledger(cfg, ledger)
            except Exception as e:
                _log_index_failure(approve_id, e)
                typer.echo(f"\n⚠  Approved (ledger) but index deferred: {e}")
                typer.echo(f"  Recovery: convmem add --file {apath} --upsert")
                typer.echo(f"  The decision is durable in the ledger; Chroma will catch up on next index.\n")
        _finish_record_messages(
            proposal,
            ledger,
            indexed=not no_index,
            ingest=ingest_result,
            approved_file=apath if no_index else None,
        )
        return

    if reject:
        if not signer:
            render_error("--signer is required with --reject")
            raise typer.Exit(1)
        try:
            proposal = do_reject(cfg, reject, signer=signer, reason=reason or "")
        except ValueError as e:
            render_error(str(e))
            raise typer.Exit(1) from e
        typer.echo(f"Rejected: {proposal['id']}")
        typer.echo(f"  Reason: {proposal.get('rejection_reason', '')}")
        return

    alts = list(alternative or []) + list(alternatives_rejected or [])
    cons = list(constraint or []) + list(constraints or [])

    if interactive:
        try:
            with interactive_session_lock(cfg):
                fields = collect_interactive_fields(
                    relates_to=relates_to or "",
                    summary=summary or "",
                    rationale=rationale or "",
                    author=author or "",
                    domain=domain,
                    site=site,
                    constraints=cons,
                    prompt=typer.prompt,
                )
                relates_to = fields["relates_to"]
                summary = fields["summary"]
                rationale = fields["rationale"]
                author = fields["author"]
                domain = fields["domain"]
                site = fields["site"]
                cons = fields["constraints"]
                if not relates_to or not summary or not rationale or not author:
                    render_error("Interactive propose requires all core fields")
                    raise typer.Exit(1)
                if not confirm_interactive_submit(
                    cfg,
                    fields,
                    confirm=typer.confirm,
                    echo=typer.echo,
                ):
                    typer.echo("Cancelled — proposal not submitted.")
                    raise typer.Exit(0)
                rec = do_propose(
                    cfg,
                    relates_to=relates_to,
                    summary=summary,
                    rationale=rationale,
                    author=author,
                    alternatives=alts,
                    constraints=cons,
                    domain=domain,
                    site=site,
                    confidence=confidence,
                    proposal_id=proposal_id,
                )
        except InteractiveLockError as e:
            render_error(str(e))
            raise typer.Exit(1) from e
        except ValueError as e:
            render_error(str(e))
            raise typer.Exit(1) from e
        typer.echo(f"Draft saved (pending): {rec['id']}")
        typer.echo(f"  Summary: {rec['summary']}")
        typer.echo(f"  Relates-to: {rec['relates_to']}")
        _pending_record_hint()
        return

    if not relates_to or not summary or not rationale or not author:
        render_error(
            "Record requires --relates-to, --summary, --rationale, and --author "
            "(or use -i / --list / --approve / --approve-last / --reject)"
        )
        raise typer.Exit(1)

    try:
        rec = do_propose(
            cfg,
            relates_to=relates_to,
            summary=summary,
            rationale=rationale,
            author=author,
            alternatives=alts,
            constraints=cons,
            domain=domain,
            site=site,
            confidence=confidence,
            proposal_id=proposal_id,
        )
    except ValueError as e:
        render_error(str(e))
        raise typer.Exit(1) from e

    typer.echo(f"Draft saved (pending): {rec['id']}")
    typer.echo(f"  Summary: {rec['summary']}")
    typer.echo(f"  Relates-to: {rec['relates_to']}")
    _pending_record_hint()


@app.command("record")
def record_command(
    list_: bool = typer.Option(False, "--list", help="Show pending drafts"),
    all_: bool = typer.Option(False, "--all", help="With --list: include approved/rejected"),
    json_out: bool = typer.Option(False, "--json", help="With --list: emit raw JSONL records"),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Record a fact interactively",
    ),
    approve: str | None = typer.Option(None, "--approve", help="Approve a specific draft id"),
    approve_last: bool = typer.Option(
        False,
        "--approve-last",
        help="Approve newest pending draft and index (default workflow)",
    ),
    no_index: bool = typer.Option(False, "--no-index", help="On approve: skip auto-index"),
    reject: str | None = typer.Option(None, "--reject", help="Reject a draft id"),
    signer: str | None = typer.Option(None, "--signer", help="Signer (default on approve: ryan)"),
    reason: str | None = typer.Option(None, "--reason", help="Required for --reject"),
    ledger_id: str | None = typer.Option(None, "--ledger-id", help="Canonical ledger id on approve"),
    parse_doc: str | None = typer.Option(None, "--parse-doc", hidden=True),
    relates_to: str | None = typer.Option(None, "--relates-to"),
    summary: str | None = typer.Option(None, "--summary"),
    rationale: str | None = typer.Option(None, "--rationale"),
    author: str | None = typer.Option(None, "--author"),
    alternative: list[str] | None = typer.Option(None, "--alternative"),
    alternatives_rejected: list[str] | None = typer.Option(None, "--alternatives-rejected"),
    constraint: list[str] | None = typer.Option(None, "--constraint"),
    constraints: list[str] | None = typer.Option(None, "--constraints"),
    domain: str = typer.Option("coding.tooling", "--domain"),
    site: str = typer.Option("", "--site"),
    confidence: float = typer.Option(0.8, "--confidence"),
    proposal_id: str | None = typer.Option(None, "--id"),
):
    """Record a durable fact for all agents (`record -i` → `record --approve-last`)."""
    propose_decision_command(
        list_=list_,
        all_=all_,
        json_out=json_out,
        interactive=interactive,
        approve=approve,
        approve_last=approve_last,
        no_index=no_index,
        reject=reject,
        signer=signer,
        reason=reason,
        ledger_id=ledger_id,
        parse_doc=parse_doc,
        relates_to=relates_to,
        summary=summary,
        rationale=rationale,
        author=author,
        alternative=alternative,
        alternatives_rejected=alternatives_rejected,
        constraint=constraint,
        constraints=constraints,
        domain=domain,
        site=site,
        confidence=confidence,
        proposal_id=proposal_id,
    )


@app.command()
def related(
    ledger_id: str = typer.Argument(..., help="Observation, decision, or verification id"),
):
    """Traverse the evidence graph around a ledger id (not semantic search)."""
    from config import load_config
    from chroma_readonly import open_readonly_unit_store
    from query import render_error
    from related import render_related

    cfg = load_config()
    store = open_readonly_unit_store(cfg["index"]["chroma_dir"])
    if not render_related(store, ledger_id):
        render_error(f"Ledger id not found: {ledger_id.strip()}")
        raise typer.Exit(1)


@app.command("unresolved")
def unresolved_command(
    site: str | None = typer.Option(None, "--site", help="Filter by site hostname"),
    domain: str | None = typer.Option(None, "--domain", help="Filter by domain"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of table"),
):
    """List open observations — no LLM, just the ledger graph.

    Shows every observation without a passing verification, plus any with a
    failed check. Filter by --site and/or --domain.
    """
    import json

    from config import load_config
    from chroma_readonly import open_readonly_unit_store
    from unresolved import list_unresolved, render_unresolved, unresolved_payload

    cfg = load_config()
    store = open_readonly_unit_store(cfg["index"]["chroma_dir"])
    payload = unresolved_payload(store, site=site, domain=domain)

    if json_out:
        typer.echo(json.dumps(payload["items"], indent=2))
    else:
        items = list_unresolved(store, site=site, domain=domain)
        render_unresolved(items)
        from next_steps import after_unresolved

        after_unresolved(site=site, count=len(items))


@app.command("exclude")
def exclude_command(
    path: str = typer.Argument(None, help="File path to exclude from indexing"),
    reason: str = typer.Option("", "--reason", help="Why this conversation is excluded"),
    list_: bool = typer.Option(False, "--list", help="Show all excluded conversations"),
    undo: str = typer.Option(None, "--undo", help="Re-include a previously excluded file path"),
):
    """Mark a conversation as excluded from indexing, or list/undo exclusions."""
    from pathlib import Path

    from config import load_config
    from ingest import load_processed, save_processed, sha256_file
    from query import render_error, render_warning

    cfg = load_config()
    processed_path = cfg["index"]["processed_log"]
    processed = load_processed(processed_path)

    if list_:
        excluded = [
            (h, e) for h, e in processed.items()
            if isinstance(e, dict) and e.get("excluded")
        ]
        if not excluded:
            typer.echo("No excluded conversations.")
            return
        typer.echo(f"{len(excluded)} excluded conversation(s):\n")
        for h, entry in excluded:
            p = entry.get("path", "?")
            r = entry.get("exclude_reason") or "—"
            typer.echo(f"  {p}")
            typer.echo(f"    reason: {r}")
            typer.echo()
        return

    _guard_write()

    if undo:
        target = str(Path(undo).expanduser().resolve())
        found = False
        for h, entry in processed.items():
            if isinstance(entry, dict) and entry.get("path") == target and entry.get("excluded"):
                entry.pop("excluded", None)
                entry.pop("exclude_reason", None)
                save_processed(processed_path, processed)
                typer.echo(f"Re-included: {target}")
                typer.echo("Run 'convmem index' to ingest it.")
                found = True
                break
        if not found:
            render_error(f"Not found in excluded list: {target}")
            raise typer.Exit(1)
        return

    if not path:
        render_error("Provide a file path to exclude, or use --list / --undo.")
        raise typer.Exit(1)

    target = str(Path(path).expanduser().resolve())
    if not Path(target).is_file():
        render_error(f"File not found: {target}")
        raise typer.Exit(1)

    try:
        file_hash = sha256_file(target)
    except OSError as e:
        render_error(f"Cannot read file: {e}")
        raise typer.Exit(1)

    entry = processed.get(file_hash, {})
    if not isinstance(entry, dict):
        entry = {}
    entry["path"] = target
    entry["excluded"] = True
    if reason:
        entry["exclude_reason"] = reason
    processed[file_hash] = entry
    save_processed(processed_path, processed)
    typer.echo(f"Excluded: {Path(target).name}")
    if reason:
        typer.echo(f"  reason: {reason}")


def main():
    # Convenience: `convmem "query"` routes to the search command when the
    # first token isn't a known subcommand.
    argv = sys.argv[1:]
    if argv and not argv[0].startswith("-") and argv[0] not in _SUBCOMMANDS:
        sys.argv = [sys.argv[0], "search"] + argv
    app()


if __name__ == "__main__":
    main()
