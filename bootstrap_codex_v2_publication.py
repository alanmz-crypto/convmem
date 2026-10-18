"""Barrier-instrumented atomic publication for Codex bootstrap v2 (T2 crash matrix)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from bootstrap_safety import BootstrapGrantError, canonical_json

BARRIER_PREFIX_ENV = "CONVMEM_BOOTSTRAP_V2_BARRIER_PREFIX"
INJECT_FSYNC_FAIL_ENV = "CONVMEM_BOOTSTRAP_V2_INJECT_FSYNC_FAIL"
INJECT_REPLACE_FAIL_ENV = "CONVMEM_BOOTSTRAP_V2_INJECT_REPLACE_FAIL"
PARENT_KILL_STAGE_ENV = "CONVMEM_BOOTSTRAP_V2_PARENT_KILL_STAGE"


class PublicationFailure(BootstrapGrantError):
    """Injected or barrier publication failure."""


def _barrier_prefix() -> Path | None:
    raw = os.environ.get(BARRIER_PREFIX_ENV, "").strip()
    if not raw:
        return None
    return Path(raw)


def publication_barrier(stage: str) -> None:
    prefix = _barrier_prefix()
    if prefix is None:
        return
    prefix.mkdir(parents=True, exist_ok=True)
    (prefix / f"stage.{stage}").write_text("1", encoding="ascii")
    if os.environ.get("CONVMEM_BOOTSTRAP_V2_BARRIER_WAIT", "").strip() == "1":
        time.sleep(1.5)
    if os.environ.get(PARENT_KILL_STAGE_ENV, "").strip() == stage:
        os._exit(92)


def _should_fail_fsync(stage: str) -> bool:
    return os.environ.get(INJECT_FSYNC_FAIL_ENV, "").strip() == stage


def _should_fail_replace(stage: str) -> bool:
    return os.environ.get(INJECT_REPLACE_FAIL_ENV, "").strip() == stage


def atomic_publish_json(path: Path, payload: dict[str, Any], *, stage: str) -> None:
    publication_barrier(f"{stage}.before_tmp_write")
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
        handle.flush()
        publication_barrier(f"{stage}.before_tmp_fsync")
        if _should_fail_fsync(f"{stage}.tmp_fsync"):
            raise PublicationFailure(f"injected_fsync_fail:{stage}.tmp_fsync")
        os.fsync(handle.fileno())
    os.chmod(tmp, 0o600)
    publication_barrier(f"{stage}.before_replace")
    if _should_fail_replace(f"{stage}.replace"):
        raise PublicationFailure(f"injected_replace_fail:{stage}.replace")
    os.replace(tmp, path)
    publication_barrier(f"{stage}.after_replace")
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        publication_barrier(f"{stage}.before_dir_fsync")
        if _should_fail_fsync(f"{stage}.dir_fsync"):
            raise PublicationFailure(f"injected_fsync_fail:{stage}.dir_fsync")
        os.fsync(directory)
    finally:
        os.close(directory)
    publication_barrier(f"{stage}.after_dir_fsync")


def append_jsonl_line(path: Path, payload: dict[str, Any], *, stage: str) -> None:
    publication_barrier(f"{stage}.before_append")
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    existed = path.exists()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(payload) + "\n")
        handle.flush()
        publication_barrier(f"{stage}.before_file_fsync")
        if _should_fail_fsync(f"{stage}.file_fsync"):
            raise PublicationFailure(f"injected_fsync_fail:{stage}.file_fsync")
        os.fsync(handle.fileno())
    os.chmod(path, 0o600)
    if not existed:
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            publication_barrier(f"{stage}.before_dir_fsync")
            if _should_fail_fsync(f"{stage}.dir_fsync"):
                raise PublicationFailure(f"injected_fsync_fail:{stage}.dir_fsync")
            os.fsync(directory)
        finally:
            os.close(directory)
    publication_barrier(f"{stage}.after_dir_fsync")
