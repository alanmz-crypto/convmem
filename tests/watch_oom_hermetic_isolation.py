"""Shared hermetic isolation guards for watch-OOM measurement workers."""

from __future__ import annotations

import builtins
import os
import socket
import sqlite3
from pathlib import Path

PRODUCTION_PREFIXES = (
    str((Path.home() / ".local/share/convmem").resolve()),
    str((Path.home() / ".config/convmem").resolve()),
)
DEFAULT_BRIEF = str((Path.home() / ".local/share/convmem/brief.md").expanduser())
DENIED: list[str] = []
NETWORK_DENIED: list[str] = []


class ProductionPathDenied(RuntimeError):
    """Attempted to open a production ConvMem path from a hermetic worker."""


class NetworkDenied(RuntimeError):
    """Attempted outbound network access from a hermetic worker."""


def _denied(path: object) -> bool:
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


def install_path_denial() -> None:
    import io

    real_open = builtins.open
    real_os_open = os.open
    real_connect = sqlite3.connect
    real_io_open = io.open
    real_path_open = Path.open

    def guarded_open(file, *args, **kwargs):
        if _denied(file):
            DENIED.append(str(file))
            raise ProductionPathDenied(str(file))
        return real_open(file, *args, **kwargs)

    def guarded_os_open(path, *args, **kwargs):
        if _denied(path):
            DENIED.append(str(path))
            raise ProductionPathDenied(str(path))
        return real_os_open(path, *args, **kwargs)

    def guarded_io_open(file, *args, **kwargs):
        if _denied(file):
            DENIED.append(str(file))
            raise ProductionPathDenied(str(file))
        return real_io_open(file, *args, **kwargs)

    def guarded_path_open(self, *args, **kwargs):
        if _denied(self):
            DENIED.append(str(self))
            raise ProductionPathDenied(str(self))
        return real_path_open(self, *args, **kwargs)

    def guarded_connect(database, *args, **kwargs):
        target = database
        if isinstance(database, str) and database.startswith("file:"):
            target = database[5:].split("?", 1)[0]
        if _denied(target):
            DENIED.append(str(database))
            raise ProductionPathDenied(str(database))
        return real_connect(database, *args, **kwargs)

    builtins.open = guarded_open  # type: ignore[assignment]
    os.open = guarded_os_open  # type: ignore[assignment]
    io.open = guarded_io_open  # type: ignore[assignment]
    Path.open = guarded_path_open  # type: ignore[assignment]
    sqlite3.connect = guarded_connect  # type: ignore[assignment]


def install_network_denial() -> None:
    """Deny ordinary Python outbound networking for this worker process."""

    def denied(*_args, **_kwargs):
        NETWORK_DENIED.append("outbound")
        raise NetworkDenied("outbound network denied in hermetic worker")

    socket.create_connection = denied  # type: ignore[assignment]
    socket.getaddrinfo = denied  # type: ignore[assignment]
    socket.socket.connect = denied  # type: ignore[assignment]
    socket.socket.connect_ex = denied  # type: ignore[assignment]


def install_hermetic_guards() -> None:
    install_path_denial()
    install_network_denial()


def hermetic_brief_cfg(chroma_dir: str, processed: str, inventory: str) -> dict:
    return {
        "index": {
            "chroma_dir": chroma_dir,
            "processed_log": processed,
        },
        "sources": {"inventory": inventory},
        "query": {"rerank": False},
    }


def forbidden_provenance_keys(rows: list[dict]) -> list[str]:
    return sorted(
        {
            key
            for row in rows
            for key in (
                "provenance_envelope",
                "provenance_commitment",
                "provenance_assertion_id",
            )
            if key in row
        }
    )
