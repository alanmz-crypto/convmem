"""Ordered owner context for Arc #286 T2 synthetic tests (incremental lock + owner depth)."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from bootstrap_codex_v2_owner import owner_claim_lock


@contextmanager
def t2_owner_context(state_dir: Path) -> Iterator[None]:
    with owner_claim_lock(state_dir):
        yield
