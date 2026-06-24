"""Health checks for the canonical convmem host — reuses brief.py probes."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from brief import _mcp_registration, _systemd_state, _watch_main_pid, _watch_process_memory
from chroma_readonly import collection_count
from config import load_config

WATCH_RSS_PASS_KB = 512 * 1024  # 512 MB


@dataclass
class DoctorCheck:
    name: str
    ok: bool
    detail: str


def _check_config() -> DoctorCheck:
    try:
        load_config()
        return DoctorCheck("config", True, "~/.config/convmem/config.toml readable")
    except FileNotFoundError as exc:
        return DoctorCheck("config", False, str(exc))


def _check_deepseek_key() -> DoctorCheck:
    if os.environ.get("DEEPSEEK_API_KEY", "").strip():
        return DoctorCheck("deepseek_key", True, "DEEPSEEK_API_KEY set")
    return DoctorCheck("deepseek_key", False, "DEEPSEEK_API_KEY not set (source env.local)")


def _check_ollama(cfg: dict) -> DoctorCheck:
    host = (cfg.get("models") or {}).get("ollama_host", "http://localhost:11434").rstrip("/")
    try:
        resp = requests.get(f"{host}/api/tags", timeout=5)
        resp.raise_for_status()
        tags = resp.json().get("models") or []
        names = [m.get("name", "") for m in tags[:5]]
        return DoctorCheck("ollama", True, f"{host} OK ({len(tags)} models; e.g. {names[:2]})")
    except requests.RequestException as exc:
        return DoctorCheck("ollama", False, f"{host} unreachable: {exc}")


def _check_chroma(cfg: dict) -> DoctorCheck:
    chroma_dir = cfg["index"]["chroma_dir"]
    units = collection_count(chroma_dir, "knowledge_units")
    summaries = collection_count(chroma_dir, "conversation_summaries")
    if units < 1:
        return DoctorCheck(
            "chroma",
            False,
            f"{chroma_dir}: 0 knowledge units (summaries={summaries})",
        )
    return DoctorCheck(
        "chroma",
        True,
        f"{units} knowledge units, {summaries} summaries",
    )


def _check_mcp_import() -> DoctorCheck:
    try:
        import mcp_server  # noqa: F401
    except ImportError as exc:
        return DoctorCheck("mcp_import", False, f"mcp_server import failed: {exc}")
    missing = [
        name
        for name in ("brief", "search_fast", "search", "ask", "related", "stats")
        if not hasattr(mcp_server, name)
    ]
    if missing:
        return DoctorCheck("mcp_import", False, f"missing tools: {', '.join(missing)}")
    return DoctorCheck("mcp_import", True, "mcp_server tools importable")


def _check_mcp_wiring() -> DoctorCheck:
    reg = _mcp_registration()
    cursor = reg.get("cursor", "unknown")
    if cursor == "registered":
        return DoctorCheck("mcp_cursor", True, "~/.cursor/mcp.json has convmem")
    return DoctorCheck("mcp_cursor", False, f"cursor MCP: {cursor}")


def _check_continue_mcp() -> DoctorCheck:
    yaml_path = Path("~/.continue/config.yaml").expanduser()
    json_path = Path("~/.continue/mcpServers/convmem.json").expanduser()
    if not yaml_path.is_file():
        return DoctorCheck("mcp_continue", False, "missing ~/.continue/config.yaml")
    text = yaml_path.read_text(encoding="utf-8")
    if "mcpServers:" not in text or "schema: v1" not in text:
        return DoctorCheck("mcp_continue", False, "config.yaml missing schema: v1 or mcpServers")
    if not json_path.is_file():
        return DoctorCheck("mcp_continue", False, "missing ~/.continue/mcpServers/convmem.json")
    if "mcp_server.py" not in json_path.read_text(encoding="utf-8"):
        return DoctorCheck("mcp_continue", False, "Continue MCP JSON missing mcp_server.py")
    return DoctorCheck("mcp_continue", True, "Continue MCP wiring present")


def _check_verify_script(*, run: bool) -> DoctorCheck:
    root = Path(__file__).resolve().parent
    script = root / "scripts" / "verify-continue.sh"
    if not script.is_file():
        return DoctorCheck("verify_continue", False, f"missing {script}")
    if not run:
        return DoctorCheck("verify_continue", True, f"{script.name} present (use --verify to run)")
    try:
        proc = subprocess.run(
            [str(script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "CONVMEM_ROOT": str(root)},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return DoctorCheck("verify_continue", False, str(exc))
    if proc.returncode == 0:
        return DoctorCheck("verify_continue", True, "scripts/verify-continue.sh PASS")
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-3:]
    return DoctorCheck(
        "verify_continue",
        False,
        "verify-continue.sh FAIL\n" + "\n".join(tail),
    )


def _check_watch_memory() -> DoctorCheck:
    mem = _watch_process_memory()
    if mem is None:
        return DoctorCheck("watch_rss", False, "convmem watch PID not found")
    rss_kb = mem.get("VmRSS", 0)
    rss_mb = rss_kb // 1024
    pid = _watch_main_pid()
    if rss_kb <= WATCH_RSS_PASS_KB:
        return DoctorCheck(
            "watch_rss",
            True,
            f"PID {pid} VmRSS {rss_mb}MB (target ≤512MB)",
        )
    return DoctorCheck(
        "watch_rss",
        False,
        f"PID {pid} VmRSS {rss_mb}MB exceeds 512MB soak target",
    )


def _check_systemd(unit: str) -> DoctorCheck:
    state = _systemd_state(unit)
    ok = state.endswith("/active") or state == "active/active"
    return DoctorCheck(f"systemd_{unit.replace('.', '_')}", ok, state)


def _check_lock(name: str, path: Path) -> DoctorCheck:
    if not path.is_file():
        return DoctorCheck(name, True, f"no lock at {path}")
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        return DoctorCheck(name, False, str(exc))
    return DoctorCheck(name, True, f"present ({raw[:80]})")


def run_doctor(
    *,
    v1: bool = False,
    run_verify: bool = False,
) -> list[DoctorCheck]:
    """Run health checks. v0 = core; v1 adds watch RSS, systemd, locks."""
    cfg = load_config()
    checks: list[DoctorCheck] = [
        _check_config(),
        _check_deepseek_key(),
        _check_ollama(cfg),
        _check_chroma(cfg),
        _check_mcp_import(),
        _check_mcp_wiring(),
        _check_continue_mcp(),
        _check_verify_script(run=run_verify),
    ]
    if v1:
        checks.extend(
            [
                _check_watch_memory(),
                _check_systemd("convmem-watch"),
                _check_systemd("convmem-refine"),
                _check_systemd("convmem-monitor.timer"),
                _check_lock(
                    "watch_lock",
                    Path(cfg["index"]["chroma_dir"]).expanduser().parent / "watch.lock",
                ),
                _check_lock(
                    "refine_lock",
                    Path(cfg["index"]["chroma_dir"]).expanduser().parent / "refine.lock",
                ),
            ]
        )
    return checks


def render_doctor_text(checks: list[DoctorCheck]) -> str:
    lines: list[str] = []
    for c in checks:
        mark = "PASS" if c.ok else "FAIL"
        lines.append(f"[{mark}] {c.name}: {c.detail}")
    failed = sum(1 for c in checks if not c.ok)
    lines.append("")
    if failed:
        lines.append(f"doctor: {failed} check(s) failed")
    else:
        lines.append("doctor: all checks passed")
    return "\n".join(lines)


def doctor_payload(checks: list[DoctorCheck]) -> dict:
    failed = sum(1 for c in checks if not c.ok)
    return {
        "ok": failed == 0,
        "failed": failed,
        "checks": [asdict(c) for c in checks],
    }


def doctor_exit_code(checks: list[DoctorCheck]) -> int:
    return 1 if any(not c.ok for c in checks) else 0
