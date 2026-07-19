#!/usr/bin/env python3
"""CLI entry for eval corpus capture (canonical: Chroma required).

Hermetic fixture runs use temp paths. Live/external capture requires an
approved run-manifest with execution_mode=real (Gate 2). Gate 1 hermetic
smokes may pass --authorize-fixture.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eval corpus capture (Chroma required)")
    parser.add_argument(
        "--authorize-fixture",
        action="store_true",
        help="Authorize hermetic/temp capture only (Gate 1 tests/smoke)",
    )
    parser.add_argument(
        "--run-manifest",
        type=Path,
        default=None,
        help="Approved run-manifest (required for execution_mode=real)",
    )
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--processed", type=Path, required=True)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument(
        "--chroma-dir",
        type=Path,
        required=True,
        help="Chroma root (required for canonical capture)",
    )
    parser.add_argument("--max-retries", type=int, default=3)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    from eval_corpus.run_manifest import assert_capture_authorized

    try:
        assert_capture_authorized(
            authorize_fixture=args.authorize_fixture,
            run_manifest_path=args.run_manifest,
            export=args.export,
            processed=args.processed,
            capture_dir=args.capture_dir,
            chroma_dir=args.chroma_dir,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Refusing capture: {exc}", file=sys.stderr)
        return 2

    from eval_corpus.capture import run_capture

    result = run_capture(
        export_src=args.export.expanduser(),
        processed_src=args.processed.expanduser(),
        capture_dir=args.capture_dir.expanduser(),
        chroma_dir=args.chroma_dir.expanduser(),
        max_retries=args.max_retries,
    )
    report = result["capture_report"]
    print(
        json.dumps(
            {
                "status": report.get("status"),
                "unit_count": report.get("unit_count"),
                "unit_corpus_fingerprint": report.get("unit_corpus_fingerprint"),
                "package_sha256": report.get("package_sha256"),
                "overlap_overall": report.get("overlap_overall"),
                "corpus_accepted": report.get("corpus_accepted"),
                "capture_dir": str(args.capture_dir.expanduser()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report.get("status") == "CAPTURE_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
