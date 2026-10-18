#!/usr/bin/env python3
"""Read-only production metadata snapshot (Arc #286 boundary evidence)."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path


def _real_home() -> Path:
    raw = os.environ.get("CONVMEM_TEST_REAL_HOME") or os.environ.get("HOME", "/")
    return Path(raw).expanduser().resolve()


def _file_meta(path: Path) -> dict:
    if not path.exists():
        return {"path": str(path), "exists": False}
    st = path.lstat()
    row = {
        "path": str(path),
        "exists": True,
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
        "is_symlink": path.is_symlink(),
    }
    if path.is_file() and not path.is_symlink():
        row["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return row


def _sessions_metadata(codex: Path) -> list[list[object]]:
    rows: list[list[object]] = []
    if not codex.is_dir():
        return rows

    def onerror(exc: OSError) -> None:
        raise exc

    for dirpath, dirnames, filenames in os.walk(codex, topdown=True, onerror=onerror, followlinks=False):
        base = Path(dirpath)
        rel_dir = "." if base == codex else str(base.relative_to(codex))
        if rel_dir != ".":
            st = base.lstat()
            rows.append([rel_dir, st.st_ino, st.st_size, st.st_mtime_ns, st.st_dev])
        for name in sorted(dirnames):
            entry = base / name
            st = entry.lstat()
            rel = str(entry.relative_to(codex))
            rows.append([rel, st.st_ino, st.st_size, st.st_mtime_ns, st.st_dev])
        for name in sorted(filenames):
            entry = base / name
            st = entry.lstat()
            rel = str(entry.relative_to(codex))
            rows.append([rel, st.st_ino, st.st_size, st.st_mtime_ns, st.st_dev])
    rows.sort(key=lambda item: str(item[0]))
    return rows


def capture(out_path: Path) -> dict:
    real = _real_home()
    config_path = real / ".config" / "convmem" / "config.toml"
    synthesis_path = real / ".local" / "share" / "convmem" / "synthesis_failures.jsonl"
    codex = real / ".codex" / "sessions"
    config_row = _file_meta(config_path)
    synthesis_row = _file_meta(synthesis_path)
    sessions_metadata = _sessions_metadata(codex)
    digest_src = json.dumps(sessions_metadata, separators=(",", ":"), sort_keys=True)
    payload = {
        "captured_ns": time.time_ns(),
        "config": {
            "mtime_ns": config_row.get("mtime_ns"),
            "sha256": config_row.get("sha256"),
            "size": config_row.get("size"),
        },
        "synthesis_failures": {
            "mtime_ns": synthesis_row.get("mtime_ns"),
            "sha256": synthesis_row.get("sha256"),
            "size": synthesis_row.get("size"),
        },
        "sessions_metadata": sessions_metadata,
        "sessions_metadata_sha256": hashlib.sha256(digest_src.encode()).hexdigest(),
        "sessions_entries": len(sessions_metadata),
    }
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/issue-286-snapshot.json")
    payload = capture(out)
    print(json.dumps({"path": str(out), "sessions_entries": payload["sessions_entries"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
