#!/usr/bin/env python3
"""Production-owned live P2 worker.

Installs service and non-loopback network denial before importing
provider-capable modules. This file must not import tests, pytest, or fakes.
"""

# Denial must be installed before provider-capable imports.
# pylint: disable=wrong-import-position,raise-missing-from

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from incremental_jsonl_isolation import (  # noqa: E402
    install_network_denial,
    install_service_denial,
)

install_network_denial()
install_service_denial()

from incremental_jsonl_canary import (  # noqa: E402
    CRASH_EXIT,
    CanaryRefused,
    ProductionCanaryBoundary,
    decode_grant,
    is_p2_live_grant,
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


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "crash-self":
        os._exit(CRASH_EXIT)
    grant = decode_grant(os.environ["CONVMEM_CANARY_GRANT"])
    digest = os.environ["CONVMEM_CANARY_GRANT_SHA256"]
    revision = os.environ["CONVMEM_CANARY_REVISION"]
    if not is_p2_live_grant(grant):
        raise CanaryRefused("canary_mode", "live worker requires p2-exact-resource-v2")
    validate_p2_live_grant(grant, expected_sha256=digest, code_revision=revision)
    boundary = ProductionCanaryBoundary.from_p2_live_grant(grant)
    if command == "gate0":
        report = gate0_preflight_live(
            grant, boundary, expected_sha256=digest, code_revision=revision
        )
        print(json.dumps(report, sort_keys=True))
        return 0
    if command == "prepare":
        payload = prepare_live_p2(
            boundary, grant, expected_sha256=digest, code_revision=revision
        )
        print(json.dumps({"status": "prepared", "capsule_digest": payload["capsule_digest"]}))
        return 0
    if command == "t3":
        payload = run_live_t3(
            boundary,
            grant,
            expected_sha256=digest,
            provider_mode="live",
        )
        print(json.dumps(payload, sort_keys=True))
        return 0
    if command == "t4":
        payload = run_live_t4(
            boundary,
            grant,
            expected_sha256=digest,
            provider_mode="live",
        )
        print(json.dumps(payload, sort_keys=True))
        return 0
    if command == "t5":
        payload = run_live_t5(
            boundary,
            grant,
            expected_sha256=digest,
            fault_selector=os.environ.get("CONVMEM_CANARY_FAULT", ""),
            provider_mode="live",
        )
        print(json.dumps(payload, sort_keys=True))
        return 0
    if command == "t6":
        digest_out = freeze_live_evidence(
            boundary,
            grant,
            expected_sha256=digest,
            gate0_report={"mode": "p2-exact-resource-v2"},
            sections={},
            disposition="recovery_unproven",
        )
        print(json.dumps({"evidence_digest": digest_out}))
        return 0
    raise CanaryRefused("canary_worker_command", f"unknown live worker command {command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CanaryRefused as exc:
        print(json.dumps({"status": "refused", "code": exc.code, "detail": exc.detail}), file=sys.stderr)
        raise SystemExit(2)
