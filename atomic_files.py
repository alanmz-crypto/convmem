"""Durable atomic file publication for JSONL exports and authoritative JSON reports.

Architecture: docs/plans/ARCHITECTURE-complete-data-backup-correction-v2.md
(atomic_files section). Distinct from eval_corpus/io_atomic.py — this module
implements the full v2 contract (mode preservation, parent-directory fsync with
guaranteed descriptor close, and pre- vs post-publication failure classes).
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any


class AtomicWriteError(OSError):
    """Base class for atomic publication failures."""


class PrePublicationError(AtomicWriteError):
    """Failure before the destination was published.

    The previous destination bytes (if any) remain intact. The invocation-owned
    temporary file is removed when possible.
    """


class PostPublicationDurabilityError(AtomicWriteError):
    """Destination was published via os.replace, but durability is uncertain.

    Typically raised when parent-directory fsync fails after a successful
    replace. The visible destination contains the complete new contents; callers
    must treat durability (crash safety of the directory entry) as uncertain.
    """


def atomic_write_bytes(path: Path | str, data: bytes, *, preserve_mode: bool = True) -> None:
    """Publish *data* to *path* via temp → fsync → replace → parent-dir fsync."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    prior_mode: int | None = None
    if preserve_mode and dest.exists():
        prior_mode = stat.S_IMODE(dest.stat().st_mode)

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{dest.name}.",
        suffix=".tmp",
        dir=str(dest.parent),
    )
    published = False
    try:
        try:
            with os.fdopen(fd, "wb") as handle:
                fd = -1  # ownership transferred to handle
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException as exc:
            raise PrePublicationError(
                f"pre-publication write failed for {dest}: {exc}"
            ) from exc

        if prior_mode is not None:
            try:
                os.chmod(tmp_name, prior_mode)
            except OSError as exc:
                raise PrePublicationError(
                    f"pre-publication mode preserve failed for {dest}: {exc}"
                ) from exc

        try:
            os.replace(tmp_name, dest)
        except BaseException as exc:
            raise PrePublicationError(
                f"pre-publication replace failed for {dest}: {exc}"
            ) from exc
        published = True

        try:
            dir_fd = os.open(str(dest.parent), os.O_RDONLY)
        except OSError as exc:
            raise PostPublicationDurabilityError(
                f"post-publication directory open failed for {dest}: {exc}"
            ) from exc
        try:
            try:
                os.fsync(dir_fd)
            except OSError as exc:
                raise PostPublicationDurabilityError(
                    f"post-publication directory fsync failed for {dest}: {exc}"
                ) from exc
        finally:
            os.close(dir_fd)
    except BaseException:
        if not published:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
        raise


def atomic_write_text(
    path: Path | str,
    text: str,
    *,
    preserve_mode: bool = True,
    encoding: str = "utf-8",
) -> None:
    """Publish *text* to *path* with durable atomic semantics."""
    atomic_write_bytes(path, text.encode(encoding), preserve_mode=preserve_mode)


def atomic_write_json(
    path: Path | str,
    obj: Any,
    *,
    preserve_mode: bool = True,
    indent: int | None = 2,
    sort_keys: bool = True,
) -> None:
    """Serialize *obj* as JSON and publish via atomic_write_text."""
    payload = json.dumps(obj, ensure_ascii=False, indent=indent, sort_keys=sort_keys)
    if not payload.endswith("\n"):
        payload += "\n"
    atomic_write_text(path, payload, preserve_mode=preserve_mode)
