"""Loopback-allowing, fail-closed network policy for live P2 workers.

This module imports only the standard library plus the isolation violation
type so the live worker can install denial before provider-capable imports.
"""

from __future__ import annotations

import socket
from typing import Any

from incremental_jsonl_isolation import IsolationViolation


def install_p2_network_policy(loopback_host: str, *, dry_run: bool = False) -> None:
    """Allow the grant loopback endpoint; deny any other connect before a socket."""
    addr, _, _port = loopback_host.partition(":")
    allowed = {addr.strip("[]").lower(), "127.0.0.1", "::1", "localhost"}
    real_create = socket.create_connection
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _host_of(address: Any) -> str:
        if isinstance(address, tuple) and address:
            return str(address[0]).split("%", 1)[0].strip("[]").lower()
        return str(address).split("%", 1)[0].strip("[]").lower()

    def _guarded_create(address, *args, **kwargs):  # noqa: ANN001
        host = _host_of(address)
        if host in allowed:
            if dry_run:
                return ("loopback-allowed", host)
            return real_create(address, *args, **kwargs)
        raise IsolationViolation(f"non-loopback denied before socket: {host}")

    def _guarded_connect(self, address):  # noqa: ANN001
        host = _host_of(address)
        if host in allowed:
            if dry_run:
                return None
            return real_connect(self, address)
        raise IsolationViolation(f"non-loopback denied before socket: {host}")

    def _guarded_connect_ex(self, address):  # noqa: ANN001
        host = _host_of(address)
        if host in allowed:
            if dry_run:
                return 0
            return real_connect_ex(self, address)
        raise IsolationViolation(f"non-loopback denied before socket: {host}")

    socket.create_connection = _guarded_create  # type: ignore[assignment]
    socket.socket.connect = _guarded_connect  # type: ignore[assignment]
    socket.socket.connect_ex = _guarded_connect_ex  # type: ignore[assignment]
