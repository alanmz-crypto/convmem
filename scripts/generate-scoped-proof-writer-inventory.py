#!/usr/bin/env python3
"""Regenerate docs/plans/SCOPED-PROOF-WRITER-INVENTORY.json from shadow inventory."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHADOW = ROOT / "docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json"
OUT = ROOT / "docs/plans/SCOPED-PROOF-WRITER-INVENTORY.json"


def build() -> dict:
    shadow = json.loads(SHADOW.read_text(encoding="utf-8"))
    routes = []
    for site in shadow.get("sites", []):
        routes.append(
            {
                "route_id": f"{site['file']}:{site['line']}",
                "entrypoint": f"{site['file']}:{site['line']}",
                "owner": site.get("required_routing", "production_chroma_write_session"),
                "disposition": "mediated_native",
                "shadow_inventory_ref": f"{site['file']}:{site['line']}",
                "coverage_status": "shadow_observed",
            }
        )
    routes.extend(
        [
            {
                "route_id": "chroma_write_store:_IndexWriteGuardedChromaStore._collection",
                "entrypoint": "chroma_write_store.py:1077",
                "owner": "incremental_jsonl",
                "disposition": "coverage_unqualified_raw_handle",
                "coverage_status": "promotion_blocker",
            },
            {
                "route_id": "nested_production_chroma_write_session",
                "entrypoint": "chroma_write_store.py:1009",
                "owner": "session_tls",
                "disposition": "nested_session_inherits_attempt",
                "coverage_status": "shadow_observed",
            },
        ]
    )
    return {
        "schema": "scoped_proof_writer_inventory_v1",
        "purpose": "Arc #286 shadow proof writer route inventory",
        "routes": routes,
        "generated_from": str(SHADOW.relative_to(ROOT)),
    }


def main() -> None:
    payload = build()
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
