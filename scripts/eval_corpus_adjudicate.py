#!/usr/bin/env python3
"""Emit corpus_acceptance.json from a separate adjudications file.

Never modifies historical_spot_check.json or other capture artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Adjudicate capture spot-check samples")
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument(
        "--adjudications",
        type=Path,
        required=True,
        help="Separate adjudications JSON (does not edit spot-check plan)",
    )
    parser.add_argument("--reviewer", default="ryan")
    parser.add_argument(
        "--authorize-fixture",
        action="store_true",
        help="Hermetic/temp only",
    )
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    from eval_corpus.adjudicate import emit_corpus_acceptance
    from eval_corpus.run_manifest import _path_is_tempish

    if args.authorize_fixture and not _path_is_tempish(args.capture_dir):
        print("Refusing: --authorize-fixture requires temp capture-dir", file=sys.stderr)
        return 2
    if not args.authorize_fixture:
        print(
            "Refusing: pass --authorize-fixture for Gate 1 hermetic adjudication "
            "(real acceptance is Gate 2 / Ryan).",
            file=sys.stderr,
        )
        return 2

    try:
        acc = emit_corpus_acceptance(
            capture_dir=args.capture_dir.expanduser(),
            adjudications_path=args.adjudications.expanduser(),
            reviewer=args.reviewer,
        )
    except Exception as exc:
        print(f"Adjudication failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(acc, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
