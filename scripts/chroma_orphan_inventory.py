#!/usr/bin/env python3
# pylint: disable=cyclic-import
"""Read-only HNSW-vs-METADATA orphan inventory (P0-B).

Writes evidence JSON under /tmp only. Never mutates Chroma or corpus.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from chroma_readonly import (  # noqa: E402  # pylint: disable=wrong-import-position
    _connect_readonly,
    _coerce_value,
    _db_path,
    collection_ids,
)
from chroma_store import (  # noqa: E402  # pylint: disable=wrong-import-position
    UNITS,
    open_chroma_for_verify,
)
from config import load_config  # noqa: E402  # pylint: disable=wrong-import-position
from llm import ollama_embed  # noqa: E402  # pylint: disable=wrong-import-position

CALIBRATION = Path("/tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl")
CEILING = 500
SLACK = 100

DIVERSE_PROBES = [
    "How does convmem doctor check chroma health?",
    "What is ksweep steering used for in convmem?",
    "Willowy Hollow staging2 CSP security headers",
    "dec_prop ledger decision record format",
    "What is Shadow ledger phase 0?",
]


def _load_calibration_questions() -> list[dict]:
    if not CALIBRATION.is_file():
        return []
    return [
        json.loads(line)
        for line in CALIBRATION.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _raw_query(chroma_dir: str, question: str, n_results: int, cfg: dict) -> dict:
    models = cfg["models"]
    embedding = ollama_embed(
        question, model=models["embed_model"], host=models["ollama_host"]
    )
    store = open_chroma_for_verify(chroma_dir)
    try:
        col = store._collection(UNITS)  # pylint: disable=protected-access
        total = col.count()
        n = min(max(n_results, 1), max(total, 1))
        raw = col.query(query_embeddings=[embedding], n_results=n)
    finally:
        store.close()
    ids = raw.get("ids", [[]])[0]
    docs = raw.get("documents", [[]])[0]
    none_indices = [i for i, d in enumerate(docs) if d is None]
    none_ids = [ids[i] for i in none_indices]
    return {
        "question": question,
        "n_results": n,
        "total_count": total,
        "result_count": len(ids),
        "none_indices": none_indices,
        "none_ids": none_ids,
        "all_ids": ids,
    }


def _sqlite_per_id(chroma_dir: str, eid: str) -> dict:
    conn = _connect_readonly(_db_path(chroma_dir))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT e.embedding_id
            FROM embeddings e
            JOIN segments s ON e.segment_id = s.id
            JOIN collections c ON s.collection = c.id
            WHERE c.name = ? AND s.scope = 'METADATA' AND e.embedding_id = ?
            """,
            (UNITS, eid),
        )
        row_found = cur.fetchone() is not None
        meta: dict = {}
        doc = None
        if row_found:
            cur.execute(
                """
                SELECT em.key, em.string_value, em.int_value, em.float_value, em.bool_value
                FROM embeddings e
                JOIN segments s ON e.segment_id = s.id
                JOIN collections c ON s.collection = c.id
                JOIN embedding_metadata em ON em.id = e.id
                WHERE c.name = ? AND s.scope = 'METADATA' AND e.embedding_id = ?
                """,
                (UNITS, eid),
            )
            for r in cur.fetchall():
                key = r["key"]
                if key == "chroma:document":
                    doc = r["string_value"]
                else:
                    meta[key] = _coerce_value(
                        r["string_value"], r["int_value"], r["float_value"], r["bool_value"]
                    )
        return {
            "row_found": row_found,
            "chroma_document": doc,
            "document_is_null": doc is None,
            "superseded": meta.get("superseded"),
            "deleted": meta.get("deleted"),
            "source_path": meta.get("source_path"),
            "title": meta.get("title"),
        }
    finally:
        conn.close()


def run_inventory(*, output: Path | None = None) -> dict:
    cfg = load_config()
    chroma_dir = cfg["index"]["chroma_dir"]
    metadata_ids = set(collection_ids(chroma_dir, UNITS))
    total = len(metadata_ids)

    probes: list[dict] = []
    for row in _load_calibration_questions():
        probes.append({"label": row.get("id", "cal"), "question": row["question"]})
    probes.append(
        {
            "label": "negative_control",
            "question": "What is convmem doctor and how does it check chroma health?",
        }
    )
    for i, q in enumerate(DIVERSE_PROBES):
        probes.append({"label": f"diverse_{i+1}", "question": q})

    query_results: list[dict] = []
    all_query_ids: set[str] = set()
    all_none_ids: set[str] = set()

    for i, probe in enumerate(probes):
        n_results = (total + SLACK) if i == 0 else min(total * 3, total + 1000)
        result = _raw_query(chroma_dir, probe["question"], n_results, cfg)
        result["label"] = probe["label"]
        query_results.append(result)
        all_query_ids.update(result["all_ids"])
        all_none_ids.update(result["none_ids"])

    orphans_hnsw_minus_meta = sorted(all_none_ids - metadata_ids)
    meta_minus_query = sorted(metadata_ids - all_query_ids)

    diff_ids = sorted(set(orphans_hnsw_minus_meta) | set(meta_minus_query))
    if len(diff_ids) > CEILING:
        per_id = {eid: _sqlite_per_id(chroma_dir, eid) for eid in diff_ids[:50]}
        diff_truncated = True
    else:
        per_id = {eid: _sqlite_per_id(chroma_dir, eid) for eid in diff_ids}
        diff_truncated = False

    if len(orphans_hnsw_minus_meta) <= 50:
        tier = "S"
    elif len(orphans_hnsw_minus_meta) <= 500:
        tier = "M"
    else:
        tier = "L"

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chroma_dir": chroma_dir,
        "metadata_id_count": total,
        "distinct_none_ids_from_probes": len(all_none_ids),
        "distinct_query_ids_union": len(all_query_ids),
        "orphans_hnsw_minus_metadata_count": len(orphans_hnsw_minus_meta),
        "metadata_minus_query_enumerated_count": len(meta_minus_query),
        "reconcile_tier_recommendation": tier,
        "ceiling_applied": diff_truncated,
        "probes": query_results,
        "orphans_hnsw_minus_metadata": orphans_hnsw_minus_meta,
        "metadata_minus_query_enumerated_sample": meta_minus_query[:100],
        "per_id_sqlite": per_id,
    }

    out = output or Path(
        f"/tmp/chroma-orphan-inventory-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    report["output_path"] = str(out)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Chroma orphan inventory (P0-B)")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = run_inventory(output=args.output)
    print(json.dumps({k: v for k, v in report.items() if k != "probes"}, indent=2))
    print(f"\nWrote {report['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
