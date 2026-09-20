"""Subprocess entrypoint for hermetic Claude incremental canary tests."""

# pylint: disable=wrong-import-position,broad-exception-caught,duplicate-code

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from claude_incremental_canary import (  # noqa: E402
    CRASH_EXIT,
    _CAPTURE_TRANSITIONS,
    _hermetic_gate0_hooks,
    capture_source,
    gate0,
    require_gate0_authority,
    run_coordinator,
    run_hermetic_matrix,
    validate_frozen_source,
)
from incremental_jsonl_isolation import (  # noqa: E402
    IsolationBoundary,
    IsolationViolation,
    install_network_denial,
)


def _boundary() -> IsolationBoundary:
    return IsolationBoundary.from_environment()


def _frozen_spec(source: Path):
    from claude_incremental_canary import FrozenSourceSpec
    import hashlib

    data = source.read_bytes()
    return FrozenSourceSpec(
        alias=source.stem,
        path=source,
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
    )


def _require_gate0(boundary) -> None:
    require_gate0_authority(boundary, hooks=_hermetic_gate0_hooks())


def main() -> int:
    install_network_denial()
    command = sys.argv[1]
    boundary = _boundary()
    if command == "gate0":
        report = gate0(hooks=_hermetic_gate0_hooks())
        print(json.dumps(report, sort_keys=True))
        return 0
    _require_gate0(boundary)
    if command == "refuse-network":
        import socket

        try:
            socket.create_connection(("203.0.113.1", 9), timeout=0.01)
            print(json.dumps({"network": "unexpected-success"}))
        except IsolationViolation:
            print(json.dumps({"network": "IsolationViolation"}))
        except OSError as exc:
            print(json.dumps({"network": type(exc).__name__}))
        return 0
    if command == "validate-source":
        source = boundary.resolve_mutable(sys.argv[2], label="canary source")
        spec = _frozen_spec(source)
        validate_frozen_source(spec)
        print(json.dumps({"validated": True, "alias": spec.alias}))
        return 0
    if command == "capture":
        source = boundary.resolve_mutable(sys.argv[2], label="canary source")
        spec = _frozen_spec(source)
        fault_name = os.environ.get("CONVMEM_CLAUDE_CANARY_FAULT", "")
        events: list[str] = []

        def fault(name: str) -> None:
            events.append(name)
            if fault_name and name == fault_name:
                raise SystemExit(CRASH_EXIT)

        descriptor = capture_source(boundary, spec, fault=fault)
        print(
            json.dumps(
                {
                    "descriptor": descriptor.__dict__,
                    "events": events,
                },
                sort_keys=True,
            )
        )
        return 0
    if command == "matrix":
        source = boundary.resolve_mutable(sys.argv[2], label="canary source")
        payload = run_hermetic_matrix(boundary, source)
        print(json.dumps(payload, sort_keys=True))
        return 0
    if command == "run":
        source = boundary.resolve_mutable(sys.argv[2], label="canary source")
        payload = run_coordinator(boundary, source)
        print(json.dumps(payload, sort_keys=True))
        return 0
    if command == "capture-transitions":
        print(json.dumps({"transitions": list(_CAPTURE_TRANSITIONS)}, sort_keys=True))
        return 0
    print(json.dumps({"error": "unknown-command", "command": command}), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IsolationViolation as exc:
        print(json.dumps({"error": "IsolationViolation", "detail": str(exc)}))
        raise SystemExit(74) from exc
