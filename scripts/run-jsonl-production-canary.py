#!/usr/bin/env python3
"""Thin explicit launcher for the JSONL production canary harness.

Not registered in the normal ConvMem CLI or watcher.
"""

# pylint: disable=invalid-name,wrong-import-position

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
    ProductionCanaryBoundary,
    decode_grant,
    gate0_preflight,
    is_p2_grant,
    run_p2_append_adoption,
    run_p2_fault_observation,
    run_p2_initial_adoption,
    run_p2_orchestration,
    validate_grant,
    validate_p2_grant,
    write_canary_overlay,
    write_evidence,
)
from chroma_write_store import current_code_revision  # noqa: E402


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_grant(grant_path: Path, expected: str):
    grant = decode_grant(grant_path)
    actual = hashlib.sha256(grant.digest_payload()).hexdigest()
    if actual != expected:
        raise CanaryRefused("canary_grant_digest", "CLI digest does not match grant file")
    revision = current_code_revision()
    if is_p2_grant(grant):
        validate_p2_grant(grant, expected_sha256=expected, code_revision=revision)
        boundary = ProductionCanaryBoundary.from_p2_grant(
            grant, root=Path(grant.evidence_dir).parent
        )
    else:
        validate_grant(grant, expected_sha256=expected, code_revision=revision)
        boundary = ProductionCanaryBoundary.from_grant(
            grant, root=Path(grant.evidence_dir).parent
        )
    return grant, boundary, revision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the JSONL production canary harness")
    parser.add_argument("--grant", required=True, help="Absolute path to the grant JSON")
    parser.add_argument("--grant-sha256", required=True, help="Expected SHA-256 of the grant")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run Gate 0 only; perform no mutations",
    )
    parser.add_argument(
        "--stage",
        choices=("p2-t3", "p2-t4", "p2-t5", "p2-t6", "p2-all"),
        help="P2 orchestration stage (P2 grants only)",
    )
    parser.add_argument(
        "--fault",
        help="Fault selector for --stage p2-t5",
    )
    args = parser.parse_args(argv)
    grant_path = Path(args.grant).expanduser()
    expected = args.grant_sha256.lower()
    try:
        grant, boundary, revision = _load_grant(grant_path, expected)
        report = gate0_preflight(
            grant,
            boundary,
            expected_sha256=expected,
            code_revision=revision,
        )
        if args.preflight_only:
            evidence_path = Path(grant.evidence_dir) / "gate0-preflight.json"
            digest = write_evidence(
                evidence_path,
                {"gate0": report, "grant_sha256": expected},
            )
            print(json.dumps({"status": "preflight_pass", "evidence_digest": digest}))
            return 0
        if not is_p2_grant(grant):
            raise CanaryRefused(
                "canary_p2_unauthorized",
                "live canary execution requires a P2 exact-resource grant",
            )
        write_canary_overlay(boundary)
        if args.stage == "p2-all":
            payload = run_p2_orchestration(
                boundary,
                grant,
                expected_sha256=expected,
                code_revision=revision,
                include_faults=True,
            )
            print(json.dumps({"status": "p2_all", **payload}))
            return 0
        if args.stage == "p2-t3":
            payload = run_p2_initial_adoption(boundary, grant, expected_sha256=expected)
        elif args.stage == "p2-t4":
            payload = run_p2_append_adoption(boundary, grant, expected_sha256=expected)
        elif args.stage == "p2-t5":
            if not args.fault:
                raise CanaryRefused("canary_p2_t5", "--fault required for p2-t5 stage")
            payload = run_p2_fault_observation(
                boundary,
                grant,
                expected_sha256=expected,
                fault_selector=args.fault,
            )
        elif args.stage == "p2-t6":
            digest = write_evidence(
                Path(grant.evidence_dir) / "p2-stage-evidence.json",
                {"gate0": report, "grant_sha256": expected, "hermetic": True},
            )
            payload = {"evidence_digest": digest}
        else:
            raise CanaryRefused(
                "canary_p2_unauthorized",
                "P2 mutation requires --stage p2-t3|p2-t4|p2-t5|p2-t6|p2-all",
            )
        print(json.dumps({"status": "ok", "stage": args.stage, "payload": payload}))
        return 0
    except CanaryRefused as exc:
        print(json.dumps({"status": "refused", "code": exc.code, "detail": exc.detail}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
