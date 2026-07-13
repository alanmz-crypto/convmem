"""Health checks for the local convmem installation — reuses brief.py probes."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import requests

from brief import _mcp_registration, _systemd_state, _watch_main_pid, _watch_process_memory
from chroma_readonly import collection_count, open_readonly_unit_store
from config import CONFIG_PATH, load_config
from planning_contract import CONTRACT_VERSION, iter_guide_paths, validate_planning_guides

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


def _standing_register_path() -> Path:
    return Path(__file__).resolve().parent / "docs" / "standing-checks-register.json"


def _eval_provenance_probe(row: dict, root: Path) -> tuple[bool, str]:
    """Probe: every scripts/eval-*.py must call model_context()/judge() unless exempt.

    Encodes the QA/Eval discipline that a *newly added* eval wires provenance +
    judge-independence. Exemptions carry a reason (e.g. deterministic retrieval
    metrics with no LLM output under test).
    """
    trig = row.get("trigger") or {}
    exempt = set()
    for entry in trig.get("exempt") or []:
        path = (entry.get("path") or "").strip()
        if path:
            exempt.add(path)
            exempt.add(Path(path).name)
    scripts_dir = root / "scripts"
    unwired: list[str] = []
    for py in sorted(scripts_dir.glob("eval-*.py")):
        rel = f"scripts/{py.name}"
        if rel in exempt or py.name in exempt:
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "model_context(" not in text and "judge(" not in text:
            unwired.append(py.name)
    if unwired:
        return True, "eval scripts missing provenance/judge wiring: " + ", ".join(unwired)
    return False, "all eval scripts wired (or exempt)"


def _charter_register_consistency_probe(all_rows: list, root: Path) -> tuple[bool, str]:
    """Probe: charter register_refs and register ids stay in sync (dogfoods Layer 2).

    Parses ``register_refs: [...]`` blocks from docs/role-charters.md and compares
    against the loaded register rows. Due if (a) a charter ref points to no
    register id (dangling) or (b) a tracked register row (status open or
    standing) is cited by no charter (orphan). Missing charter file -> not due
    (advisory, never crash).
    """
    import re

    charter = root / "docs" / "role-charters.md"
    if not charter.is_file():
        return False, f"charter file not found ({charter})"
    text = charter.read_text(encoding="utf-8", errors="ignore")
    charter_refs: set[str] = set()
    for m in re.finditer(r"register_refs:\s*\[([^\]]*)\]", text):
        for tok in m.group(1).split(","):
            tok = tok.strip().strip("`\"'")
            # Skip template placeholders like "<Layer 2 check IDs ...>".
            if tok and "<" not in tok and ">" not in tok:
                charter_refs.add(tok)
    all_ids = {str(r.get("id")) for r in all_rows if isinstance(r, dict) and r.get("id")}
    # Require both open backlog rows and charter-owned "standing" rows to be
    # cited: standing rows exist for the charter<->register traceability link,
    # so a dropped citation must still be caught. Closed rows are exempt.
    tracked_ids = {
        str(r.get("id"))
        for r in all_rows
        if isinstance(r, dict) and r.get("status") in ("open", "standing") and r.get("id")
    }
    dangling = sorted(charter_refs - all_ids)
    orphan = sorted(tracked_ids - charter_refs)
    problems: list[str] = []
    if dangling:
        problems.append("dangling charter refs (no register row): " + ", ".join(dangling))
    if orphan:
        problems.append("orphan tracked rows (no charter ref): " + ", ".join(orphan))
    if problems:
        return True, "; ".join(problems)
    return False, f"{len(charter_refs)} charter refs match {len(tracked_ids)} tracked (open+standing) rows"


def _merge_order_probe(row: dict, root: Path) -> tuple[bool, str]:
    """Probe: crush.json global_context_paths canonical order on the Crush surface.

    Asserts CONVMEM-RITUAL.md is first AND CRUSH.md (when present) is last —
    the two ends of the canonical order enforced by deploy-builder-reference.sh.
    Note verify-builder-reference.sh only asserts ritual-first; this probe covers
    both ends. Scope is Crush only (other surfaces have no merge order).

    Mirrors the order assertion in scripts/verify-builder-reference.sh, but runs
    on every doctor pass instead of only (non-fatally) at deploy end — closing
    the residual where a manual crush.json edit breaks salience order between
    deploys. Remediation: bash scripts/deploy-builder-reference.sh (designated
    last writer; re-sorts to ritual-first / CRUSH-last).
    """
    trig = row.get("trigger") or {}
    injected = (trig.get("crush_config") or "").strip()
    candidates = (
        [Path(injected).expanduser()]
        if injected
        else [
            Path("~/.config/crush/crush.json").expanduser(),
            Path("~/.crush/crush.json").expanduser(),
        ]
    )
    config = next((p for p in candidates if p.is_file()), None)
    if config is None:
        return False, "crush.json not found (no Crush surface on this machine)"
    try:
        cfg_json = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return True, f"crush.json unreadable ({type(exc).__name__}) — order unverifiable"
    paths = list((cfg_json.get("options") or {}).get("global_context_paths") or [])
    if not paths:
        return False, "no global_context_paths configured"
    problems: list[str] = []
    # Basename equality, not suffix match — "00-CRUSH.md".endswith("CRUSH.md") is True.
    if Path(str(paths[0])).name != "CONVMEM-RITUAL.md":
        problems.append(f"CONVMEM-RITUAL.md not first (paths[0]={paths[0]})")
    # CRUSH.md, when present, must be last (canonical order: ritual -> ... -> CRUSH.md).
    crush_positions = [i for i, p in enumerate(paths) if Path(str(p)).name == "CRUSH.md"]
    if crush_positions and crush_positions[-1] != len(paths) - 1:
        problems.append(f"CRUSH.md not last (index {crush_positions[-1]} of {len(paths) - 1})")
    if problems:
        return True, "; ".join(problems) + " — run: bash scripts/deploy-builder-reference.sh"
    return False, f"ritual first, CRUSH.md last-or-absent ({len(paths)} paths)"


# The two design docs where a live UNVERIFIED marker would be a resting state.
# Deliberately excludes the retro artifact ("UNVERIFIED sweep" heading) and the
# retro template (instructs in uppercase) — both would false-fire this probe.
_UNVERIFIED_SCOPE = ("docs/role-mapping.md", "docs/role-charters.md")


def _unverified_resting_state_probe(row: dict, root: Path) -> tuple[bool, str]:
    """Probe: no live UNVERIFIED marker left sitting in the mapping/charter docs.

    Mechanizes the 2026-07-07 retro rule that UNVERIFIED is a todo-with-an-owner,
    not a fifth resting category. Convention: a *live* mark is written uppercase
    ``UNVERIFIED`` (typically ``UNVERIFIED(owner)``); historical lowercase prose
    ("was unverified") is invisible to the probe. Case-sensitive whole-word match
    over exactly the two files in ``_UNVERIFIED_SCOPE``. Due lists file:line hits;
    missing files are skipped (advisory, never crash).
    """
    import re

    marker = re.compile(r"\bUNVERIFIED\b")
    hits: list[str] = []
    for rel in _UNVERIFIED_SCOPE:
        doc = root / rel
        if not doc.is_file():
            continue
        for lineno, line in enumerate(
            doc.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
        ):
            if marker.search(line):
                hits.append(f"{rel}:{lineno}")
    if hits:
        return True, "live UNVERIFIED marker(s) — assign an owner and resolve: " + ", ".join(hits)
    return False, f"no live UNVERIFIED marker in {len(_UNVERIFIED_SCOPE)} design docs"


def _exposure_window_probe(row: dict, cfg: dict) -> tuple[bool, str]:
    """Probe: corpus confirmed clean after every critical/high observation close.

    The flagship "P0 done != corpus clean" gap: closing a P0 observation in the
    ledger does not mean stale/poisoned units were swept. Due when any
    critical/high observation has a closed status (per evidence_boost, the same
    machinery as `convmem unresolved`) whose close date is after this row's
    last_verified. Unlike corpus_size rows, bumping last_verified IS the reset
    here — it records "corpus-clean scan done after that close".

    Close date = pass-verification child timestamps (or the observation's own
    timestamp when it carries verification_result: pass), NOT last_touched —
    a later note attached to a closed P0 must not re-fire the row.
    """
    from evidence import evidence_boost
    from ledger import _dedupe_by_ledger_id, _kind, build_ledger_index
    from unresolved import OPEN_STATUSES

    raw = str(row.get("last_verified") or "").strip()
    try:
        last_verified = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return True, f"exposure-window: last_verified unparseable ({raw!r})"

    def _ts_date(ts: str):
        ts = (ts or "").strip()
        if not ts:
            return None
        try:
            if "T" in ts:
                return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
            return datetime.strptime(ts[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    store = open_readonly_unit_store(cfg["index"]["chroma_dir"])
    by_ledger_id, by_relates_to = build_ledger_index(store)

    latest_close = None
    latest_lid = ""
    closed_count = 0
    for lid, meta in by_ledger_id.items():
        kind = _kind(meta)
        if kind != "observation" and (meta.get("type") or "").strip().lower() != "observation":
            continue
        if (meta.get("severity") or "medium").strip().lower() not in ("critical", "high"):
            continue
        _, status = evidence_boost(meta, by_relates_to=by_relates_to)
        if status in OPEN_STATUSES:
            continue
        closed_count += 1
        children = _dedupe_by_ledger_id(
            by_relates_to.get(lid, []) + by_relates_to.get(meta.get("id", ""), [])
        )
        pass_ts = [
            c.get("timestamp", "")
            for c in children
            if _kind(c) == "verification"
            and (c.get("result") or c.get("verification_result") or "").strip().lower() == "pass"
        ]
        if pass_ts:
            close_dates = [d for d in (_ts_date(t) for t in pass_ts) if d]
        elif (meta.get("verification_result") or "").strip().lower() == "pass":
            close_dates = [d for d in [_ts_date(meta.get("timestamp", ""))] if d]
        else:
            # Closed with no verification evidence: fall back to last_touched.
            all_ts = [meta.get("timestamp", "")] + [c.get("timestamp", "") for c in children]
            close_dates = [d for d in (_ts_date(t) for t in all_ts) if d]
        if not close_dates:
            continue
        close = max(close_dates)
        if latest_close is None or close > latest_close:
            latest_close, latest_lid = close, lid

    if closed_count == 0:
        return False, "no closed critical/high observations"
    if latest_close is not None and latest_close > last_verified:
        return True, (
            f"P0 {latest_lid} closed {latest_close}, corpus-clean scan not recorded "
            f"(last_verified {last_verified})"
        )
    return False, f"clean-scan recorded after last P0 close ({closed_count} closed)"


def _standing_row_due(
    row: dict, cfg: dict, root: Path, all_rows: list
) -> tuple[bool, str]:
    """Evaluate one register row's trigger against live state. Returns (due, detail)."""
    trig = row.get("trigger") or {}
    ttype = trig.get("type", "none")

    if ttype == "none":
        return False, "tracked, no trigger"

    if ttype == "charter":
        # Charter-owned standing habit: the trigger is the Role 6 charter
        # read_when retrieval hook (a human evaluates it in-situ), not a
        # doctor-polled condition. Never doctor-due by design. Normally
        # unreachable here because status="standing" rows are filtered before
        # this call — kept for direct callers and as self-documentation.
        return False, "charter-triggered (read_when hook); never doctor-due"

    if ttype in ("manual", "cadence"):
        raw = str(row.get("last_verified") or "").strip()
        try:
            last = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return True, f"{ttype}: last_verified unparseable ({raw!r})"
        age = (datetime.now().date() - last).days
        if ttype == "manual":
            limit = int(trig.get("max_age_days") or row.get("max_age_days") or 90)
            return (age > limit, f"manual: {age}d since verified (limit {limit}d)")
        interval = int(trig.get("interval_days") or 30)
        return (age > interval, f"cadence: {age}d since verified (interval {interval}d)")

    if ttype == "corpus_size":
        baseline = int(trig.get("baseline") or 0)
        multiple = float(trig.get("multiple") or 2.0)
        if baseline <= 0:
            return False, "corpus_size: no baseline recorded"
        count = collection_count(cfg["index"]["chroma_dir"], "knowledge_units")
        threshold = baseline * multiple
        return (count > threshold, f"corpus_size: {count} vs threshold {threshold:.0f}")

    if ttype == "probe":
        probe = trig.get("probe") or row.get("id")
        if probe in ("eval_provenance_wiring", "eval-provenance-wiring"):
            return _eval_provenance_probe(row, root)
        if probe in ("charter_register_consistency", "charter-register-consistency"):
            return _charter_register_consistency_probe(all_rows, root)
        if probe in ("merge_order_position", "merge-order-position"):
            return _merge_order_probe(row, root)
        if probe in ("exposure_window_tracking", "exposure-window-tracking"):
            return _exposure_window_probe(row, cfg)
        if probe in ("unverified_resting_state", "unverified-resting-state"):
            return _unverified_resting_state_probe(row, root)
        return False, f"unknown probe {probe!r} (treated as not due)"

    return False, f"unknown trigger type {ttype!r}"


