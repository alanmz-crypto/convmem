"""Filesystem watch — incremental index on transcript changes (Milestone F0).

Uses watchdog (inotify on Linux) with debounce, then spawns `convmem index --file`
in a subprocess so Chroma/ML memory is not retained in the watch parent.
"""

# The RK acceptance harness intentionally mirrors watch's process cleanup path.
# pylint: disable=duplicate-code

from __future__ import annotations

import json
import math
import os
import re
import shutil
import signal
import sys
import time
from collections.abc import Callable
from pathlib import Path

from adapters.detect import get_parser
from process_lock import acquire_pid_lock, release_lock

_DEFAULT_INDEX_MEM_MAX = "2G"
_DEFAULT_INDEX_MEM_HIGH = "1500M"
# Interim liveness backstop only (UNRATIFIED). The primary OOM control is the
# per-child memory scope (_scoped_index_cmd). A tuned value awaits the watch-OOM
# full-file-reindex design; do not treat 15*60 as endorsed.
_DEFAULT_INDEX_TIMEOUT_SECONDS = 15 * 60

# Native-fault signals from an index child (negative subprocess returncode):
# SIGSEGV, SIGABRT, SIGBUS. Not -9 (SIGKILL, e.g. OOM killer) or -15 (SIGTERM,
# e.g. our own timeout teardown) — those are not the poison-pill crash class.
_NATIVE_FAULT_SIGNALS = frozenset({-11, -6, -7})
_DEFAULT_CB_FILE_CRASH_THRESHOLD = 3  # N: consecutive native faults on one path
_DEFAULT_CB_TIMEOUT_THRESHOLD = 3  # M: consecutive timeouts on one path
_DEFAULT_CB_GLOBAL_THRESHOLD = 5  # global native faults within the window
_DEFAULT_CB_GLOBAL_WINDOW_SECONDS = 30 * 60  # 30 minutes
_NATIVE_FAULT_LOG = Path("~/.local/share/convmem/native_crash_failures.jsonl").expanduser()

# Live databases that change constantly — watch re-index causes OOM + duplication.
_LIVE_WATCH_SKIP_SUFFIXES = (
    "kiro-cli/data.sqlite3",
    "convmem/imports/webui.db",
    ".copilot/session-store.db",
)
_CURSOR_CHAT_STORE_ROOT = Path("~/.config/cursor/chats").expanduser()
_COPILOT_SESSION_STATE_ROOT = Path("~/.copilot/session-state").expanduser()


def is_live_watch_db(path: Path | str) -> bool:
    """True for append-heavy DBs that must not be watch re-indexed."""
    p = Path(path).expanduser().resolve()
    s = str(p)
    if any(s.endswith(suffix) for suffix in _LIVE_WATCH_SKIP_SUFFIXES):
        return True
    try:
        p.relative_to(_CURSOR_CHAT_STORE_ROOT)
        return p.name == "store.db"
    except ValueError:
        pass
    try:
        p.relative_to(_COPILOT_SESSION_STATE_ROOT)
        # Per-session SQLite + WAL siblings while Copilot CLI is running
        return p.name == "session.db" or p.name.startswith("session.db-")
    except ValueError:
        return False


# Module-level cache for the hot inotify path — avoid re-loading config
# and processed.json on every event (thousands/min from Cursor store.db writes).
_processed_cache: dict | None = None


def _cached_processed() -> dict:
    global _processed_cache
    if _processed_cache is None:
        from config import load_config
        from ingest import load_processed

        cfg = load_config()
        _processed_cache = load_processed(cfg["index"]["processed_log"])
    return _processed_cache


def _invalidate_processed_cache() -> None:
    global _processed_cache
    _processed_cache = None


