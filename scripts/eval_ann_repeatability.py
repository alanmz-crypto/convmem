#!/usr/bin/env python3
"""Assess three captured ANN realizations as a separate R7 diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _read_report(path: Path) -> tuple[str, str, dict[str, list[str]]]:
    raw = path.read_bytes()
    body = json.loads(raw.decode("utf-8"))
    if not isinstance(body, dict):
        raise ValueError("ANN realization report must be a JSON object")
    name = str(body.get("realization") or "")
    verdict = str(body.get("evidence_verdict") or "")
    queries = body.get("queries")
    if not name or not verdict or not isinstance(queries, dict):
        raise ValueError("ANN report requires realization, evidence_verdict, and queries")
    normalized = {
        str(query_id): [str(hit) for hit in hits]
        for query_id, hits in queries.items()
        if isinstance(hits, list)
    }
    if len(normalized) != len(queries):
        raise ValueError("ANN report queries must map to hit lists")
    return name, verdict, normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assess ANN rebuild repeatability")
    parser.add_argument("--authorize-fixture", action="store_true")
    parser.add_argument("--run-manifest", type=Path, default=None)
    parser.add_argument("--grant", type=Path, default=None)
    parser.add_argument("--grant-id", default=None)
    parser.add_argument("--attempt-id", default=None)
    parser.add_argument("--realization-report", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    from eval_corpus.ann_stability import assess_ann_repeatability
    from eval_corpus.io_atomic import atomic_write_json

    reports = [path.expanduser() for path in args.realization_report]
    if len(reports) != 3:
        print("ANN repeatability requires exactly three reports", file=sys.stderr)
        return 2
    try:
        parsed = [_read_report(path) for path in reports]
        names = [row[0] for row in parsed]
        if len(set(names)) != len(names):
            raise ValueError("ANN realization names must be unique")
        realizations = {name: queries for name, _verdict, queries in parsed}
        verdicts = {name: verdict for name, verdict, _queries in parsed}
        assessment = assess_ann_repeatability(
            realizations,
            verdicts,
            top_k=args.top_k,
        )
        out = args.out.expanduser()
        if out.exists() or out.is_symlink():
            raise PermissionError(f"ANN assessment output must be absent: {out}")
        if args.run_manifest is not None and not args.authorize_fixture:
            from eval_corpus.run_manifest import (
                consume_operation_grant,
                load_run_manifest,
            )

            manifest = load_run_manifest(args.run_manifest)
            source_identity = manifest.get("source_identity") or {}
            consume_operation_grant(
                args.grant,
                operation="ann_repeatability",
                manifest_path=args.run_manifest,
                grant_id=args.grant_id,
                approved_paths={
                    "out": out,
                    **{f"realization_{index}": path for index, path in enumerate(reports)},
                },
                approved_git_oid=source_identity.get("approved_source_git_oid"),
                attempt_id=args.attempt_id,
                run_id=manifest.get("run_id"),
                manifest=manifest,
            )
        output = {
            "schema_version": "ann_repeatability_report_v1",
            "operation": "ann_repeatability",
            "inputs": [
                {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                for path in reports
            ],
            "assessment": assessment,
        }
        atomic_write_json(out, output)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"ANN repeatability failed closed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
