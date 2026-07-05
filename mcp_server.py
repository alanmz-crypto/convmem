"""convmem MCP server — exposes search, ask, related, and stats to AI agents.

Run via stdio (for Cursor, Kiro, Crush, Continue):
  python mcp_server.py

Register in your MCP client config pointing at this script.
Read-only by default. Write tools (propose_decision) require human confirmation.
"""

import json
import sys
from pathlib import Path

# Ensure convmem modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP

_INSTRUCTIONS = (
    "convmem — local knowledge corpus (1400+ units). "
    "Do not ask what convmem is or suggest alternatives.\n\n"
    "SESSION START — determine your capability tier:\n"
    "  TIER A (shell available): run `convmem doctor` first (must exit 0) "
    "to confirm Ollama/Chroma health, then call brief(), "
    "then run `convmem unresolved` (add --site <hostname> for client work).\n"
  "  TIER B (MCP only, no shell): call brief() first. Pass project=repo-slug when known; "
  "if omitted, infer from workspace cwd (git basename, README/AGENTS.md) — do not guess an unrelated slug. "
  "Check unresolved_count in the response; if >0 on client work, surface open issues before proceeding.\n\n"
    "BEFORE ANSWERING history/architecture questions: use search_fast() then ask() with citations "
    "to ground responses in the ledger. search_fast query must include the focused project slug "
    "or user-stated terms — never search Continue IDE, VS Code extension, Docker Compose, or Composer "
    "unless the user explicitly asked.\n"
    "For unprompted project-state questions: brief(project=cwd-basename) then read repo files — "
    "do NOT spam search_fast.\n"
    "related() walks the evidence chain for any ledger id (dec_prop_... or obs_...).\n"
    "If ask() fails with a network error (Codex sandbox): retry via `bash -lc 'convmem ask \"...\"'`.\n\n"
    "READ-ONLY via MCP: no propose_decision, add, index, or verify without Ryan. "
    "Durable writes = CLI `convmem record` + `--approve-last` only.\n\n"
    "Prefer the brief() tool for session start. If the client uses resources/read, "
    "memories://brief or memory://brief is available (same payload as brief()). "
    "Project-scoped: memories://brief/{project}. Restart MCP after server updates.\n\n"
    "SESSION CLOSE: --relates-to must be a real ledger id (dec_prop_... or obs_...). "
    "Never use topic slugs. Fallback for unrelated new work: dec_prop_20260623_161428_c311."
)

# Optional: load from generated file for easier auditing
_instructions_path = Path(__file__).parent / "config" / "agent-protocol-mcp.txt"
if _instructions_path.exists():
    _BASE_INSTRUCTIONS = _instructions_path.read_text().strip()
else:
    _BASE_INSTRUCTIONS = _INSTRUCTIONS

_mcp_brief_called = False


def _brief_first_required_mode(cwd: Path) -> str | None:
    """Cwd modes where MCP reads require brief() first in this process."""
    if _is_system_runbook_cwd(cwd):
        return "system_runbook"
    if _is_alien_workspace_cwd(cwd):
        return "workspace_local"
    return None


def _blocked_until_brief_json() -> str | None:
    """System runbook + workspace_local cwd: MCP reads require brief() first."""
    if _mcp_brief_called:
        return None
    cwd_path, _ = _workspace_project_slug()
    mode = _brief_first_required_mode(Path(cwd_path))
    if not mode:
        return None
    if mode == "system_runbook":
        message = (
            "Call brief() first (no args on system runbook cwd). "
            "Then search_fast(runbook_hint.suggested_search_fast)."
        )
    else:
        message = (
            "Call brief() first on workspace_local cwd (before List/Read/Bash). "
            "Then search_fast(workspace_hint.suggested_search_fast). "
            "Cataloging/indexing questions require brief + search_fast + Read README.md — "
            "never answer from directory listing alone."
        )
    return json.dumps(
        {"blocked_until_brief": True, "brief_mode": mode, "message": message},
        indent=2,
    )


def _workspace_project_slug() -> tuple[str, str]:
    import os

    cwd = Path(os.getcwd()).resolve()
    return str(cwd), cwd.name.lower()