def _evaluate_standing_rows(
    rows: list, cfg: dict, base: Path
) -> tuple[int, list[dict]]:
    """Evaluate every open register row's trigger. Returns (open_count, due_rows)
    where due_rows is ``[{"id":.., "detail":..}]``. A broken probe nags (is_due)
    rather than crashing — same contract as the doctor check.

    ``status: standing`` rows (charter-owned review habits) are excluded from the
    open-count and never evaluated here by design — they are backlog-adjacent but
    not fireable work. Do not "fix" the apparent omission by counting them."""
    open_count = 0
    due: list[dict] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("status") != "open":
            continue
        open_count += 1
        try:
            is_due, detail = _standing_row_due(row, cfg, base, rows)
        except Exception as exc:  # a broken probe should nag, never crash
            is_due, detail = True, f"probe error: {type(exc).__name__}"
        if is_due:
            due.append({"id": row.get("id", "?"), "detail": detail})
    return open_count, due


def _load_standing_register(
    *,
    register_path: Path | None = None,
    root: Path | None = None,
) -> tuple[Path, Path, list | None, str | None]:
    """Shared load/parse for the standing-checks register JSON.

    Returns ``(path, base, rows, error)``. On success ``error`` is ``None`` and
    ``rows`` is the checks list. On failure ``rows`` is ``None`` and ``error`` is
    one of: ``"missing"``, ``"unreadable:<exc>"``, or ``"no_checks_list"``.
    Callers map those differently (quiet ``(0, [])`` vs doctor skip messages).
    """
    path = register_path or _standing_register_path()
    base = root or Path(__file__).resolve().parent
    if not path.is_file():
        return path, base, None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return path, base, None, f"unreadable:{exc}"
    rows = data.get("checks") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return path, base, None, "no_checks_list"
    return path, base, rows, None


