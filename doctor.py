"""Health checks for the local convmem installation — reuses brief.py probes."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from brief import _mcp_registration, _systemd_state, _watch_main_pid, _watch_process_memory
from chroma_readonly import collection_count
from config import CONFIG_PATH, load_config

WATCH_RSS_PASS_KB = 512 * 1024  # 512 MB


@dataclass
class DoctorCheck:
    name: str
    ok: bool
    detail: str


def _check_config() -> DoctorCheck:
    try:
        load_config()
        return DoctorCheck("config", True, f"{CONFIG_PATH} readable")
    except FileNotFoundError as exc:
        return DoctorCheck("config", False, str(exc))


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE and export KEY=VALUE lines from a shell env file."""
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        # Strip optional 'export ' prefix.
        if stripped.startswith("export "):
            stripped = stripped[7:]
        key, _, val = stripped.partition("=")
        key = key.strip()
        val = val.strip().strip("\"'")
        if key:
            env[key] = val
    return env


def _resolve_deepseek_key() -> str:
    """Look up DEEPSEEK_API_KEY from os.environ, env.local, and env.systemd."""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key

    for fname in ("env.local", "env.systemd"):
        path = Path("~/.config/convmem").expanduser() / fname
        parsed = _parse_env_file(path)
        key = parsed.get("DEEPSEEK_API_KEY", "").strip()
        if key:
            return key

    return ""


def _check_deepseek_key() -> DoctorCheck:
    key = _resolve_deepseek_key()
    if key:
        return DoctorCheck("deepseek_key", True, "DEEPSEEK_API_KEY set")
    return DoctorCheck(
        "deepseek_key",
        False,
        "DEEPSEEK_API_KEY not set (os.environ or ~/.config/convmem/env.local or env.systemd)",
    )


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


def _jsonl_unit_stats(export: Path) -> tuple[int, int]:
    """Return (line_count, unique_unit_id_count) for units_export JSONL."""
    import json

    lines = 0
    ids: set[str] = set()
    if not export.is_file():
        return 0, 0
    for line in export.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        lines += 1
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        uid = (rec.get("id") or rec.get("ledger_id") or "").strip()
        if uid:
            ids.add(uid)
    return lines, len(ids)


def _check_index_drift(cfg: dict) -> DoctorCheck:
    """Compare Chroma knowledge_units count to units_export JSONL unique ids."""
    chroma_dir = Path(cfg["index"]["chroma_dir"]).expanduser()
    export = Path(cfg["index"].get("units_export", "")).expanduser()
    chroma_count = collection_count(str(chroma_dir), "knowledge_units")
    if not export.is_file():
        return DoctorCheck(
            "index_drift",
            True,
            f"no units_export at {export} (Chroma={chroma_count})",
        )
    line_count, unique_count = _jsonl_unit_stats(export)
    if chroma_count < 1 and (line_count > 0 or unique_count > 0):
        return DoctorCheck(
            "index_drift",
            False,
            f"Chroma empty but JSONL has {line_count} lines ({unique_count} unique ids)",
        )
    if unique_count < 1:
        return DoctorCheck(
            "index_drift",
            True,
            f"empty units_export (Chroma={chroma_count})",
        )
    ratio = chroma_count / unique_count
    detail = (
        f"Chroma {chroma_count} vs JSONL {unique_count} unique ids "
        f"({line_count} lines, {ratio:.0%} indexed)"
    )
    if ratio < 0.15 and unique_count > 500:
        return DoctorCheck(
            "index_drift",
            False,
            detail + " — run: rm ~/.local/share/convmem/processed.json && convmem index",
        )
    if ratio < 0.3 and unique_count > 500:
        return DoctorCheck("index_drift", True, f"WARN: {detail}")
    return DoctorCheck("index_drift", True, detail)


