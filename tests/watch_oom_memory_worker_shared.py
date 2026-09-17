"""Shared subprocess worker helpers for watch-OOM hermetic measurement."""

from __future__ import annotations

import argparse
import json
import resource
import sys
from typing import Callable

from tests.linux_proc import peak_rss_bytes as _peak_rss_bytes
from tests.linux_proc import rss_bytes as _rss_bytes
from tests.watch_oom_hermetic_isolation import (
    DENIED,
    NETWORK_DENIED,
    NetworkDenied,
    ProductionPathDenied,
    hermetic_brief_cfg,
    install_hermetic_guards,
)

C5_MODES = ("c5-negative", "c5-negative-network")


def add_common_worker_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--chroma-dir", default="")
    parser.add_argument("--inventory", default="")
    parser.add_argument("--processed", default="")


def prepare_worker() -> None:
    install_hermetic_guards()
    limit = 2 * 1024 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def handle_c5_negative_network() -> int:
    import socket

    try:
        socket.create_connection(("1.1.1.1", 80), timeout=0.1)
    except NetworkDenied:
        pass
    emit_worker_json(
        {
            "network_denied": bool(NETWORK_DENIED),
            "network_events": NETWORK_DENIED,
        }
    )
    return 0 if NETWORK_DENIED else 2


def handle_c5_negative_path(chroma_dir: str, processed: str, inventory: str) -> int:
    from brief import refresh_brief_after_change

    cfg = hermetic_brief_cfg(chroma_dir, processed, inventory)
    try:
        refresh_brief_after_change(cfg)
    except ProductionPathDenied as exc:
        DENIED.append(str(exc))
    emit_worker_json({"denied": bool(DENIED), "denied_paths": DENIED})
    return 0 if DENIED else 2


def emit_worker_json(payload: dict) -> None:
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")


def denied_exit_code() -> int:
    return 0 if not DENIED else 3


def handle_baseline() -> int:
    emit_worker_json(
        {
            "baseline_rss_bytes": _rss_bytes(),
            "peak_rss_bytes": _peak_rss_bytes(),
        }
    )
    return 0


def maybe_handle_c5(mode: str, chroma_dir: str, processed: str, inventory: str) -> int | None:
    if mode == "c5-negative-network":
        return handle_c5_negative_network()
    if mode == "c5-negative":
        return handle_c5_negative_path(chroma_dir, processed, inventory)
    return None


def run_worker_main(
    *,
    mode_choices: tuple[str, ...],
    extra_args: Callable[[argparse.ArgumentParser], None] | None,
    dispatch: Callable[[argparse.Namespace], int],
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=mode_choices, required=True)
    add_common_worker_args(parser)
    if extra_args is not None:
        extra_args(parser)
    args = parser.parse_args()
    prepare_worker()
    c5_rc = maybe_handle_c5(args.mode, args.chroma_dir, args.processed, args.inventory)
    if c5_rc is not None:
        return c5_rc
    if args.mode == "baseline":
        return handle_baseline()
    return dispatch(args)
