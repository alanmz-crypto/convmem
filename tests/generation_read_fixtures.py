"""Shared FileGenerationStore staging helpers for read-path tests."""

from __future__ import annotations

from chroma_store import UNITS
from file_generation_store import STABLE_SCOPE, FileGenerationStore, StagedRow
from tests.test_file_generation_store import file_row


def stage_owner_a_active_alpha(
    store: FileGenerationStore,
    *,
    title: str | None = None,
) -> None:
    kwargs = {}
    if title is not None:
        kwargs["title"] = title
    store.stage_rows(
        [
            file_row(
                "fg1_active_a",
                "LA",
                "N",
                document="active alpha",
                embedding=[0.8, 0.2],
                **kwargs,
            ),
        ]
    )


def stage_dec_stable_row(store: FileGenerationStore, *, source_path: str | None = None) -> None:
    metadata = {"ledger_id": "dec_stable"}
    if source_path is not None:
        metadata["source_path"] = source_path
    store.stage_rows(
        [
            StagedRow(
                UNITS,
                "dec_stable",
                "dec_stable",
                "stable governed",
                [0.7, 0.3],
                metadata,
                STABLE_SCOPE,
            ),
        ]
    )


def inactive_neighbor_rows(
    count: int,
    *,
    start: int = 0,
    title: str | None = None,
) -> list:
    rows = []
    for index in range(start, start + count):
        kwargs = {}
        if title is not None:
            kwargs["title"] = title
        rows.append(
            file_row(
                f"fg1_inactive_{index}",
                f"LI{index}",
                "N+1",
                document=f"inactive forbidden {index}",
                embedding=[1.0, 0.001 * index],
                **kwargs,
            )
        )
    return rows
