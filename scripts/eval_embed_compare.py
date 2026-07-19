#!/usr/bin/env python3
"""Dual-view paired compare CLI (fixture or approved run-manifest)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eval embed paired compare")
    parser.add_argument("--authorize-fixture", action="store_true")
    parser.add_argument("--run-manifest", type=Path, default=None)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="comparison manifest JSON")
    parser.add_argument(
        "--mode",
        choices=("injectable",),
        default="injectable",
        help="Gate 1 hermetic uses injectable query fns via --scores-json",
    )
    parser.add_argument(
        "--scores-json",
        type=Path,
        help="Hermetic: {baseline: {query: [hits]}, challenger: {...}}",
    )
    parser.add_argument("--baseline-units-per-sec", type=float, default=None)
    parser.add_argument("--challenger-units-per-sec", type=float, default=None)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    from eval_corpus.io_atomic import atomic_write_json
    from eval_corpus.run_manifest import DEFAULT_UNCERTAINTY, assert_compare_authorized
    from eval_corpus.runner import compare_paired_arms, measure_view_latency

    try:
        manifest = assert_compare_authorized(
            authorize_fixture=args.authorize_fixture,
            run_manifest_path=args.run_manifest,
        )
    except Exception as exc:
        print(f"Refusing compare: {exc}", file=sys.stderr)
        return 2

    uncertainty = {**DEFAULT_UNCERTAINTY}
    for k in DEFAULT_UNCERTAINTY:
        if k in manifest:
            uncertainty[k] = manifest[k]

    rows = _load_jsonl(args.golden.expanduser())
    package = _load_jsonl(args.package.expanduser())

    if not args.scores_json:
        print("Gate 1 hermetic compare requires --scores-json injectable hits", file=sys.stderr)
        return 3

    scores = json.loads(args.scores_json.expanduser().read_text(encoding="utf-8"))

    def make_fn(arm: str):
        table = scores[arm]

        def _fn(query, *, top_k, eval_view):
            hits = list(table.get(query) or [])
            return hits[:top_k]

        return _fn

    report = compare_paired_arms(
        rows,
        make_fn("baseline"),
        make_fn("challenger"),
        package_units=package,
        uncertainty=uncertainty,
    )
    # Throughput from injectable timing (deterministic fake clock via measure)
    queries = [r["query"] for r in rows]
    state = {"t": 0.0}

    def clock():
        state["t"] += 0.01
        return state["t"]

    lat = measure_view_latency(
        queries,
        make_fn("baseline"),
        view="embedding_influenced",
        clock=clock,
    )
    report["throughput"] = {
        "retrieval_queries_per_sec": round(1000.0 / lat.mean_ms, 6) if lat.mean_ms else 0.0,
        "baseline_units_per_sec": args.baseline_units_per_sec,
        "challenger_units_per_sec": args.challenger_units_per_sec,
    }
    report["run_manifest_execution_mode"] = manifest.get("execution_mode")
    atomic_write_json(args.out.expanduser(), report)
    print(json.dumps({"out": str(args.out), "verdict": report["uncertainty"]["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
