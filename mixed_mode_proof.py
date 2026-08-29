"""CG-2 mixed-mode backend characterization and proof gates.

Measures authority safety, authorized cardinality, and retrieval quality as
separate properties against an authority-clean control.  Physical deletion,
online GC, and internal queue surgery remain disabled in this slice.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

from chroma_store import ChromaStore, UNITS
from file_generation_store import FileGenerationStore
from file_generation_validate import chroma_sequence_positions
from logical_accounting import (
    PhysicalRowClass,
    build_physical_inventory_report,
    classify_physical_row,
    discover_file_generations_by_owner,
)
from chroma_readonly import collection_metadata_rows
from mixed_mode_control import build_authority_clean_control
from mixed_mode_retrieval import (
    MixedModeCandidateBudget,
    assert_pinned_chroma_version,
    query_units_mixed_ann,
    verify_authority_safety,
)
from serving_authority import FrozenAuthorityVector, generation_root_for_cfg, resolve_frozen_authority_vector
from serving_index_repository import ServingIndexRepository, open_serving_index_repository

PROOF_SCHEMA = "convmem/mixed-mode-proof-v1"
PHYSICAL_DELETION_DISABLED = True


def characterize_chroma_storage(chroma_dir: str | Path) -> dict[str, Any]:
    chroma_path = Path(chroma_dir).expanduser()
    sqlite_path = chroma_path / "chroma.sqlite3"
    sequence = chroma_sequence_positions(chroma_path)
    sqlite_bytes = sqlite_path.stat().st_size if sqlite_path.is_file() else 0
    return {
        "chroma_version": assert_pinned_chroma_version(),
        "sqlite_bytes": sqlite_bytes,
        "sequence_positions": sequence,
        "physical_deletion_disabled": PHYSICAL_DELETION_DISABLED,
    }


def measure_authorized_cardinality(
    mixed_rows: list[dict[str, Any]],
    control_rows: list[dict[str, Any]],
    *,
    requested_k: int,
) -> dict[str, Any]:
    mixed_count = len(mixed_rows)
    control_count = len(control_rows)
    underfill = mixed_count < requested_k <= control_count
    mismatch = control_count != mixed_count
    return {
        "requested_k": requested_k,
        "mixed_authorized_count": mixed_count,
        "control_count": control_count,
        "underfill": underfill,
        "count_mismatch": mismatch,
        "pass": not underfill and not mismatch,
    }


def measure_retrieval_quality(
    mixed_rows: list[dict[str, Any]],
    control_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    mixed_ids = [str(row.get("id")) for row in mixed_rows]
    control_ids = [str(row.get("id")) for row in control_rows]
    overlap = [row_id for row_id in mixed_ids if row_id in set(control_ids)]
    rank_divergence = [
        index
        for index, row_id in enumerate(mixed_ids)
        if index >= len(control_ids) or control_ids[index] != row_id
    ]
    return {
        "overlap_count": len(overlap),
        "mixed_ids": mixed_ids,
        "control_ids": control_ids,
        "rank_divergence_positions": rank_divergence,
        "exact_rank_match": not rank_divergence,
    }


def retention_inventory_report(
    chroma_dir: str | Path,
    vector: FrozenAuthorityVector,
) -> dict[str, Any]:
    physical = build_physical_inventory_report(
        str(chroma_dir),
        active_generations=vector.active_generations(),
        previous_generations=vector.previous_generations(),
    )
    counts = physical.get("counts_by_class") or {}
    return {
        "active_generations": vector.active_generations(),
        "previous_generations": vector.previous_generations(),
        "retained_inactive_count": int(counts.get("retained_inactive", 0)),
        "abandoned_count": int(counts.get("abandoned", 0)),
        "serving_units": int(physical.get("serving_units_count", 0)),
        "physical_units": int(physical.get("physical_units_count", 0)),
        "physical_deletion_disabled": PHYSICAL_DELETION_DISABLED,
    }


def retained_rollback_baseline_inventory(
    chroma_dir: str | Path,
    vector: FrozenAuthorityVector,
    *,
    owner_digest: str,
    grb_generation_id: str,
) -> dict[str, Any]:
    """Report whether retained G_rb remains protected and not GC-eligible."""

    inventory = retention_inventory_report(chroma_dir, vector)
    known_by_owner = discover_file_generations_by_owner(str(chroma_dir), UNITS)
    grb_rows = 0
    abandoned_grb_rows = 0
    for meta in collection_metadata_rows(str(chroma_dir), UNITS):
        if str(meta.get("owner_digest") or "") != owner_digest:
            continue
        if str(meta.get("generation_id") or "") != grb_generation_id:
            continue
        grb_rows += 1
        classification = classify_physical_row(
            meta,
            collection_kind=UNITS,
            active_generations=vector.active_generations(),
            previous_generations=vector.previous_generations(),
            known_generations_by_owner=known_by_owner,
        )
        if classification == PhysicalRowClass.ABANDONED:
            abandoned_grb_rows += 1
    return {
        **inventory,
        "grb_generation_id": grb_generation_id,
        "grb_row_count": grb_rows,
        "grb_abandoned_row_count": abandoned_grb_rows,
        "grb_protected": grb_rows > 0 and abandoned_grb_rows == 0,
        "grb_gc_eligible": abandoned_grb_rows > 0,
        "physical_deletion_disabled": PHYSICAL_DELETION_DISABLED,
    }


def run_mixed_mode_proof(
    chroma_dir: str | Path,
    control_chroma_dir: str | Path,
    embedding: list[float],
    top_k: int,
    *,
    vector: FrozenAuthorityVector,
    budget: MixedModeCandidateBudget | None = None,
) -> dict[str, Any]:
    """Compare mixed-mode ANN retrieval against an authority-clean control."""

    budget = budget or MixedModeCandidateBudget()
    source_path = Path(chroma_dir).expanduser()
    control_path = Path(control_chroma_dir).expanduser()

    control_info = build_authority_clean_control(
        source_path,
        control_path,
        active_generations=vector.active_generations,
        previous_generations=vector.previous_generations,
    )

    with FileGenerationStore(
        source_path,
        active_generations=vector.active_generations,
        previous_generations=vector.previous_generations,
    ) as mixed_store:
        mixed_rows = query_units_mixed_ann(
            mixed_store,
            embedding,
            top_k,
            vector=vector,
            budget=budget,
        )

    with ChromaStore(str(control_path), create_collections=False) as control_store:
        control_rows = control_store.query_units(embedding, top_k)

    safety = verify_authority_safety(mixed_rows, vector)
    cardinality = measure_authorized_cardinality(
        mixed_rows, control_rows, requested_k=top_k
    )
    quality = measure_retrieval_quality(mixed_rows, control_rows)
    storage = characterize_chroma_storage(source_path)
    retention = retention_inventory_report(source_path, vector)

    gates = {
        "authority_safety_pass": safety["pass"],
        "authorized_cardinality_pass": cardinality["pass"],
        "physical_deletion_disabled": PHYSICAL_DELETION_DISABLED,
    }

    return {
        "schema": PROOF_SCHEMA,
        "chroma_version": storage["chroma_version"],
        "control": control_info,
        "authority_safety": safety,
        "authorized_cardinality": cardinality,
        "retrieval_quality": quality,
        "storage": storage,
        "retention": retention,
        "gates": gates,
        "gate_pass": all(
            gates[key]
            for key in (
                "authority_safety_pass",
                "authorized_cardinality_pass",
                "physical_deletion_disabled",
            )
        ),
    }


def query_control_exact_cosine(
    store: FileGenerationStore,
    embedding: list[float],
    top_k: int,
    *,
    collection_name: str = UNITS,
) -> list[dict[str, Any]]:
    """Secondary diagnostic: exact cosine over the authority-filtered active set."""

    rows = store._get_rows(collection_name, include_embeddings=True)  # pylint: disable=protected-access
    query_vector = store._validated_embedding(embedding, label="query")  # pylint: disable=protected-access
    scored: list[dict[str, Any]] = []
    for row in rows:
        row_embedding = store._validated_embedding(  # pylint: disable=protected-access
            row.get("embedding"),
            label=str(row["id"]),
            expected_dimension=len(query_vector),
        )
        scored.append(
            {
                "id": row["id"],
                "metadata": row["metadata"],
                "document": row["document"],
                "distance": store._cosine_distance(  # pylint: disable=protected-access
                    query_vector, row_embedding, label=str(row["id"])
                ),
            }
        )
    scored.sort(key=lambda item: (float(item["distance"]), str(item["id"])))
    return scored[:top_k]


class RehearsalEmptyCommittedView:
    def query_units(self, _embedding, _top_k):
        return []

    def get_unit(self, _unit_id):
        return None


@dataclass
class RehearsalProcessSession:
    """Tracks open serving resources for one simulated process lifetime."""

    serving_repo: ServingIndexRepository | None = None
    authority_vector: Any | None = None
    backing_store: Any | None = None

    def close(self) -> None:
        if self.serving_repo is not None:
            self.serving_repo.close()
            self.serving_repo = None
        self.authority_vector = None
        self.backing_store = None

    def is_closed(self) -> bool:
        return self.serving_repo is None


def rehearsal_real_owner_digests(generation_root: Path) -> set[str]:
    """Exclude guard filenames that discover_owner_digests mis-classifies as owners."""

    from serving_authority import discover_owner_digests

    return {
        digest
        for digest in discover_owner_digests(generation_root)
        if not digest.endswith(".canary_guard")
    }


def resolve_rehearsal_authority_vector(cfg: dict[str, Any]) -> FrozenAuthorityVector:
    generation_root = generation_root_for_cfg(cfg)
    if generation_root.exists():
        return resolve_frozen_authority_vector(
            cfg, owner_digests=rehearsal_real_owner_digests(generation_root)
        )
    return resolve_frozen_authority_vector(cfg)


@contextmanager
def open_public_serving_repository_for_rehearsal(
    cfg: dict[str, Any],
) -> Iterator[ServingIndexRepository]:
    """Invoke public serving open with rehearsal-corrected owner discovery."""

    with patch(
        "serving_index_repository.resolve_frozen_authority_vector",
        resolve_rehearsal_authority_vector,
    ):
        with open_serving_index_repository(cfg) as repo:
            yield repo


def open_rehearsal_serving_session(cfg: dict[str, Any]) -> RehearsalProcessSession:
    """Open a request-scoped serving repository like production reads."""

    from serving_index_repository import _open_backing_store

    session = RehearsalProcessSession()
    vector = resolve_rehearsal_authority_vector(cfg)
    store = _open_backing_store(vector)
    session.authority_vector = vector
    session.backing_store = store
    session.serving_repo = ServingIndexRepository(vector, store, cfg=cfg)
    return session


_REHEARSAL_SUBPROCESS_SCRIPT = r"""
import json
import os
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
result_path = Path(sys.argv[2])
probe = payload["probe"]
cfg = payload["cfg"]
owner_digest = payload["owner_digest"]

