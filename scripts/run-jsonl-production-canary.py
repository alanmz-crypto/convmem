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
    is_p2_live_grant,
    validate_grant,
)
from incremental_jsonl_canary_p2 import (  # noqa: E402
    freeze_live_evidence,
    gate0_preflight_live,
    prepare_live_p2,
    run_live_t3,
    run_live_t4,
    run_live_t5,
    validate_p2_live_grant,
)
from chroma_write_store import current_code_revision  # noqa: E402


def _load_grant(grant_path: Path, expected: str):
    grant = decode_grant(grant_path)
    actual = hashlib.sha256(grant.digest_payload()).hexdigest()
    if actual != expected:
        raise CanaryRefused("canary_grant_digest", "CLI digest does not match grant file")
    revision = current_code_revision()
    return grant, revision


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
        choices=(
            "prepare",
            "t3-initial",
            "t4-append",
            "t5-fault",
            "t6-evidence",
            "p2-t3",
            "p2-t4",
            "p2-t5",
            "p2-t6",
            "p2-all",
        ),
        help="P2 orchestration stage",
    )
    parser.add_argument(
        "--fault",
        help="Fault selector for --stage t5-fault/p2-t5",
    )
    args = parser.parse_args(argv)
    grant_path = Path(args.grant).expanduser()
    expected = args.grant_sha256.lower()
    try:
        grant, revision = _load_grant(grant_path, expected)
        if not args.preflight_only and not is_p2_live_grant(grant):
            if is_p2_grant(grant):
                raise CanaryRefused(
                    "canary_mode_retired",
                    "p2-exact-resource-v1 is not live-capable; use p2-exact-resource-v2",
                )
            raise CanaryRefused(
                "canary_p2_unauthorized",
                "live canary execution requires a P2 exact-resource grant",
            )
        if args.stage == "p2-all":
            raise CanaryRefused(
                "canary_p2_all_refused",
                "live P2 has no all-stages command; use one stage transition per invocation",
            )
        if is_p2_live_grant(grant):
            validate_p2_live_grant(grant, expected_sha256=expected, code_revision=revision)
            boundary = ProductionCanaryBoundary.from_p2_live_grant(grant)
            report = gate0_preflight_live(
                grant,
                boundary,
                expected_sha256=expected,
                code_revision=revision,
            )
            if args.preflight_only:
                print(json.dumps({"status": "preflight_pass", "gate0": report}, sort_keys=True))
                return 0
            stage = args.stage
            if stage == "prepare":
                payload = prepare_live_p2(
                    boundary,
                    grant,
                    expected_sha256=expected,
                    code_revision=revision,
                )
            elif stage in {"t3-initial", "p2-t3"}:
                payload = run_live_t3(
                    boundary,
                    grant,
                    expected_sha256=expected,
                    provider_mode="live",
                )
            elif stage in {"t4-append", "p2-t4"}:
                payload = run_live_t4(
                    boundary,
                    grant,
                    expected_sha256=expected,
                    provider_mode="live",
                )
            elif stage in {"t5-fault", "p2-t5"}:
                if not args.fault:
                    raise CanaryRefused("canary_p2_t5", "--fault required for t5 stage")
                payload = run_live_t5(
                    boundary,
                    grant,
                    expected_sha256=expected,
                    fault_selector=args.fault,
                    provider_mode="live",
                )
            elif stage in {"t6-evidence", "p2-t6"}:
                digest = freeze_live_evidence(
                    boundary,
                    grant,
                    expected_sha256=expected,
                    gate0_report=report,
                    sections={},
                )
                payload = {"evidence_digest": digest, "hermetic": False}
            else:
                raise CanaryRefused(
                    "canary_p2_unauthorized",
                    "P2 mutation requires --stage prepare|t3-initial|t4-append|t5-fault|t6-evidence",
                )
            print(json.dumps({"status": "ok", "stage": stage, "payload": payload}, default=str))
            return 0
        validate_grant(grant, expected_sha256=expected, code_revision=revision)
        boundary = ProductionCanaryBoundary.from_grant(
            grant, root=Path(grant.evidence_dir).parent
        )
        report = gate0_preflight(
            grant,
            boundary,
            expected_sha256=expected,
            code_revision=revision,
        )
        if args.preflight_only:
            print(json.dumps({"status": "preflight_pass", "gate0": report}, sort_keys=True))
            return 0
        raise CanaryRefused(
            "canary_p2_unauthorized",
            "live canary execution requires a P2 exact-resource grant",
        )
    except CanaryRefused as exc:
        print(json.dumps({"status": "refused", "code": exc.code, "detail": exc.detail}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
