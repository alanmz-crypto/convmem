"""Filesystem watch — incremental index on transcript changes (Milestone F0).

Uses watchdog (inotify on Linux) with debounce, then calls ingest.index(force_file=…).
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


def is_excluded_from_index(path: Path | str) -> bool:
    """True when processed.json marks this path excluded."""
    from config import load_config
    from ingest import load_processed, sha256_file

    p = Path(path).expanduser().resolve()
    try:
        file_hash = sha256_file(str(p))
    except OSError:
        return False
    cfg = load_config()
    processed = load_processed(cfg["index"]["processed_log"])
    entry = processed.get(file_hash)
    if isinstance(entry, dict) and entry.get("excluded"):
        return True
    path_key = str(p)
    for entry in processed.values():
        if not isinstance(entry, dict) or not entry.get("excluded"):
            continue
        ep = entry.get("path")
        if ep and str(Path(ep).expanduser().resolve()) == path_key:
            return True
    return False


def is_watchable(path: Path | str) -> bool:
    """True if watch should index this path (parser exists, not live DB, not excluded)."""
    p = Path(path)
    if not is_indexable(p):
        return False
    if is_live_watch_db(p):
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


def flush_path(
    path: str,
    *,
    index_fn: Callable[..., dict],
    verbose: bool = True,
) -> dict | None:
    """Run incremental index for one file. Returns stats or None if skipped."""
    p = Path(path)
    if not p.is_file():
        if verbose:
            print(f"[watch] skip (not a file): {path}", file=sys.stderr)
        return None
    if not is_watchable(p):
        if verbose and is_indexable(p):
            if is_live_watch_db(p):
                print(f"[watch] skip (live DB): {path}", file=sys.stderr)
            elif is_excluded_from_index(p):
                print(f"[watch] skip (excluded): {path}", file=sys.stderr)
        elif verbose:
            print(f"[watch] skip (no parser): {path}", file=sys.stderr)
        return None
    from ingest import watch_skip_reason

    skip = watch_skip_reason(p)
    if skip:
        if verbose:
            print(f"[watch] skip ({skip}): {p.name}", file=sys.stderr)
        return None
    if verbose:
        print(f"[watch] indexing {p.name}", file=sys.stderr)
    return index_fn(force_file=str(p.resolve()), verbose=verbose)


def _lock_path_from_config(cfg: dict) -> Path:
    watch_cfg = cfg.get("watch") or {}
    if watch_cfg.get("lock_file"):
        return Path(watch_cfg["lock_file"]).expanduser()
    chroma = Path(cfg["index"]["chroma_dir"]).expanduser()
    return chroma.parent / "watch.lock"


def acquire_lock(lock_path: Path) -> None:
    """Create a PID lock; exit if another live watch holds it."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        try:
            other_pid = int(lock_path.read_text().strip())
        except ValueError:
            other_pid = 0
        if other_pid > 0:
            try:
                os.kill(other_pid, 0)
            except OSError:
                pass
            else:
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
    from ingest import index as run_index

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

    class Handler(FileSystemEventHandler):
        def on_any_event(self, event: FileSystemEvent) -> None:
            if event.is_directory:
                return
            path = Path(event.src_path)
            if not is_watchable(path):
                return
            scheduler.note(str(path.resolve()))

    observer = Observer()
    handler = Handler()
    for root in roots:
        if verbose:
            print(f"[watch] observing {root}", file=sys.stderr)
        observer.schedule(handler, str(root), recursive=True)

    observer.start()
    if verbose:
        print(
            f"[watch] started (debounce={debounce}s, pid={os.getpid()}). Ctrl+C to stop.",
            file=sys.stderr,
        )

    try:
        while True:
            for path in scheduler.ready():
                flush_path(path, index_fn=run_index, verbose=verbose)
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
