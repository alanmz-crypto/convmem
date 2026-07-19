"""Atomic write helpers for eval artifacts (write-temp + fsync + rename)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


def sha256_file(path: Path | str) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write_bytes(path: Path | str, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def atomic_write_text(path: Path | str, text: str, *, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


def atomic_write_json(
    path: Path | str,
    obj: Any,
    *,
    indent: int | None = 2,
    sort_keys: bool = True,
) -> None:
    payload = json.dumps(obj, ensure_ascii=False, indent=indent, sort_keys=sort_keys)
    if not payload.endswith("\n"):
        payload += "\n"
    atomic_write_text(path, payload)


def atomic_copy_file(src: Path | str, dest: Path | str) -> str:
    """Copy src→dest via temp+fsync+replace. Returns sha256 of dest bytes."""
    src_p = Path(src)
    dest_p = Path(dest)
    dest_p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{dest_p.name}.",
        suffix=".tmp",
        dir=str(dest_p.parent),
    )
    try:
        with os.fdopen(fd, "wb") as out, open(src_p, "rb") as inp:
            shutil.copyfileobj(inp, out, length=1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp_name, dest_p)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return sha256_file(dest_p)