def _cwd_is_project_root(cwd: Path) -> bool:
    """True when MCP cwd looks like a git/code project, not a system runbook folder."""
    home = Path.home()
    for anchor in ("Projects", "WordPress", "GitClones"):
        try:
            cwd.relative_to(home / anchor)
            return True
        except ValueError:
            continue
    if (cwd / ".git").is_dir():
        return True
    if (cwd / "AGENTS.md").is_file() or (cwd / "STATUS.md").is_file():
        return True
    return False


def _is_alien_workspace_cwd(cwd: Path) -> bool:
    """True when cwd is neither a repo project root nor a system runbook path."""
    return not _cwd_is_project_root(cwd) and not _is_system_runbook_cwd(cwd)


def _project_matches_cwd(cwd: Path, project: dict) -> bool:
    repo = (project.get("repo_path") or "").strip()
    if not repo:
        return False
    try:
        cwd_r = cwd.expanduser().resolve()
        repo_r = Path(repo).expanduser().resolve()
    except (OSError, ValueError):
        return False
    if cwd_r == repo_r:
        return True
    try:
        cwd_r.relative_to(repo_r)
        return True
    except ValueError:
        return False


def _trim_brief_for_workspace_local(payload: dict, cwd: Path, cwd_slug: str) -> dict:
    matched = [p for p in payload.get("projects", []) if _project_matches_cwd(cwd, p)]
    payload["projects"] = matched
    for key in (
        "recent_decisions",
        "recent_monitor",
        "recent_inter_model_titles",
        "recent_unit_titles",
    ):
        if key in payload:
            payload[key] = []
    if matched:
        payload["focus_project"] = matched[0].get("slug")
    else:
        payload.pop("focus_project", None)
    crush_db = cwd / ".crush" / "crush.db"
    readme = cwd / "README.md"
    payload["workspace_hint"] = {
        "directory": str(cwd),
        "basename": cwd.name,
        "has_crush_db": crush_db.is_file(),
        "has_readme_md": readme.is_file(),
        "has_agents_md": (cwd / "AGENTS.md").is_file(),
        "suggested_search_fast": f"{cwd_slug} crush catalog index {cwd.name}",
        "mandatory_tool_order": [
            "folder_state() or brief()",
            "search_fast(workspace_hint.suggested_search_fast)",
            "Read README.md or inspect .crush/ if cataloging",
        ],
        "cataloging_answer_must_cite": [
            "has_crush_db (local Crush SQLite index)",
            "search_fast corpus hits for this directory",
            "README.md content when has_readme_md",
        ],
        "insufficient_alone": "Listing folder names without brief/search_fast is FAIL",
        "do_not_pass_project_slug": True,
        "suggested_actions": [
            f"search_fast('{cwd_slug} crush catalog') for corpus hits about this directory",
            f"Read {readme} if present",
            f"List {cwd}/.crush for index artifacts",
        ],
    }
    return payload


def _is_system_runbook_cwd(cwd: Path) -> bool:
    """Arch CORE runbook paths (boot, pacman, journal, systemd) — not repo slugs."""
    s = str(cwd)
    if s.startswith(("/boot", "/etc", "/var/", "/usr/lib/systemd")):
        return True
    user_systemd = str(home / ".config" / "systemd" / "user") if (home := Path.home()) else ""
    if user_systemd and s.startswith(user_systemd):
        return True
    return False


