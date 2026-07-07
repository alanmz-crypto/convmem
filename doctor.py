"""Health checks for the local convmem installation — reuses brief.py probes."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
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
    status: str = ""  # "pass", "fail", or "skip"; derived from ok if empty

    def effective_status(self) -> str:
        if self.status:
            return self.status
        return "pass" if self.ok else "fail"


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


def _check_restic_external() -> DoctorCheck:
    """Offsite Restic repo freshness (RESTIC_EXTERNAL_REPOSITORY).

    Non-fatal by design: this is the removable-drive copy, decoupled from the
    live-write gate. Never returns fail — pass when the offsite copy covers
    today, warn when it is stale/empty (drive mounted), skip when disabled or
    the drive is unplugged.
    """
    name = "restic_external"
    env_file = Path("~/.config/convmem/restic.env").expanduser()
    env = _parse_env_file(env_file)
    repo = env.get("RESTIC_EXTERNAL_REPOSITORY", "").strip()
    if not repo:
        return DoctorCheck(
            name,
            True,
            "no RESTIC_EXTERNAL_REPOSITORY configured (offsite copy disabled)",
            status="skip",
        )
    if shutil.which("restic") is None:
        return DoctorCheck(name, True, "restic not on PATH", status="skip")

    pass_file = env.get("RESTIC_PASSWORD_FILE", "").strip()
    if not pass_file or not Path(pass_file).expanduser().is_file():
        return DoctorCheck(
            name, True, f"RESTIC_PASSWORD_FILE missing ({pass_file or 'unset'})", status="skip"
        )

    if not (Path(repo).expanduser() / "config").is_file():
        return DoctorCheck(
            name, True, f"offsite repo not mounted/reachable: {repo} (USB unplugged?)", status="skip"
        )

    probe_env = dict(os.environ)
    probe_env["RESTIC_PASSWORD_FILE"] = str(Path(pass_file).expanduser())
    try:
        proc = subprocess.run(
            ["restic", "-r", repo, "snapshots", "--tag", "convmem-chroma", "--json"],
            capture_output=True,
            text=True,
            env=probe_env,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return DoctorCheck(name, True, f"offsite repo probe failed: {exc}", status="skip")
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:]
        return DoctorCheck(
            name, True, "offsite repo unreadable — " + " ".join(detail), status="skip"
        )

    try:
        snaps = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return DoctorCheck(name, True, "offsite snapshots JSON unparsable", status="skip")

    if not snaps:
        return DoctorCheck(
            name,
            True,
            "offsite repo has no convmem-chroma snapshots — run scripts/restic-copy-external.sh",
            status="warn",
        )

    latest = max(snaps, key=lambda s: s["time"])
    ts = datetime.fromisoformat(latest["time"].replace("Z", "+00:00"))
    local_day = ts.astimezone().date()
    today = datetime.now().astimezone().date()
    if local_day >= today:
        return DoctorCheck(name, True, f"offsite copy covers today (last={local_day})")
    return DoctorCheck(
        name,
        True,
        f"offsite copy STALE (last={local_day}) — check convmem-restic-external.timer "
        "or run scripts/restic-copy-external.sh",
        status="warn",
    )


def _check_restic_password_backup() -> DoctorCheck:
    """Offline copy of the Restic password (RESTIC_PASSWORD_BACKUP_FILE).

    The password unlocks BOTH repos. With only one copy inside ~/.config/convmem,
    a Tier-2 config wipe orphans everything. Non-fatal: warn until a second,
    independent copy exists and matches.
    """
    name = "restic_password_backup"
    env_file = Path("~/.config/convmem/restic.env").expanduser()
    env = _parse_env_file(env_file)
    primary = env.get("RESTIC_PASSWORD_FILE", "").strip()
    if not primary:
        return DoctorCheck(name, True, "no RESTIC_PASSWORD_FILE configured", status="skip")
    primary_path = Path(primary).expanduser()
    if not primary_path.is_file():
        return DoctorCheck(name, True, f"primary password missing ({primary})", status="skip")

    backup = env.get("RESTIC_PASSWORD_BACKUP_FILE", "").strip()
    if not backup:
        return DoctorCheck(
            name,
            True,
            "no offline password copy (RESTIC_PASSWORD_BACKUP_FILE unset) — a config wipe "
            "orphans both repos; run scripts/backup-restic-password.sh <dest>",
            status="warn",
        )
    backup_path = Path(backup).expanduser()
    if not backup_path.is_file():
        return DoctorCheck(
            name,
            True,
            f"offline password copy missing at {backup} — run scripts/backup-restic-password.sh",
            status="warn",
        )

    config_dir = str(Path("~/.config/convmem").expanduser())
    if str(backup_path).startswith(config_dir):
        return DoctorCheck(
            name,
            True,
            f"offline copy is inside {config_dir} — won't survive a config wipe; "
            "store it on separate media",
            status="warn",
        )

    try:
        import hashlib

        h_primary = hashlib.sha256(primary_path.read_bytes()).hexdigest()
        h_backup = hashlib.sha256(backup_path.read_bytes()).hexdigest()
    except OSError as exc:
        return DoctorCheck(name, True, f"could not read password files: {exc}", status="warn")
    if h_primary != h_backup:
        return DoctorCheck(
            name,
            True,
            f"offline copy at {backup} is STALE/mismatched — run scripts/backup-restic-password.sh",
            status="warn",
        )
    return DoctorCheck(name, True, f"offline password copy present and matches ({backup})")


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


# Fixed known-good excerpt for the summarization canary — a good summarizer
# must produce a structurally valid 3-sentence + Keywords summary from this.
_CANARY_EXCERPT = (
    "User: what is the ollama model used for in convmem?\n"
    "Assistant: Ollama runs locally at http://localhost:11434 and serves embeddings "
    "via nomic-embed-text plus summarization via llama3.1:8b. The distill path prefers "
    "deepseek-v4-flash through the DeepSeek API when a key is set, else falls back to "
    "the local llama3.1:8b. This keeps the system local-first."
)


def _check_summarization_canary(cfg: dict) -> DoctorCheck:
    """Cheap real-time output-quality probe for the local summarizer.

    Not a full eval — one fixed excerpt, one call. Catches gross quality
    collapse between scheduled eval runs: (a) structural validity of the summary
    and (b) latency under a threshold (a silent GPU->CPU fallback or contention
    shows up as a large latency jump well before output looks obviously broken).
    """
    import time

    models = cfg.get("models") or {}
    model = models.get("summarize_model", "llama3.1:8b")
    host = models.get("ollama_host", "http://localhost:11434")
    latency_max_ms = int(((cfg.get("eval") or {}).get("canary_latency_ms_max")) or 15000)
    # Bound the call generously above the latency threshold.
    timeout_s = max(30.0, (latency_max_ms / 1000.0) * 2)

    try:
        from eval_grading import grade_summary
        from llm import SUMMARIZE_PROMPT, generate

        prompt = SUMMARIZE_PROMPT.format(messages=_CANARY_EXCERPT)
        start = time.perf_counter()
        summary = generate(
            prompt,
            model=model,
            ollama_host=host,
            deepseek_base_url=models.get("deepseek_base_url", "https://api.deepseek.com"),
            timeout=timeout_s,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
    except requests.RequestException as exc:
        # Infra problem (unreachable / timeout) — _check_ollama owns reachability.
        return DoctorCheck(
            "summarization_canary", True,
            f"skipped: summarizer call failed ({type(exc).__name__}); see ollama check",
            status="skip",
        )
    except Exception as exc:
        return DoctorCheck(
            "summarization_canary", True,
            f"skipped: {type(exc).__name__}: {str(exc)[:120]}",
            status="skip",
        )

    grade = grade_summary(summary)
    structural_ok = grade["structural_pass"]
    latency_ok = elapsed_ms <= latency_max_ms

    if structural_ok and latency_ok:
        return DoctorCheck(
            "summarization_canary", True,
            f"{model} OK ({elapsed_ms}ms; 3 sentences + {grade['n_keywords']} keywords)",
        )
    reasons = []
    if not structural_ok:
        reasons.append(
            f"structure invalid (sentences={grade['n_sentences']}, keywords={grade['n_keywords']})"
        )
    if not latency_ok:
        reasons.append(f"latency {elapsed_ms}ms > {latency_max_ms}ms (possible CPU fallback/contention)")
    return DoctorCheck(
        "summarization_canary", False,
        f"{model}: " + "; ".join(reasons),
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
    from runtime_guard import runtime_summary, write_boundary_message, workspace_repo

    chroma = cfg["index"]["chroma_dir"]
    blocked = write_boundary_message(chroma)
    detail = runtime_summary(chroma)
    if blocked is None:
        return DoctorCheck("write_lane", True, detail)
    # Cross-lane block is expected when workspace doesn't match config lane.
    # Report as skip (informational) rather than failure.
    workspace = workspace_repo()
    if workspace and workspace != "prod":
        return DoctorCheck("write_lane", False, detail, status="skip")
    return DoctorCheck("write_lane", False, detail)


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
        _check_restic_external(),
        _check_restic_password_backup(),
        _check_synthesis_gate(),
        _check_summarization_canary(cfg),
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
        lines.append(f"[{c.effective_status().upper()}] {c.name}: {c.detail}")
    failed = sum(1 for c in checks if c.effective_status() == "fail")
    warned = sum(1 for c in checks if c.effective_status() == "warn")
    skipped = sum(1 for c in checks if c.effective_status() == "skip")
    lines.append("")
    if failed:
        lines.append(f"doctor: {failed} check(s) failed")
    else:
        lines.append("doctor: all checks passed")
    if warned:
        lines.append(f"  ({warned} warning(s) — non-fatal)")
    if skipped:
        lines.append(f"  ({skipped} skipped — expected for cross-lane workspace)")
    return "\n".join(lines)


def doctor_payload(checks: list[DoctorCheck]) -> dict:
    failed = sum(1 for c in checks if c.effective_status() == "fail")
    warned = sum(1 for c in checks if c.effective_status() == "warn")
    skipped = sum(1 for c in checks if c.effective_status() == "skip")
    return {
        "ok": failed == 0,
        "failed": failed,
        "warned": warned,
        "skipped": skipped,
        "checks": [asdict(c) for c in checks],
    }


def doctor_exit_code(checks: list[DoctorCheck]) -> int:
    return 1 if any(c.effective_status() == "fail" for c in checks) else 0
