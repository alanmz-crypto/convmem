#!/usr/bin/env python3
"""Repair empty Chroma document fields on ledger decision/verification units."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from config import load_config
from observe import repair_empty_ledger_documents


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-embed ledger units with empty Chroma documents"
    )
    parser.add_argument("--dry-run", action="store_true", help="Report only; no writes")
    parser.add_argument("--limit", type=int, default=0, help="Max repairs (0 = all)")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    stats = repair_empty_ledger_documents(
        cfg,
        dry_run=args.dry_run,
        limit=args.limit,
        verbose=not args.quiet,
    )
    print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
