"""Shared helpers for exclude --purge unit tests."""

from __future__ import annotations

import threading
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


def purge_cfg(td: Path) -> dict:
    return {
        "index": {
            "processed_log": str(td / "processed.json"),
            "units_export": str(td / "knowledge_units.jsonl"),
            "chroma_dir": str(td / "chroma"),
        }
    }


@contextmanager
def patch_source_flock(*, after_acquire=None):
    """Instrument source_flock with wait_/acq_/rel_ events (no timing heuristics)."""
    import purge_locks
    import source_purge

    events = defaultdict(threading.Event)
    real = purge_locks.source_flock
    callbacks = after_acquire or {}

    @contextmanager
    def wrapped(cfg, canonical_path):
        tid = threading.current_thread().name
        events[f"wait_{tid}"].set()
        with real(cfg, canonical_path) as lock:
            events[f"acq_{tid}"].set()
            cb = callbacks.get(tid)
            if cb:
                cb()
            yield lock
        events[f"rel_{tid}"].set()

    with mock.patch.object(purge_locks, "source_flock", wrapped), mock.patch.object(
        source_purge, "source_flock", wrapped
    ):
        yield events


@contextmanager
def patch_export_flock(*, after_acquire=None, extra_modules=None):
    """Instrument export_flock with wait_/acq_/rel_ events (no timing heuristics)."""
    import purge_locks
    import source_purge

    events = defaultdict(threading.Event)
    real_path = purge_locks.export_flock_path
    callbacks = after_acquire or {}

    @contextmanager
    def wrapped_path(export_path):
        tid = threading.current_thread().name
        events[f"wait_{tid}"].set()
        cm = real_path(export_path)
        lock = cm.__enter__()
        try:
            events[f"acq_{tid}"].set()
            cb = callbacks.get(tid)
            if cb:
                cb()
            yield lock
        finally:
            cm.__exit__(None, None, None)
            events[f"rel_{tid}"].set()

    @contextmanager
    def wrapped_cfg(cfg):
        cm = wrapped_path(cfg["index"]["units_export"])
        lock = cm.__enter__()
        try:
            yield lock
        finally:
            cm.__exit__(None, None, None)

    stack_patches = [
        mock.patch.object(purge_locks, "export_flock_path", wrapped_path),
        mock.patch.object(purge_locks, "export_flock", wrapped_cfg),
        mock.patch.object(source_purge, "export_flock", wrapped_cfg),
    ]
    for mod in extra_modules or ():
        stack_patches.append(mock.patch.object(mod, "export_flock", wrapped_cfg))

    # Enter all patches
    for p in stack_patches:
        p.start()
    try:
        yield events
    finally:
        for p in reversed(stack_patches):
            p.stop()


_live_config_lock = threading.RLock()
_live_config_depth = 0
_live_config_active: dict | None = None
_live_config_patcher = None


@contextmanager
def patch_live_config(cfg: dict):
    """Thread/nest-safe stand-in for live config after the writer lease.

    Concurrent ``mock.patch`` on ``config.load_config`` is unsafe: one thread
    stopping its patch can restore the real loader while another still needs
    the hermetic cfg. Use a process-wide refcount instead.
    """
    global _live_config_depth, _live_config_active, _live_config_patcher
    with _live_config_lock:
        _live_config_active = cfg
        _live_config_depth += 1
        if _live_config_depth == 1:
            _live_config_patcher = mock.patch(
                "config.load_config",
                side_effect=lambda *_a, **_k: _live_config_active,
            )
            _live_config_patcher.start()
    try:
        yield
    finally:
        with _live_config_lock:
            _live_config_depth -= 1
            if _live_config_depth == 0:
                assert _live_config_patcher is not None
                _live_config_patcher.stop()
                _live_config_patcher = None
                _live_config_active = None