def _system_runbook_hint(cwd: Path) -> dict[str, str] | None:
    """CORE 8 cwd → subject + search_fast query + ledger pointer (dec_prop from matrix)."""
    s = str(cwd.resolve())
    home = Path.home()
    table: dict[str, dict[str, str]] = {
        str(home / ".config" / "systemd" / "user"): {
            "subject": "user systemd services",
            "suggested_search_fast": "user systemd services systemctl",
            "ledger_hint": "dec_prop_20260629_125949_d79b",
        },
        "/boot/loader/entries": {
            "subject": "boot entries",
            "suggested_search_fast": "boot loader entries systemd-boot",
            "ledger_hint": "dec_prop_20260629_070300_1c89",
        },
        "/etc": {
            "subject": "pacman configuration",
            "suggested_search_fast": "pacman configuration mirrorlist reflector",
            "ledger_hint": "dec_prop_20260629_150516_6d70",
        },
        "/var/lib/pacman": {
            "subject": "installed packages",
            "suggested_search_fast": "pacman installed packages database",
            "ledger_hint": "dec_prop_20260629_150516_6d70",
        },
        "/var/cache/pacman/pkg": {
            "subject": "package cache",
            "suggested_search_fast": "pacman package cache",
            "ledger_hint": "dec_prop_20260629_150516_6d70",
        },
        "/var/log/journal": {
            "subject": "system logs",
            "suggested_search_fast": "journal system logs",
            "ledger_hint": "dec_prop_20260629_063749_aa9e",
        },
        "/usr/lib/systemd/system": {
            "subject": "vendor systemd units",
            "suggested_search_fast": "vendor systemd units",
            "ledger_hint": "dec_prop_20260629_150516_6d70",
        },
    }
    if s in table:
        return table[s]
    for path, hint in table.items():
        if s.startswith(path + "/") or s == path:
            return dict(hint)
    return None


def _build_mcp_instructions(base: str) -> str:
    """Append cwd-specific mandatory brief-first block (Continue sets MCP process cwd)."""
    import os

    cwd = Path(os.getcwd()).resolve()
    cwd_slug = cwd.name.lower()
    mode = _brief_first_required_mode(cwd)
    if mode == "workspace_local":
        return (
            f"{base}\n\n---\n"
            f"**ACTIVE SESSION** `{cwd}` (**workspace_local** — not ~/Projects/*).\n"
            "**FIRST tool call MUST be `folder_state()` or `brief()`** — "
            "never List/Read/Bash first.\n"
            'Prompts like "state of this folder" / "cataloging" → '
            f"`folder_state()` → `search_fast('{cwd_slug} crush catalog')` → files.\n\n"
            "**Read tool quirk**: Continue expects `filepath=` (not `path=`). "
            "If the model emits `path=` as the parameter name, the call fails. "
            "Always use `filepath=` for Read.\n\n"
            "**No XML tool text**: never emit `<function=...>` or `<parameter=...>` "
            "as chat text — those syntaxes are not executed by Continue.\n"
        )
    if mode == "system_runbook":
        return (
            f"{base}\n\n---\n"
            f"**ACTIVE SESSION** `{cwd}` (**system_runbook**).\n"
            "**FIRST tool call MUST be `brief()`** — never List/Read/Bash before brief.\n"
        )
    return base


mcp = FastMCP(
    "convmem",
    instructions=_build_mcp_instructions(_BASE_INSTRUCTIONS),
)


