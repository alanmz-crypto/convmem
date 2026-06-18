"""Extract procedures from Crush tool_call/tool_result pairs.

Reads Crush DBs, pairs bash commands with their outputs, groups into
per-session procedures, then uses one LLM call per procedure for a
human-readable title + summary.

Usage:
  python extract_procedures.py                          # all Crush DBs
  python extract_procedures.py --db ~/.crush/crush.db   # one DB
  python extract_procedures.py --print                  # stdout instead of file
  convmem add --file procedures.jsonl --upsert
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from config import load_config
from domains import normalize_domain
from llm import generate

PROCEDURE_PROMPT = """Given these shell commands and their outputs from an AI coding session, write:
1. A short title (under 10 words) describing what was accomplished
2. A 1-2 sentence summary of the procedure
3. A domain dotted-path (e.g. coding.devops, web_stack.security, coding.ml)
4. 5-8 keywords (tool names, commands, concepts)

Commands:
{steps}

Reply in JSON only:
{{"title": "...", "summary": "...", "domain": "...", "keywords": ["...", ...]}}"""

_MAX_STEPS_CHARS = 4000


def _parse_input(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def extract_pairs(db_path: str) -> dict[str, list[dict]]:
    """Extract tool_call/tool_result bash pairs grouped by session."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT session_id, role, parts FROM messages ORDER BY session_id, created_at, id"
    ).fetchall()
    con.close()

    # Index all tool_results by call_id
    results_by_id: dict[str, str] = {}
    for _, _, parts_raw in rows:
        parts = json.loads(parts_raw) if parts_raw else []
        for p in parts:
            if p.get("type") == "tool_result":
                data = p.get("data", {})
                call_id = data.get("tool_call_id", "")
                content = data.get("content", "")
                if call_id:
                    results_by_id[call_id] = content[:500]

    # Pair bash calls with results
    by_session: dict[str, list[dict]] = {}
    for sid, _, parts_raw in rows:
        parts = json.loads(parts_raw) if parts_raw else []
        for p in parts:
            if p.get("type") != "tool_call":
                continue
            data = p.get("data", {})
            if data.get("name") != "bash":
                continue
            call_id = data.get("id", "")
            inp = _parse_input(data.get("input", "{}"))
            cmd = inp.get("command", "").strip()
            desc = inp.get("description", "").strip()
            if not cmd:
                continue
            outcome = results_by_id.get(call_id, "")
            by_session.setdefault(sid, []).append({
                "cmd": cmd,
                "description": desc,
                "outcome": outcome[:300],
            })

    return by_session


def _render_steps(steps: list[dict], budget: int = _MAX_STEPS_CHARS) -> str:
    lines = []
    used = 0
    for s in steps:
        line = f"$ {s['cmd']}"
        if s.get("description"):
            line = f"# {s['description']}\n{line}"
        out = s.get("outcome", "").strip()
        if out:
            line += f"\n→ {out[:150]}"
        if used + len(line) > budget:
            break
        lines.append(line)
        used += len(line)
    return "\n\n".join(lines)


def _session_short(session_id: str) -> str:
    return session_id[:12] if session_id else "unknown"


def generate_procedure(
    session_id: str,
    steps: list[dict],
    *,
    db_path: str,
    workspace: str,
    model: str,
    ollama_host: str,
    deepseek_base_url: str,
) -> dict | None:
    """Generate one procedure record with LLM title/summary."""
    if len(steps) < 2:
        return None

    rendered = _render_steps(steps)
    prompt = PROCEDURE_PROMPT.format(steps=rendered)

    try:
        raw = generate(prompt, model, ollama_host, deepseek_base_url)
    except Exception as e:
        print(f"  [warn] LLM failed for session {session_id[:8]}: {e}", file=sys.stderr)
        raw = None

    # Parse LLM response
    if raw:
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            meta = json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            meta = None
    else:
        meta = None

    if not meta or not isinstance(meta, dict):
        # Fallback: deterministic title from first command
        meta = {
            "title": f"Shell session: {steps[0]['cmd'][:40]}",
            "summary": f"{len(steps)} commands executed in Crush session",
            "domain": "coding.devops",
            "keywords": list({s["cmd"].split()[0] for s in steps[:8]}),
        }

    title = str(meta.get("title", ""))[:80]
    summary = str(meta.get("summary", ""))[:200]
    domain = normalize_domain(meta.get("domain"))
    keywords = meta.get("keywords", [])
    if not isinstance(keywords, list):
        keywords = []
    keywords = [str(k).strip() for k in keywords if str(k).strip()][:8]

    if not title or not summary:
        return None

    steps_json = json.dumps(
        [{"cmd": s["cmd"][:200], "outcome": s.get("outcome", "")[:150]} for s in steps],
        separators=(",", ":"),
    )

    return {
        "id": f"proc_{_session_short(session_id)}",
        "kind": "observation",
        "domain": domain,
        "author_model": "crush-session",
        "site": "",
        "summary": summary,
        "title": title,
        "keywords": keywords,
        "tool": "crush",
        "source_path": db_path,
        "confidence": 0.75,
        "evidence": {
            "session_id": session_id,
            "workspace": workspace,
            "step_count": len(steps),
            "steps_json": steps_json,
        },
    }


def _workspace_from_db(db_path: str) -> str:
    p = Path(db_path)
    if p.name == "crush.db" and p.parent.name == ".crush":
        return str(p.parent.parent)
    return ""


def extract_all(
    db_paths: list[str] | None = None,
    *,
    min_steps: int = 2,
    verbose: bool = True,
) -> list[dict]:
    """Extract procedures from all Crush DBs."""
    cfg = load_config()
    models = cfg["models"]
    model = models.get("distill_model", "deepseek-v4-flash")
    ollama_host = models["ollama_host"]
    deepseek_base_url = models.get("deepseek_base_url", "https://api.deepseek.com")

    if db_paths is None:
        db_paths = [str(p) for p in Path.home().rglob(".crush/crush.db")]

    records: list[dict] = []
    for db_path in sorted(db_paths):
        workspace = _workspace_from_db(db_path)
        if verbose:
            print(f"  [scan] {db_path} ({workspace or 'no workspace'})", file=sys.stderr)

        by_session = extract_pairs(db_path)
        for session_id, steps in by_session.items():
            if len(steps) < min_steps:
                continue
            rec = generate_procedure(
                session_id,
                steps,
                db_path=db_path,
                workspace=workspace,
                model=model,
                ollama_host=ollama_host,
                deepseek_base_url=deepseek_base_url,
            )
            if rec:
                records.append(rec)
                if verbose:
                    print(f"  [proc] {rec['title'][:50]} ({len(steps)} steps)", file=sys.stderr)

    return records


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract procedures from Crush tool_call pairs")
    ap.add_argument("--db", type=str, help="Single Crush DB path (default: discover all)")
    ap.add_argument("-o", "--output", type=Path, default=Path("procedures.jsonl"))
    ap.add_argument("--print", action="store_true", help="Print JSONL to stdout")
    ap.add_argument("--min-steps", type=int, default=2, help="Minimum bash steps per procedure")
    args = ap.parse_args()

    db_paths = [args.db] if args.db else None
    records = extract_all(db_paths, min_steps=args.min_steps)

    if not records:
        print("No procedures extracted.", file=sys.stderr)
        raise SystemExit(0)

    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    if getattr(args, "print"):
        print("\n".join(lines))
    else:
        args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {len(records)} procedure(s) → {args.output}")
        print(f"Ingest: convmem add --file {args.output} --upsert")


if __name__ == "__main__":
    main()
