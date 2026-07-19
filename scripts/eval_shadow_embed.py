#!/usr/bin/env python3
"""CLI entry for embed-only shadow build (R4/R5 only — not authorized under R1)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Eval shadow embed build (requires R4 or R5)")
    parser.add_argument(
        "--authorize-r4",
        action="store_true",
        help="Nomic shadow build authorization",
    )
    parser.add_argument(
        "--authorize-r5",
        action="store_true",
        help="Challenger shadow build authorization",
    )
    args = parser.parse_args()
    if not (args.authorize_r4 or args.authorize_r5):
        print(
            "Refusing shadow build: pass --authorize-r4 or --authorize-r5 after Ryan grant.",
            file=sys.stderr,
        )
        return 2
    print(
        "Authorization flag present, but live shadow embedding is not run under R1. "
        "Library: eval_corpus.shadow_build (manifest/result + row-safe resume).",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    sys.path.insert(0, str(REPO))
    raise SystemExit(main())
