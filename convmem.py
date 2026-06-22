"""convmem CLI (typer).

Usage:
  convmem "query"            search (raw summaries in Step 4)
  convmem "query" --raw      explicit fallback over conversation summaries
  convmem "query" --top 10   more results
  convmem "query" --domain web_stack.security   scope to a domain (+children)
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
"""

import json
import sys

import typer

from chroma_readonly import collection_count
from open_source import run_open

app = typer.Typer(add_completion=False, help="Search your past AI conversations.")

_SUBCOMMANDS = {
    "index", "stats", "search", "ask", "open", "add", "verify", "related",
    "watch", "refine", "monitor", "exclude", "brief",
}
# Primary search is misleading until distillation backfill catches up to summaries.
_MIN_UNITS_FOR_PRIMARY = 50


def _unit_count() -> int:
    from config import load_config

    cfg = load_config()
    return collection_count(cfg["index"]["chroma_dir"], "knowledge_units")


def _primary_search_ready() -> bool:
    return _unit_count() >= _MIN_UNITS_FOR_PRIMARY


@app.command()
def search(
    query: str = typer.Argument(..., help="What you're trying to recall"),
    raw: bool = typer.Option(False, "--raw", help="Search conversation summaries (fallback layer)"),
    top: int = typer.Option(5, "--top", help="Number of results"),
    domain: str | None = typer.Option(
        None, "--domain", help="Scope to a domain and its children, e.g. web_stack.security"
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
        results = query_raw(query, top_k=top)
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
        results = query_units(query, top_k=top, domain=domain)
        render_search_results(results, units=True)

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
        run_interactive(top_k=top, raw=raw, first_question=question, domain=domain, evidence=evidence)
        return
    if not question:
        render_error("Provide a question, or use -i for interactive mode.")
        raise typer.Exit(1)

    out = ask(question, top_k=top, raw=raw, domain=domain, evidence=evidence)
    render_ask_output(out)
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
    from ingest import index as run_index

    stats = run_index(force_file=file, limit_files=limit, force_reindex=force)
    typer.echo("")
    typer.echo(
        f"Done. files_processed={stats['files_processed']} "
        f"files_skipped={stats['files_skipped']} "
        f"chunks_indexed={stats['chunks_indexed']} "
        f"units_indexed={stats.get('units_indexed', 0)}"
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
    from config import load_config
    from chroma_store import ChromaStore
    from observe import ingest_observation, ingest_observation_file
    from query import render_error, render_warning
    from pathlib import Path

    cfg = load_config()
    models = cfg["models"]
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
    no_lock: bool = typer.Option(False, "--no-lock", help="Skip PID lock (daemon only)"),
):
    """Background index refinement — dedupe, domain backfill, audit queue (F1)."""
    from refine import JOB_NAMES, print_stats, run_job, run_refine_daemon

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
        return

    path = write_brief(cfg, out_path=out, with_tests=with_tests, quiet=True)
    if print_:
        typer.echo(text)
    typer.echo(f"Written → {path}")


@app.command()
def related(
    ledger_id: str = typer.Argument(..., help="Observation, decision, or verification id"),
):
    """Traverse the evidence graph around a ledger id (not semantic search)."""
    from config import load_config
    from chroma_store import ChromaStore
    from query import render_error
    from related import render_related

    cfg = load_config()
    store = ChromaStore(cfg["index"]["chroma_dir"])
    if not render_related(store, ledger_id):
        render_error(f"Ledger id not found: {ledger_id.strip()}")
        raise typer.Exit(1)


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
