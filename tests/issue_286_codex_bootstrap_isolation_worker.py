"""Subprocess entrypoint for Arc Codex #286 T1 hermetic verification."""

# pylint: disable=wrong-import-position,broad-exception-caught,consider-using-with

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from incremental_jsonl_isolation import (  # noqa: E402
    ISOLATION_ENV_ALLOWLIST,
    IsolationBoundary,
    IsolationViolation,
)

_SITE = os.environ.get("CONVMEM_INCREMENTAL_SITE", "")
if _SITE:
    sys.path.append(_SITE)


def _bootstrap_isolation() -> IsolationBoundary:
    return IsolationBoundary.from_environment()


def _probe_network() -> dict[str, object]:
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        sock.connect(("127.0.0.1", 9))
        return {"status": "unexpected-success", "errno": None}
    except OSError as exc:
        return {"status": "connect_failed", "errno": exc.errno}
    finally:
        sock.close()


def _probe_forbidden_filesystem(boundary: IsolationBoundary) -> str:
    if not boundary.forbidden_roots:
        return "no-forbidden-roots"
    target = boundary.forbidden_roots[0]
    try:
        boundary.resolve_mutable(target / "escape-probe", label="production escape probe")
        return "unexpected-success"
    except IsolationViolation:
        return "IsolationViolation"


def _probe_escape_root(boundary: IsolationBoundary) -> str:
    try:
        boundary.resolve_mutable(
            boundary.root / ".." / "outside-isolation",
            label="isolation root escape probe",
        )
        return "unexpected-success"
    except IsolationViolation:
        return "IsolationViolation"


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "boundary-probe":
        boundary = _bootstrap_isolation()
        print(
            json.dumps(
                {
                    "root": str(boundary.root),
                    "network": _probe_network(),
                    "forbidden_root": _probe_forbidden_filesystem(boundary),
                    "root_escape": _probe_escape_root(boundary),
                    "cwd": os.getcwd(),
                    "home": os.environ.get("HOME"),
                    "xdg_config": os.environ.get("XDG_CONFIG_HOME"),
                    "credential_names": [
                        name
                        for name in os.environ
                        if any(
                            marker in name.upper()
                            for marker in ("API_KEY", "SECRET", "PASSWORD", "CREDENTIAL")
                        )
                        and name != "CONVMEM_INCREMENTAL_TOKEN"
                    ],
                    "production_override_names": [
                        name
                        for name in os.environ
                        if name.startswith("CONVMEM_")
                        and name not in ISOLATION_ENV_ALLOWLIST
                    ],
                }
            ),
            flush=True,
        )
        return 0

    if command == "hash-oracle":
        boundary = _bootstrap_isolation()
        from tests.fixtures.issue_286_codex_bootstrap_v2_hash_oracle import (  # noqa: PLC0415
            build_oracle_grant,
        )

        grant = build_oracle_grant(boundary.root)
        print(
            json.dumps(
                {
                    "operation_id": grant["operation_id"],
                    "grant_fingerprint_v2": grant["grant_fingerprint_v2"],
                    "source_state_id": grant["source_state_id"],
                    "kiro_default_state_id": grant["kiro_default_state_id"],
                }
            ),
            flush=True,
        )
        return 0

    if command == "pytest":
        boundary = _bootstrap_isolation()
        failure_log = boundary.root / "logs" / "synthesis_failures.jsonl"
        failure_log.parent.mkdir(parents=True, exist_ok=True)
        import ingest  # noqa: PLC0415

        ingest._SYNTHESIS_FAIL_LOG = failure_log
        from bootstrap_codex_v2_owner import set_worker_isolation_boundary  # noqa: PLC0415

        set_worker_isolation_boundary(boundary)
        import pytest  # noqa: PLC0415

        basetemp = boundary.root / "pytest-tmp"
        basetemp.mkdir(parents=True, exist_ok=True)
        return int(pytest.main(["--basetemp", str(basetemp), *sys.argv[2:]]))

    raise SystemExit(f"unknown worker command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
