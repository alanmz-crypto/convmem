"""Isolated process-kill worker; fault hooks exist only in this test file."""
# pylint: disable=protected-access,wrong-import-position
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests._safe_harbor_bootstrap import require_t3_bootstrap, validate_chroma_argv_path
require_t3_bootstrap()
FIXTURE = Path(os.environ["SAFE_HARBOR_T3_FIXTURE_ROOT"])
if len(sys.argv) != 6:
    raise SystemExit("usage: worker ACTION CHROMA PHASE READY RELEASE")
ACTION, RAW_CHROMA, PHASE, RAW_READY, RAW_RELEASE = sys.argv[1:]
CHROMA, READY, RELEASE = [
    validate_chroma_argv_path(raw, fixture_root=FIXTURE)
    for raw in (RAW_CHROMA, RAW_READY, RAW_RELEASE)
]

import chroma_write_guard as cwg


def barrier() -> None:
    """Parent kills only after the actual boundary has been reached."""
    READY.write_text(PHASE, encoding="utf-8")
    deadline = time.monotonic() + 30
    while not RELEASE.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError(f"parent did not release {PHASE}")
        time.sleep(0.01)


def wrap_method(name: str, *, before: bool = False) -> None:
    original = getattr(cwg.ChromaWriteGuard, name)

    def wrapped(self, *args, **kwargs):
        if before:
            barrier()
        result = original(self, *args, **kwargs)
        if not before:
            barrier()
        return result

    setattr(cwg.ChromaWriteGuard, name, wrapped)


def install() -> None:
    methods = {
        "before_preservation_io": ("_ensure_preservation_complete", True),
        "after_manifest_before_bind": ("_bind_preservation_to_incident", True),
        "after_preservation_bind": ("_bind_preservation_to_incident", False),
        "after_disposition_before_marker_removal": ("_remove_quarantine_marker_durable", True),
        "after_marker_removal": ("_remove_quarantine_marker_durable", False),
    }
    if PHASE in methods:
        method, before = methods[PHASE]
        wrap_method(method, before=before)
        return
    if PHASE == "after_first_copy":
        original_copy = cwg._copy_durable

        def copy(src, dst):
            original_copy(src, dst)
            if dst.parent.name == "originals":
                barrier()

        cwg._copy_durable = copy
        return
    if PHASE == "after_first_replacement":
        original_replace = os.replace

        def replace(src, dst):
            original_replace(src, dst)
            if str(src).endswith(".guard-restore"):
                barrier()

        os.replace = replace
        return
    raise ValueError(f"unknown phase {PHASE}")


def main() -> None:
    install()
    guard = cwg.ChromaWriteGuard(CHROMA)
    if ACTION == "restore":
        cwg.recover(CHROMA)
    elif ACTION == "release":
        view = guard.read_authority()
        assert view.document is not None
        guard.release_quarantine(
            disposition_ref="isolated-owner-disposition",
            authority_digest=cwg.authority_submission_digest(view.document),
        )
    else:
        raise ValueError(f"unknown action {ACTION}")
    raise AssertionError("operation returned without reaching its kill boundary")


if __name__ == "__main__":
    main()
