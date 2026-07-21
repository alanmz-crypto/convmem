#!/usr/bin/env python3
"""CLI entry for eval corpus capture (canonical: Chroma required).

Hermetic fixture runs use temp paths. Live/external capture requires an
approved run-manifest with execution_mode=real (Gate 2). Gate 1 hermetic
smokes may pass --authorize-fixture.

R2b capture: when the manifest has authorization_phase=r2b, the CLI uses
bind_r2b_capture and passes the capability through to run_capture. The
capability chain enforces max_retries=1 and all fixed R2b controls.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Eval corpus capture (Chroma required)"
    )
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

    r2b_capability = None

    if args.run_manifest is not None:
        from eval_corpus.run_manifest import load_run_manifest

        try:
            manifest = load_run_manifest(args.run_manifest)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"Refusing capture: {exc}", file=sys.stderr)
            return 2

        if str(manifest.get("authorization_phase") or "") == "r2b":
            if args.max_retries != 1:
                print(
                    "R2b capture requires --max-retries 1",
                    file=sys.stderr,
                )
                return 2

            from eval_corpus.capture import recompute_source_snapshot
            from eval_corpus.r2b_capture_auth import bind_r2b_capture

            try:
                r2b_capability = bind_r2b_capture(
                    run_manifest_path=args.run_manifest,
                    runtime={
                        "export": args.export,
                        "processed": args.processed,
                        "capture_dir": args.capture_dir,
                        "chroma_dir": args.chroma_dir,
                    },
                    snapshot_recompute_fn=recompute_source_snapshot,
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                print(f"Refusing R2b capture: {exc}", file=sys.stderr)
                return 2

    if r2b_capability is None:
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

    max_retries = 1 if r2b_capability is not None else args.max_retries
    result = run_capture(
        export_src=args.export.expanduser(),
        processed_src=args.processed.expanduser(),
        capture_dir=args.capture_dir.expanduser(),
        chroma_dir=args.chroma_dir.expanduser(),
        max_retries=max_retries,
        r2b_capability=r2b_capability,
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
    status = report.get("status")
    if status == "CAPTURE_COMPLETE":
        return 0
    if status == "UNRESOLVED":
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
