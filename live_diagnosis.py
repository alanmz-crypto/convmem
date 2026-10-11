"""Scratch-only live watch-child diagnosis hooks (issue #268 D1).

Inactive unless CONVMEM_LIVE_DIAG_SCRATCH_ROOTS is set. All mutable paths and
telemetry files must resolve under those roots; production opens are denied when
CONVMEM_LIVE_DIAG_HERMETIC=1.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from hermetic_open_guards import install_open_guards, restore_open_guards
from hermetic_path_guard import PRODUCTION_PREFIXES

_PHASE_ENV = "CONVMEM_LIVE_DIAG_PHASE_PATH"
_ROOTS_ENV = "CONVMEM_LIVE_DIAG_SCRATCH_ROOTS"
_HERMETIC_ENV = "CONVMEM_LIVE_DIAG_HERMETIC"
_SOURCE_SHA_ENV = "CONVMEM_LIVE_DIAG_SOURCE_SHA256"
_SOURCE_SIZE_ENV = "CONVMEM_LIVE_DIAG_SOURCE_SIZE"
_SOURCE_MTIME_ENV = "CONVMEM_LIVE_DIAG_SOURCE_MTIME_NS"
_DENIAL_PATH_ENV = "CONVMEM_LIVE_DIAG_DENIAL_PATH"
_GATE_PATH_ENV = "CONVMEM_LIVE_DIAG_INDEX_GATE_PATH"
_SUPERVISOR_PID_ENV = "CONVMEM_LIVE_DIAG_SUPERVISOR_PID_PATH"
GATE_PENDING = "pending"
GATE_SCOPE_READY = "scope_ready"
GATE_SPAWN_GRANTED = "spawn_granted"
GATE_INDEX_AT_GATE = "index_at_gate"
GATE_RUN_GRANTED = "run_granted"
_HANDSHAKE_WAIT_SECONDS = 900.0
_PHASE_LINES_ENV = "CONVMEM_LIVE_DIAG_PHASE_LINES"
_MAX_PHASE_LINES = 4096
_MAX_DENIAL_EVENTS = 256

_HERMETIC_INSTALLED = False
_DENIED: list[str] = []
_NETWORK_DENIED: list[str] = []
_RESTORE_HOOKS: dict[str, object] = {}


class LiveDiagnosisRefused(RuntimeError):
    """Fail-closed refusal for the live diagnosis harness."""


def _scratch_roots() -> list[Path] | None:
    raw = os.environ.get(_ROOTS_ENV, "").strip()
    if not raw:
        return None
    try:
        items = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LiveDiagnosisRefused("invalid_scratch_roots_json") from exc
    if not isinstance(items, list) or not items:
        raise LiveDiagnosisRefused("scratch_roots_empty")
    roots: list[Path] = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            raise LiveDiagnosisRefused("scratch_root_not_string")
        roots.append(Path(item).expanduser().resolve())
    return roots


def active() -> bool:
    return _scratch_roots() is not None


def _under_scratch(path: Path, roots: list[Path]) -> bool:
    resolved = path.expanduser().resolve()
    return any(resolved.is_relative_to(root) for root in roots)


def _phase_path() -> Path | None:
    raw = os.environ.get(_PHASE_ENV, "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    roots = _scratch_roots()
    if roots is None:
        raise LiveDiagnosisRefused("phase_path_without_scratch_roots")
    if not _under_scratch(path, roots):
        raise LiveDiagnosisRefused(f"phase_path_outside_scratch:{path}")
    return path


def _phase_lines_written() -> int:
    raw = os.environ.get(_PHASE_LINES_ENV, "").strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def _bump_phase_lines() -> None:
    os.environ[_PHASE_LINES_ENV] = str(_phase_lines_written() + 1)


def _denial_path() -> Path | None:
    raw = os.environ.get(_DENIAL_PATH_ENV, "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    roots = _scratch_roots()
    if roots is None or not _under_scratch(path, roots):
        raise LiveDiagnosisRefused("denial_path_outside_scratch")
    return path


def emit_denial_event(kind: str, detail: str) -> None:
    """Append one bounded denial row visible to the out-of-cgroup parent."""
    path = _denial_path()
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.stat().st_size > 512 * 1024:
        raise LiveDiagnosisRefused("denial_log_full")
    if path.is_file():
        with path.open("r", encoding="utf-8") as handle:
            existing = sum(1 for _ in handle)
        if existing >= _MAX_DENIAL_EVENTS:
            raise LiveDiagnosisRefused("denial_log_full")
    row = {
        "ts": time.time(),
        "pid": os.getpid(),
        "kind": kind,
        "detail": detail[:500],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def mark(phase: str, **fields: Any) -> None:
    """Append one bounded phase marker when diagnosis mode is armed."""
    if not active():
        return
    path = _phase_path()
    if path is None:
        return
    if _phase_lines_written() >= _MAX_PHASE_LINES:
        raise LiveDiagnosisRefused("phase_log_full")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": time.time(),
        "phase": phase,
        **fields,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    _bump_phase_lines()


def init_index_gate_pending() -> None:
    raw = os.environ.get(_GATE_PATH_ENV, "").strip()
    if not raw:
        return
    path = Path(raw).expanduser()
    roots = _scratch_roots()
    if roots is None or not _under_scratch(path, roots):
        raise LiveDiagnosisRefused("index_gate_outside_scratch")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("pending\n", encoding="ascii")


def write_index_gate_state(state: str) -> None:
    raw = os.environ.get(_GATE_PATH_ENV, "").strip()
    if not raw:
        return
    Path(raw).write_text(f"{state}\n", encoding="ascii")


def read_index_gate_state() -> str | None:
    raw = os.environ.get(_GATE_PATH_ENV, "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_file():
        return None
    return path.read_text(encoding="ascii").strip()


def _synthetic_fast_handshake() -> bool:
    return os.environ.get("CONVMEM_LIVE_DIAG_SYNTHETIC_FAST") == "1"


def _wait_for_gate_state(expected: str, *, timeout: float = _HANDSHAKE_WAIT_SECONDS) -> None:
    if _synthetic_fast_handshake():
        return
    allowed_before: set[str | None] = {GATE_PENDING, None}
    if expected == GATE_SPAWN_GRANTED:
        allowed_before.add(GATE_SCOPE_READY)
    if expected == GATE_RUN_GRANTED:
        allowed_before.update({GATE_SPAWN_GRANTED, GATE_INDEX_AT_GATE})
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = read_index_gate_state()
        if state == expected:
            return
        if state in allowed_before:
            time.sleep(0.05)
            continue
        raise LiveDiagnosisRefused(f"index_gate_invalid:{state}")
    raise LiveDiagnosisRefused(f"index_gate_timeout:{expected}")


def wait_for_spawn_granted() -> None:
    if os.environ.get(_HERMETIC_ENV) != "1":
        return
    if not os.environ.get(_GATE_PATH_ENV, "").strip():
        return
    _wait_for_gate_state(GATE_SPAWN_GRANTED)


def wait_for_run_granted() -> None:
    if os.environ.get(_HERMETIC_ENV) != "1":
        return
    if not os.environ.get(_GATE_PATH_ENV, "").strip():
        return
    _wait_for_gate_state(GATE_RUN_GRANTED)


def publish_supervisor_pid() -> None:
    raw = os.environ.get(_SUPERVISOR_PID_ENV, "").strip()
    if not raw:
        return
    roots = _scratch_roots()
    if roots is None:
        raise LiveDiagnosisRefused("supervisor_pid_without_scratch_roots")
    path = Path(raw).expanduser()
    if not _under_scratch(path, roots):
        raise LiveDiagnosisRefused("supervisor_pid_outside_scratch")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{os.getpid()}\n", encoding="ascii")


def signal_index_at_gate() -> None:
    write_index_gate_state(GATE_INDEX_AT_GATE)


def assert_source_unchanged(path: str | Path) -> None:
    expected = os.environ.get(_SOURCE_SHA_ENV, "").strip()
    if not expected or not active():
        return
    p = Path(path).expanduser().resolve()
    with p.open("rb") as handle:
        observed = hashlib.file_digest(handle, "sha256").hexdigest()
    if observed != expected:
        raise LiveDiagnosisRefused("source_identity_drift")


def _on_production_path_denied(target: object) -> None:
    _DENIED.append(str(target))
    emit_denial_event("production_path", str(target))
    raise LiveDiagnosisRefused(f"production_path_denied:{target}")


def _on_network_denied() -> None:
    _NETWORK_DENIED.append("outbound")
    emit_denial_event("network", "outbound")
    raise LiveDiagnosisRefused("network_denied")


def _install_hermetic_guards() -> None:
    global _HERMETIC_INSTALLED  # pylint: disable=global-statement
    if _HERMETIC_INSTALLED:
        return
    _RESTORE_HOOKS.update(
        install_open_guards(
            on_path_denied=_on_production_path_denied,
            on_network_denied=_on_network_denied,
        )
    )
    _HERMETIC_INSTALLED = True


def teardown_hermetic_guards() -> None:
    """Test-only restore so parent canary snapshots stay read-only outside workers."""
    global _HERMETIC_INSTALLED  # pylint: disable=global-statement
    if not _HERMETIC_INSTALLED:
        return
    restore_open_guards(_RESTORE_HOOKS)
    _HERMETIC_INSTALLED = False
    _DENIED.clear()
    _NETWORK_DENIED.clear()


def _roots_must_not_include_production(roots: list[Path]) -> None:
    for root in roots:
        resolved = root.resolve()
        for prefix in PRODUCTION_PREFIXES:
            prod = Path(prefix).expanduser().resolve()
            if resolved == prod or resolved.is_relative_to(prod):
                raise LiveDiagnosisRefused("scratch_root_is_production")
            try:
                prod.relative_to(resolved)
            except ValueError:
                continue
            raise LiveDiagnosisRefused("scratch_is_ancestor_of_production")


def _require_nonempty_source_sha() -> None:
    if os.environ.get(_HERMETIC_ENV) != "1":
        return
    if not os.environ.get(_SOURCE_SHA_ENV, "").strip():
        raise LiveDiagnosisRefused("source_sha_missing")


def _assert_frozen_source_contract() -> None:
    if os.environ.get(_HERMETIC_ENV) != "1":
        return
    raw_path = os.environ.get("CONVMEM_LIVE_DIAG_SOURCE_PATH", "").strip()
    if not raw_path:
        raise LiveDiagnosisRefused("source_contract_missing")
    _assert_frozen_source_contract_for_path(Path(raw_path))


def assert_source_identity_postcheck(path: str | Path) -> None:
    """Parent-side postcheck using externally supplied identity contract."""
    if os.environ.get(_HERMETIC_ENV) != "1":
        return
    _assert_frozen_source_contract_for_path(Path(path))


def _assert_frozen_source_contract_for_path(path: Path) -> None:
    roots = _scratch_roots()
    if roots is None:
        raise LiveDiagnosisRefused("source_contract_without_scratch_roots")
    expected = os.environ.get(_SOURCE_SHA_ENV, "").strip()
    raw_path = os.environ.get("CONVMEM_LIVE_DIAG_SOURCE_PATH", "").strip()
    if not raw_path or not expected:
        raise LiveDiagnosisRefused("source_contract_missing")
    resolved = path.expanduser().resolve()
    if resolved != Path(raw_path).expanduser().resolve():
        raise LiveDiagnosisRefused("source_path_mismatch")
    if not _under_scratch(resolved, roots):
        raise LiveDiagnosisRefused("source_path_outside_scratch")
    with resolved.open("rb") as handle:
        observed = hashlib.file_digest(handle, "sha256").hexdigest()
    if observed != expected:
        raise LiveDiagnosisRefused("source_identity_drift")
    expected_size = os.environ.get(_SOURCE_SIZE_ENV, "").strip()
    expected_mtime = os.environ.get(_SOURCE_MTIME_ENV, "").strip()
    st = resolved.stat()
    if expected_size and str(st.st_size) != expected_size:
        raise LiveDiagnosisRefused("source_size_drift")
    if expected_mtime and str(st.st_mtime_ns) != expected_mtime:
        raise LiveDiagnosisRefused("source_mtime_drift")


def _publish_index_child_pid() -> None:
    raw = os.environ.get("CONVMEM_LIVE_DIAG_INDEX_PID_PATH", "").strip()
    if not raw:
        return
    roots = _scratch_roots()
    if roots is None:
        raise LiveDiagnosisRefused("index_pid_without_scratch_roots")
    path = Path(raw).expanduser()
    if not _under_scratch(path, roots):
        raise LiveDiagnosisRefused("index_pid_path_outside_scratch")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{os.getpid()}\n", encoding="ascii")


def _require_config_path() -> Path:
    raw = os.environ.get("CONVMEM_CONFIG", "").strip()
    if not raw:
        raise LiveDiagnosisRefused("config_missing_for_hermetic")
    path = Path(raw).expanduser()
    if not path.is_file():
        raise LiveDiagnosisRefused("config_not_found_for_hermetic")
    return path


def _assert_config_under_scratch() -> None:
    roots = _scratch_roots()
    if roots is None:
        raise LiveDiagnosisRefused("hermetic_without_scratch_roots")
    _roots_must_not_include_production(roots)
    config_path = _require_config_path()
    if not _under_scratch(config_path, roots):
        raise LiveDiagnosisRefused(f"config_path_outside_scratch:{config_path}")
    from config import load_config

    cfg = load_config(config_path)
    idx = cfg.get("index") or {}
    paths = [
        idx.get("chroma_dir"),
        idx.get("processed_log"),
        idx.get("units_export"),
        cfg.get("sources", {}).get("inventory"),
    ]
    brief = os.environ.get("CONVMEM_LIVE_DIAG_BRIEF_PATH", "").strip()
    if brief:
        paths.append(brief)
    writer = os.environ.get("CONVMEM_LIVE_DIAG_WRITER_ROOT", "").strip()
    if writer:
        paths.append(writer)
    for raw in paths:
        if not raw:
            raise LiveDiagnosisRefused("config_incomplete_mutable_root")
        if not _under_scratch(Path(str(raw)), roots):
            raise LiveDiagnosisRefused(f"config_path_outside_scratch:{raw}")


def _install_scratch_writer_routes() -> None:
    raw = os.environ.get("CONVMEM_LIVE_DIAG_WRITER_ROOT", "").strip()
    if not raw:
        raise LiveDiagnosisRefused("writer_root_missing_for_hermetic_index")
    roots = _scratch_roots()
    if roots is None:
        raise LiveDiagnosisRefused("writer_root_without_scratch_roots")
    writer_root = Path(raw).expanduser().resolve()
    if not _under_scratch(writer_root, roots):
        raise LiveDiagnosisRefused("writer_root_outside_scratch")
    config_path = os.environ.get("CONVMEM_CONFIG", "").strip()
    if not config_path:
        raise LiveDiagnosisRefused("config_missing_for_hermetic_index")

    from contextlib import contextmanager
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    import ingest
    import writer_census
    from config import load_config

    cfg = load_config(Path(config_path))
    chroma_root = Path(cfg["index"]["chroma_dir"]).expanduser()
    writer_census.start_writer_census(
        chroma_root=chroma_root,
        writer_gate_path=writer_root / "writer.lock",
        census_dir=writer_root / "census",
        now=datetime.now(timezone.utc) - timedelta(days=2),
    )

    real_write_session = ingest.production_chroma_write_session
    real_writer_boundary = ingest.production_writer_boundary

    @contextmanager
    def hermetic_write_session(**kwargs):
        kwargs.setdefault("config_path", config_path)
        kwargs.setdefault("lock_path", writer_root / "writer.lock")
        kwargs.setdefault("attest_dir", writer_root / "attest")
        kwargs.setdefault("census_dir", writer_root / "census")
        with real_write_session(**kwargs) as session:
            yield session

    @contextmanager
    def hermetic_writer_boundary(**kwargs):
        kwargs.setdefault("lock_path", writer_root / "writer.lock")
        kwargs.setdefault("attest_dir", writer_root / "attest")
        kwargs.setdefault("census_dir", writer_root / "census")
        with real_writer_boundary(**kwargs) as attestation:
            yield attestation

    patch.object(ingest, "production_chroma_write_session", hermetic_write_session).start()
    patch.object(ingest, "production_writer_boundary", hermetic_writer_boundary).start()

    agent_dir = writer_root / "agent_runs"
    agent_dir.mkdir(parents=True, exist_ok=True)
    import agent_run_ledger

    patch.object(agent_run_ledger, "DEFAULT_DATA_DIR", agent_dir).start()

    register_raw = os.environ.get("CONVMEM_LIVE_DIAG_REGISTER_PATH", "").strip()
    if register_raw:
        register_path = Path(register_raw).expanduser().resolve()
        if not _under_scratch(register_path, roots):
            raise LiveDiagnosisRefused("register_path_outside_scratch")
        import doctor

        patch.object(doctor, "_standing_register_path", return_value=register_path).start()
        patch.object(doctor, "_exposure_window_probe", return_value=(False, "live-diagnosis")).start()

    import brief

    patch.object(brief, "_systemd_state", return_value="disabled/inactive").start()
    patch.object(brief, "_mcp_registration", return_value={}).start()
    patch.object(brief, "_watch_process_memory", return_value=None).start()
    patch.object(brief, "_pending_decision_ingest", return_value=[]).start()


def _install_fake_providers() -> None:
    from unittest.mock import patch

    import ingest

    def distill_stub(*_args, **_kwargs):
        units = [
            {
                "type": "explanation",
                "title": "live-diagnosis unit",
                "summary": "Deterministic distill stub for scratch harness.",
                "keywords": ["live", "diagnosis"],
                "confidence": 0.95,
                "domain": "coding.storage",
            }
        ]
        return units, json.dumps(units, ensure_ascii=False, sort_keys=True)

    vector = [0.1, 0.2]
    patch("ingest.summarize", return_value="live-diagnosis summary").start()
    patch("ingest._distill_with_provenance", side_effect=distill_stub).start()
    patch("ingest.ollama_embed", return_value=vector).start()
    patch("llm.summarize", return_value="live-diagnosis summary").start()
    patch("llm.ollama_embed", return_value=vector).start()
    patch("distill.distill_with_response", side_effect=distill_stub).start()
    patch("ingest.time.sleep").start()
    setattr(ingest, "_LIVE_DIAG_PATCHED", True)


def _redirect_brief_path() -> None:
    raw = os.environ.get("CONVMEM_LIVE_DIAG_BRIEF_PATH", "").strip()
    if not raw:
        return
    roots = _scratch_roots()
    if roots is None or not _under_scratch(Path(raw), roots):
        raise LiveDiagnosisRefused("brief_path_outside_scratch")
    import brief

    brief.DEFAULT_BRIEF_PATH = Path(raw).expanduser()


def _run_configured_net_probe(role: str) -> None:
    if os.environ.get(_HERMETIC_ENV) != "1":
        return
    try:
        from tests.watch_oom_live_diagnosis_net_probe import (
            NetProbeVerificationError,
            run_configured_net_probe,
        )

        run_configured_net_probe(role)
    except NetProbeVerificationError as exc:
        raise LiveDiagnosisRefused(str(exc)) from exc


def _require_denial_path() -> None:
    if os.environ.get(_HERMETIC_ENV) != "1":
        return
    raw = os.environ.get(_DENIAL_PATH_ENV, "").strip()
    if not raw:
        raise LiveDiagnosisRefused("denial_path_missing")
    path = Path(raw).expanduser()
    roots = _scratch_roots()
    if roots is None or not _under_scratch(path, roots):
        raise LiveDiagnosisRefused("denial_path_outside_scratch")


def bootstrap_index_child() -> None:
    """Entry hook for `convmem index` subprocess under the D1 harness."""
    if os.environ.get(_HERMETIC_ENV) != "1":
        return
    _require_denial_path()
    _require_nonempty_source_sha()
    _assert_config_under_scratch()
    _assert_frozen_source_contract()
    _publish_index_child_pid()
    signal_index_at_gate()
    wait_for_run_granted()
    _redirect_brief_path()
    _install_scratch_writer_routes()
    _install_hermetic_guards()
    _install_fake_providers()
    mark("index_child_bootstrap")


def bootstrap_watch_worker() -> None:
    """Entry hook for the parent-side watch flush worker."""
    if os.environ.get(_HERMETIC_ENV) != "1":
        return
    _require_denial_path()
    _require_nonempty_source_sha()
    _assert_config_under_scratch()
    _redirect_brief_path()
    _run_configured_net_probe("outer")
    _install_hermetic_guards()
    mark("watch_worker_bootstrap")


def hermetic_denial_snapshot() -> dict[str, list[str]]:
    return {"denied_paths": list(_DENIED), "network_denied": list(_NETWORK_DENIED)}
