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

from incremental_jsonl_canary_network import install_p2_network_policy  # noqa: E402
from incremental_jsonl_isolation import install_service_denial  # noqa: E402

_SITE = os.environ.get("CONVMEM_INCREMENTAL_SITE", "")
if _SITE:
    sys.path.append(_SITE)

_LOOPBACK = os.environ.get("CONVMEM_CANARY_LOOPBACK", "127.0.0.1:11434")
install_p2_network_policy(_LOOPBACK)
install_service_denial()

from incremental_jsonl_canary import (  # noqa: E402
    CRASH_EXIT,
    CanaryRefused,
    ProductionCanaryBoundary,
    canary_coordinator,
    canary_writer_scope,
    decode_grant,
    fault_point_for_selector,
    is_p2_live_grant,
)
from incremental_jsonl_canary_p2 import (  # noqa: E402
    FAULT_STAGE,
    HermeticCanaryInvoker,
    bind_live_append_for_faults,
    freeze_live_evidence,
    gate0_preflight_live,
    install_provider_invoker,
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
    if command == "t5-bind":
        payload = bind_live_append_for_faults(grant, expected_sha256=digest)
        print(json.dumps(payload, sort_keys=True))
        return 0
    if command == "t5":
        payload = run_live_t5(
            boundary,
            grant,
            expected_sha256=digest,
            fault_selector=os.environ.get("CONVMEM_CANARY_FAULT", ""),
            provider_mode=os.environ.get("CONVMEM_CANARY_PROVIDER_MODE", "live"),
        )
        print(json.dumps(payload, sort_keys=True))
        return 0
    if command == "t5-fault":
        selector = os.environ.get("CONVMEM_CANARY_FAULT", "")
        if selector not in FAULT_STAGE:
            raise CanaryRefused("canary_fault_unknown", f"unknown fault selector: {selector}")
        provider_mode = os.environ.get("CONVMEM_CANARY_PROVIDER_MODE", "live")
        if provider_mode == "live":
            invoker = None
        elif provider_mode == "hermetic":
            invoker = HermeticCanaryInvoker()
        else:
            raise CanaryRefused("canary_provider_mode", f"unknown provider mode {provider_mode}")
        point = fault_point_for_selector(selector)

        def _fault(current: str) -> None:
            if current == point:
                os._exit(CRASH_EXIT)

        with install_provider_invoker(invoker, provider_mode=provider_mode):
            coordinator = canary_coordinator(boundary, grant.source.path, fault=_fault)
            with canary_writer_scope(boundary):
                coordinator.run()
        raise CanaryRefused("canary_fault_missed", f"fault {selector} was not reached")
    if command == "t6":
        digest_out = freeze_live_evidence(
            boundary,
            grant,
            expected_sha256=digest,
            gate0_report={"mode": "p2-exact-resource-v2"},
            sections={},
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
