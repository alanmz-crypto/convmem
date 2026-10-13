"""Shared fixtures; callers must enter through the isolated launcher."""
# pylint: disable=protected-access,wrong-import-position,ungrouped-imports
from __future__ import annotations

import signal
import subprocess
import sys
import time
from pathlib import Path

from tests._safe_harbor_bootstrap import require_t3_bootstrap
require_t3_bootstrap()
from chroma_write_guard import ChromaWriteGuard, ChromaWriteQuarantinedError, recover
from tests.test_chroma_write_guard import _make_store, _segment, _set_header_count, _worker

ROOT = Path(__file__).resolve().parents[1]
FAULT_WORKER = ROOT / "tests" / "_safe_harbor_t3_fault_worker.py"


def segment_file_bytes_snapshot(seg: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in seg.iterdir() if p.is_file()}


def tear_and_trigger_restore(tmp_path: Path) -> tuple[Path, ChromaWriteGuard]:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 50)
    guard = ChromaWriteGuard(chroma)
    try:
        recover(chroma)
    except ChromaWriteQuarantinedError:
        pass
    else:
        raise AssertionError("a completed restore must remain quarantined")
    assert guard.quarantine_state()["incidents"][0]["repair"]["status"] == "complete"
    return chroma, guard


def kill_worker_at_barrier(chroma: Path, *, phase: str, ready: Path, release: Path,
                           timeout: float = 25.0) -> None:
    action = "release" if phase in {"after_disposition_before_marker_removal", "after_marker_removal"} else "restore"
    command = [sys.executable, "-s", "-B", str(FAULT_WORKER), action, str(chroma), phase, str(ready), str(release)]
    with subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
        try:
            deadline = time.monotonic() + timeout
            while not ready.exists() and proc.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            reached = ready.exists()
            if proc.poll() is None:
                proc.kill()
            out, err = proc.communicate(timeout=10)
            assert reached, f"boundary {phase} not reached: {out} {err}"
            assert ready.read_text() == phase
            assert proc.returncode == -signal.SIGKILL, (proc.returncode, out, err)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)
