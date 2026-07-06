#!/usr/bin/env python3
"""
inventory.py — Step 2 (corrected)
Walk source paths, detect file formats, report counts and sizes.
Does not parse message content. Output: inventory.jsonl + terminal summary.
"""

import json
import sqlite3
from collections import Counter
from pathlib import Path

from adapters.kiro_session_jsonl import is_kiro_session_jsonl
from adapters.codex_history_jsonl import is_codex_history_jsonl
from adapters.codex_rollout_jsonl import is_codex_rollout_jsonl
from adapters.inter_model_doc import is_inter_model_doc
from adapters.sqlite_chat import is_sqlite_crush_schema

OUTPUT = Path("~/.local/share/convmem/inventory.jsonl").expanduser()

SOURCES = [
    "~/.local/share/kiro-cli/data.sqlite3",
    "~/.kiro/sessions",
    "~/.codex/history.jsonl",
    "~/.codex/sessions",
    "~/.config/cursor/chats",
    "~/.cursor/projects",
    "~/.continue/sessions",
    Path.home(),  # for aider glob only — see walk_sources
    "~/.local/share/convmem/imports/webui.db",
]

def detect_format(path: Path) -> str | None:
    # Aider — filename-exact match only
    if path.name == ".aider.chat.history.md":
        return "aider_markdown"

    if is_inter_model_doc(path):
        return "inter_model_doc"

    # All other markdown — skip
    if path.suffix == ".md":
        return None

    # JSONL — Cursor agent-transcripts, kiro-cli sessions, Codex history
    if path.suffix == ".jsonl":
        if "agent-transcripts" in path.parts:
            return "jsonl_cursor"
        if is_kiro_session_jsonl(path):
            return "jsonl_kiro_session"
        if is_codex_history_jsonl(path):
            return "jsonl_codex_history"
        if is_codex_rollout_jsonl(path):
            return "jsonl_codex_rollout"
        return None  # metrics, telemetry, other jsonl — skip

    # SQLite
    if path.suffix in (".sqlite3", ".db"):
        return detect_sqlite(path)

    # JSON — only under ~/.continue/sessions/
    if path.suffix == ".json":
        return detect_json_continue(path)

    return None

def detect_sqlite(path: Path) -> str | None:
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "conversations_v2" in tables:
            con.close()
            return "sqlite_kiro"
        if "chat_message" in tables:
            con.close()
            return "sqlite_openwebui"
        if "blobs" in tables and "meta" in tables:
            con.close()
            return "sqlite_cursor_store"
        if is_sqlite_crush_schema(con, tables):
            con.close()
            return "sqlite_crush"
        con.close()
        return None
    except Exception:
        return None

def detect_json_continue(path: Path) -> str | None:
    # Only classify JSON under ~/.continue/sessions/
    try:
        home = Path.home()
        sessions_dir = home / ".continue" / "sessions"
        path.relative_to(sessions_dir)  # raises ValueError if not under sessions
    except ValueError:
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, dict) and "history" in data:
            return "json_continue_sessions"
        return None
    except Exception:
        return None

def walk_sources(sources) -> list[dict]:
    records = []
    skips = []
    seen = set()
    home = Path.home()

    for src in sources:
        if src == home:
            # Aider + Crush — targeted globs, not full home walk
            for child in home.rglob(".aider.chat.history.md"):
                try:
                    key = str(child)
                    if key in seen:
                        continue
                    seen.add(key)
                    records.append({
                        "path": key,
                        "format": "aider_markdown",
                        "size_kb": round(child.stat().st_size / 1024, 1),
                    })
                except PermissionError:
                    skips.append(f"permission denied: {child}")
            for child in home.glob("**/.crush/crush.db"):
                try:
                    key = str(child)
                    if key in seen:
                        continue
                    fmt = detect_format(child)
                    if fmt != "sqlite_crush":
                        continue
                    seen.add(key)
                    records.append({
                        "path": key,
                        "format": fmt,
                        "size_kb": round(child.stat().st_size / 1024, 1),
                    })
                except PermissionError:
                    skips.append(f"permission denied: {child}")
            continue

        p = Path(src).expanduser()

        if not p.exists():
            skips.append(f"not found: {p}")
            continue

        try:
            p.stat()
        except PermissionError:
            skips.append(f"permission denied: {p}")
            continue

        if p.is_file():
            fmt = detect_format(p)
            if fmt:
                key = str(p)
                if key not in seen:
                    seen.add(key)
                    records.append({
                        "path": key,
                        "format": fmt,
                        "size_kb": round(p.stat().st_size / 1024, 1),
                    })
        else:
            for child in p.rglob("*"):
                if not child.is_file():
                    continue
                try:
                    fmt = detect_format(child)
                except PermissionError:
                    skips.append(f"permission denied: {child}")
                    continue
                if fmt:
                    key = str(child)
                    if key not in seen:
                        seen.add(key)
                        records.append({
                            "path": key,
                            "format": fmt,
                            "size_kb": round(child.stat().st_size / 1024, 1),
                        })

    if skips:
        print("\nSkipped:")
        for s in skips:
            print(f"  [skip] {s}")

    return records

def summarize(records: list[dict]):
    counts = Counter(r["format"] for r in records)
    total_kb = sum(r["size_kb"] for r in records)
    print(f"\n{'─'*50}")
    print(f"  Files found: {len(records)}  |  Total: {total_kb/1024:.1f} MB")
    print(f"{'─'*50}")
    for fmt, count in sorted(counts.items()):
        kb = sum(r["size_kb"] for r in records if r["format"] == fmt)
        print(f"  {fmt:<32} {count:>4} file(s)   {kb/1024:.1f} MB")
    print(f"{'─'*50}\n")

if __name__ == "__main__":
    print("Running inventory...")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    records = walk_sources(SOURCES)
    with open(OUTPUT, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    summarize(records)
    print(f"Written to {OUTPUT}")
