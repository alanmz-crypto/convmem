"""Scratch mount type probes shared by D1 and exposure e2e harnesses."""

from __future__ import annotations

import subprocess
from pathlib import Path


def scratch_filesystem_type(scratch_dir: Path, *, timeout: float = 10.0) -> str:
    """Return findmnt FSTYPE for *scratch_dir*, or raise on probe failure."""
    mount = subprocess.run(
        ["findmnt", "-n", "-o", "FSTYPE", "-T", str(scratch_dir)],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return mount.stdout.strip()
