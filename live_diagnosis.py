"""Scratch-only live watch-child diagnosis hooks (issue #268 D1).

Inactive unless CONVMEM_LIVE_DIAG_SCRATCH_ROOTS is set. All mutable paths and
telemetry files must resolve under those roots; production opens are denied when
CONVMEM_LIVE_DIAG_HERMETIC=1.
"""

from __future__ import annotations

import builtins
import hashlib
import json
import os
import socket
import sqlite3
import time
from pathlib import Path
from typing import Any

_PHASE_ENV = "CONVMEM_LIVE_DIAG_PHASE_PATH"
_ROOTS_ENV = "CONVMEM_LIVE_DIAG_SCRATCH_ROOTS"
_HERMETIC_ENV = "CONVMEM_LIVE_DIAG_HERMETIC"
_SOURCE_SHA_ENV = "CONVMEM_LIVE_DIAG_SOURCE_SHA256"
_MAX_PHASE_LINES = 4096

PRODUCTION_PREFIXES = (
    str((Path.home() / ".local/share/convmem").resolve()),
    str((Path.home() / ".config/convmem").resolve()),
)
DEFAULT_BRIEF = str((Path.home() / ".local/share/convmem/brief.md").expanduser())

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


def mark(phase: str, **fields: Any) -> None:
    """Append one bounded phase marker when diagnosis mode is armed."""
    if not active():
        return
    path = _phase_path()
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) >= _MAX_PHASE_LINES:
            raise LiveDiagnosisRefused("phase_log_full")
    payload = {
        "ts": time.time(),
        "phase": phase,
        **fields,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def assert_source_unchanged(path: str | Path) -> None:
    expected = os.environ.get(_SOURCE_SHA_ENV, "").strip()
    if not expected or not active():
        return
    p = Path(path).expanduser().resolve()
    with p.open("rb") as handle:
        observed = hashlib.file_digest(handle, "sha256").hexdigest()
    if observed != expected:
        raise LiveDiagnosisRefused("source_identity_drift")


def _production_denied(path: object) -> bool:
    try:
        raw = os.fspath(path)
    except TypeError:
        return False
    expanded = str(Path(raw).expanduser())
    try:
        resolved = str(Path(expanded).resolve())
    except OSError:
        resolved = expanded
    if DEFAULT_BRIEF in (expanded, resolved):
        return True
    for prefix in PRODUCTION_PREFIXES:
        if resolved.startswith(prefix) or expanded.startswith(prefix):
            return True
    return False


def _install_hermetic_guards() -> None:
    global _HERMETIC_INSTALLED  # noqa: PLW0603
    if _HERMETIC_INSTALLED:
        return
    import io

    real_open = builtins.open
    real_os_open = os.open
    real_connect = sqlite3.connect
    real_io_open = io.open
    real_path_open = Path.open

    def guarded_open(file, *args, **kwargs):
        if _production_denied(file):
            _DENIED.append(str(file))
            raise LiveDiagnosisRefused(f"production_path_denied:{file}")
        return real_open(file, *args, **kwargs)

    def guarded_os_open(path, *args, **kwargs):
        if _production_denied(path):
            _DENIED.append(str(path))
            raise LiveDiagnosisRefused(f"production_path_denied:{path}")
        return real_os_open(path, *args, **kwargs)

    def guarded_io_open(file, *args, **kwargs):
        if _production_denied(file):
            _DENIED.append(str(file))
            raise LiveDiagnosisRefused(f"production_path_denied:{file}")
        return real_io_open(file, *args, **kwargs)

    def guarded_path_open(self, *args, **kwargs):
        if _production_denied(self):
            _DENIED.append(str(self))
            raise LiveDiagnosisRefused(f"production_path_denied:{self}")
        return real_path_open(self, *args, **kwargs)

    def guarded_connect(database, *args, **kwargs):
        target = database
        if isinstance(database, str) and database.startswith("file:"):
            target = database[5:].split("?", 1)[0]
        if _production_denied(target):
            _DENIED.append(str(database))
            raise LiveDiagnosisRefused(f"production_path_denied:{database}")
        return real_connect(database, *args, **kwargs)

    def denied(*_args, **_kwargs):
        _NETWORK_DENIED.append("outbound")
        raise LiveDiagnosisRefused("network_denied")

    _RESTORE_HOOKS.update(
        {
            "builtins.open": real_open,
            "os.open": real_os_open,
            "io.open": real_io_open,
            "Path.open": real_path_open,
            "sqlite3.connect": real_connect,
            "socket.create_connection": socket.create_connection,
            "socket.getaddrinfo": socket.getaddrinfo,
            "socket.socket.connect": socket.socket.connect,
            "socket.socket.connect_ex": socket.socket.connect_ex,
        }
    )
    builtins.open = guarded_open  # type: ignore[assignment]
    os.open = guarded_os_open  # type: ignore[assignment]
    io.open = guarded_io_open  # type: ignore[assignment]
    Path.open = guarded_path_open  # type: ignore[assignment]
    sqlite3.connect = guarded_connect  # type: ignore[assignment]
    socket.create_connection = denied  # type: ignore[assignment]
    socket.getaddrinfo = denied  # type: ignore[assignment]
    socket.socket.connect = denied  # type: ignore[assignment]
    socket.socket.connect_ex = denied  # type: ignore[assignment]
    _HERMETIC_INSTALLED = True


def teardown_hermetic_guards() -> None:
    """Test-only restore so parent canary snapshots stay read-only outside workers."""
    global _HERMETIC_INSTALLED  # noqa: PLW0603
    if not _HERMETIC_INSTALLED:
        return
    import io

    builtins.open = _RESTORE_HOOKS["builtins.open"]  # type: ignore[assignment]
    os.open = _RESTORE_HOOKS["os.open"]  # type: ignore[assignment]
    io.open = _RESTORE_HOOKS["io.open"]  # type: ignore[assignment]
    Path.open = _RESTORE_HOOKS["Path.open"]  # type: ignore[assignment]
    sqlite3.connect = _RESTORE_HOOKS["sqlite3.connect"]  # type: ignore[assignment]
    socket.create_connection = _RESTORE_HOOKS["socket.create_connection"]  # type: ignore[assignment]
    socket.getaddrinfo = _RESTORE_HOOKS["socket.getaddrinfo"]  # type: ignore[assignment]
    socket.socket.connect = _RESTORE_HOOKS["socket.socket.connect"]  # type: ignore[assignment]
    socket.socket.connect_ex = _RESTORE_HOOKS["socket.socket.connect_ex"]  # type: ignore[assignment]
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
    roots = _scratch_roots()
    if roots is None:
        raise LiveDiagnosisRefused("source_contract_without_scratch_roots")
    raw_path = os.environ.get("CONVMEM_LIVE_DIAG_SOURCE_PATH", "").strip()
    expected = os.environ.get(_SOURCE_SHA_ENV, "").strip()
    if not raw_path or not expected:
        raise LiveDiagnosisRefused("source_contract_missing")
    path = Path(raw_path).expanduser().resolve()
    if not _under_scratch(path, roots):
        raise LiveDiagnosisRefused("source_path_outside_scratch")
    with path.open("rb") as handle:
        observed = hashlib.file_digest(handle, "sha256").hexdigest()
    if observed != expected:
        raise LiveDiagnosisRefused("source_identity_drift")


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
    ingest._LIVE_DIAG_PATCHED = True  # type: ignore[attr-defined]


def _redirect_brief_path() -> None:
    raw = os.environ.get("CONVMEM_LIVE_DIAG_BRIEF_PATH", "").strip()
    if not raw:
        return
    roots = _scratch_roots()
    if roots is None or not _under_scratch(Path(raw), roots):
        raise LiveDiagnosisRefused("brief_path_outside_scratch")
    import brief

    brief.DEFAULT_BRIEF_PATH = Path(raw).expanduser()


def bootstrap_index_child() -> None:
    """Entry hook for `convmem index` subprocess under the D1 harness."""
    if os.environ.get(_HERMETIC_ENV) != "1":
        return
    _require_nonempty_source_sha()
    _assert_config_under_scratch()
    _assert_frozen_source_contract()
    _redirect_brief_path()
    _install_scratch_writer_routes()
    _install_hermetic_guards()
    _install_fake_providers()
    _publish_index_child_pid()
    mark("index_child_bootstrap")


def bootstrap_watch_worker() -> None:
    """Entry hook for the parent-side watch flush worker."""
    if os.environ.get(_HERMETIC_ENV) != "1":
        return
    _require_nonempty_source_sha()
    _assert_config_under_scratch()
    _redirect_brief_path()
    _install_hermetic_guards()
    mark("watch_worker_bootstrap")


def hermetic_denial_snapshot() -> dict[str, list[str]]:
    return {"denied_paths": list(_DENIED), "network_denied": list(_NETWORK_DENIED)}
