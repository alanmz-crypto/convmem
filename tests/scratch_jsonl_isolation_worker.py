"""Subprocess entrypoint for the scratch isolation executable gate."""

# pylint: disable=wrong-import-position,broad-exception-caught,consider-using-with

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# First repository import: stdlib-only bootstrap, before any ConvMem adapter.
from scratch_jsonl_prototype.isolation import (  # noqa: E402
    ScratchBoundary,
    ScratchPidLock,
    install_network_denial,
)


def main() -> int:
    boundary = ScratchBoundary.from_environment()
    install_network_denial()
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
        print(
            json.dumps(
                {
                    "root": str(boundary.root),
                    "format": fmt,
                    "parser": getattr(parser, "__module__", None),
                    "network": network,
                    "cwd": os.getcwd(),
                    "fd_targets": [
                        target
                        for name in os.listdir("/proc/self/fd")
                        for target in (
                            (
                                os.readlink(f"/proc/self/fd/{name}")
                                if os.path.lexists(f"/proc/self/fd/{name}")
                                else ""
                            ),
                        )
                        if target
                    ],
                }
            ),
            flush=True,
        )
        return 0
    if command == "crash-with-child":
        lock = ScratchPidLock(boundary, "locks/worker.lock")
        lock.acquire()
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(300)"],
            close_fds=True,
        )
        print(json.dumps({"child_pid": child.pid, "lock": str(lock.path)}), flush=True)
        os._exit(73)
    if command == "run":
        from scratch_jsonl_prototype.engine import (  # noqa: PLC0415
            ScratchIncrementalJsonl,
            evidence_dict,
        )

        source = boundary.resolve_mutable(sys.argv[2], label="source fixture")
        fingerprint = sys.argv[3]
        fault_point = sys.argv[4] if len(sys.argv) > 4 else ""

        def abrupt(point: str) -> None:
            if point == fault_point:
                os._exit(86)

        engine = ScratchIncrementalJsonl(
            boundary,
            source,
            transform_fingerprint=fingerprint,
            fault=abrupt,
        )
        run = engine.run()
        print(
            json.dumps(
                {
                    "run": evidence_dict(run),
                    "projection": engine.active_projection(),
                    "checkpoint": engine.checkpoint(),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 0
    if command == "chroma-run":
        install_network_denial()
        from scratch_jsonl_prototype.chroma_projection import ScratchChromaProjection  # noqa: PLC0415
        source = boundary.resolve_mutable(sys.argv[2], label="source fixture")
        projection = ScratchChromaProjection(boundary, source_path=source)
        projection.upsert([{"id": "worker-row", "document": "worker", "metadata": {}}], "worker-generation")
        print(json.dumps(projection.authority(), sort_keys=True, default=lambda value: value.tolist()), flush=True)
        return 0
    raise ValueError(f"unknown command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
