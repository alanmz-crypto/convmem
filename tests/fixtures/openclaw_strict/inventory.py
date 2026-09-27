"""Runtime prefix inventory and hash verification."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from constants import EXPECTED_TEST_RUNTIME_TREE_SHA256  # pylint: disable=E0401  # fixture path-injection import; module resolved via sys.path


def _mode_octal(st_mode: int) -> str:
    return f"{st_mode & 0o7777:04o}"


def inventory_runtime_tree(runtime_root: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    root = runtime_root.resolve()
    if not root.is_dir():
        raise SystemExit(f"runtime_root_missing:{root}")
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in list(dirnames) + list(filenames):
            p = Path(dirpath) / name
            if p.is_symlink():
                raise SystemExit(f"runtime_symlink_forbidden:{p.relative_to(root).as_posix()}")
        for name in filenames:
            p = Path(dirpath) / name
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            mode = _mode_octal(p.stat().st_mode)
            entries.append({"mode": mode, "path": rel, "sha256": f"sha256:{digest}"})
    entries.sort(key=lambda e: e["path"])
    return entries


def tree_sha256(entries: list[dict[str, str]]) -> str:
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def verify_runtime_tree(
    runtime_root: Path,
    expected: str = EXPECTED_TEST_RUNTIME_TREE_SHA256,
) -> dict[str, Any]:
    entries = inventory_runtime_tree(runtime_root)
    digest = tree_sha256(entries)
    if digest != expected:
        raise SystemExit(f"runtime_tree_hash_mismatch:got={digest}:expected={expected}:files={len(entries)}")
    writable = [e["path"] for e in entries if int(e["mode"], 8) & 0o222]
    if writable:
        raise SystemExit(f"runtime_writable_paths:{writable[:5]}")
    return {
        "test_runtime_tree_sha256": digest,
        "regular_file_count": len(entries),
        "symlink_count": 0,
        "writable_path_count": 0,
        "entries": entries,
    }
