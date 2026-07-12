#!/usr/bin/env python3
"""Evaluate query_units against golden_queries.jsonl (P@1 / P@5)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures"
GOLDEN = FIXTURES / "golden_queries.jsonl"
BASELINE = FIXTURES / "golden_queries_baseline.json"


def load_golden(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def ledger_ids_from_hits(hits: list[dict]) -> list[str]:
    out: list[str] = []
    for h in hits:
        lid = ((h.get("metadata") or {}).get("ledger_id") or "").strip()
        out.append(lid)
    return out


def eval_row(row: dict, *, chroma_dir: str | None = None) -> dict:
    from query import query_units

    query = row["query"]
    top_k = int(row.get("top_k") or 5)
    acceptable = list(row.get("acceptable_ids") or [])
    hits = query_units(query, top_k=top_k, chroma_dir=chroma_dir)
    ids = ledger_ids_from_hits(hits)
    rank = None
    matched = ""
    for i, lid in enumerate(ids, 1):
        if lid in acceptable:
            rank = i
            matched = lid
            break
    return {
        "query": query,
        "acceptable_ids": acceptable,
        "top_k": top_k,
        "hit_ids": ids,
        "matched_id": matched,
        "rank": rank,
        "p_at_1": rank == 1 if rank else False,
        "p_at_k": rank is not None,
    }


def summarize(results: list[dict]) -> dict:
    n = len(results) or 1
    # MRR: mean reciprocal rank of the first acceptable hit (0 when no hit).
    mrr = sum(1.0 / r["rank"] for r in results if r["rank"]) / n
    # recall@k here == hit@k: acceptable_ids are alternative correct answers,
    # so a row is "recalled" if any acceptable id lands within its top_k.
    recall_at_k = sum(1 for r in results if r["p_at_k"]) / n
    return {
        "count": len(results),
        "p_at_1": sum(1 for r in results if r["p_at_1"]) / n,
        "p_at_k": sum(1 for r in results if r["p_at_k"]) / n,
        "mrr": round(mrr, 4),
        "recall_at_k": round(recall_at_k, 4),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden-query retrieval eval")
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--top-k", type=int, default=0, help="Override top_k for all rows")
    parser.add_argument(
        "--chroma-dir",
        type=Path,
        default=None,
        help="Query against this Chroma root instead of config index.chroma_dir",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Evaluate only the first N golden rows (0 = all)",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(REPO))
    rows = load_golden(args.golden)
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]
    if args.top_k:
        for row in rows:
            row["top_k"] = args.top_k

    chroma_dir = str(args.chroma_dir.expanduser()) if args.chroma_dir else None
    report = summarize([eval_row(r, chroma_dir=chroma_dir) for r in rows])

    print(f"Golden queries: {report['count']}")
    print(f"P@1: {report['p_at_1']:.2%}")
    print(f"P@k: {report['p_at_k']:.2%}")
    print(f"MRR: {report['mrr']:.4f}")
    print(f"Recall@k: {report['recall_at_k']:.2%}")
    for r in report["results"]:
        mark = "PASS" if r["p_at_k"] else "FAIL"
        rank = r["rank"] or "-"
        print(f"  [{mark}] rank={rank} {r['query'][:50]!r} -> {r['matched_id'] or 'none'}")

    if args.update_baseline:
        args.baseline.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote baseline {args.baseline}")
        return 0

    if not args.baseline.is_file():
        print(f"\nNo baseline at {args.baseline} — run with --update-baseline", file=sys.stderr)
        return 1

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    regressions: list[str] = []
    base_by_query = {r["query"]: r for r in baseline.get("results") or []}
    for r in report["results"]:
        prev = base_by_query.get(r["query"])
        if not prev:
            continue
        if prev.get("p_at_k") and not r["p_at_k"]:
            regressions.append(r["query"])

    if regressions:
        print("\nREGRESSION vs baseline:", file=sys.stderr)
        for q in regressions:
            print(f"  - {q}", file=sys.stderr)
        return 1

    print("\nNo regression vs baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
