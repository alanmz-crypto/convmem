"""Subprocess writer for tests/test_chroma_write_guard.py (not collected by pytest).

Usage: python tests/_chroma_write_guard_worker.py MODE CHROMA_DIR START COUNT [GATE] [--guard]

Modes:
  write      write COUNT summaries starting at id START, one guarded call each
  hold       open the store and load the index, wait for GATE to exist, then write
  loop       write forever from START (a kill target)
"""

from __future__ import annotations

import hashlib
import os
import random
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
if os.environ.get("SAFE_HARBOR_T3_BOOTSTRAPPED") == "1":
    from tests._safe_harbor_bootstrap import require_t3_bootstrap, validate_chroma_argv_path

    require_t3_bootstrap()
    _fixture_root = os.environ.get("SAFE_HARBOR_T3_FIXTURE_ROOT", "").strip()
    _fixture = Path(_fixture_root).expanduser() if _fixture_root else None
    if __name__ == "__main__":
        if len(sys.argv) < 3:
            raise RuntimeError("missing synthetic Chroma path")
        validate_chroma_argv_path(sys.argv[2], fixture_root=_fixture)
else:
    validate_chroma_argv_path = None  # type: ignore[assignment,misc]
    _fixture = None

from chroma_store import ChromaStore  # pylint: disable=wrong-import-position
from chroma_write_guard import ChromaWriteGuard  # pylint: disable=wrong-import-position

DIM = 16


def embedding(uid: str) -> list[float]:
    seed = int.from_bytes(hashlib.sha256(uid.encode()).digest()[:8], "little")
    rng = random.Random(seed)
    return [rng.random() - 0.5 for _ in range(DIM)]


def write_one(store: ChromaStore, index: int) -> None:
    uid = f"s{index}"
    store.add_summary(uid, f"summary {uid}", embedding(uid), {"source_path": "/fixture", "n": index})


def main() -> None:
    mode, root, start, count = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    if validate_chroma_argv_path is not None:
        validate_chroma_argv_path(root, fixture_root=_fixture)
    guarded = "--guard" in sys.argv
    gate = sys.argv[5] if len(sys.argv) > 5 and not sys.argv[5].startswith("--") else None
    store = ChromaStore(root, write_guard=ChromaWriteGuard(root) if guarded else None)
    try:
        if mode == "hold":
            store.query_summaries(embedding("s0"), 1)  # load the HNSW into this process
            print("holding", flush=True)
            while gate and not Path(gate).exists():
                time.sleep(0.02)
        if mode == "loop":
            index = start
            while True:
                write_one(store, index)
                print(index, flush=True)
                index += 1
        for index in range(start, start + count):
            write_one(store, index)
        print("done", flush=True)
    finally:
        store.close()


if __name__ == "__main__":
    main()
