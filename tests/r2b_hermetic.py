"""Shared hermetic helpers for R2b capture-auth tests (no live eval-root writes)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval_corpus.r2b_capture_auth import bind_r2b_capture
from eval_corpus.run_manifest import (
    make_r2b_run_manifest_for_tests,
    write_approval_sidecar,
)


def write_json(path: Path, body: dict) -> Path:
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def r2b_eval_capture_dir(root: Path, run_id: str) -> Path:
    return root / ".local" / "share" / "convmem" / "eval" / run_id / "capture"


def r2b_auth_dir(root: Path, run_id: str) -> Path:
    return (
        root
        / ".local"
        / "share"
        / "convmem"
        / "authorizations"
        / "r2b"
        / run_id
    )


def create_chroma_fixture(
    chroma_dir: Path,
    records: list[dict],
    collection_name: str = "knowledge_units",
    collection_id: str = "test-coll-uuid",
) -> None:
    """Create a minimal Chroma SQLite fixture for testing."""
    chroma_dir.mkdir(parents=True, exist_ok=True)
    db = chroma_dir / "chroma.sqlite3"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE collections (id TEXT, name TEXT)")
    conn.execute(
        "CREATE TABLE segments (id TEXT, collection TEXT, scope TEXT)"
    )
    conn.execute(
        "CREATE TABLE embeddings "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, embedding_id TEXT, segment_id TEXT)"
    )
    conn.execute(
        "CREATE TABLE embedding_metadata "
        "(id INTEGER, key TEXT, string_value TEXT, bool_value INTEGER)"
    )
    conn.execute(
        "INSERT INTO collections VALUES (?, ?)",
        (collection_id, collection_name),
    )
    seg_id = "test-seg-uuid"
    conn.execute(
        "INSERT INTO segments VALUES (?, ?, ?)",
        (seg_id, collection_id, "METADATA"),
    )
    for rec in records:
        cur = conn.execute(
            "INSERT INTO embeddings (embedding_id, segment_id) VALUES (?, ?)",
            (rec["id"], seg_id),
        )
        row_id = cur.lastrowid
        if rec.get("document") is not None:
            conn.execute(
                "INSERT INTO embedding_metadata VALUES (?, ?, ?, ?)",
                (row_id, "chroma:document", rec["document"], None),
            )
        if rec.get("superseded"):
            conn.execute(
                "INSERT INTO embedding_metadata VALUES (?, ?, ?, ?)",
                (row_id, "superseded", None, 1),
            )
    conn.commit()
    conn.close()


def r2b_source_paths(
    root: Path, run_id: str = "test-r2b-run"
) -> dict[str, str]:
    """Create hermetic source + path strings with eval/auth root markers."""
    eval_base = r2b_eval_capture_dir(root, run_id)
    auth_base = r2b_auth_dir(root, run_id)
    export = root / "source" / "knowledge_units.jsonl"
    processed = root / "source" / "processed.json"
    chroma_dir = root / "source" / "chroma"

    for d in [eval_base.parent, auth_base, export.parent, chroma_dir]:
        d.mkdir(parents=True, exist_ok=True)

    export.write_text('{"id":"unit1"}\n', encoding="utf-8")
    processed.write_text("{}", encoding="utf-8")
    create_chroma_fixture(
        chroma_dir, [{"id": "unit1", "document": "doc text 1"}]
    )

    return {
        "export": str(export),
        "processed": str(processed),
        "capture_dir": str(eval_base),
        "chroma_dir": str(chroma_dir),
    }


def fresh_placeholder_snapshot() -> dict[str, Any]:
    """Synthetic snapshot for schema-only tests (not bound to real files)."""
    return {
        "export_sha256": "a" * 64,
        "processed_state": "present",
        "processed_sha256": "b" * 64,
        "chroma_collection_name": "knowledge_units",
        "chroma_collection_id": "test-coll-uuid",
        "chroma_extracted_unit_count": 5,
        "chroma_sorted_id_hash": "c" * 64,
        "chroma_capture_slice_sha256": "d" * 64,
        "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def trusted_snapshot_for_paths(
    paths: dict[str, str], *, include_processed: bool = True
) -> dict[str, Any]:
    """Recompute a trusted snapshot from hermetic source files."""
    # Late import: avoid pulling capture into the hermetic helper import graph.
    from eval_corpus.capture import recompute_source_snapshot

    export = Path(paths["export"])
    processed = Path(paths["processed"])
    chroma_dir = Path(paths["chroma_dir"])
    snap = recompute_source_snapshot(
        export=export, processed=processed, chroma_dir=chroma_dir
    )
    if not include_processed:
        snap["processed_state"] = "absent"
        snap["processed_sha256"] = None
    return snap


def capture_runtime(paths: dict[str, str]) -> dict[str, str]:
    """Exact CAPTURE_FIELDS runtime dict from hermetic path strings."""
    return {
        "export": paths["export"],
        "processed": paths["processed"],
        "capture_dir": paths["capture_dir"],
        "chroma_dir": paths["chroma_dir"],
    }


def bind_r2b_pass_snapshot(
    *,
    manifest_path: Path,
    paths: dict[str, str],
    snap: dict[str, Any],
):
    """Mint an R2b capability with stub restic + fixed snapshot recompute."""

    def _pass_snapshot(**_kw: Any) -> dict[str, Any]:
        return snap

    return bind_r2b_capture(
        run_manifest_path=manifest_path,
        runtime=capture_runtime(paths),
        snapshot_recompute_fn=_pass_snapshot,
        restic_gate_fn=lambda: None,
    )


def setup_r2b_capture_env(
    root: Path,
    run_id: str = "test-r2b-run",
    chroma_records: list[dict] | None = None,
    export_lines: list[str] | None = None,
    include_processed: bool = True,
):
    """Full R2b capture environment with manifest, Chroma, sources, capability."""
    if chroma_records is None:
        chroma_records = [
            {"id": "unit1", "document": "doc text 1"},
            {"id": "unit2", "document": "doc text 2"},
        ]
    if export_lines is None:
        export_lines = [
            json.dumps({"id": r["id"], "source": "test"}) for r in chroma_records
        ]

    eval_base = r2b_eval_capture_dir(root, run_id)
    auth_dir = r2b_auth_dir(root, run_id)
    source_dir = root / "source"

    for d in [eval_base.parent, auth_dir, source_dir]:
        d.mkdir(parents=True, exist_ok=True)

    export_path = source_dir / "knowledge_units.jsonl"
    export_path.write_text("\n".join(export_lines) + "\n", encoding="utf-8")

    processed_path = source_dir / "processed.json"
    if include_processed:
        processed_path.write_text("{}", encoding="utf-8")

    chroma_dir = source_dir / "chroma"
    create_chroma_fixture(chroma_dir, chroma_records)

    paths = {
        "export": str(export_path),
        "processed": str(processed_path),
        "capture_dir": str(eval_base),
        "chroma_dir": str(chroma_dir),
    }
    snap = trusted_snapshot_for_paths(paths, include_processed=include_processed)
    # Keep timestamp fresh even if recompute ran slightly earlier.
    snap["snapshot_timestamp"] = datetime.now(timezone.utc).isoformat()
    if not include_processed:
        # Ensure file remains absent for binder/capture semantics.
        if processed_path.exists():
            processed_path.unlink()

    body = make_r2b_run_manifest_for_tests(
        paths=paths, run_id=run_id, source_snapshot=snap
    )
    man = write_json(auth_dir / "capture.json", body)
    write_approval_sidecar(man)
    cap = bind_r2b_pass_snapshot(manifest_path=man, paths=paths, snap=snap)
    return cap, paths, body, snap, man
