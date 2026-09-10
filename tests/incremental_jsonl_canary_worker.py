"""Subprocess worker for hermetic JSONL production-canary tests."""

# pylint: disable=wrong-import-position,broad-exception-caught

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

_SITE = os.environ.get("CONVMEM_INCREMENTAL_SITE", "")
if _SITE:
    sys.path.append(_SITE)

from incremental_jsonl_canary import (  # noqa: E402
    CRASH_EXIT,
    CanaryRefused,
    ProductionCanaryBoundary,
    canary_coordinator,
    canary_writer_scope,
    consume_nonce,
    decode_grant,
    fault_point_for_selector,
    install_call_budget_guard,
    validate_grant,
    write_canary_overlay,
)
from incremental_jsonl_isolation import (  # noqa: E402
    install_network_denial,
    install_service_denial,
)


def main() -> int:
    install_network_denial()
    install_service_denial()
    command = sys.argv[1]
    if command == "probe":
        grant = decode_grant(os.environ["CONVMEM_CANARY_GRANT"])
        digest = os.environ["CONVMEM_CANARY_GRANT_SHA256"]
        revision = os.environ["CONVMEM_CANARY_REVISION"]
        validate_grant(grant, expected_sha256=digest, code_revision=revision)
        root = Path(grant.evidence_dir).parent
        boundary = ProductionCanaryBoundary.from_grant(grant, root=root)
        write_canary_overlay(boundary)
        descriptor, stat_result = boundary.open_source_readonly()
        os.close(descriptor)
        print(
            json.dumps(
                {
                    "root": str(boundary.root),
                    "source_size": stat_result.st_size,
                    "overlay": boundary.grant.config_overlay,
                }
            )
        )
        return 0
    if command == "run":
        grant = decode_grant(os.environ["CONVMEM_CANARY_GRANT"])
        digest = os.environ["CONVMEM_CANARY_GRANT_SHA256"]
        revision = os.environ["CONVMEM_CANARY_REVISION"]
        validate_grant(grant, expected_sha256=digest, code_revision=revision)
        root = Path(grant.evidence_dir).parent
        boundary = ProductionCanaryBoundary.from_grant(grant, root=root)
        write_canary_overlay(boundary)
        consume_nonce(boundary.root, grant, expected_sha256=digest)
        selector = os.environ.get("CONVMEM_CANARY_FAULT", "")
        fault_point = fault_point_for_selector(selector) if selector else ""
        crash = False

        def fault(name: str) -> None:
            nonlocal crash
            if fault_point and name == fault_point:
                crash = True
                os._exit(CRASH_EXIT)

        from tests.incremental_jsonl_helpers import install_fakes  # noqa: PLC0415

        import pytest

        with pytest.MonkeyPatch.context() as mp:
            install_fakes(mp)
            with install_call_budget_guard(grant.call_ceilings["whole_run"]) as guard:
                coordinator = canary_coordinator(
                    boundary,
                    grant.source.path,
                    fault=fault if fault_point else None,
                    counters=guard.counts,
                )
                with canary_writer_scope(boundary):
                    result = coordinator.run()
        if crash:
            os._exit(CRASH_EXIT)
        print(
            json.dumps(
                {
                    "run": {
                        "outcome": result.outcome,
                        "reused_artifacts": result.reused_artifacts,
                    },
                    "counters": guard.counts.as_dict(),
                }
            )
        )
        return 0
    if command == "refuse-network":
        import socket

        try:
            socket.create_connection(("203.0.113.1", 9), timeout=0.01)
            print(json.dumps({"network": "unexpected-success"}))
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"network": type(exc).__name__}))
        return 0
    raise CanaryRefused("canary_worker_command", f"unknown worker command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
