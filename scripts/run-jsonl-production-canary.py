#!/usr/bin/env python3
"""Thin explicit launcher for the JSONL production canary harness.

Not registered in the normal ConvMem CLI or watcher.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from incremental_jsonl_canary import (  # noqa: E402
    CanaryRefused,
    decode_grant,
    gate0_preflight,
    ProductionCanaryBoundary,
    validate_grant,
    write_evidence,
)
from chroma_write_store import current_code_revision  # noqa: E402


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the JSONL production canary harness")
    parser.add_argument("--grant", required=True, help="Absolute path to the grant JSON")
    parser.add_argument("--grant-sha256", required=True, help="Expected SHA-256 of the grant")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run Gate 0 only; perform no mutations",
    )
    args = parser.parse_args(argv)
    grant_path = Path(args.grant).expanduser()
    expected = args.grant_sha256.lower()
    try:
        grant = decode_grant(grant_path)
        actual = _sha256_file(grant_path)
        if actual != expected:
            raise CanaryRefused("canary_grant_digest", "CLI digest does not match grant file")
        validate_grant(grant, expected_sha256=expected, code_revision=current_code_revision())
        boundary = ProductionCanaryBoundary.from_grant(grant)
        report = gate0_preflight(
            grant,
            boundary,
            expected_sha256=expected,
            code_revision=current_code_revision(),
        )
        if args.preflight_only:
            evidence_path = Path(grant.evidence_dir) / "gate0-preflight.json"
            digest = write_evidence(
                evidence_path,
                {"gate0": report, "grant_sha256": expected},
            )
            print(json.dumps({"status": "preflight_pass", "evidence_digest": digest}))
            return 0
        raise CanaryRefused(
            "canary_p2_unauthorized",
            "live canary execution requires a separate P2 grant; use hermetic tests in P1",
        )
    except CanaryRefused as exc:
        print(json.dumps({"status": "refused", "code": exc.code, "detail": exc.detail}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
