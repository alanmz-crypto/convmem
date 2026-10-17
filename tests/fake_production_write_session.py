"""Shared fake production write session that participates in lock-order counting."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from chroma_write_store import (
    ProductionWriteSession,
    SinkInjectionDecision,
    _enter_chroma_store_session,
    _exit_chroma_store_session,
)


@contextmanager
def counting_fake_production_write_session(
    store: Any,
    live_cfg: dict,
    **_: Any,
) -> Iterator[ProductionWriteSession]:
    """Mirror production session depth tracking for lock-order tests."""
    _enter_chroma_store_session()
    try:
        yield ProductionWriteSession(
            store=store,
            live_cfg=live_cfg,
            decision=SinkInjectionDecision(False, "test fake session"),
        )
    finally:
        _exit_chroma_store_session()