def is_excluded_by_path(path: Path | str, *, processed: dict | None = None) -> bool:
    """True when processed.json marks this resolved path excluded (no file hash)."""
    from ingest import _processed_path_str

    p = Path(path).expanduser().resolve()
    path_key = str(p)
    if processed is None:
        processed = _cached_processed()
    for entry in processed.values():
        if not isinstance(entry, dict) or not entry.get("excluded"):
            continue
        ep = entry.get("path")
        if ep and _processed_path_str(ep) == path_key:
            return True
    return False


def is_excluded_from_index(path: Path | str) -> bool:
    """Alias for path-based exclusion check (watch hot path avoids hashing)."""
    return is_excluded_by_path(path)


def is_watchable(path: Path | str) -> bool:
    """True if watch should index this path (parser exists, not live DB, not excluded).

    Live-DB check runs FIRST — avoids opening SQLite connections on store.db
    writes (Cursor fires inotify events on every chat message). The old order
    (is_indexable before is_live_watch_db) leaked ~35 MB/min from repeated
    sqlite3.connect() → schema query → close cycles.
    """
    p = Path(path)
    # Fast path: skip known live databases before any expensive detection.
    if is_live_watch_db(p):
        return False
    if not is_indexable(p):
        return False
    if is_excluded_from_index(p):
        return False
    return True


def is_indexable(path: Path | str) -> bool:
    """True if ingest has a parser for this path."""
    return get_parser(path) is not None


def watch_roots(source_paths: list[str]) -> list[Path]:
    """Directory roots to attach observers (files → parent dir)."""
    roots: set[Path] = set()
    for raw in source_paths:
        path = Path(raw).expanduser()
        if not path.exists():
            continue
        roots.add(path.parent if path.is_file() else path)
    return sorted(roots)


class DebounceScheduler:
    """Wait `debounce_seconds` after the last event before flushing a path."""

    def __init__(self, debounce_seconds: float = 30.0):
        self.debounce_seconds = debounce_seconds
        self._last_event: dict[str, float] = {}

    def note(self, path: str) -> None:
        self._last_event[path] = time.monotonic()

    def ready(self) -> list[str]:
        now = time.monotonic()
        due: list[str] = []
        for path, seen_at in list(self._last_event.items()):
            if now - seen_at >= self.debounce_seconds:
                due.append(path)
        return due

    def forget(self, path: str) -> None:
        self._last_event.pop(path, None)

    def pending_count(self) -> int:
        return len(self._last_event)


def _convmem_cli_argv() -> list[str]:
    return [sys.executable, str(Path(__file__).resolve().parent / "convmem.py")]


def _user_systemd_session_available() -> bool:
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    return bool(runtime) and Path(runtime).is_dir()


def _scoped_index_cmd(
    inner_cmd: list[str],
    cfg: dict,
    *,
    verbose: bool = False,
) -> list[str]:
    """Wrap index argv in a memory-capped systemd user scope when available."""
    if not shutil.which("systemd-run") or not _user_systemd_session_available():
        if verbose and not getattr(_scoped_index_cmd, "fallback_logged", False):
            print(
                "[watch] systemd-run scope unavailable; index child uncapped",
                file=sys.stderr,
            )
            _scoped_index_cmd.fallback_logged = True
        return inner_cmd

    watch_cfg = cfg.get("watch") or {}
    mem_max = watch_cfg.get("subprocess_memory_max", _DEFAULT_INDEX_MEM_MAX)
    mem_high = watch_cfg.get("subprocess_memory_high", _DEFAULT_INDEX_MEM_HIGH)
    return [
        "systemd-run",
        "--user",
        "--scope",
        "--quiet",
        "-p",
        f"MemoryMax={mem_max}",
        "-p",
        f"MemoryHigh={mem_high}",
        "-p",
        "MemorySwapMax=0",
        "--",
    ] + inner_cmd