def _enrich_brief_payload(payload: dict, slug_meta: dict[str, str]) -> dict:
    if slug_meta.get("project_slug_corrected_from"):
        payload["project_slug_corrected"] = {
            "from": slug_meta["project_slug_corrected_from"],
            "to": slug_meta["project_slug_corrected_to"],
            "reason": (
                f"MCP cwd is {slug_meta.get('mcp_cwd')} — not ~/Projects/convmem. "
                "Brief scoped to workspace slug instead."
            ),
        }
    elif slug_meta.get("project_inferred_from_cwd"):
        payload["project_inferred_from_cwd"] = slug_meta["project_inferred_from_cwd"]
    if slug_meta.get("brief_mode") == "system_runbook":
        payload["brief_mode"] = "system_runbook"
        hint = _system_runbook_hint(Path(slug_meta.get("mcp_cwd", "")))
        if hint:
            payload["runbook_hint"] = hint
        payload["answer_from"] = (
            "System runbook cwd (not a git project). Turn 1 MUST be brief() before List/Read/Bash. "
            "Then search_fast(runbook_hint.suggested_search_fast) and read files under mcp_cwd. "
            "Answer the user's question — never claim 'no previous conversation' when tools ran."
        )
        payload["search_policy"] = (
            "search_fast with runbook_hint.suggested_search_fast or user subject; "
            "do not infer project slug from directory basename."
        )
    elif slug_meta.get("brief_mode") == "workspace_local":
        cwd = Path(slug_meta.get("mcp_cwd", ""))
        cwd_slug = slug_meta.get("mcp_cwd_slug", cwd.name.lower())
        payload["brief_mode"] = "workspace_local"
        payload = _trim_brief_for_workspace_local(payload, cwd, cwd_slug)
        # Strip global stats that models wrongly cite as local folder properties
        payload.pop("units", None)
        payload.pop("summaries", None)
        payload["inventory"] = {"total": 0, "indexed": 0, "pending": 0, "deferred": 0}
        payload["services"] = {}
        payload["watch_memory_kb"] = None
        payload["coordination"] = {}
        payload["workspace_local_note"] = (
            "Corpus-wide stats are ZEROED OUT to prevent confusion. "
            "Answer about mcp_cwd ONLY via workspace_hint, search_fast hits, and local files. "
            "Do NOT cite inventory.total, units, summaries, or services — those are convmem global values, not this directory."
        )
        payload["answer_from"] = (
            "Local workspace cwd (not ~/Projects/* repo). Turn 1 MUST be MCP brief() "
            "before List/Read/Bash — no exceptions. Cataloging/indexing questions: turn 2 "
            "search_fast(workspace_hint.suggested_search_fast); turn 3 Read README.md if "
            "workspace_hint.has_readme_md. Answer ONLY about mcp_cwd indexing — cite "
            "has_crush_db, search_fast hits, and README. Do NOT invent organization from "
            "folder names alone or summarize unrelated projects[]."
        )
        payload["search_policy"] = (
            "search_fast with workspace_hint.suggested_search_fast or user question + directory name; "
            "never default to projects[0] when projects[] is empty."
        )
    if slug_meta.get("project_slug_warning"):
        payload["project_slug_warning"] = slug_meta["project_slug_warning"]
    payload["mcp_cwd"] = slug_meta.get("mcp_cwd")
    return payload


def _resolve_brief_project(project: str) -> tuple[str, dict[str, str]]:
    """Infer or correct project slug from MCP process cwd (Continue sets cwd to workspace)."""
    cwd_path, cwd_slug = _workspace_project_slug()
    cwd = Path(cwd_path)
    meta: dict[str, str] = {"mcp_cwd": cwd_path, "mcp_cwd_slug": cwd_slug}
    system_runbook = _is_system_runbook_cwd(cwd)
    if system_runbook:
        meta["brief_mode"] = "system_runbook"

    arg = (project or "").strip()
    if arg and _is_alien_workspace_cwd(cwd) and not system_runbook:
        meta["brief_mode"] = "workspace_local"
        meta["project_slug_ignored"] = arg
        meta["project_slug_warning"] = (
            f"project={arg} ignored on workspace_local cwd — use folder_state() unscoped; "
            "directory basename is not a corpus project slug."
        )
        return "", meta

    if not arg:
        if system_runbook:
            meta["project_inference_skipped"] = "system runbook cwd — use unscoped brief"
            return "", meta
        if _cwd_is_project_root(cwd) and cwd_slug:
            meta["project_inferred_from_cwd"] = cwd_slug
            return cwd_slug, meta
        if _is_alien_workspace_cwd(cwd):
            meta["brief_mode"] = "workspace_local"
        return "", meta

    arg_l = arg.lower()
    if arg_l == "convmem" and cwd_slug and cwd_slug != "convmem":
        if _cwd_is_project_root(cwd) and not system_runbook:
            meta["project_slug_corrected_from"] = "convmem"
            meta["project_slug_corrected_to"] = cwd_slug
            return cwd_slug, meta
        if system_runbook:
            meta["project_slug_corrected_from"] = "convmem"
            meta["project_slug_corrected_to"] = ""
            meta["project_slug_warning"] = (
                "project=convmem wrong for system runbook cwd — use brief() unscoped "
                "and search_fast with user subject (boot entries, pacman, journal)."
            )
            return "", meta
    return arg, meta


