"""Subprocess entrypoint for the production-integration isolation gate."""

# pylint: disable=wrong-import-position,broad-exception-caught,consider-using-with,line-too-long

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from incremental_jsonl_isolation import (  # noqa: E402
    ISOLATION_ENV_ALLOWLIST,
    IsolationBoundary,
    IsolationViolation,
    SourceAdvisoryLock,
    install_network_denial,
    install_service_denial,
)

_SITE = os.environ.get("CONVMEM_INCREMENTAL_SITE", "")
if _SITE:
    sys.path.append(_SITE)


def _fd_targets() -> list[str]:
    targets: list[str] = []
    for name in os.listdir("/proc/self/fd"):
        path = f"/proc/self/fd/{name}"
        if os.path.lexists(path):
            try:
                targets.append(os.readlink(path))
            except OSError:
                continue
    return targets


def main() -> int:
    service_log: list[str] = []
    boundary = IsolationBoundary.from_environment()
    install_network_denial()
    install_service_denial(service_log)
    command = sys.argv[1]
    if command == "probe":
        from adapters.detect import detect_format, get_parser  # noqa: PLC0415

        source = boundary.resolve_mutable(sys.argv[2], label="source fixture")
        fmt = detect_format(source)
        parser = get_parser(source)
        try:
            import socket

            socket.create_connection(("203.0.113.1", 9), timeout=0.01)
            network = "unexpected-success"
        except Exception as exc:  # noqa: BLE001
            network = type(exc).__name__
        watcher = "denied"
        try:
            subprocess.Popen(["convmem-watch", "--once"])  # noqa: S603
            watcher = "unexpected-success"
        except IsolationViolation:
            watcher = "IsolationViolation"
        print(
            json.dumps(
                {
                    "root": str(boundary.root),
                    "format": fmt,
                    "parser": getattr(parser, "__module__", None),
                    "network": network,
                    "watcher": watcher,
                    "cwd": os.getcwd(),
                    "fd_targets": _fd_targets(),
                    "home": os.environ.get("HOME"),
                    "xdg_config": os.environ.get("XDG_CONFIG_HOME"),
                    "service_log": service_log,
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
    if command == "crash-with-child":
        lock = SourceAdvisoryLock(boundary, "locks/worker.lock")
        lock.acquire()
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(300)"],
            close_fds=True,
        )
        print(
            json.dumps({"child_pid": child.pid, "lock": str(lock.path)}),
            flush=True,
        )
        os._exit(73)
    if command == "run":
        import ingest  # noqa: PLC0415
        from incremental_jsonl import IncrementalJsonlCoordinator  # noqa: PLC0415

        source = boundary.resolve_mutable(sys.argv[2], label="source fixture")
        enabled = sys.argv[3] == "1"
        fault_point = sys.argv[4] if len(sys.argv) > 4 else ""

        def fake_summarize(text, **_kwargs):
            return f"summary:{hashlib.sha256(text.encode()).hexdigest()[:16]}"

        def fake_embed(text, **_kwargs):
            digest = hashlib.sha256(text.encode()).digest()
            return [((digest[index] / 255.0) * 2.0) - 1.0 for index in range(8)]

        def fake_distill(text, **_kwargs):
            return [
                {
                    "type": "explanation",
                    "title": f"Isolated unit {text[:12]}",
                    "summary": "Reusable isolated knowledge unit for hermetic tests.",
                    "keywords": ["kiro", "jsonl", "incremental"],
                    "confidence": 0.95,
                    "domain": "general",
                }
            ]

        ingest.summarize = fake_summarize
        ingest.ollama_embed = fake_embed
        ingest.distill = fake_distill

        def abrupt(point: str) -> None:
            if point == fault_point:
                os._exit(86)

        coordinator = IncrementalJsonlCoordinator.from_isolated_boundary(
            boundary,
            source,
            enabled=enabled,
            fault=abrupt,
        )
        result = coordinator.run()
        checkpoint = None
        try:
            checkpoint = coordinator.checkpoint()
        except Exception:  # noqa: BLE001
            checkpoint = None
        print(
            json.dumps(
                {
                    "run": result.to_dict(),
                    "checkpoint": checkpoint,
                    "counters": result.counters.as_dict(),
                },
                sort_keys=True,
                default=str,
            ),
            flush=True,
        )
        return 0
    raise ValueError(f"unknown command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
