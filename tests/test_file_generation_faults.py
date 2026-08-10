from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from chroma_store import UNITS
from file_generation_store import FileGenerationStore, StagedRow


def _row(physical: str, logical: str, generation: str, owner: str, document: str):
    return StagedRow(
        UNITS,
        physical,
        logical,
        document,
        [1.0, 0.0],
        {"source_path": "/tmp/source.jsonl"},
        "file",
        owner,
        generation,
    )


def test_process_death_after_partial_candidate_never_changes_serving_generation(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    owner = "owner-crash"
    active = {owner: "N"}
    with FileGenerationStore(chroma, active_generations=lambda: active) as store:
        store.stage_rows([_row("fg1_old", "L-old", "N", owner, "old")])

    script = r"""
import os, sys
from chroma_store import UNITS
from file_generation_store import FileGenerationStore, StagedRow
chroma, owner = sys.argv[1:]
active = {owner: "N"}
store = FileGenerationStore(chroma, active_generations=lambda: active)
store.stage_rows([StagedRow(UNITS, "fg1_partial", "L-new-1", "new-1", [1.0,0.0],
    {"source_path":"/tmp/source.jsonl"}, "file", owner, "N+1")])
os._exit(23)
"""
    proc = subprocess.run(
        [sys.executable, "-c", script, str(chroma), owner],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
    )
    assert proc.returncode == 23

    with FileGenerationStore(chroma, active_generations=lambda: active) as reopened:
        assert [row["id"] for row in reopened.query_units([1.0, 0.0], 10)] == [
            "fg1_old"
        ]
        # The process-crash residue may be recoverable, but it remains inert.
        physical = reopened.all_physical_ids(UNITS)
        assert "fg1_old" in physical
        assert "fg1_partial" in physical


def test_file_shrink_and_valid_empty_generation_expose_exact_smaller_set(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    owner = "owner-shrink"
    active: dict[str, str] = {}
    previous: dict[str, str] = {}
    with FileGenerationStore(
        chroma,
        active_generations=lambda: active,
        previous_generations=lambda: previous,
    ) as store:
        store.stage_rows(
            [
                _row("fg1_n_1", "L1", "N", owner, "one"),
                _row("fg1_n_2", "L2", "N", owner, "two"),
            ]
        )
        active[owner] = "N"
        store.stage_rows([_row("fg1_np1_1", "L1", "N+1", owner, "one-new")])
        previous[owner] = "N"
        active[owner] = "N+1"
        assert store.count_units() == 1
        assert store.get_unit_by_logical_id("L2") is None

        # A valid empty generation intentionally serves zero rows.  No deletion
        # of N/N+1 is needed; authority is solely the selected generation.
        previous[owner] = "N+1"
        active[owner] = "N+2"
        assert store.count_units() == 0
        assert store.all_physical_ids(UNITS) == {
            "fg1_n_1",
            "fg1_n_2",
            "fg1_np1_1",
        }


def test_candidate_staging_has_no_authoritative_shadow_sink(tmp_path: Path) -> None:
    active: dict[str, str] = {}
    with FileGenerationStore(
        tmp_path / "chroma", active_generations=lambda: active
    ) as store:
        assert store.raw_store.mutation_sink is None
        store.stage_rows([_row("fg1_candidate", "L", "N", "owner", "fact")])
        assert store.raw_store.mutation_sink is None
