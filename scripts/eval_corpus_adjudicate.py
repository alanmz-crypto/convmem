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
    parser.add_argument(
        "--acceptance-out",
        type=Path,
        default=None,
        help="Output path for corpus_acceptance.json (default: capture-dir/corpus_acceptance.json)",
    )
    parser.add_argument("--reviewer", default="ryan")
    parser.add_argument("--authorize-fixture", action="store_true")
    parser.add_argument("--run-manifest", type=Path, default=None)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    from eval_corpus.adjudicate import emit_corpus_acceptance
    from eval_corpus.run_manifest import bind_adjudicate

    capture_dir = args.capture_dir.expanduser()
    adjudications = args.adjudications.expanduser()
    acceptance_out = (
        args.acceptance_out.expanduser()
        if args.acceptance_out
        else capture_dir / "corpus_acceptance.json"
    )

    try:
        bind_adjudicate(
            authorize_fixture=args.authorize_fixture,
            run_manifest_path=args.run_manifest,
            runtime={
                "capture_dir": capture_dir,
                "adjudications": adjudications,
                "acceptance_out": acceptance_out,
            },
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Refusing adjudicate: {exc}", file=sys.stderr)
        return 2

    try:
        acc = emit_corpus_acceptance(
            capture_dir=capture_dir,
            adjudications_path=adjudications,
            reviewer=args.reviewer,
            acceptance_path=acceptance_out,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Adjudication failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(acc, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
