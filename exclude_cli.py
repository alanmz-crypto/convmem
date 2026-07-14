#!/usr/bin/env python3
"""CLI helpers for ``convmem exclude`` purge/undo (keeps convmem.py lean)."""

from __future__ import annotations

from pathlib import Path

import typer


def resolve_purge_target(path: str) -> str:
    """Resolve a purge target for the purge API.

    Existing relative files may be resolved here. Missing-file targets must
    already be absolute or home-qualified.
    """
    path_obj = Path(path).expanduser()
    if not str(path).startswith(("/", "~")):
        if path_obj.is_file():
            return str(path_obj.resolve())
        raise ValueError(
            "Missing-file purge targets must be absolute or home-qualified "
            f"(got {path!r})"
        )
    try:
        return str(path_obj.resolve())
    except OSError:
        return str(path_obj)


def resolve_undo_target(path: str) -> str:
    """Resolve an undo target to an absolute / home-qualified path."""
    path_obj = Path(path).expanduser()
    if not str(path).startswith(("/", "~")):
        if path_obj.is_file():
            return str(path_obj.resolve())
        # Soft-exclude undo historically resolved even when missing.
        return str(path_obj.resolve())
    try:
        return str(path_obj.resolve())
    except OSError:
        return str(path_obj)


def run_exclude_undo(cfg: dict, undo: str, *, echo, render_error) -> None:
    from source_purge import undo_exclude_source

    target = resolve_undo_target(undo)
    if not undo_exclude_source(cfg, target):
        render_error(f"Not found in excluded list: {target}")
        raise typer.Exit(1)
    echo(f"Re-included: {target}")
    echo("Run 'convmem index' to ingest it.")


def run_exclude_purge(
    cfg: dict,
    path: str,
    reason: str,
    yes: bool,
    *,
    echo,
    confirm,
    render_error,
) -> None:
    from source_purge import execute_purge, preview_purge

    try:
        purge_target = resolve_purge_target(path)
    except ValueError as exc:
        render_error(str(exc))
        raise typer.Exit(1) from exc

    path_obj = Path(path).expanduser()
    if not Path(purge_target).is_file() and not path_obj.is_file():
        echo(
            f"Warning: file not found on disk ({path}); "
            "purging derived rows and writing synthetic exclusion marker."
        )
    try:
        preview = preview_purge(cfg, purge_target)
    except ValueError as exc:
        render_error(str(exc))
        raise typer.Exit(1) from exc

    echo(f"Purge preview for: {preview.canonical_path}")
    echo(f"  Chroma knowledge_units:        {preview.units} units")
    echo(f"  Chroma conversation_summaries: {preview.summaries} summaries")
    echo(f"  knowledge_units.jsonl:          {preview.jsonl_lines} lines")
    echo("")
    echo("This is logical removal from active derived stores.")
    echo(
        "Residual bytes may persist in Chroma free-space, filesystem blocks, "
        "and Restic snapshots."
    )
    echo(
        "This cannot be undone (re-indexing from source required after --undo)."
    )
    if not yes:
        if not confirm("Proceed?", default=False):
            echo("Aborted.")
            raise typer.Exit(0)
    result = execute_purge(cfg, purge_target, reason=reason)
    if result.exit_code == 0:
        echo(
            f"Purged: {Path(result.canonical_path).name} "
            f"(units={result.units_deleted} summaries={result.summaries_deleted} "
            f"jsonl={result.jsonl_removed})"
        )
    else:
        render_error(result.message or "purge incomplete")
    raise typer.Exit(result.exit_code)


def run_exclude_list(processed: dict, *, echo) -> None:
    excluded = [
        (h, e) for h, e in processed.items()
        if isinstance(e, dict) and e.get("excluded")
    ]
    if not excluded:
        echo("No excluded conversations.")
        return
    echo(f"{len(excluded)} excluded conversation(s):\n")
    for _h, entry in excluded:
        p = entry.get("path", "?")
        r = entry.get("exclude_reason") or "—"
        echo(f"  {p}")
        echo(f"    reason: {r}")
        echo()


def run_exclude_soft(cfg: dict, path: str, reason: str, *, echo, render_error) -> None:
    from ingest import exclude_processed_path, sha256_file

    target = str(Path(path).expanduser().resolve())
    if not Path(target).is_file():
        render_error(f"File not found: {target}")
        raise typer.Exit(1)
    try:
        file_hash = sha256_file(target)
    except OSError as exc:
        render_error(f"Cannot read file: {exc}")
        raise typer.Exit(1) from exc
    exclude_processed_path(cfg["index"]["processed_log"], target, file_hash, reason=reason)
    echo(f"Excluded: {Path(target).name}")
    if reason:
        echo(f"  reason: {reason}")
