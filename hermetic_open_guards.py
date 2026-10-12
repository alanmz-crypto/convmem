"""Install production-path open guards shared by D1 and watch-OOM hermetic workers."""

from __future__ import annotations

import builtins
import io
import os
import sqlite3
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

from hermetic_path_guard import production_path_denied

PathDeniedHandler = Callable[[object], None]
NetworkDeniedHandler = Callable[[], None]


def install_path_open_guards(*, on_path_denied: PathDeniedHandler) -> dict[str, Any]:
    """Patch open/connect hooks; return originals for teardown."""
    real_open = builtins.open
    real_os_open = os.open
    real_connect = sqlite3.connect
    real_io_open = io.open
    real_path_open = Path.open

    def guarded_open(file, *args, **kwargs):
        if production_path_denied(file):
            on_path_denied(file)
        return real_open(file, *args, **kwargs)

    def guarded_os_open(path, *args, **kwargs):
        if production_path_denied(path):
            on_path_denied(path)
        return real_os_open(path, *args, **kwargs)

    def guarded_io_open(file, *args, **kwargs):
        if production_path_denied(file):
            on_path_denied(file)
        return real_io_open(file, *args, **kwargs)

    def guarded_path_open(self, *args, **kwargs):
        if production_path_denied(self):
            on_path_denied(self)
        return real_path_open(self, *args, **kwargs)

    def guarded_connect(database, *args, **kwargs):
        target = database
        if isinstance(database, str) and database.startswith("file:"):
            target = database[5:].split("?", 1)[0]
        if production_path_denied(target):
            on_path_denied(database)
        return real_connect(database, *args, **kwargs)

    restore_hooks = {
        "builtins.open": real_open,
        "os.open": real_os_open,
        "io.open": real_io_open,
        "Path.open": real_path_open,
        "sqlite3.connect": real_connect,
    }
    builtins.open = guarded_open  # type: ignore[assignment]
    os.open = guarded_os_open  # type: ignore[assignment]
    io.open = guarded_io_open  # type: ignore[assignment]
    Path.open = guarded_path_open  # type: ignore[assignment]
    sqlite3.connect = guarded_connect  # type: ignore[assignment]
    return restore_hooks


def install_network_guards(*, on_network_denied: NetworkDeniedHandler) -> dict[str, Any]:
    def denied(*_args, **_kwargs):
        on_network_denied()

    restore_hooks = {
        "socket.create_connection": socket.create_connection,
        "socket.getaddrinfo": socket.getaddrinfo,
        "socket.socket.connect": socket.socket.connect,
        "socket.socket.connect_ex": socket.socket.connect_ex,
    }
    socket.create_connection = denied  # type: ignore[assignment]
    socket.getaddrinfo = denied  # type: ignore[assignment]
    socket.socket.connect = denied  # type: ignore[assignment]
    socket.socket.connect_ex = denied  # type: ignore[assignment]
    return restore_hooks


def install_open_guards(
    *,
    on_path_denied: PathDeniedHandler,
    on_network_denied: NetworkDeniedHandler,
) -> dict[str, Any]:
    """Patch path and network hooks; return combined originals for teardown."""
    path_hooks = install_path_open_guards(on_path_denied=on_path_denied)
    network_hooks = install_network_guards(on_network_denied=on_network_denied)
    return {**path_hooks, **network_hooks}


def restore_open_guards(restore_hooks: dict[str, Any]) -> None:
    if "builtins.open" in restore_hooks:
        builtins.open = restore_hooks["builtins.open"]  # type: ignore[assignment]
        os.open = restore_hooks["os.open"]  # type: ignore[assignment]
        io.open = restore_hooks["io.open"]  # type: ignore[assignment]
        Path.open = restore_hooks["Path.open"]  # type: ignore[assignment]
        sqlite3.connect = restore_hooks["sqlite3.connect"]  # type: ignore[assignment]
    if "socket.create_connection" in restore_hooks:
        socket.create_connection = restore_hooks["socket.create_connection"]  # type: ignore[assignment]
        socket.getaddrinfo = restore_hooks["socket.getaddrinfo"]  # type: ignore[assignment]
        socket.socket.connect = restore_hooks["socket.socket.connect"]  # type: ignore[assignment]
        socket.socket.connect_ex = restore_hooks["socket.socket.connect_ex"]  # type: ignore[assignment]
