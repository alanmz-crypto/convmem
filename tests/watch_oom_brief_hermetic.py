# pylint: disable=too-many-arguments,too-many-locals,duplicate-code
"""Hermetic Chroma fixtures for bounded brief-metadata Execute (C0–C6)."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

FROZEN_NOW_ISO = "2026-09-13T12:00:00Z"
FROZEN_NOW = datetime(2026, 9, 13, 12, 0, 0, tzinfo=timezone.utc)
ENVELOPE_32K = "E" * 32768
ENVELOPE_2K = "E" * 2048

# Exact brief projection union (output fields). SQL keys omit `id` and map
# `document` to chroma:document.
BRIEF_PROJECTION_FIELDS = (
    "id",
    "ledger_id",
    "ledger_kind",
    "type",
    "relates_to",
    "timestamp",
    "result",
    "verification_result",
    "severity",
    "site",
    "domain",
    "title",
    "summary",
    "rationale",
    "tool",
    "source_path",
    "superseded",
    "deleted",
    "document",
)
BRIEF_SQL_METADATA_KEYS = tuple(
    key for key in BRIEF_PROJECTION_FIELDS if key not in {"id", "document"}
)
FORBIDDEN_BRIEF_KEYS = (
    "provenance_envelope",
    "provenance_commitment",
    "provenance_assertion_id",
)


def _insert_metadata(conn: sqlite3.Connection, row_id: int, key: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        conn.execute(
            "INSERT INTO embedding_metadata (id, key, bool_value) VALUES (?, ?, ?)",
            (row_id, key, int(value)),
        )
        return
    if isinstance(value, int):
        conn.execute(
            "INSERT INTO embedding_metadata (id, key, int_value) VALUES (?, ?, ?)",
            (row_id, key, value),
        )
        return
    if isinstance(value, float):
        conn.execute(
            "INSERT INTO embedding_metadata (id, key, float_value) VALUES (?, ?, ?)",
            (row_id, key, value),
        )
        return
    conn.execute(
        "INSERT INTO embedding_metadata (id, key, string_value) VALUES (?, ?, ?)",
        (row_id, key, str(value)),
    )


def write_chroma_sqlite(
    chroma_dir: Path,
    collections: dict[str, list[dict]],
) -> Path:
    """Write a minimal Chroma SQLite DB readable by chroma_readonly helpers."""
    chroma_dir.mkdir(parents=True, exist_ok=True)
    db = chroma_dir / "chroma.sqlite3"
    if db.exists():
        db.unlink()
    conn = sqlite3.connect(str(db))
    try:
        conn.executescript(
            """
            CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE segments (
                id TEXT PRIMARY KEY, collection TEXT NOT NULL, scope TEXT NOT NULL
            );
            CREATE TABLE embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                embedding_id TEXT NOT NULL,
                segment_id TEXT NOT NULL
            );
            CREATE TABLE embedding_metadata (
                id INTEGER NOT NULL,
                key TEXT NOT NULL,
                string_value TEXT,
                int_value INTEGER,
                float_value REAL,
                bool_value INTEGER
            );
            """
        )
        for coll_i, (name, records) in enumerate(collections.items()):
            cid = f"coll-{coll_i}"
            sid = f"seg-{coll_i}"
            conn.execute("INSERT INTO collections VALUES (?, ?)", (cid, name))
            conn.execute(
                "INSERT INTO segments VALUES (?, ?, 'METADATA')",
                (sid, cid),
            )
            for rec in records:
                cur = conn.execute(
                    "INSERT INTO embeddings (embedding_id, segment_id) VALUES (?, ?)",
                    (rec["id"], sid),
                )
                row_id = int(cur.lastrowid)
                document = rec.get("document")
                if document is not None:
                    _insert_metadata(conn, row_id, "chroma:document", document)
                for key, value in (rec.get("metadata") or {}).items():
                    _insert_metadata(conn, row_id, key, value)
        conn.commit()
    finally:
        conn.close()
    return db


def write_memory_fixture(
    chroma_dir: Path,
    n: int,
    *,
    envelope: str,
    inventory: Path,
    processed: Path,
    source_path: Path,
) -> None:
    """Bulk synthetic Chroma for C6; caller owns the measured worker."""
    chroma_dir.mkdir(parents=True, exist_ok=True)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    if not source_path.exists():
        source_path.write_text("memory-source\n", encoding="utf-8")
    db = chroma_dir / "chroma.sqlite3"
    if db.exists():
        db.unlink()
    conn = sqlite3.connect(str(db))
    try:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        conn.executescript(
            """
            CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE segments (
                id TEXT PRIMARY KEY, collection TEXT NOT NULL, scope TEXT NOT NULL
            );
            CREATE TABLE embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                embedding_id TEXT NOT NULL,
                segment_id TEXT NOT NULL
            );
            CREATE TABLE embedding_metadata (
                id INTEGER NOT NULL,
                key TEXT NOT NULL,
                string_value TEXT,
                int_value INTEGER,
                float_value REAL,
                bool_value INTEGER
            );
            """
        )
        conn.execute("INSERT INTO collections VALUES ('c0', 'knowledge_units')")
        conn.execute("INSERT INTO collections VALUES ('c1', 'conversation_summaries')")
        conn.execute("INSERT INTO segments VALUES ('s0', 'c0', 'METADATA')")
        conn.execute("INSERT INTO segments VALUES ('s1', 'c1', 'METADATA')")
        src = str(source_path)
        meta_rows: list[tuple] = []
        for i in range(n):
            eid = f"m-{i:06d}"
            cur = conn.execute(
                "INSERT INTO embeddings (embedding_id, segment_id) VALUES (?, 's0')",
                (eid,),
            )
            row_id = int(cur.lastrowid)
            kind = "decision" if i % 17 == 0 else "observation"
            title = f"Unit {i}"
            ts = f"2026-09-13T{i % 24:02d}:{(i % 60):02d}:00Z"
            fields = {
                "chroma:document": f"doc {i}",
                "ledger_id": f"obs_mem_{i}" if kind != "decision" else f"dec_prop_mem_{i}",
                "ledger_kind": kind,
                "type": "decision" if kind == "decision" else "observation",
                "title": title,
                "summary": title,
                "rationale": f"rationale {i}",
                "timestamp": ts,
                "source_path": src,
                "provenance_envelope": envelope,
            }
            if kind == "observation" and i % 19 == 0:
                fields["verification_result"] = "pass"
            for key, value in fields.items():
                meta_rows.append((row_id, key, value, None, None, None))
            if len(meta_rows) >= 5000:
                conn.executemany(
                    "INSERT INTO embedding_metadata "
                    "(id, key, string_value, int_value, float_value, bool_value) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    meta_rows,
                )
                meta_rows.clear()
        if meta_rows:
            conn.executemany(
                "INSERT INTO embedding_metadata "
                "(id, key, string_value, int_value, float_value, bool_value) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                meta_rows,
            )
        conn.commit()
    finally:
        conn.close()
    inventory.write_text(
        json.dumps({"path": str(source_path), "format": "jsonl"}) + "\n",
        encoding="utf-8",
    )
    processed.write_text(
        json.dumps({"hash-mem": {"path": str(source_path), "format": "jsonl"}}),
        encoding="utf-8",
    )


def c0_source_path(tmp_root: Path) -> Path:
    """Inventory/chroma path that resolve_project_from_path maps to convmem."""
    path = tmp_root / "Projects" / "convmem" / "session.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("c0-source\n", encoding="utf-8")
    os.utime(path, (FROZEN_NOW.timestamp() - 3600, FROZEN_NOW.timestamp() - 3600))
    return path


def c0_records(source_path: str, *, envelope: str = ENVELOPE_32K) -> dict[str, list[dict]]:
    """Deterministic C0 corpus: decisions, monitor, ledger graph, projects."""
    common_env = {"provenance_envelope": envelope, "provenance_commitment": "commit-forbidden"}

    def rec(eid: str, document: str, **meta: Any) -> dict:
        payload = dict(common_env)
        payload.update(meta)
        return {"id": eid, "document": document, "metadata": payload}

    units = [
        rec(
            "emb-00",
            "superseded newest decision body",
            ledger_id="dec_prop_superseded",
            ledger_kind="decision",
            type="decision",
            title="Superseded newest decision",
            summary="should still appear in recent decisions",
            rationale="tombstone still listed by current brief scan",
            timestamp="2026-09-13T18:00:00Z",
            superseded=True,
            source_path=source_path,
        ),
        rec(
            "emb-12",
            "second newest decision body",
            ledger_id="dec_prop_second",
            ledger_kind="decision",
            type="decision",
            title="Second newest decision",
            summary="second",
            rationale="keep second",
            timestamp="2026-09-13T17:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-10",
            "equal-ts decision A body",
            ledger_id="dec_prop_equal_a",
            ledger_kind="decision",
            type="decision",
            title="Equal-ts decision A",
            summary="equal A",
            rationale="tie-break A",
            timestamp="2026-09-13T16:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-11",
            "equal-ts decision B body",
            ledger_id="dec_prop_equal_b",
            ledger_kind="decision",
            type="decision",
            title="Equal-ts decision B",
            summary="equal B",
            rationale="tie-break B",
            timestamp="2026-09-13T16:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-13",
            "fifth decision body",
            ledger_id="dec_prop_fifth",
            ledger_kind="decision",
            type="decision",
            title="Fifth decision",
            summary="fifth",
            rationale="keep fifth",
            timestamp="2026-09-13T15:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-14",
            "dropped sixth decision body",
            ledger_id="dec_prop_sixth",
            ledger_kind="decision",
            type="decision",
            title="Dropped sixth decision",
            summary="should not appear in top five",
            rationale="cutoff",
            timestamp="2026-09-13T14:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-m0",
            "monitor newest",
            ledger_id="obs_mon_newest",
            ledger_kind="observation",
            type="observation",
            tool="convmem-monitor",
            title="Newest monitor hit",
            summary="monitor new",
            result="pass",
            verification_result="pass",
            site="staging.example",
            timestamp="2026-09-13T18:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-m1",
            "monitor mid",
            ledger_id="obs_mon_mid",
            ledger_kind="observation",
            type="observation",
            tool="convmem-monitor",
            title="Mid monitor hit",
            summary="monitor mid",
            result="fail",
            verification_result="pass",
            site="staging.example",
            timestamp="2026-09-13T17:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-m2",
            "monitor third",
            ledger_id="obs_mon_third",
            ledger_kind="observation",
            type="observation",
            tool="convmem-monitor",
            title="Third monitor hit",
            summary="monitor third",
            result="pass",
            verification_result="pass",
            site="staging.example",
            timestamp="2026-09-13T16:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-m3",
            "monitor dropped",
            ledger_id="obs_mon_dropped",
            ledger_kind="observation",
            type="observation",
            tool="convmem-monitor",
            title="Dropped monitor hit",
            summary="should not appear in top three",
            result="pass",
            verification_result="pass",
            site="staging.example",
            timestamp="2026-09-13T15:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-o1",
            "open observation body",
            ledger_id="obs_open",
            ledger_kind="observation",
            type="observation",
            title="Open observation",
            summary="needs attention",
            severity="high",
            site="staging.example",
            domain="web_stack.security",
            timestamp="2026-09-13T11:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-o2",
            "failed observation body",
            ledger_id="obs_failed",
            ledger_kind="observation",
            type="observation",
            title="Failed observation",
            summary="check failed",
            severity="medium",
            site="staging.example",
            domain="web_stack.security",
            timestamp="2026-09-13T10:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-v2",
            "failing verification body",
            ledger_id="ver_failed",
            ledger_kind="verification",
            type="observation",
            title="Failing verification",
            summary="still failing",
            relates_to="obs_failed",
            result="fail",
            timestamp="2026-09-13T10:30:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-o3",
            "resolved observation body",
            ledger_id="obs_resolved",
            ledger_kind="observation",
            type="observation",
            title="Resolved observation",
            summary="already passed",
            severity="low",
            site="staging.example",
            domain="web_stack.security",
            timestamp="2026-09-13T09:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-v3",
            "passing verification body",
            ledger_id="ver_passed",
            ledger_kind="verification",
            type="observation",
            title="Passing verification",
            summary="fixed",
            relates_to="obs_resolved",
            result="pass",
            timestamp="2026-09-13T09:30:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-o4",
            "superseded observation body",
            ledger_id="obs_superseded",
            ledger_kind="observation",
            type="observation",
            title="Superseded observation",
            summary="tombstoned",
            severity="high",
            timestamp="2026-09-13T08:00:00Z",
            superseded=True,
            source_path=source_path,
        ),
        rec(
            "emb-o5",
            "deleted but not superseded observation",
            ledger_id="obs_deleted",
            ledger_kind="observation",
            type="observation",
            title="Deleted observation",
            summary="deleted flag is not a brief exclusion",
            severity="low",
            timestamp="2026-09-13T07:00:00Z",
            deleted=True,
            source_path=source_path,
        ),
        rec(
            "emb-p0",
            "extra project title older",
            ledger_id="",
            title="Older project title",
            timestamp="2026-09-13T01:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-p1",
            "extra project title newer",
            ledger_id="",
            title="Newer project title",
            timestamp="2026-09-13T02:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-p2",
            "extra project title newest",
            ledger_id="",
            title="Newest project title",
            timestamp="2026-09-13T03:00:00Z",
            source_path=source_path,
        ),
        rec(
            "emb-p3",
            "fourth project title dropped from rollup",
            ledger_id="",
            title="Dropped project title",
            timestamp="2026-09-13T00:30:00Z",
            source_path=source_path,
        ),
    ]
    summaries = [
        {"id": "sum-01", "document": "summary one", "metadata": {"title": "s1"}},
        {"id": "sum-02", "document": "summary two", "metadata": {"title": "s2"}},
    ]
    return {"knowledge_units": units, "conversation_summaries": summaries}


def write_c0_fixture(tmp_root: Path, *, envelope: str = ENVELOPE_32K) -> dict[str, Any]:
    """Create chroma + inventory + processed files for the C0 oracle."""
    source = c0_source_path(tmp_root)
    chroma_dir = tmp_root / "chroma"
    write_chroma_sqlite(chroma_dir, c0_records(str(source), envelope=envelope))
    inventory = tmp_root / "inventory.jsonl"
    processed = tmp_root / "processed.json"
    inventory.write_text(
        json.dumps({"path": str(source), "format": "jsonl"}) + "\n",
        encoding="utf-8",
    )
    processed.write_text(
        json.dumps(
            {
                "hash-c0": {
                    "path": str(source),
                    "format": "jsonl",
                }
            }
        ),
        encoding="utf-8",
    )
    return {
        "chroma_dir": chroma_dir,
        "inventory": inventory,
        "processed": processed,
        "source_path": source,
        "cfg": {
            "index": {
                "chroma_dir": str(chroma_dir),
                "processed_log": str(processed),
            },
            "sources": {"inventory": str(inventory)},
            "query": {"rerank": False},
        },
    }


EXPECTED_DECISION_IDS = (
    "dec_prop_superseded",
    "dec_prop_second",
    "dec_prop_equal_a",
    "dec_prop_equal_b",
    "dec_prop_fifth",
)
EXPECTED_MONITOR_TITLES = (
    "Newest monitor hit",
    "Mid monitor hit",
    "Third monitor hit",
)
EXPECTED_UNRESOLVED_COUNT = 4  # obs_open, obs_failed, ver_failed, obs_deleted
EQUAL_TS_DECISION_ORDER = ("dec_prop_equal_a", "dec_prop_equal_b")


def normalize_brief_payload(data: dict) -> dict:
    """JSON-stable brief payload: Path → str, skip live probe objects."""
    out = {}
    for key, value in data.items():
        if key == "inter_model_inbox":
            out[key] = str(value)
            continue
        if isinstance(value, Path):
            out[key] = str(value)
            continue
        out[key] = value
    decisions = []
    for row in out.get("recent_decisions") or []:
        decisions.append(
            {
                "id": row.get("id"),
                "ledger_id": row.get("ledger_id"),
                "title": row.get("title"),
                "timestamp": row.get("timestamp"),
                "rationale": row.get("rationale"),
                "superseded": row.get("superseded"),
            }
        )
    out["recent_decisions_norm"] = decisions
    monitors = []
    for row in out.get("recent_monitor") or []:
        monitors.append(
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "timestamp": row.get("timestamp"),
                "tool": row.get("tool"),
                "result": row.get("result"),
            }
        )
    out["recent_monitor_norm"] = monitors
    projects = []
    for row in out.get("projects") or []:
        projects.append(
            {
                "slug": row.get("slug"),
                "indexed_sources": row.get("indexed_sources"),
                "knowledge_units": row.get("knowledge_units"),
                "recent_unit_titles": row.get("recent_unit_titles"),
                "formats": row.get("formats"),
            }
        )
    out["projects_norm"] = projects
    return out


@contextmanager
def freeze_brief_probes() -> Iterator[None]:
    """Pin environment probes so C0/C6 compare chroma-derived fields only."""
    import brief  # noqa: F401  # pylint: disable=import-outside-toplevel,unused-import
    import doctor  # noqa: F401  # pylint: disable=import-outside-toplevel,unused-import

    frozen_handoff = {
        "path": "docs/inter-model/LATEST.md",
        "mtime_iso": FROZEN_NOW_ISO,
        "age_label": "just now",
        "age_seconds": 0,
        "date_label": "2026-09-13",
        "author": "Cursor",
    }
    with ExitStack() as stack:
        stack.enter_context(patch("brief._now_iso", return_value=FROZEN_NOW_ISO))
        stack.enter_context(patch("brief._systemd_state", return_value="enabled/active"))
        stack.enter_context(
            patch(
                "brief._mcp_registration",
                return_value={
                    "cursor": "registered",
                    "crush": "registered",
                    "crush_live": "verified",
                    "stdio": "verified",
                },
            )
        )
        stack.enter_context(patch("brief._watch_process_memory", return_value=None))
        stack.enter_context(patch("brief._pending_decision_ingest", return_value=[]))
        stack.enter_context(patch("brief._latest_handoff_info", return_value=frozen_handoff))
        stack.enter_context(
            patch("brief._handoff_staleness", return_value={"stale": False})
        )
        stack.enter_context(
            patch(
                "brief._recent_inter_model_titles",
                return_value=[
                    "CURSOR-2026-09-13-watch-oom-stream-brief-metadata-execute-handoff.md"
                ],
            )
        )
        stack.enter_context(
            patch(
                "doctor.standing_register_status",
                return_value=(14, []),
            )
        )
        real_datetime = __import__("datetime").datetime

        class _FrozenDateTime(real_datetime):
            @classmethod
            def now(cls, tz=None):
                if tz is None:
                    return FROZEN_NOW.replace(tzinfo=None)
                return FROZEN_NOW.astimezone(tz)

        stack.enter_context(patch("brief.datetime", _FrozenDateTime))
        yield
