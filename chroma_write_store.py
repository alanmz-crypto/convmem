"""Authoritative production write-store factory for Phase 0 shadow injection.

ChromaStore does not load config. Only this factory may decide sink injection
after shadow_ledger.decide_sink_injection. T1 exposes the decision gate; T2
attaches the sink object when inject=True.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Mapping

from chroma_store import ChromaStore
from shadow_ledger import SinkInjectionDecision, decide_sink_injection

WritePurpose = Literal["production", "test"]


def open_chroma_for_write(
    cfg: Mapping[str, Any] | None,
    chroma_dir: str | Path,
    *,
    purpose: WritePurpose = "production",
    create_collections: bool = True,
    mutation_sink: Any | None = None,
) -> tuple[ChromaStore, SinkInjectionDecision]:
    """Open a write-capable ChromaStore; sink only when decision.inject and provided.

    Read / verify / evaluation / restore-drill / disposable replay must not call
    this for production injection — they keep mutation_sink=None on their own
    constructors (T2).
    """
    decision = decide_sink_injection(cfg, chroma_dir=chroma_dir)
    if purpose != "production":
        decision = SinkInjectionDecision(
            False, f"purpose={purpose} forces mutation_sink=None"
        )
        sink = None
    elif not decision.inject:
        sink = None
    else:
        # Eligible: attach caller-provided sink (T2 constructs it). T1 tests
        # leave mutation_sink=None so no live shadowing occurs.
        sink = mutation_sink

    try:
        store = ChromaStore(
            str(chroma_dir),
            create_collections=create_collections,
            mutation_sink=sink,
        )
    except TypeError:
        store = ChromaStore(
            str(chroma_dir),
            create_collections=create_collections,
        )
    return store, decision
