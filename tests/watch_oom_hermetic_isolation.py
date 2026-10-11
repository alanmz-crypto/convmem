"""Shared hermetic isolation guards for watch-OOM measurement workers."""

from __future__ import annotations

import socket

from hermetic_open_guards import install_path_open_guards
DENIED: list[str] = []
NETWORK_DENIED: list[str] = []


class ProductionPathDenied(RuntimeError):
    """Attempted to open a production ConvMem path from a hermetic worker."""


class NetworkDenied(RuntimeError):
    """Attempted outbound network access from a hermetic worker."""


def _on_production_path_denied(target: object) -> None:
    DENIED.append(str(target))
    raise ProductionPathDenied(str(target))


def install_path_denial() -> None:
    install_path_open_guards(on_path_denied=_on_production_path_denied)


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