if probe == "public_open_generation":
    from unittest.mock import patch

    from mixed_mode_proof import resolve_rehearsal_authority_vector
    from serving_index_repository import open_serving_index_repository

    with patch(
        "serving_index_repository.resolve_frozen_authority_vector",
        resolve_rehearsal_authority_vector,
    ):
        with open_serving_index_repository(cfg) as repo:
            generation_id = repo.authority_vector.active_generations()[owner_digest]
            vector_id = id(repo.authority_vector)
    result = {
        "pid": os.getpid(),
        "parent_pid": os.getppid(),
        "active_generation_id": generation_id,
        "authority_vector_id": vector_id,
        "via_public_serving_open": True,
    }
elif probe == "restart_recovery":
    from unittest.mock import patch

    from file_generation_pointer import recover_active_pointer
    from mixed_mode_proof import (
        resolve_rehearsal_authority_vector,
        retained_rollback_baseline_inventory,
    )
    from serving_authority import generation_root_for_cfg
    from serving_index_repository import open_serving_index_repository
    from source_reconciler import pending_owner_work

    owner_key = payload["owner_key"]
    chroma_dir = payload["chroma_dir"]
    expected_grb = payload["expected_grb_generation_id"]
    generations = generation_root_for_cfg(cfg)
    recovered = recover_active_pointer(
        generations,
        owner_key,
        chroma_dir=chroma_dir,
        cfg=cfg,
    )
    pending = bool(pending_owner_work(cfg))
    with patch(
        "serving_index_repository.resolve_frozen_authority_vector",
        resolve_rehearsal_authority_vector,
    ):
        with open_serving_index_repository(cfg) as repo:
            reopened_generation = repo.authority_vector.active_generations()[owner_digest]
            reopened_mode = repo.authority_vector.by_owner[owner_digest].mode.value
            serving_repo_id = id(repo)
    reopened_vector = resolve_rehearsal_authority_vector(cfg)
    retention = retained_rollback_baseline_inventory(
        chroma_dir,
        reopened_vector,
        owner_digest=owner_digest,
        grb_generation_id=expected_grb,
    )
    result = {
        "pid": os.getpid(),
        "parent_pid": os.getppid(),
        "pending_after_restart": pending,
        "recovered_active_generation_id": recovered.pointer["active_generation_id"],
        "reopened_active_generation_id": reopened_generation,
        "reopened_authority_mode": reopened_mode,
        "serving_repo_id": serving_repo_id,
        "retention": retention,
        "recovery_in_fresh_process": True,
        "via_public_serving_open": True,
    }
