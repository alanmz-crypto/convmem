"""Subprocess entrypoint for hermetic Claude incremental canary tests."""

# pylint: disable=wrong-import-position,broad-exception-caught,duplicate-code

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from claude_incremental_canary import (  # noqa: E402
    CANARY_INTERNAL_ROOT,
    CRASH_EXIT,
    PublicationDurability,
    _CAPTURE_TRANSITIONS,
    _build_gate0_evidence,
    _granted_source_relative,
    capture_source,
    run_coordinator,
    validate_frozen_source,
)
from incremental_jsonl_isolation import (  # noqa: E402
    ISOLATION_ROOT_ENV,
    IsolationBoundary,
    IsolationViolation,
    install_network_denial,
    known_production_roots,
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


def _assert_stdio_pipes() -> None:
    for fd in (1, 2):
        mode = os.fstat(fd).st_mode
        if not stat.S_ISFIFO(mode):
            raise IsolationViolation("worker stdio is not a pipe")


def _assert_namespace_paths(alias: str | None = None) -> None:
    root = os.environ.get(ISOLATION_ROOT_ENV, "")
    if root != CANARY_INTERNAL_ROOT:
        raise IsolationViolation("isolation root is not the namespace path")
    if not Path(CANARY_INTERNAL_ROOT).is_dir():
        raise IsolationViolation("namespace root missing")
    config = Path(f"{CANARY_INTERNAL_ROOT}/home/.config/convmem/config.toml")
    if not config.is_file():
        raise IsolationViolation("namespace config missing")
    if alias:
        granted = Path(f"{CANARY_INTERNAL_ROOT}/{_granted_source_relative(alias)}")
        if not granted.is_file():
            raise IsolationViolation("granted source missing in namespace")
    for path in (
        Path("/home/lauer/.local/share/convmem"),
        Path("/home/lauer/.config/convmem"),
        Path("/home/lauer/.kiro"),
    ):
        if path.exists():
            raise IsolationViolation("host production root visible in namespace")


def _mountinfo_sensitive_strings() -> tuple[str, ...]:
    strings: list[str] = []
    mountinfo = Path("/proc/self/mountinfo")
    if mountinfo.is_file():
        for line in mountinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            for token in line.split():
                if token.endswith(".jsonl") and len(token) == 33:
                    strings.append(token[:-6])
                if "convmem-claude-gate2" in token or "convmem-jsonl-prod" in token:
                    strings.append(token)
    return tuple(dict.fromkeys(strings))


def _scrub_mountinfo_leaks(text: str) -> str:
    for token in _mountinfo_sensitive_strings():
        if token and token in text:
            raise IsolationViolation("mountinfo leak in worker output")
    return text


def main() -> int:
    install_network_denial()
    _assert_stdio_pipes()
    forced = os.environ.get("CONVMEM_CLAUDE_CANARY_FORCE_EXIT", "")
    if forced:
        raise SystemExit(int(forced))
    command = sys.argv[1]
    boundary = _boundary()
    alias = None
    if len(sys.argv) > 2:
        alias = Path(sys.argv[2]).stem
    _assert_namespace_paths(alias)
    if command == "verify-pipes":
        print(json.dumps({"pipes": True}, sort_keys=True))
        return 0
    if command == "gate0":
        evidence = _build_gate0_evidence()
        print(_scrub_mountinfo_leaks(json.dumps(evidence.to_mapping(), sort_keys=True)))
        return 0
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
        data = validate_frozen_source(spec)
        st = source.stat()
        from adapters.claude_session_jsonl import parse_complete_prefix
        import hashlib

        view = parse_complete_prefix(str(source), raw=data)
        descriptor = {
            "alias": spec.alias,
            "relative_path": _granted_source_relative(spec.alias),
            "device": int(st.st_dev),
            "inode": int(st.st_ino),
            "size": int(st.st_size),
            "complete_boundary": view.complete_boundary,
            "prefix_sha256": view.prefix_sha256,
            "sha256": hashlib.sha256(view.raw_prefix).hexdigest(),
            "physical_lines": view.raw_prefix.count(b"\n"),
            "durability": str(PublicationDurability.CONFIRMED),
        }
        print(
            _scrub_mountinfo_leaks(
                json.dumps(
                    {
                        "descriptor": descriptor,
                        "events": list(_CAPTURE_TRANSITIONS),
                    },
                    sort_keys=True,
                )
            )
        )
        return 0
    if command == "matrix":
        source = boundary.resolve_mutable(sys.argv[2], label="canary source")
        payload = run_coordinator(boundary, source)
        print(_scrub_mountinfo_leaks(json.dumps(payload, sort_keys=True)))
        return 0
    if command == "run":
        source = boundary.resolve_mutable(sys.argv[2], label="canary source")
        payload = run_coordinator(boundary, source)
        print(_scrub_mountinfo_leaks(json.dumps(payload, sort_keys=True)))
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