def _search_payload(results: list[dict]) -> str:
    out = []
    for r in results:
        meta = r.get("metadata", {})
        out.append({
            "score": r.get("score"),
            "rank_score": r.get("rank_score"),
            "recency_boost": r.get("recency_boost"),
            "ledger_lookup": r.get("ledger_lookup", False),
            "title": meta.get("title", ""),
            "type": meta.get("type", ""),
            "domain": meta.get("domain", ""),
            "site": meta.get("site", ""),
            "tool": meta.get("tool", ""),
            "source_path": meta.get("source_path", ""),
            "ledger_id": meta.get("ledger_id", ""),
            "document": (r.get("document") or "")[:500],
        })
    return json.dumps(out, indent=2)


def _search_fast_off_topic(query: str) -> bool:
    """True when query matches known Continue/qwen confabulation patterns."""
    q = (query or "").lower()
    needles = (
        "continue working",
        "vs code extension",
        "vscode extension",
        "docker compose plugin",
        "compose plugin",
        "compose ui project",
        "compose ui component",
        "vs code extension development",
    )
    return any(n in q for n in needles)


@mcp.tool()
def brief(project: str = "", with_tests: bool = False) -> str:
    """MANDATORY first MCP tool every session — before List/Read/Bash. Repo cwd: brief(project=<basename>). System runbook (/boot, /etc, /var, systemd): brief() unscoped. Local workspace (~/Documents etc): brief() then search_fast(workspace_hint.suggested_search_fast). Read-only."""
    global _mcp_brief_called
    from brief import gather_brief_payload

    _mcp_brief_called = True
    resolved, slug_meta = _resolve_brief_project(project)
    payload = gather_brief_payload(with_tests=with_tests, project=resolved)
    payload = _enrich_brief_payload(payload, slug_meta)
    return json.dumps(payload, indent=2, default=str)


@mcp.tool()
def folder_state(project: str = "", with_tests: bool = False) -> str:
    """REQUIRED first MCP tool when user asks about folder/directory/workspace state, cataloging, or indexing. Same as brief(). Never List/Read/Bash before this. On workspace_local cwd do not pass project= — use folder_state() with no args."""
    return brief(project=project, with_tests=with_tests)


def _brief_resource_json(project: str = "") -> str:
    from brief import gather_brief_payload

    resolved, slug_meta = _resolve_brief_project(project)
    payload = gather_brief_payload(with_tests=False, project=resolved)
    payload = _enrich_brief_payload(payload, slug_meta)
    return json.dumps(payload, indent=2, default=str)


@mcp.resource(
    "memories://brief",
    name="brief",
    description="Session orientation JSON (same as brief() tool). Prefer brief() when invoking tools.",
    mime_type="application/json",
)
def brief_resource() -> str:
    return _brief_resource_json("")


@mcp.resource(
    "memory://brief",
    name="brief-memory-scheme",
    description="Alias of memories://brief (some clients use memory://).",
    mime_type="application/json",
)
def brief_resource_memory_scheme() -> str:
    return _brief_resource_json("")


@mcp.resource(
    "memories://brief/{project}",
    name="brief-project",
    description="Session orientation for one repo slug (same as brief(project=...)).",
    mime_type="application/json",
)
def brief_project_resource(project: str) -> str:
    return _brief_resource_json(project)


@mcp.resource(
    "memory://brief/{project}",
    name="brief-project-memory-scheme",
    description="Alias of memories://brief/{project}.",
    mime_type="application/json",
)
def brief_project_resource_memory_scheme(project: str) -> str:
    return _brief_resource_json(project)


@mcp.tool()
def search_fast(query: str, top_k: int = 5, domain: str = "", site: str = "") -> str:
    """Fast corpus search. System runbook: call brief() first. Repo: include project slug in query."""
    from query import query_units

    blocked = _blocked_until_brief_json()
    if blocked:
        return blocked

    if _search_fast_off_topic(query):
        return json.dumps(
            {
                "results": [],
                "blocked_off_topic": True,
                "message": (
                    "Query blocked: appears unrelated to the focused repo (Continue IDE / "
                    "VS Code extension / Docker Compose confabulation). Use brief(projects[]) "
                    "and read files in the workspace instead."
                ),
            },
            indent=2,
        )

    results = query_units(
        query, top_k=top_k, domain=domain or None, site=site or None
    )
    if not results:
        return json.dumps({"results": [], "message": "No relevant knowledge units found."})
    return _search_payload(results)


