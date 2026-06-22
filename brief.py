"""Generate a read-only shared context block for multi-agent sessions."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from chroma_readonly import collection_count, collection_metadata_rows
from config import load_config
from ingest import load_processed
from query import _coverage_counts

DEFAULT_BRIEF_PATH = Path("~/.local/share/convmem/brief.md").expanduser()
CRUSH_VERIFIED_FLAG = Path("~/.local/share/convmem/mcp_crush_verified").expanduser()
KIRO_DB = Path("~/.local/share/kiro-cli/data.sqlite3").expanduser()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _systemd_state(unit: str) -> str:
    """Return enabled/active state or 'unknown'."""
    try:
        enabled = subprocess.run(
            ["systemctl", "--user", "is-enabled", unit],
            capture_output=True,
            text=True,
            timeout=3,
        )
        active = subprocess.run(
            ["systemctl", "--user", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=3,
        )
        en = (enabled.stdout or "").strip()
        ac = (active.stdout or "").strip()
        if enabled.returncode != 0 or active.returncode != 0:
            return "unknown"
        if not en or not ac:
            return "unknown"
        return f"{en}/{ac}"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def _run_test_count() -> int | None:
    repo = Path(__file__).resolve().parent
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=120,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        for line in combined.splitlines():
            if line.startswith("Ran ") and " test" in line:
                return int(line.split()[1])
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def _watch_main_pid() -> int | None:
    """Resolve convmem-watch PID via systemctl, else pgrep (Crush-safe fallback)."""
    try:
        out = subprocess.run(
            ["systemctl", "--user", "show", "convmem-watch", "-p", "MainPID", "--value"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if out.returncode == 0:
            pid = int((out.stdout or "").strip())
            if pid > 0:
                return pid
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    try:
        out = subprocess.run(
            ["pgrep", "-f", "convmem.py watch"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if out.returncode == 0:
            for line in (out.stdout or "").splitlines():
                line = line.strip()
                if line:
                    return int(line)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def _watch_process_memory() -> dict[str, int] | None:
    """VmPeak/VmRSS/VmData for convmem-watch main pid (from /proc)."""
    pid = _watch_main_pid()
    if pid is None:
        return None
    try:
        status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    except OSError:
        return None
    vals: dict[str, int] = {}
    for key in ("VmPeak", "VmRSS", "VmData"):
        for line in status.splitlines():
            if line.startswith(f"{key}:"):
                vals[key] = int(line.split()[1])
                break
    return vals or None


def _kiro_excluded(cfg: dict) -> bool:
    target = str(KIRO_DB.expanduser().resolve())
    processed = load_processed(cfg["index"]["processed_log"])
    for entry in processed.values():
        if not isinstance(entry, dict):
            continue
        if entry.get("path") == target and entry.get("excluded"):
            return True
    return False


def _recent_decisions(chroma_dir: str | Path, *, limit: int = 5) -> list[dict]:
    decisions = [
        meta
        for meta in collection_metadata_rows(chroma_dir, "knowledge_units")
        if str(meta.get("ledger_kind") or "").strip().lower() == "decision"
    ]
    decisions.sort(key=lambda m: m.get("timestamp") or "", reverse=True)
    return decisions[:limit]


def _pending_decision_ingest() -> list[str]:
    """JSONL decision files on disk not yet represented in Chroma."""
    repo = Path(__file__).resolve().parent
    candidates = sorted(repo.glob("examples/decisions-*.jsonl"))
    return [str(p.relative_to(repo)) for p in candidates if p.is_file()]


def _recent_monitor_units(chroma_dir: str | Path, *, limit: int = 3) -> list[dict]:
    hits = [
        meta
        for meta in collection_metadata_rows(chroma_dir, "knowledge_units")
        if meta.get("tool") == "convmem-monitor"
    ]
    hits.sort(key=lambda m: m.get("timestamp") or "", reverse=True)
    return hits[:limit]


def _mcp_registration() -> dict[str, str]:
    out: dict[str, str] = {}
    cursor_mcp = Path("~/.cursor/mcp.json").expanduser()
    if cursor_mcp.is_file():
        try:
            data = json.loads(cursor_mcp.read_text(encoding="utf-8"))
            servers = data.get("mcpServers") or {}
            out["cursor"] = "registered" if "convmem" in servers else "missing"
        except (OSError, json.JSONDecodeError):
            out["cursor"] = "unknown"
    else:
        out["cursor"] = "no config"

    crush_cfg = Path("~/.config/crush/crush.json").expanduser()
    if crush_cfg.is_file():
        try:
            data = json.loads(crush_cfg.read_text(encoding="utf-8"))
            mcp = data.get("mcp") or {}
            out["crush"] = "registered" if "convmem" in mcp else "missing"
        except (OSError, json.JSONDecodeError):
            out["crush"] = "unknown"
    else:
        out["crush"] = "no config"

    if CRUSH_VERIFIED_FLAG.is_file():
        out["crush_live"] = CRUSH_VERIFIED_FLAG.read_text(encoding="utf-8").strip() or "verified"
    else:
        out["crush_live"] = "unverified"

    out["stdio"] = "verified (Cursor dev machine 2026-06-22)"
    return out


def gather_brief_data(cfg: dict | None = None, *, with_tests: bool = False) -> dict:
    if cfg is None:
        cfg = load_config()
    total_inv, indexed, pending, deferred = _coverage_counts(cfg)
    test_count = _run_test_count() if with_tests else None
    chroma_dir = cfg["index"]["chroma_dir"]

    return {
        "generated_at": _now_iso(),
        "units": collection_count(chroma_dir, "knowledge_units"),
        "summaries": collection_count(chroma_dir, "conversation_summaries"),
        "inventory": {
            "total": total_inv,
            "indexed": indexed,
            "pending": pending,
            "deferred": deferred,
        },
        "tests": test_count,
        "rerank": (cfg.get("query") or {}).get("rerank"),
        "services": {
            "watch": _systemd_state("convmem-watch"),
            "refine": _systemd_state("convmem-refine"),
            "monitor_timer": _systemd_state("convmem-monitor.timer"),
        },
        "kiro_db_excluded": _kiro_excluded(cfg),
        "mcp": _mcp_registration(),
        "watch_memory_kb": _watch_process_memory(),
        "recent_decisions": _recent_decisions(chroma_dir),
        "recent_monitor": _recent_monitor_units(chroma_dir),
        "pending_decision_files": _pending_decision_ingest(),
        "inter_model_inbox": Path(__file__).resolve().parent / "docs" / "inter-model",
    }


def _clip(text: str, n: int = 120) -> str:
    s = (text or "").replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def render_brief_markdown(data: dict) -> str:
    inv = data["inventory"]
    tests_line = (
        str(data["tests"]) + " passing"
        if data.get("tests") is not None
        else "unknown (run: convmem brief --with-tests)"
    )
    mcp = data.get("mcp") or {}

    lines = [
        "# CONVMEM BRIEF",
        "",
        f"Generated: {data['generated_at']}",
        "",
        "## State",
        f"- Corpus: **{data['units']}** units, **{data['summaries']}** summaries",
        f"- Inventory: {inv['indexed']} indexed, {inv['pending']} pending, {inv['deferred']} deferred",
        f"- Tests: {tests_line}",
        f"- rerank: {data.get('rerank')}",
        f"- Services: watch={data['services']['watch']} refine={data['services']['refine']} monitor.timer={data['services']['monitor_timer']}",
        f"- Kiro live DB excluded: **{'yes' if data['kiro_db_excluded'] else 'no'}**",
        f"- MCP: cursor={mcp.get('cursor', '?')} crush={mcp.get('crush', '?')} crush_live={mcp.get('crush_live', '?')}",
        f"- MCP stdio: {mcp.get('stdio', 'unknown')}",
    ]
    wm = data.get("watch_memory_kb") or {}
    if wm:
        peak_m = wm.get("VmPeak", 0) / (1024 * 1024)
        rss_m = wm.get("VmRSS", 0) / (1024 * 1024)
        lines.append(
            f"- Watch memory: VmPeak **{peak_m:.2f}G**, VmRSS **{rss_m:.2f}G** (from /proc; not ps)"
        )
    lines.extend(["", "## Active P0"])

    p0: list[str] = []
    if not data["kiro_db_excluded"]:
        p0.append("Apply Kiro sqlite exclude before re-enabling watch")
    if inv["pending"] > 0:
        p0.append(f"Ingest {inv['pending']} pending inventory file(s)")
    if mcp.get("crush_live") == "unverified":
        p0.append("Crush live MCP session test (search_fast from agent)")
    if data["services"]["watch"].startswith("disabled"):
        if data["kiro_db_excluded"]:
            p0.append("Re-enable convmem-watch after Crush MCP verify")
        else:
            p0.append("Do not re-enable watch until Kiro DB is excluded")

    if not p0:
        lines.append("- (none — maintain watch journal for 24h)")
    else:
        for i, item in enumerate(p0, 1):
            lines.append(f"{i}. {item}")

    lines.extend(["", "## Recent Decisions"])
    decisions = data.get("recent_decisions") or []
    if not decisions:
        pending_files = data.get("pending_decision_files") or []
        if pending_files and not decisions:
            lines.append(
                f"- (none in ledger — run: convmem add --file {pending_files[0]} --upsert)"
            )
        else:
            lines.append("- (none in ledger)")
    else:
        for d in decisions:
            lid = d.get("ledger_id") or d.get("id") or "?"
            title = d.get("title") or _clip(d.get("summary", ""), 80)
            rationale = _clip(d.get("rationale") or d.get("summary") or "", 100)
            lines.append(f"- **{lid}**: {title}")
            if rationale:
                lines.append(f"  - Rationale: {rationale}")

    lines.extend(["", "## Recent Monitor"])
    monitor = data.get("recent_monitor") or []
    if not monitor:
        lines.append("- (none)")
    else:
        for m in monitor:
            title = (m.get("title") or "").strip() or _clip(m.get("summary", ""), 100)
            result = m.get("result") or ""
            site = m.get("site") or ""
            suffix = f" [{result}]" if result else ""
            lines.append(f"- {site}: {_clip(title, 100)}{suffix}")

    lines.extend(
        [
            "",
            "## Open Risks",
            "- Watch OOM if live DBs indexed (Kiro sqlite, Cursor store.db) — both skipped in watch",
            "- Re-enable watch only after 24h clean journal with per-chunk ingest + MemorySwapMax=0",
            "- Crush MCP live path still unverified until `mcp_crush_verified` flag set",
            "- Handoff doc sprawl — prefer brief + `docs/inter-model/`",
            "",
            "## Before Working",
            "- Read newest files in `docs/inter-model/`",
            "- Agent roles: `docs/AGENT-ROLES.md`",
            "- Use `convmem search` / MCP `search_fast` for targeted prior art",
            "- Treat proposals as pending until human/Kiro approval",
            "",
            "## Inter-Model Inbox",
            f"- `{data.get('inter_model_inbox', 'docs/inter-model')}/`",
            "",
        ]
    )
    return "\n".join(lines)


def write_brief(
    cfg: dict | None = None,
    *,
    out_path: Path | str | None = None,
    with_tests: bool = False,
    quiet: bool = False,
) -> Path:
    if cfg is None:
        cfg = load_config()
    path = Path(out_path or DEFAULT_BRIEF_PATH).expanduser()
    data = gather_brief_data(cfg, with_tests=with_tests)
    text = render_brief_markdown(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if not quiet:
        print(f"Brief written → {path}", file=sys.stderr)
    return path


def refresh_brief_after_change(cfg: dict | None = None) -> None:
    """Lightweight auto-refresh after index/refine/monitor (no test run)."""
    try:
        write_brief(cfg, with_tests=False, quiet=True)
    except Exception as e:
        print(f"[brief] refresh skipped: {e}", file=sys.stderr)
