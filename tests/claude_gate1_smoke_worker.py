"""Subprocess worker for hermetic Claude Gate 1 ``index --file`` smoke."""

# pylint: disable=wrong-import-position,broad-exception-caught,duplicate-code

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from claude_gate1_smoke import (  # noqa: E402
    assert_transcript_under_claude_projects,
    run_hermetic_index_cli,
    validate_output_containment,
)
from incremental_jsonl_isolation import (  # noqa: E402
    IsolationBoundary,
    IsolationViolation,
    install_network_denial,
)

_SITE = os.environ.get("CONVMEM_INCREMENTAL_SITE", "")
if _SITE:
    sys.path.append(_SITE)


def _emit(payload: dict) -> None:
    print(json.dumps(payload, sort_keys=True), flush=True)


def _run_index(transcript: Path) -> int:
    boundary = IsolationBoundary.from_environment()
    install_network_denial()
    preflight = validate_output_containment(boundary)
    resolved = boundary.resolve_mutable(transcript, label="claude transcript")
    assert_transcript_under_claude_projects(resolved, Path(os.environ["HOME"]))
    from adapters.detect import detect_format  # noqa: PLC0415

    fmt = detect_format(resolved)
    if fmt != "jsonl_claude_session":
        raise IsolationViolation(f"unexpected format for synthetic fixture: {fmt}")
    exit_code, stats, _stdout = run_hermetic_index_cli(
        resolved,
        preflight=preflight,
    )
    _emit(
        {
            "exit_code": exit_code,
            "format_name": fmt,
            "files_processed": stats["files_processed"],
            "files_skipped": stats["files_skipped"],
            "chunks_indexed": stats["chunks_indexed"],
            "units_indexed": stats["units_indexed"],
            "scratch_root": str(boundary.root),
            "config_path": str(boundary.layout["user_config"]),
        }
    )
    return exit_code


def _probe_neighbor(transcript: Path) -> int:
    boundary = IsolationBoundary.from_environment()
    install_network_denial()
    resolved = boundary.resolve_mutable(transcript, label="neighbor fixture")
    from adapters.detect import detect_format  # noqa: PLC0415

    _emit({"format_name": detect_format(resolved)})
    return 0


def main() -> int:
    command = sys.argv[1]
    target = Path(sys.argv[2])
    if command == "run":
        return _run_index(target)
    if command == "probe":
        return _probe_neighbor(target)
    raise ValueError(f"unknown command: {command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IsolationViolation as exc:
        _emit({"error": type(exc).__name__, "detail": str(exc)})
        raise SystemExit(74) from exc