else:
    raise SystemExit(f"unknown rehearsal probe: {probe!r}")

result_path.write_text(json.dumps(result), encoding="utf-8")
"""


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _run_rehearsal_subprocess_probe(payload: dict[str, Any]) -> dict[str, Any]:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="cg2-d5-probe-") as tmp:
        payload_path = Path(tmp) / "payload.json"
        result_path = Path(tmp) / "result.json"
        payload_path.write_text(json.dumps(payload), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-c", _REHEARSAL_SUBPROCESS_SCRIPT, str(payload_path), str(result_path)],
            cwd=_repo_root(),
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "rehearsal subprocess probe failed: "
                f"exit={proc.returncode} stderr={proc.stderr!r} stdout={proc.stdout!r}"
            )
        return json.loads(result_path.read_text(encoding="utf-8"))


def run_rehearsal_subprocess_public_open(
    cfg: dict[str, Any],
    owner_digest: str,
) -> dict[str, Any]:
    """Fresh OS process public serving open; returns resolved active generation."""

    result = _run_rehearsal_subprocess_probe(
        {
            "probe": "public_open_generation",
            "cfg": cfg,
            "owner_digest": owner_digest,
        }
    )
    result["mechanism"] = "fresh_os_subprocess_public_serving_open"
    result["subprocess_is_fresh_process"] = result["pid"] != os.getpid()
    return result


def run_rehearsal_subprocess_restart_recovery(
    cfg: dict[str, Any],
    *,
    owner_key: str,
    owner_digest: str,
    chroma_dir: str | Path,
    expected_grb_generation_id: str,
    parent_pid: int,
    parent_serving_repo_id: int | None,
) -> dict[str, Any]:
    """Close parent serving in caller; child reconstructs state from durable artifacts."""

    result = _run_rehearsal_subprocess_probe(
        {
            "probe": "restart_recovery",
            "cfg": cfg,
            "owner_digest": owner_digest,
            "owner_key": owner_key,
            "chroma_dir": str(chroma_dir),
            "expected_grb_generation_id": expected_grb_generation_id,
        }
    )
    child_serving_id = result.pop("serving_repo_id")
    result.update(
        {
            "mechanism": "fresh_os_subprocess_recovery_from_durable_artifacts",
            "parent_pid": parent_pid,
            "subprocess_is_fresh_process": result["pid"] != parent_pid,
            "parent_serving_destroyed": parent_serving_repo_id is not None,
            "child_serving_repo_is_new_object": child_serving_id != parent_serving_repo_id,
            "recovery_matches_expected_grb": (
                result["recovered_active_generation_id"] == expected_grb_generation_id
                and result["reopened_active_generation_id"] == expected_grb_generation_id
            ),
        }
    )
    return result
