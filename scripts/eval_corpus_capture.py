#!/usr/bin/env python3
"""CLI entry for eval corpus capture (live paths require --authorize-r2b).

Hermetic fixture runs are supported for tests/smoke; they still need explicit
paths and never touch production defaults unless those paths are passed in.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eval corpus capture (requires R2b for live)")
    parser.add_argument(
        "--authorize-r2b",
        action="store_true",
        help="Required flag acknowledging Ryan R2b authorization for capture writes",
    )
    parser.add_argument("--export", type=Path, required=True, help="Source knowledge_units.jsonl")
    parser.add_argument("--processed", type=Path, required=True, help="Source processed.json")
    parser.add_argument(
        "--capture-dir",
        type=Path,
        required=True,
        help="Destination capture directory (created; artifacts written atomically)",
    )
    parser.add_argument(
        "--chroma-dir",
        type=Path,
        default=None,
        help="Optional Chroma root for one-txn readonly SQLite extract",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Copy drift retries (default 3)",
    )
    args = parser.parse_args(argv)

    if not args.authorize_r2b:
        print(
            "Refusing to capture: pass --authorize-r2b only after Ryan grants R2b. "
            "R2a (dirs/configs) does not authorize corpus construction.",
            file=sys.stderr,
        )
        return 2

    sys.path.insert(0, str(REPO))
    from eval_corpus.capture import run_capture

    result = run_capture(
        export_src=args.export.expanduser(),
        processed_src=args.processed.expanduser(),
        capture_dir=args.capture_dir.expanduser(),
        chroma_dir=args.chroma_dir.expanduser() if args.chroma_dir else None,
        max_retries=args.max_retries,
    )
    report = result["capture_report"]
    print(json.dumps({
        "status": report.get("status"),
        "unit_count": report.get("unit_count"),
        "unit_corpus_fingerprint": report.get("unit_corpus_fingerprint"),
        "package_sha256": report.get("package_sha256"),
        "chroma_extract": report.get("chroma_extract"),
        "capture_dir": str(args.capture_dir.expanduser()),
    }, indent=2, sort_keys=True))
    return 0 if report.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