@mcp.tool()
def search(query: str, top_k: int = 5, domain: str = "", site: str = "") -> str:
    """Search the knowledge corpus for relevant units. Returns scored results."""
    from query import query_units

    results = query_units(
        query, top_k=top_k, domain=domain or None, site=site or None
    )
    return _search_payload(results)


@mcp.tool()
def ask(
    question: str,
    top_k: int = 5,
    domain: str = "",
    site: str = "",
    evidence: bool = True,
) -> str:
    """Answer a question using retrieved memories. Returns answer + citations."""
    blocked = _blocked_until_brief_json()
    if blocked:
        return blocked
    from ask import ask as run_ask

    result = run_ask(
        question,
        top_k=top_k,
        domain=domain or None,
        site=site or None,
        raw=False,
        evidence=evidence,
    )
    return json.dumps({
        "answer": result.get("answer", ""),
        "confidence": result.get("confidence"),
        "warning": result.get("warning"),
        "synthesis_failed": result.get("synthesis_failed", False),
        "synthesis_interrupted": result.get("synthesis_interrupted", False),
        "citations": [
            {
                "n": c.get("n"),
                "title": c.get("title", ""),
                "type": c.get("type", ""),
                "tool": c.get("tool", ""),
                "source_path": c.get("source_path", ""),
                "domain": c.get("domain", ""),
                "when": c.get("when", ""),
                "score": c.get("score"),
            }
            for c in (result.get("citations") or [])
        ],
    }, indent=2)


@mcp.tool()
def unresolved(site: str = "", domain: str = "") -> str:
    """List open observations (read-only). Returns count + items JSON."""
    blocked = _blocked_until_brief_json()
    if blocked:
        return blocked
    from chroma_readonly import open_readonly_unit_store
    from config import load_config
    from unresolved import unresolved_payload

    cfg = load_config()
    store = open_readonly_unit_store(cfg["index"]["chroma_dir"])
    payload = unresolved_payload(
        store,
        site=site or None,
        domain=domain or None,
    )
    return json.dumps(payload, indent=2)


@mcp.tool()
def related(ledger_id: str) -> str:
    """Traverse the evidence chain for an observation, decision, or verification."""
    from chroma_store import ChromaStore
    from config import load_config
    from ledger import related_chain

    cfg = load_config()
    store = ChromaStore(cfg["index"]["chroma_dir"])
    chain = related_chain(store, ledger_id)
    if chain is None:
        return json.dumps({"error": f"Ledger id not found: {ledger_id}"})

    target = chain["target"]["metadata"]
    result = {
        "target": {
            "ledger_id": target.get("ledger_id", ""),
            "kind": chain["target_kind"],
            "title": target.get("title", ""),
            "domain": target.get("domain", ""),
        },
        "anchor_id": chain["anchor_id"],
        "decisions": [
            {"ledger_id": m.get("ledger_id", ""), "title": m.get("title", "")}
            for m in chain["decisions"]
        ],
        "verifications": [
            {
                "ledger_id": m.get("ledger_id", ""),
                "result": m.get("result", ""),
                "author_model": m.get("author_model", ""),
            }
            for m in chain["verifications"]
        ],
    }
    if chain.get("observation"):
        result["observation"] = {
            "ledger_id": chain["observation"].get("ledger_id", ""),
            "title": chain["observation"].get("title", ""),
        }
    return json.dumps(result, indent=2)


@mcp.tool()
def stats() -> str:
    """Show corpus statistics: unit counts by source and domain."""
    blocked = _blocked_until_brief_json()
    if blocked:
        return blocked
    from collections import Counter
    from chroma_store import ChromaStore
    from config import load_config

    cfg = load_config()
    store = ChromaStore(cfg["index"]["chroma_dir"])
    metas = store.units_metadata()
    by_tool = Counter(m.get("tool", "?") for m in metas)
    by_domain = Counter(m.get("domain") or "untagged" for m in metas)
    return json.dumps({
        "total_units": len(metas),
        "by_tool": dict(by_tool.most_common(10)),
        "by_domain": dict(by_domain.most_common(15)),
    }, indent=2)


if __name__ == "__main__":
    import asyncio

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(mcp.run_stdio_async())
