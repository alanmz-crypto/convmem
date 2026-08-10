"""Hermetic CG-1 scale evidence for committed-generation reads."""

from __future__ import annotations

import tracemalloc
from time import perf_counter

from chroma_store import SUMMARIES, UNITS
from file_generation_store import FILE_SCOPE, FileGenerationStore, StagedRow

OWNER_COUNT = 1_300
ACTIVE_UNIT_COUNT = 20_000
ACTIVE_SUMMARY_COUNT = 2_500
HISTORICAL_UNIT_COUNT = 1_300
HISTORICAL_SUMMARY_COUNT = 130


def _row(
    collection: str,
    physical_id: str,
    logical_id: str,
    owner: str,
    generation: str,
    source_path: str,
    embedding: list[float],
) -> StagedRow:
    return StagedRow(
        collection,
        physical_id,
        logical_id,
        f"document for {logical_id}",
        embedding,
        {"source_path": source_path, "title": logical_id},
        FILE_SCOPE,
        owner,
        generation,
    )


def _stage_backend_batched(store, rows: list[StagedRow], batch_size: int = 5_000) -> None:
    """Load a large committed fixture without quadratic staging qualification."""
    grouped: dict[str, list[StagedRow]] = {}
    for row in rows:
        grouped.setdefault(row.collection_name, []).append(row)
    for collection_name, collection_rows in grouped.items():
        collection = store.raw_store._collection(collection_name)
        for start in range(0, len(collection_rows), batch_size):
            batch = collection_rows[start : start + batch_size]
            collection.upsert(
                ids=[row.physical_id for row in batch],
                documents=[row.document for row in batch],
                embeddings=[row.embedding for row in batch],
                metadatas=[
                    {
                        **dict(row.metadata),
                        "id": row.physical_id,
                        "physical_id": row.physical_id,
                        "logical_id": row.logical_id,
                        "generation_scope": row.generation_scope,
                        "owner_digest": row.owner_digest,
                        "generation_id": row.generation_id,
                    }
                    for row in batch
                ],
            )