def _flush_path_subprocess(path: str, *, verbose: bool) -> dict:
    """Run index in a child process so ML/Chroma memory is released after each file."""
    import subprocess

    from config import load_config

    cfg = load_config()
    watch_cfg = cfg.get("watch") or {}
    try:
        timeout = float(
            watch_cfg.get("subprocess_timeout_seconds", _DEFAULT_INDEX_TIMEOUT_SECONDS)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "watch.subprocess_timeout_seconds must be a positive number"
        ) from exc
    if timeout <= 0 or not math.isfinite(timeout):
        raise ValueError("watch.subprocess_timeout_seconds must be a positive number")
    inner_cmd = _convmem_cli_argv() + ["index", "--file", path]
    cmd = _scoped_index_cmd(inner_cmd, cfg, verbose=verbose)
    if verbose:
        print(f"[watch] spawn: {' '.join(inner_cmd[-3:])}", file=sys.stderr)
    with subprocess.Popen(
        cmd,
        text=True,
        stdout=subprocess.PIPE if not verbose else None,
        stderr=subprocess.PIPE if not verbose else None,
        start_new_session=True,
    ) as proc:
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.communicate()
            raise RuntimeError(
                f"index subprocess timed out after {timeout:g} seconds"
            ) from exc
        if proc.returncode != 0:
            err = (stderr or stdout or "").strip()
            raise RuntimeError(err or f"index subprocess exit {proc.returncode}")
        if verbose and stdout:
            for line in stdout.splitlines():
                print(line, file=sys.stderr)
    return {"subprocess": True, "path": path}


def parse_native_fault_returncode(message: str) -> int | None:
    """Extract the index-subprocess returncode from a flush_path RuntimeError message.

    Returns the (possibly negative) returncode when the message matches
    ``_flush_path_subprocess``'s "index subprocess exit <N>" shape, or ``None`` for
    any other message (a timeout, or an ordinary parse/provider-drop error).
    """
    match = re.search(r"index subprocess exit (-?\d+)\s*$", message)
    if not match:
        return None
    return int(match.group(1))


def is_native_fault_returncode(returncode: int | None) -> bool:
    """True for a signal death this circuit breaker should count (not -9/-15/timeout)."""
    return returncode is not None and returncode in _NATIVE_FAULT_SIGNALS


def is_timeout_message(message: str) -> bool:
    return "index subprocess timed out after" in message


def _circuit_breaker_state_path_from_config(cfg: dict) -> Path:
    watch_cfg = cfg.get("watch") or {}
    if watch_cfg.get("circuit_breaker_state_file"):
        return Path(watch_cfg["circuit_breaker_state_file"]).expanduser()
    chroma = Path(cfg["index"]["chroma_dir"]).expanduser()
    return chroma.parent / "watch_circuit_breaker.json"


def log_native_crash(path: str, message: str, *, log_path: Path | None = None) -> None:
    """Append a native-crash record for doctor's native_crash_count to read."""
    from datetime import datetime, timezone

    target = log_path or _NATIVE_FAULT_LOG
    target.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "path": path,
        "message": message[:500],
    }
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