def _check_mcp_import() -> DoctorCheck:
    try:
        import mcp_server  # noqa: F401
    except ImportError as exc:
        return DoctorCheck("mcp_import", False, f"mcp_server import failed: {exc}")
    missing = [
        name
        for name in ("brief", "search_fast", "search", "ask", "related", "stats", "unresolved")
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


def _check_restic() -> DoctorCheck:
    """Restic live-write gate: toolchain + snapshot covers today (fail-closed policy)."""
    script = Path(__file__).resolve().parent / "scripts" / "restic-ensure-chroma-snapshot.sh"
    if not script.is_file():
        return DoctorCheck("restic_gate", False, f"missing {script}")
    if shutil.which("restic") is None:
        return DoctorCheck(
            "restic_gate",
            False,
            "restic not on PATH (pacman -S restic or conda-forge; see config/restic.env.example)",
        )
    env_file = Path("~/.config/convmem/restic.env").expanduser()
    if not env_file.is_file():
        return DoctorCheck(
            "restic_gate",
            False,
            f"missing {env_file} — run scripts/setup-restic-chroma.sh",
        )
    try:
        proc = subprocess.run(
            [str(script), "--require-current"],
            capture_output=True,
            text=True,
            timeout=300,
            env=os.environ,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return DoctorCheck("restic_gate", False, str(exc))
    if proc.returncode == 0:
        return DoctorCheck(
            "restic_gate",
            True,
            "snapshot covers today (tag=convmem-chroma; threshold=local calendar day)",
        )
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-2:]
    return DoctorCheck(
        "restic_gate",
        False,
        "Restic gate not ready — " + " ".join(tail),
    )


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


def _check_synthesis_gate() -> DoctorCheck:
    """P1c gate: count synthesis failures in the last 7 days."""
    import json as _json
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td

    log_path = Path("~/.local/share/convmem/synthesis_failures.jsonl").expanduser()
    if not log_path.is_file():
        return DoctorCheck(
            "synthesis_gate",
            True,
            "0 failures in 7d (gate: >=3/week investigate ask pipeline; P1c Phase 1 shipped)",
        )
    cutoff = _dt.now(_tz.utc) - _td(days=7)
    count = 0
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = _json.loads(line)
            ts = _dt.strptime(entry["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_tz.utc)
            if ts >= cutoff:
                count += 1
        except (KeyError, ValueError, _json.JSONDecodeError):
            continue
    if count >= 3:
        return DoctorCheck(
            "synthesis_gate",
            False,
            f"{count} failures in 7d — synthesis gate TRIGGERED (>=3; investigate ask pipeline)",
        )
    return DoctorCheck(
        "synthesis_gate",
        True,
        f"{count} failures in 7d (gate: >=3/week investigate; partial synthesis on timeout shipped)",
    )


def _check_index_gate() -> DoctorCheck:
    """Detect approved decisions whose Chroma indexing failed (delayed-index)."""
    import json as _json
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td

    log_path = Path("~/.local/share/convmem/index_failures.jsonl").expanduser()
    if not log_path.is_file():
        return DoctorCheck("index_gate", True, "0 index failures (all approved decisions indexed)")
    cutoff = _dt.now(_tz.utc) - _td(days=7)
    count = 0
    latest_id = ""
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = _json.loads(line)
            ts = _dt.strptime(entry["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_tz.utc)
            if ts >= cutoff:
                count += 1
                latest_id = entry.get("proposal_id", "")
        except (KeyError, ValueError, _json.JSONDecodeError):
            continue
    if count >= 3:
        return DoctorCheck(
            "index_gate",
            False,
            f"{count} index failures in 7d — >=3; recovery: convmem add --file <approved.jsonl> --upsert (gate)",
        )
    if count > 0:
        return DoctorCheck(
            "index_gate", True, f"{count} index failures in 7d (latest: {latest_id})"
        )
    return DoctorCheck("index_gate", True, "0 index failures in 7d")


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


def _check_write_lane(cfg: dict) -> DoctorCheck:
    from runtime_guard import runtime_summary, write_boundary_message

    chroma = cfg["index"]["chroma_dir"]
    blocked = write_boundary_message(chroma)
    detail = runtime_summary(chroma)
    return DoctorCheck("write_lane", blocked is None, detail)


def _check_empty_ledger_documents(cfg: dict) -> DoctorCheck:
    """Informational — empty Chroma documents on decision/verification units."""
    try:
        from observe import repair_empty_ledger_documents

        stats = repair_empty_ledger_documents(cfg, dry_run=True, verbose=False)
    except Exception as exc:
        return DoctorCheck("ledger_documents", False, str(exc))
    empty = int(stats.get("empty") or 0)
    if empty == 0:
        return DoctorCheck(
            "ledger_documents",
            True,
            f"0 empty decision/verification docs ({stats.get('scanned', 0)} scanned)",
        )
    return DoctorCheck(
        "ledger_documents",
        True,
        f"{empty} empty — repair: bash ~/Projects/convmem/scripts/repair-ledger-documents.sh",
    )


def _check_digest_timer() -> DoctorCheck:
    state = _systemd_state("convmem-cross-project-digest.timer")
    ok = state.endswith("/active") or state == "active/active"
    return DoctorCheck("digest_timer", ok, state or "not installed")


def run_doctor(
    *,
    v1: bool = False,
    run_verify: bool = False,
) -> list[DoctorCheck]:
    """Run health checks. v0 = core; v1 adds watch RSS, systemd, locks."""
    cfg = load_config()
    checks: list[DoctorCheck] = [
        _check_config(),
        _check_write_lane(cfg),
        _check_deepseek_key(),
        _check_ollama(cfg),
        _check_chroma(cfg),
        _check_index_drift(cfg),
        _check_restic(),
        _check_synthesis_gate(),
        _check_index_gate(),
        _check_empty_ledger_documents(cfg),
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
                _check_digest_timer(),
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
