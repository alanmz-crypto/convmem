#!/usr/bin/env python3
"""Compare live vs shadow TOML; exit 1 on unauthorized diffs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    sys.path.insert(0, str(REPO))
    from eval_corpus.config_audit import config_diff_violations

    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore

    parser = argparse.ArgumentParser()
    parser.add_argument("--live", type=Path, required=True)
    parser.add_argument("--shadow", type=Path, required=True)
    args = parser.parse_args()
    live = tomllib.loads(args.live.read_text(encoding="utf-8"))
    shadow = tomllib.loads(args.shadow.read_text(encoding="utf-8"))
    violations = config_diff_violations(live, shadow)
    if violations:
        print("UNAUTHORIZED CONFIG DIFF:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print("Config diff within allowlist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
