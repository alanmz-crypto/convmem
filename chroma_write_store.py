"""Authoritative production write-store factory for Phase 0 shadow injection.

ChromaStore does not load config. Only this factory may decide sink injection
after shadow_ledger.decide_sink_injection and construct JsonlUnitMutationSink.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Mapping

from chroma_store import ChromaStore
from shadow_ledger import SinkInjectionDecision, decide_sink_injection, resolve_shadow_settings
from shadow_sink import JsonlUnitMutationSink

WritePurpose = Literal["production", "test"]


def open_chroma_for_write(
    cfg: Mapping[str, Any] | None,
    chroma_dir: str | Path,
    *,
    purpose: WritePurpose = "production",
    create_collections: bool = True,
    mutation_sink: Any | None = None,
) -> tuple[ChromaStore, SinkInjectionDecision]:
    """Open a write-capable ChromaStore; attach sink only when contract allows.

    Read / verify / evaluation / restore-drill / disposable replay must not call
    this for production injection — they keep mutation_sink=None.
    """
    decision = decide_sink_injection(cfg, chroma_dir=chroma_dir)
    sink: Any | None = None
    if purpose != "production":
        decision = SinkInjectionDecision(
            False, f"purpose={purpose} forces mutation_sink=None"
        )
    elif mutation_sink is not None:
        sink = mutation_sink if decision.inject else None
    elif decision.inject:
        settings = resolve_shadow_settings(cfg)
        sink = JsonlUnitMutationSink(
            ledger_path=settings.ledger_path,
            health_path=settings.health_path,
        )

    store = ChromaStore(
        str(chroma_dir),
        create_collections=create_collections,
        mutation_sink=sink,
    )
    return store, decision
