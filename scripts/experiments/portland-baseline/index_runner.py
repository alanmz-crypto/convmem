#!/usr/bin/env python3
"""Pinned-cwd ConvMem indexing for Portland baseline experiment harness."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

# Stable cwd for all harness subprocesses that invoke convmem CLI.
INDEX_CWD = Path.home() / "Projects" / "convmem"


def index_file(
    *,
    config_path: str | Path,
    source_path: str | Path,
    cwd: str | Path | None = None,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    """Index one source file into an isolated corpus using a pinned working directory."""
    workdir = Path(cwd or INDEX_CWD).resolve()
    if not workdir.is_dir():
        raise FileNotFoundError(f"index cwd does not exist: {workdir}")
    env = os.environ.copy()
    env["CONVMEM_CONFIG"] = str(Path(config_path).resolve())
    return subprocess.run(
        ["convmem", "index", "--file", str(Path(source_path).resolve())],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(workdir),
        timeout=timeout,
        check=False,
    )
