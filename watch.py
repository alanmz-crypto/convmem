"""Filesystem watch — incremental index on transcript changes (Milestone F0).

Uses watchdog (inotify on Linux) with debounce, then spawns `convmem index --file`
in a subprocess so Chroma/ML memory is not retained in the watch parent.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Callable

from adapters.detect import get_parser

# Live databases that change constantly — watch re-index causes OOM + duplication.
_LIVE_WATCH_SKIP_SUFFIXES = (
    "kiro-cli/data.sqlite3",
    "convmem/imports/webui.db",
)
_CURSOR_CHAT_STORE_ROOT = Path("~/.config/cursor/chats").expanduser()


def is_live_watch_db(path: Path | str) -> bool:
    """True for append-heavy DBs that must not be watch re-indexed."""
    p = Path(path).expanduser().resolve()
    s = str(p)
    if any(s.endswith(suffix) for suffix in _LIVE_WATCH_SKIP_SUFFIXES):
        return True
    try:
        p.relative_to(_CURSOR_CHAT_STORE_ROOT)
    except ValueError:
        return False
    return p.name == "store.db"


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


def _flush_path_subprocess(path: str, *, verbose: bool) -> dict:
    """Run index in a child process so ML/Chroma memory is released after each file."""
    import subprocess

    cmd = _convmem_cli_argv() + ["index", "--file", path]
    if verbose:
        print(f"[watch] spawn: {' '.join(cmd[-3:])}", file=sys.stderr)
    proc = subprocess.run(
        cmd,
        text=True,
        capture_output=not verbose,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(err or f"index subprocess exit {proc.returncode}")
    if verbose and proc.stdout:
        for line in proc.stdout.splitlines():
            print(line, file=sys.stderr)
    return {"subprocess": True, "path": path}


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
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        try:
            other_pid = int(lock_path.read_text().strip())
        except ValueError:
            other_pid = 0
        if _is_live_watch_pid(other_pid):
            print(
                f"[watch] another instance is running (pid {other_pid}). "
                f"Lock: {lock_path}",
                file=sys.stderr,
            )
            sys.exit(1)
        lock_path.unlink(missing_ok=True)
    lock_path.write_text(str(os.getpid()), encoding="utf-8")


def release_lock(lock_path: Path) -> None:
    if not lock_path.exists():
        return
    try:
        if int(lock_path.read_text().strip()) == os.getpid():
            lock_path.unlink(missing_ok=True)
    except (ValueError, OSError):
        lock_path.unlink(missing_ok=True)


def load_watch_settings(cfg: dict) -> tuple[float, list[str], Path]:
    watch_cfg = cfg.get("watch") or {}
    debounce = float(watch_cfg.get("debounce_seconds", 30))
    paths = watch_cfg.get("paths") or cfg.get("sources", {}).get("paths") or []
    if not paths:
        raise ValueError("No watch paths — set [sources].paths or [watch].paths in config.toml")
    lock_path = _lock_path_from_config(cfg)
    return debounce, list(paths), lock_path


def run_watch(
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

    roots = watch_roots(watch_paths)
    if not roots:
        print("[watch] no existing watch roots — check [sources].paths", file=sys.stderr)
        raise SystemExit(1)

    if use_lock:
        acquire_lock(lock_path)

    scheduler = DebounceScheduler(debounce_seconds=debounce)

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
            for path in scheduler.ready():
                try:
                    flush_path(path, verbose=verbose, use_subprocess=True)
                except Exception as e:
                    print(f"[watch] error processing {path}: {e}", file=sys.stderr)
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
