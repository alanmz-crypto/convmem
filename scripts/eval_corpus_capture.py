#!/usr/bin/env python3
"""CLI entry for eval corpus capture (R2b only — not authorized under R1).

R1 ships this script as a stub surface; invoking against live paths requires R2b.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Eval corpus capture (requires R2b)")
    parser.add_argument(
        "--authorize-r2b",
        action="store_true",
        help="Required flag acknowledging Ryan R2b authorization",
    )
    args = parser.parse_args()
    if not args.authorize_r2b:
        print(
            "Refusing to capture: pass --authorize-r2b only after Ryan grants R2b. "
            "R2a (dirs/configs) does not authorize corpus construction.",
            file=sys.stderr,
        )
        return 2
    print(
        "R2b authorized flag set, but live capture is not implemented in this "
        "R1 milestone beyond library helpers (eval_corpus.capture). "
        "Stop — wire full SQLite extract + package build under a later commit "
        "when R2b is executed.",
        file=sys.stderr,
    )
    return 3


if __name__ == "__main__":
    sys.path.insert(0, str(REPO))
    raise SystemExit(main())
