#!/usr/bin/env bash
# Arc #286 — read-only production boundary snapshot (metadata only; no transcript bodies).
set -euo pipefail
OUT="${1:-/tmp/issue-286-boundary-snapshot.json}"
python3 - "$OUT" <<'INNER'
import hashlib
import json
import os
import sys
from pathlib import Path

out = Path(sys.argv[1])
real = Path(os.environ.get("CONVMEM_TEST_REAL_HOME") or os.environ["HOME"]).expanduser().resolve()
paths = [
    real / ".config/convmem/config.toml",
    real / ".local/share/convmem",
    real / ".codex/sessions",
    real / ".kiro/sessions",
    real / ".local/share/convmem/synthesis_failures.jsonl",
]

def meta(p: Path):
    if not p.exists():
        return {"path": str(p), "exists": False}
    st = p.lstat()
    row = {
        "path": str(p),
        "exists": True,
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
        "is_symlink": p.is_symlink(),
    }
    if p.is_file() and not p.is_symlink():
        row["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    return row

payload = {"real_home": str(real), "entries": [meta(p) for p in paths]}
codex = real / ".codex/sessions"
inv = []

def on_walk_error(exc: OSError) -> None:
    raise exc

if codex.is_dir():
    for dirpath, dirnames, filenames in os.walk(codex, topdown=True, onerror=on_walk_error, followlinks=False):
        base = Path(dirpath)
        for name in sorted(dirnames):
            entry = base / name
            st = entry.lstat()
            inv.append(
                {
                    "path": str(entry.relative_to(codex)),
                    "kind": "symlink" if entry.is_symlink() else "dir",
                    "size": st.st_size,
                    "mtime_ns": st.st_mtime_ns,
                }
            )
        for name in sorted(filenames):
            entry = base / name
            st = entry.lstat()
            inv.append(
                {
                    "path": str(entry.relative_to(codex)),
                    "kind": "symlink" if entry.is_symlink() else "file",
                    "size": st.st_size,
                    "mtime_ns": st.st_mtime_ns,
                }
            )
    inv.sort(key=lambda row: row["path"])
payload["codex_sessions_inventory"] = inv
digest_src = json.dumps(inv, sort_keys=True, separators=(",", ":"))
payload["codex_sessions_inventory_digest"] = hashlib.sha256(digest_src.encode()).hexdigest()
payload["codex_sessions_inventory_count"] = len(inv)
out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(out)
INNER
