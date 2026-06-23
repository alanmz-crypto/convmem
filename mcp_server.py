"""convmem MCP server — exposes search, ask, related, and stats to AI agents.

Run via stdio (for Cursor, Kiro, Crush, Continue):
  python mcp_server.py

Register in your MCP client config pointing at this script.
Read-only by default. Write tools (propose_decision) require human confirmation.
"""

import json
import sys
from pathlib import Path

# Ensure convmem modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("convmem", instructions="Local knowledge corpus. Search past AI sessions, ask questions with citations, traverse evidence chains.")


def _search_payload(results: list[dict]) -> str:
    out = []
    for r in results:
        meta = r.get("metadata", {})
        out.append({
            "score": r.get("score"),
            "title": meta.get("title", ""),
            "type": meta.get("type", ""),
            "domain": meta.get("domain", ""),
            "site": meta.get("site", ""),
            "tool": meta.get("tool", ""),
            "source_path": meta.get("source_path", ""),
            "ledger_id": meta.get("ledger_id", ""),
            "document": (r.get("document") or "")[:500],
        })
    return json.dumps(out, indent=2)


@mcp.tool()
def search_fast(query: str, top_k: int = 5, domain: str = "", site: str = "") -> str:
    """Fast retrieval-only search (no LLM synthesis). Use for low-latency lookups."""
    from query import query_units

    results = query_units(
        query, top_k=top_k, domain=domain or None, site=site or None
    )
    if not results:
        return json.dumps({"results": [], "message": "No relevant knowledge units found."})
    return _search_payload(results)


@mcp.tool()
def search(query: str, top_k: int = 5, domain: str = "", site: str = "") -> str:
    """Search the knowledge corpus for relevant units. Returns scored results."""
    from query import query_units

    results = query_units(
        query, top_k=top_k, domain=domain or None, site=site or None
    )
    return _search_payload(results)


@mcp.tool()
def ask(
    question: str,
    top_k: int = 5,
    domain: str = "",
    site: str = "",
    evidence: bool = False,
) -> str:
    """Answer a question using retrieved memories. Returns answer + citations."""
    from ask import ask as run_ask

    result = run_ask(
        question,
        top_k=top_k,
        domain=domain or None,
        site=site or None,
        raw=False,
        evidence=evidence,
    )
    return json.dumps({
        "answer": result.get("answer", ""),
        "confidence": result.get("confidence"),
        "warning": result.get("warning"),
        "synthesis_failed": result.get("synthesis_failed", False),
        "citations": [
            {
                "n": c.get("n"),
                "title": c.get("title", ""),
                "type": c.get("type", ""),
                "tool": c.get("tool", ""),
                "source_path": c.get("source_path", ""),
                "domain": c.get("domain", ""),
                "when": c.get("when", ""),
                "score": c.get("score"),
            }
            for c in (result.get("citations") or [])
        ],
    }, indent=2)


@mcp.tool()
def related(ledger_id: str) -> str:
    """Traverse the evidence chain for an observation, decision, or verification."""
    from chroma_store import ChromaStore
    from config import load_config
    from ledger import related_chain

    cfg = load_config()
    store = ChromaStore(cfg["index"]["chroma_dir"])
    chain = related_chain(store, ledger_id)
    if chain is None:
        return json.dumps({"error": f"Ledger id not found: {ledger_id}"})

    target = chain["target"]["metadata"]
    result = {
        "target": {
            "ledger_id": target.get("ledger_id", ""),
            "kind": chain["target_kind"],
            "title": target.get("title", ""),
            "domain": target.get("domain", ""),
        },
        "anchor_id": chain["anchor_id"],
        "decisions": [
            {"ledger_id": m.get("ledger_id", ""), "title": m.get("title", "")}
            for m in chain["decisions"]
        ],
        "verifications": [
            {
                "ledger_id": m.get("ledger_id", ""),
                "result": m.get("result", ""),
                "author_model": m.get("author_model", ""),
            }
            for m in chain["verifications"]
        ],
    }
    if chain.get("observation"):
        result["observation"] = {
            "ledger_id": chain["observation"].get("ledger_id", ""),
            "title": chain["observation"].get("title", ""),
        }
    return json.dumps(result, indent=2)


@mcp.tool()
def stats() -> str:
    """Show corpus statistics: unit counts by source and domain."""
    from collections import Counter
    from chroma_store import ChromaStore
    from config import load_config

    cfg = load_config()
    store = ChromaStore(cfg["index"]["chroma_dir"])
    metas = store.units_metadata()
    by_tool = Counter(m.get("tool", "?") for m in metas)
    by_domain = Counter(m.get("domain") or "untagged" for m in metas)
    return json.dumps({
        "total_units": len(metas),
        "by_tool": dict(by_tool.most_common(10)),
        "by_domain": dict(by_domain.most_common(15)),
    }, indent=2)


if __name__ == "__main__":
    import asyncio

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(mcp.run_stdio_async())
