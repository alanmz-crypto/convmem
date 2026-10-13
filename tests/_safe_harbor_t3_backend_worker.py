"""Subprocess helper for tests/test_safe_harbor_t3_backend_proof.py (not collected).

Fresh processes exercise Chroma restart semantics without parent client caches.
The parent must set isolated HOME/XDG/CONVMEM/TMPDIR before spawning this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROD_HOME = Path("/home/lauer")


def _require_isolated() -> None:
    home = Path.home().resolve()
    if home == PROD_HOME:
        raise RuntimeError(f"refusing production HOME {home}")
    for key in (
        "CONVMEM_CONFIG",
        "CONVMEM_ROOT",
        "CONVMEM_RESTIC_ENV",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
        "RESTIC_CACHE_DIR",
        "TMPDIR",
    ):
        raw = os.environ.get(key, "")
        if not raw or not Path(raw).is_absolute():
            raise RuntimeError(f"refusing unset/relative {key}={raw!r}")
        resolved = Path(raw).resolve(strict=False)
        banned = [
            PROD_HOME / ".local/share/convmem",
            PROD_HOME / ".config/convmem",
            PROD_HOME / "Projects/convmem/.worktrees/runtime-main",
        ]
        for path in banned:
            if resolved == path or path in resolved.parents:
                raise RuntimeError(f"refusing production-overlapping {key}={resolved}")
    for secret in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        if secret in os.environ:
            raise RuntimeError(f"refusing inherited {secret}")


def _seq_id(value: Any) -> int:
    if isinstance(value, bytes):
        return int.from_bytes(value, "big")
    return int(value or 0)


def _embedding(seed: int) -> list[float]:
    digest = hashlib.sha256(f"safe-harbor-t3:{seed}".encode()).digest()
    return [((digest[i] % 200) - 100) / 100.0 for i in range(16)]


def _vector_segment_dir(chroma: Path) -> Path:
    for entry in chroma.iterdir():
        if entry.is_dir() and (entry / "header.bin").is_file():
            return entry
    raise FileNotFoundError(f"no vector segment under {chroma}")


def _sqlite_snapshot(chroma: Path, collection: str) -> dict[str, Any]:
    db = chroma / "chroma.sqlite3"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = con.execute("select id, name from collections where name = ?", (collection,)).fetchone()
        if not row:
            raise KeyError(f"collection {collection!r} missing")
        collection_id, _ = row
        scopes = dict(
            con.execute("select scope, id from segments where collection = ?", (collection_id,)).fetchall()
        )
        meta_seg, vec_seg = scopes.get("METADATA"), scopes.get("VECTOR")
        applied = {sid: _seq_id(seq) for sid, seq in con.execute("select segment_id, seq_id from max_seq_id")}
        floor = min(applied.get(meta_seg, 0), applied.get(vec_seg, 0))
        queue_len = con.execute("select count(*) from embeddings_queue").fetchone()[0]
        pending = con.execute(
            "select count(*) from embeddings_queue where topic like ? and seq_id > ?",
            (f"%/{collection_id}", floor),
        ).fetchone()[0]
        return {
            "collection_id": collection_id,
            "metadata_segment_id": meta_seg,
            "vector_segment_id": vec_seg,
            "metadata_watermark": applied.get(meta_seg, 0),
            "vector_watermark": applied.get(vec_seg, 0),
            "queue_total": queue_len,
            "queue_pending_after_floor": pending,
        }
    finally:
        con.close()


def _run_sequence(chroma: Path, collection: str) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    import chromadb  # pylint: disable=import-outside-toplevel

    client = chromadb.PersistentClient(path=str(chroma))
    col = client.get_or_create_collection(
        collection,
        configuration={"hnsw": {"space": "cosine", "sync_threshold": 3, "batch_size": 1}},
    )
    trace: list[dict[str, Any]] = []

    def step(label: str, fn) -> None:
        fn()
        trace.append({"step": label, "sqlite": _sqlite_snapshot(chroma, collection)})

    step(
        "add_a",
        lambda: col.upsert(
            ids=["a"],
            documents=["doc-a"],
            embeddings=[_embedding(1)],
            metadatas=[{"n": 1}],
        ),
    )
    step("update_metadata_a", lambda: col.update(ids=["a"], metadatas=[{"n": 2}]))
    step("update_embedding_a", lambda: col.update(ids=["a"], embeddings=[_embedding(99)]))
    step(
        "upsert_a",
        lambda: col.upsert(
            ids=["a"],
            documents=["doc-a2"],
            embeddings=[_embedding(100)],
            metadatas=[{"n": 3}],
        ),
    )
    step("delete_a", lambda: col.delete(ids=["a"]))
    step(
        "reinsert_a",
        lambda: col.upsert(
            ids=["a"],
            documents=["doc-a3"],
            embeddings=[_embedding(200)],
            metadatas=[{"n": 4}],
        ),
    )
    client.close()
    return {"trace": trace}


def _json_embedding(emb: Any) -> list[float] | None:
    if emb is None:
        return None
    if hasattr(emb, "tolist"):
        return [float(x) for x in emb.tolist()]
    return [float(x) for x in emb]


def _read_embeddings(chroma: Path, collection: str, ids: list[str]) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    import chromadb  # pylint: disable=import-outside-toplevel

    client = chromadb.PersistentClient(path=str(chroma))
    col = client.get_collection(collection)
    got = col.get(ids=ids, include=["embeddings", "metadatas"])
    out = {
        id_: {"embedding": _json_embedding(emb), "metadata": meta}
        for id_, emb, meta in zip(got["ids"], got["embeddings"], got["metadatas"], strict=True)
    }
    client.close()
    return out


def _restart_ping(chroma: Path, collection: str) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    import chromadb  # pylint: disable=import-outside-toplevel

    client = chromadb.PersistentClient(path=str(chroma))
    col = client.get_collection(collection)
    count = col.count()
    client.close()
    return {"count": count, "sqlite": _sqlite_snapshot(chroma, collection)}


def main() -> None:
    _require_isolated()
    mode = sys.argv[1]
    if mode == "sequence":
        chroma, collection, out = Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
        payload = _run_sequence(chroma, collection)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("ok", flush=True)
        return
    if mode == "observe":
        chroma, collection, out = Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
        payload = _sqlite_snapshot(chroma, collection)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("ok", flush=True)
        return
    if mode == "read_embeddings":
        chroma, collection, ids_json = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
        ids = json.loads(ids_json)
        print(json.dumps(_read_embeddings(chroma, collection, ids)), flush=True)
        return
    if mode == "restart_ping":
        chroma, collection = Path(sys.argv[2]), sys.argv[3]
        print(json.dumps(_restart_ping(chroma, collection)), flush=True)
        return
    raise SystemExit(f"unknown mode {mode!r}")


if __name__ == "__main__":
    main()