def test_committed_generation_reads_scale_past_sqlite_expression_depth(tmp_path):
    """Large active owner sets remain exact and keep inactive history out of reads."""
    active = {
        f"owner-{owner:04d}": f"generation-{owner:04d}"
        for owner in range(OWNER_COUNT)
    }
    store = FileGenerationStore(
        tmp_path / "chroma",
        active_generations=lambda: active,
    )
    try:
        build_started = perf_counter()
        active_rows: list[StagedRow] = []
        unit_index = 0
        for owner_index, owner in enumerate(active):
            unit_count = 16 if owner_index < 500 else 15
            generation = active[owner]
            source_path = f"/sources/{owner}.jsonl"
            for _ in range(unit_count):
                logical_id = f"logical-unit-{unit_index:05d}"
                active_rows.append(
                    _row(
                        UNITS,
                        f"fg1_{generation}_u{unit_index:05d}",
                        logical_id,
                        owner,
                        generation,
                        source_path,
                        [0.0, 1.0],
                    )
                )
                unit_index += 1
        for summary_index in range(ACTIVE_SUMMARY_COUNT):
            owner_index = summary_index % OWNER_COUNT
            owner = f"owner-{owner_index:04d}"
            generation = active[owner]
            active_rows.append(
                _row(
                    SUMMARIES,
                    f"fg1_{generation}_s{summary_index:04d}",
                    f"logical-summary-{summary_index:04d}",
                    owner,
                    generation,
                    f"/sources/{owner}.jsonl",
                    [0.0, 1.0],
                )
            )
        assert unit_index == ACTIVE_UNIT_COUNT
        build_elapsed = perf_counter() - build_started

        stage_started = perf_counter()
        _stage_backend_batched(store, active_rows)
        active_stage_elapsed = perf_counter() - stage_started

        historical_rows: list[StagedRow] = []
        for owner_index in range(HISTORICAL_UNIT_COUNT):
            owner = f"owner-{owner_index:04d}"
            historical_generation = f"historical-{owner_index:04d}"
            historical_rows.append(
                _row(
                    UNITS,
                    f"fg1_{historical_generation}_u",
                    f"logical-unit-{owner_index:05d}",
                    owner,
                    historical_generation,
                    f"/sources/{owner}.jsonl",
                    [1.0, 0.0],
                )
            )
        for summary_index in range(HISTORICAL_SUMMARY_COUNT):
            owner_index = summary_index % OWNER_COUNT
            owner = f"owner-{owner_index:04d}"
            historical_generation = f"historical-{owner_index:04d}"
            historical_rows.append(
                _row(
                    SUMMARIES,
                    f"fg1_{historical_generation}_s",
                    f"logical-summary-{summary_index:04d}",
                    owner,
                    historical_generation,
                    f"/sources/{owner}.jsonl",
                    [1.0, 0.0],
                )
            )
        history_stage_started = perf_counter()
        _stage_backend_batched(store, historical_rows)
        history_stage_elapsed = perf_counter() - history_stage_started

        reads_started = perf_counter()
        assert store.count_units() == ACTIVE_UNIT_COUNT
        assert store.count_summaries() == ACTIVE_SUMMARY_COUNT

        top_k = store.query_units([1.0, 0.0], 7)
        assert len(top_k) == 7
        assert all(
            row["metadata"]["generation_id"] == active[row["metadata"]["owner_digest"]]
            for row in top_k
        )
        assert all("historical-" not in row["id"] for row in top_k)

        tracemalloc.start()
        scan_started = perf_counter()
        unit_rows_60 = store.query_units([1.0, 0.0], 60)
        scan_elapsed = perf_counter() - scan_started
        scan_current_bytes, scan_peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        for top_k_value, unit_rows in (
            (5, store.query_units([1.0, 0.0], 5)),
            (20, store.query_units([1.0, 0.0], 20)),
            (60, unit_rows_60),
        ):
            assert len(unit_rows) == top_k_value
            assert all(
                row["metadata"]["generation_id"]
                == active[row["metadata"]["owner_digest"]]
                for row in unit_rows
            )
            assert all("historical-" not in row["id"] for row in unit_rows)

        summary_rows = store.query_summaries([1.0, 0.0], 20)
        assert len(summary_rows) == 20
        assert all(
            row["metadata"]["generation_id"]
            == active[row["metadata"]["owner_digest"]]
            for row in summary_rows
        )
        assert all("historical-" not in row["id"] for row in summary_rows)

        source_owner = "owner-0000"
        source_rows = store.rows_for_source(
            UNITS,
            f"/sources/{source_owner}.jsonl",
            owner_digest=source_owner,
        )
        assert len(source_rows) == 16
        assert all(
            row["metadata"]["generation_id"] == active[source_owner]
            for row in source_rows
        )

        logical = store.get_unit_by_logical_id("logical-unit-00000")
        assert logical is not None
        assert logical["id"].startswith("fg1_generation-0000")
        assert store.get_unit_by_physical_id("fg1_historical-0000_u") is None

        sqlite_rows = store.readonly_sqlite_rows(UNITS)
        assert len(sqlite_rows) == ACTIVE_UNIT_COUNT
        assert all(row.get("generation_id") in active.values() for row in sqlite_rows)
        reads_elapsed = perf_counter() - reads_started

        print(
            "CG-1 scale timings: "
            f"build={build_elapsed:.3f}s "
            f"active_stage={active_stage_elapsed:.3f}s "
            f"history_stage={history_stage_elapsed:.3f}s "
            f"exact_scan_top60={scan_elapsed:.6f}s "
            f"exact_scan_python_memory=current:{scan_current_bytes}B "
            f"peak:{scan_peak_bytes}B "
            f"reads={reads_elapsed:.3f}s"
        )
    finally:
        store.close()
