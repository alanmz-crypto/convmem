"""CLI subprocess checks for expand command registration."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_expand_help_via_convmem_py_subprocess() -> None:
    """Expand must register before ``convmem.py`` runs ``main()`` as __main__."""
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "convmem.py"), "expand", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "expand" in (proc.stdout + proc.stderr).lower()