def standing_register_status(
    cfg: dict,
    *,
    register_path: Path | None = None,
    root: Path | None = None,
) -> tuple[int, list[dict]]:
    """Structured Layer 2 status for brief/programmatic callers.

    Returns ``(open_count, due_rows)`` with ``due_rows = [{"id":.., "detail":..}]``.
    A missing / unreadable / malformed register yields ``(0, [])`` — nothing to
    nag — so callers can treat it as "quiet" without special-casing.
    """
    _path, base, rows, error = _load_standing_register(
        register_path=register_path, root=root
    )
    if error is not None or rows is None:
        return 0, []
    return _evaluate_standing_rows(rows, cfg, base)


def _check_standing_register(
    cfg: dict,
    *,
    register_path: Path | None = None,
    root: Path | None = None,
) -> DoctorCheck:
    """Layer 2 Standing Checks — advisory nag for state-dependent maintenance jobs.

    Generalizes ``_check_synthesis_gate`` / ``_check_index_gate``: read a
    persistent register, evaluate each open row's trigger, warn on any that are
    due. Advisory only — always returns ``ok=True`` (status ``warn`` when due)
    so it never changes the doctor exit code; malformed/missing register skips.
    """
    path, base, rows, error = _load_standing_register(
        register_path=register_path, root=root
    )
    if error == "missing":
        return DoctorCheck("standing_register", True, f"no register at {path}", status="skip")
    if error is not None and error.startswith("unreadable:"):
        detail = error[len("unreadable:") :]
        return DoctorCheck(
            "standing_register", True, f"register unreadable: {detail}", status="skip"
        )
    if error == "no_checks_list" or rows is None:
        return DoctorCheck(
            "standing_register", True, "register has no checks list", status="skip"
        )

    open_count, due_rows = _evaluate_standing_rows(rows, cfg, base)
    standing_count = sum(
        1 for r in rows if isinstance(r, dict) and r.get("status") == "standing"
    )
    standing_suffix = f" ({standing_count} charter-standing)" if standing_count else ""
    if not due_rows:
        return DoctorCheck(
            "standing_register", True, f"{open_count} open checks, 0 due{standing_suffix}"
        )
    due = [f"{r['id']} ({r['detail']})" for r in due_rows]
    return DoctorCheck(
        "standing_register",
        True,  # advisory — keep ok True so exit code stays 0
        f"{len(due)}/{open_count} standing checks DUE: " + "; ".join(due),
        status="warn",
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _check_hooks_path(*, root: Path | None = None) -> DoctorCheck:
    """Advisory: core.hooksPath must point at scripts/git-hooks with executable pre-push."""
    name = "hooks_path"
    base = root or _repo_root()
    if not (base / ".git").exists() and not (base / ".git").is_file():
        # worktree .git may be a file
        git_dir = base / ".git"
        if not git_dir.exists():
            return DoctorCheck(name, True, "not a git repo", status="skip")
    from git_hooks import hooks_path_ok

    ok, detail = hooks_path_ok(base)
    if ok:
        return DoctorCheck(name, True, detail)
    return DoctorCheck(name, True, detail, status="warn")


def _check_wip_on_main(*, root: Path | None = None) -> DoctorCheck:
    """Advisory: main must not carry WIP-pattern commit subjects (last 50)."""
    name = "wip_on_main"
    base = root or _repo_root()
    from git_hooks import wip_subjects_on_main

    try:
        wip = wip_subjects_on_main(base, limit=50)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return DoctorCheck(name, True, f"git probe failed: {exc}", status="skip")
    # Empty list + failed git log: distinguish via probing main
    probe = subprocess.run(
        ["git", "rev-parse", "--verify", "main"],
        cwd=base,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if probe.returncode != 0:
        return DoctorCheck(name, True, "main branch unavailable", status="skip")
    if not wip:
        return DoctorCheck(name, True, "main: 0 WIP commits in last 50")
    sample = "; ".join(wip[:3])
    return DoctorCheck(
        name,
        True,
        f"main has {len(wip)} WIP commit(s) — move to wip/<slug> branch: {sample}",
        status="warn",
    )


def _check_dirty_main(*, root: Path | None = None) -> DoctorCheck:
    """WARN when tracked files are dirty while on main (Always-GitHub-Fallback)."""
    name = "dirty_main"
    base = root or _repo_root()
    from git_hooks import dirty_tracked_on_main

    try:
        dirty, detail = dirty_tracked_on_main(base)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return DoctorCheck(name, True, f"git probe failed: {exc}", status="skip")
    if dirty:
        return DoctorCheck(
            name,
            True,
            f"{detail} — use convmem work start/resume (do not edit on main)",
            status="warn",
        )
    return DoctorCheck(name, True, detail)


def _check_unpushed_commits(*, root: Path | None = None) -> DoctorCheck:
    """WARN when current branch has commits not on upstream."""
    name = "unpushed_commits"
    base = root or _repo_root()
    from git_hooks import current_branch, unpushed_commits

    branch = current_branch(base)
    if branch in ("main", "master", ""):
        return DoctorCheck(name, True, f"skip on {branch or 'detached'}", status="skip")
    try:
        err, subjects = unpushed_commits(base)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return DoctorCheck(name, True, f"git probe failed: {exc}", status="skip")
    if err:
        return DoctorCheck(
            name,
            True,
            f"{err} — push with explicit refspec after work start",
            status="warn",
        )
    if not subjects:
        return DoctorCheck(name, True, "0 unpushed commits vs upstream")
    sample = "; ".join(subjects[:3])
    return DoctorCheck(
        name,
        True,
        f"{len(subjects)} unpushed commit(s) — push immediately: {sample}",
        status="warn",
    )


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


def _check_planning_guide_contract() -> DoctorCheck:
    """Hard-fail when docs/planning/* phase guides violate Contract v1."""
    root = Path(__file__).resolve().parent
    problems = validate_planning_guides(root)
    if problems:
        detail = f"contract {CONTRACT_VERSION}: " + "; ".join(problems[:5])
        if len(problems) > 5:
            detail += f"; +{len(problems) - 5} more"
        return DoctorCheck("planning_guide_contract", False, detail)
    n = len(iter_guide_paths(root))
    return DoctorCheck("planning_guide_contract", True, f"contract {CONTRACT_VERSION}: {n} guide(s) ok")


def run_doctor(
    *,
    v1: bool = False,
    run_verify: bool = False,
) -> list[DoctorCheck]:
    """Run health checks. v0 = core; v1 adds watch RSS, summarization canary, systemd, locks."""
    cfg = load_config()
    checks: list[DoctorCheck] = [
        _check_config(),
        _check_write_lane(cfg),
        _check_hooks_path(),  # before WIP/dirty — root cause if hook missing
        _check_wip_on_main(),
        _check_dirty_main(),
        _check_unpushed_commits(),
        _check_deepseek_key(),
        _check_ollama(cfg),
        _check_chroma(cfg),
        _check_index_drift(cfg),
        _check_restic(),
        _check_restic_external(),
        _check_restic_password_backup(),
        _check_synthesis_gate(),
        _check_index_gate(),
        _check_standing_register(cfg),
        _check_planning_guide_contract(),
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
                _check_summarization_canary(cfg),
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