class CircuitBreakerState:
    """Per-path native-fault/timeout quarantine plus a global breaker.

    Persisted atomically (temp file + os.replace) so a process death mid-write
    cannot leave the state file partially written — the exact failure class this
    feature exists to survive.
    """

    def __init__(self, state_path: Path):
        self.state_path = state_path
        self._data = self._load()

    def _load(self) -> dict:
        try:
            raw = self.state_path.read_text(encoding="utf-8")
        except OSError:
            return {"paths": {}, "global_events": []}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {"paths": {}, "global_events": []}
        if not isinstance(data, dict):
            return {"paths": {}, "global_events": []}
        data.setdefault("paths", {})
        data.setdefault("global_events", [])
        return data

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_name(self.state_path.name + f".tmp{os.getpid()}")
        tmp.write_text(json.dumps(self._data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.state_path)

    def is_quarantined(self, path: str) -> bool:
        entry = self._data["paths"].get(path)
        return bool(entry and entry.get("quarantined"))

    def record_success(self, path: str) -> None:
        """Reset a path's counters after a clean index. Does not clear quarantine."""
        entry = self._data["paths"].get(path)
        if entry and not entry.get("quarantined"):
            del self._data["paths"][path]
            self._save()

    def record_failure(
        self,
        path: str,
        *,
        native_fault: bool,
        timeout: bool,
        now: float | None = None,
        crash_threshold: int = _DEFAULT_CB_FILE_CRASH_THRESHOLD,
        timeout_threshold: int = _DEFAULT_CB_TIMEOUT_THRESHOLD,
    ) -> bool:
        """Record a failure for path. Returns True if path is now quarantined."""
        if now is None:
            now = time.time()
        entry = self._data["paths"].setdefault(
            path, {"native_crash_count": 0, "timeout_count": 0, "quarantined": False}
        )
        if native_fault:
            entry["native_crash_count"] += 1
            self._data["global_events"].append(now)
            if entry["native_crash_count"] >= crash_threshold:
                entry["quarantined"] = True
        elif timeout:
            entry["timeout_count"] += 1
            if entry["timeout_count"] >= timeout_threshold:
                entry["quarantined"] = True
        self._save()
        return bool(entry["quarantined"])

    def global_breaker_tripped(
        self,
        *,
        now: float | None = None,
        global_threshold: int = _DEFAULT_CB_GLOBAL_THRESHOLD,
        global_window_seconds: float = _DEFAULT_CB_GLOBAL_WINDOW_SECONDS,
    ) -> bool:
        """True when >= global_threshold native faults (any path) hit within the window."""
        if now is None:
            now = time.time()
        cutoff = now - global_window_seconds
        recent = [t for t in self._data["global_events"] if t >= cutoff]
        if len(recent) != len(self._data["global_events"]):
            self._data["global_events"] = recent
            self._save()
        return len(recent) >= global_threshold

    def clear(self, path: str | None = None) -> None:
        if path is None:
            self._data = {"paths": {}, "global_events": []}
        else:
            self._data["paths"].pop(path, None)
        self._save()


def flush_path(
    path: str,
    *,
    index_fn: Callable[..., dict] | None = None,
    verbose: bool = True,
    use_subprocess: bool = False,
) -> dict | None:
    """Run incremental index for one file. Returns stats or None if skipped."""
    from config import load_config
    from ingest import load_processed, watch_skip_reason

    p = Path(path).expanduser().resolve()
    if not p.is_file():
        if verbose:
            print(f"[watch] skip (not a file): {path}", file=sys.stderr)
        return None
    if not is_indexable(p):
        if verbose:
            print(f"[watch] skip (no parser): {p.name}", file=sys.stderr)
        return None
    if is_live_watch_db(p):
        if verbose:
            print(f"[watch] skip (live DB): {p.name}", file=sys.stderr)
        return None

    cfg = load_config()
    processed = load_processed(cfg["index"]["processed_log"])
    if is_excluded_by_path(p, processed=processed):
        if verbose:
            print(f"[watch] skip (excluded): {p.name}", file=sys.stderr)
        return None

    skip = watch_skip_reason(p, processed=processed)
    if skip:
        if verbose:
            print(f"[watch] skip ({skip}): {p.name}", file=sys.stderr)
        return None
    if use_subprocess:
        if verbose:
            print(f"[watch] indexing {p.name}", file=sys.stderr)
        result = _flush_path_subprocess(str(p), verbose=verbose)
        _invalidate_processed_cache()
        return result
    if index_fn is None:
        from ingest import index as index_fn_impl

        index_fn = index_fn_impl
    if verbose:
        print(f"[watch] indexing {p.name}", file=sys.stderr)
    return index_fn(force_file=str(p), verbose=verbose)


def _lock_path_from_config(cfg: dict) -> Path:
    watch_cfg = cfg.get("watch") or {}
    if watch_cfg.get("lock_file"):
        return Path(watch_cfg["lock_file"]).expanduser()
    chroma = Path(cfg["index"]["chroma_dir"]).expanduser()
    return chroma.parent / "watch.lock"


def _pid_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode(errors="replace")


def _is_live_watch_pid(pid: int) -> bool:
    """True when pid is a running convmem watch process (not PID reuse)."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    cmd = _pid_cmdline(pid)
    return "convmem" in cmd and " watch" in cmd


def acquire_lock(lock_path: Path) -> None:
    """Create a PID lock; exit if another live watch holds it."""
    acquire_pid_lock(
        lock_path,
        pid=os.getpid(),
        is_live_pid=_is_live_watch_pid,
        label="watch",
    )


def load_watch_settings(cfg: dict) -> tuple[float, list[str], Path]:
    watch_cfg = cfg.get("watch") or {}
    debounce = float(watch_cfg.get("debounce_seconds", 30))
    base = watch_cfg.get("paths") or cfg.get("sources", {}).get("paths") or []
    extra = watch_cfg.get("extra_paths") or []
    paths = list(base) + list(extra)
    if not paths:
        raise ValueError("No watch paths — set [sources].paths or [watch].paths in config.toml")
    lock_path = _lock_path_from_config(cfg)
    return debounce, paths, lock_path


def _process_ready_path(
    path: str,
    *,
    cfg: dict,
    breaker: CircuitBreakerState,
    verbose: bool,
) -> None:
    """Run watch's per-path body once: reconcile token, quarantine skip, or index.

    Extracted from run_watch's main loop to keep that loop's branch/nesting
    count within the repo's complexity gate.
    """
    from repository_knowledge_sync import (
        is_reconcile_token,
        reconcile_manifest,
        token_manifest_path,
    )

    try:
        if is_reconcile_token(path):
            reconcile_manifest(token_manifest_path(path), cfg)
            return
        if breaker.is_quarantined(path):
            if verbose:
                print(f"[watch] skip (quarantined): {path}", file=sys.stderr)
            return
        flush_path(path, verbose=verbose, use_subprocess=True)
        breaker.record_success(path)
    except Exception as e:  # pylint: disable=broad-exception-caught
        _record_ready_path_failure(path, e, breaker=breaker, verbose=verbose)


def _record_ready_path_failure(
    path: str,
    exc: Exception,
    *,
    breaker: CircuitBreakerState,
    verbose: bool,
) -> None:
    from repository_knowledge_sync import is_reconcile_token

    message = str(exc)
    if not is_reconcile_token(path):
        returncode = parse_native_fault_returncode(message)
        native_fault = is_native_fault_returncode(returncode)
        timeout = is_timeout_message(message)
        if native_fault or timeout:
            quarantined = breaker.record_failure(path, native_fault=native_fault, timeout=timeout)
            if native_fault:
                log_native_crash(path, message)
            if quarantined and verbose:
                print(f"[watch] quarantined after repeated failures: {path}", file=sys.stderr)
    print(f"[watch] error processing {path}: {exc}", file=sys.stderr)


def run_watch(  # pylint: disable=too-many-locals,broad-exception-caught
    *,
    debounce_seconds: float | None = None,
    paths: list[str] | None = None,
    use_lock: bool = True,
    verbose: bool = True,
) -> None:
    """Block until interrupted; debounce and index changed ingestible files."""
    from config import load_config

    try:
        from watchdog.events import FileSystemEvent, FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError as e:
        print(
            "[watch] watchdog is required: pip install watchdog",
            file=sys.stderr,
        )
        raise SystemExit(1) from e

    cfg = load_config()
    debounce, config_paths, lock_path = load_watch_settings(cfg)
    if debounce_seconds is not None:
        debounce = debounce_seconds
    if paths is not None:
        watch_paths = paths
    else:
        watch_paths = config_paths

    from repository_knowledge_scope import apply_config, manifests_from_cfg
    from repository_knowledge_sync import (
        ManifestPoller,
        is_reconcile_token,
        reconcile_all,
        reconcile_manifest,
        reconcile_token,
        repository_roots_from_cfg,
        token_manifest_path,
    )

    apply_config(cfg)
    rk_roots = repository_roots_from_cfg(cfg)
    roots = sorted(set(watch_roots(watch_paths)) | set(rk_roots))
    if not roots:
        print("[watch] no existing watch roots — check [sources].paths", file=sys.stderr)
        raise SystemExit(1)

    if use_lock:
        acquire_lock(lock_path)

    from source_reconciler import run_startup_reconciliation

    try:
        run_startup_reconciliation(cfg)
    except (OSError, RuntimeError) as exc:
        print(f"[watch] source reconciliation sweep failed: {exc}", file=sys.stderr)

    try:
        reconcile_all(cfg)
    except Exception as exc:
        print(f"[watch] repository-knowledge startup sync failed: {exc}", file=sys.stderr)

    scheduler = DebounceScheduler(debounce_seconds=debounce)
    breaker = CircuitBreakerState(_circuit_breaker_state_path_from_config(cfg))
    poller = ManifestPoller()
    manifest_abs = set()
    for raw in manifests_from_cfg(cfg):
        try:
            manifest_abs.add(str(Path(raw).expanduser().resolve()))
        except OSError:
            manifest_abs.add(str(Path(raw).expanduser()))

    # Batching: the inotify handler thread only records raw paths (no detection).
    # The main loop drains the batch and runs expensive is_watchable() + format
    # detection once per unique path per cycle, avoiding thousands of JSON.parse
    # and sqlite3.connect calls per minute from high-frequency store.db writes.
    from threading import Lock

    _batch_lock = Lock()
    _batch: list[str] = []

    class Handler(FileSystemEventHandler):
        def on_any_event(self, event: FileSystemEvent) -> None:
            if event.is_directory:
                return
            # Fast: just record the path. Main loop does detection.
            with _batch_lock:
                _batch.append(event.src_path)

    def _drain_batch() -> None:
        with _batch_lock:
            if not _batch:
                return
            paths = _batch.copy()
            _batch.clear()
        # Deduplicate: only run detection once per unique path per cycle.
        seen: set[str] = set()
        for raw in paths:
            p = Path(raw)
            path_str = str(p.resolve())
            if path_str in seen:
                continue
            seen.add(path_str)
            if path_str in manifest_abs:
                scheduler.note(reconcile_token(path_str))
                continue
            if is_watchable(p):
                scheduler.note(path_str)

    observer = Observer()
    handler = Handler()
    for root in roots:
        if verbose:
            print(f"[watch] observing {root}", file=sys.stderr)
        observer.schedule(handler, str(root), recursive=True)

    observer.start()
    if verbose:
        print(
            f"[watch] started (debounce={debounce}s, pid={os.getpid()}, "
            f"subprocess_index=on). Ctrl+C to stop.",
            file=sys.stderr,
        )

    try:
        while True:
            _drain_batch()
            if poller.due():
                for manifest_path in manifest_abs:
                    if poller.changed(manifest_path):
                        scheduler.note(reconcile_token(manifest_path))
            for path in scheduler.ready():
                if not is_reconcile_token(path) and breaker.global_breaker_tripped():
                    if verbose:
                        print(
                            "[watch] circuit breaker: too many native faults "
                            "recently — pausing index spawns until the window clears",
                            file=sys.stderr,
                        )
                    break  # leave remaining ready paths pending; retry after the window ages out
                _process_ready_path(path, cfg=cfg, breaker=breaker, verbose=verbose)
                scheduler.forget(path)
            time.sleep(1)
    except KeyboardInterrupt:
        if verbose:
            print("\n[watch] stopping", file=sys.stderr)
    finally:
        observer.stop()
        observer.join(timeout=5)
        if use_lock:
            release_lock(lock_path)
