"""CG-2 copied-corpus rehearsal and Execute evidence bundle (T5).

Runs only in isolated temporary roots.  Does not publish production fences,
pointers, activation manifests, or perform GC.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

import chromadb

from cg2_property_map import build_property_map_report
from chroma_store import ChromaStore, open_chroma_for_read
from mixed_mode_proof import PHYSICAL_DELETION_DISABLED, characterize_chroma_storage
from mixed_mode_retrieval import PINNED_CHROMA_VERSION
from serving_authority import AuthorityResolutionRetryBudget
from serving_index_repository import open_serving_index_repository
from source_reconciler import ReconciliationBudget

REHEARSAL_SCHEMA = "convmem/cg2-rehearsal-v1"
ARCHITECTURE_SHA = "e680ce837653698a5be8b78ba02db2f880c40c63"
def _git_sha(path: str | None = None) -> str:
    cmd = ["git", "rev-parse", "HEAD"]
    if path:
        cmd = ["git", "rev-parse", path]
    return subprocess.check_output(cmd, text=True).strip()


def measured_budgets() -> dict[str, Any]:
    authority = AuthorityResolutionRetryBudget()
    reconciliation = ReconciliationBudget()
    return {
        "authority_resolution_retry_budget": {
            "max_attempts": authority.max_attempts,
            "max_elapsed_seconds": authority.max_elapsed,
        },
        "reconciliation": {
            "max_pending_owners": reconciliation.max_pending_owners,
            "max_reconciliation_staleness_seconds": reconciliation.max_reconciliation_staleness,
        },
        "chroma_version": PINNED_CHROMA_VERSION,
        "physical_deletion_disabled": PHYSICAL_DELETION_DISABLED,
        "note": "Latency and soak budgets ratified at gateway soak grant; not measured in isolated rehearsal",
    }


def external_review_record() -> dict[str, Any]:
    """Execute applicability decision copied into VERIFY — not invented at verify time."""

    return {
        "gate_applicability": "pending_pr_open",
        "reason": (
            "BugBot / independent security review applies at PR open for the "
            "feat/2026-08-15-cg2-production-activation tip; Execute records SHA "
            "when review completes"
        ),
        "bugbot_reviewed_sha": None,
    }


def run_legacy_gateway_rehearsal(tmp_path: Path) -> dict[str, Any]:
    """Legacy-only serving equivalence on an isolated copied corpus."""

    chroma = tmp_path / "chroma"
    chroma.mkdir(parents=True, exist_ok=True)
    cfg = {
        "models": {
            "embed_model": "nomic-embed-text",
            "ollama_host": "http://localhost:11434",
            "rerank_model": "rerank",
        },
        "query": {"rerank": False, "recency_weight": 0.0, "top_k_candidates": 5},
        "index": {
            "chroma_dir": str(chroma),
            "generation_root": str(tmp_path / "file_generations"),
            "processed_log": str(tmp_path / "processed.json"),
        },
    }
    embedding = [0.2, 0.8, 0.1, 0.3, 0.0, 0.5, 0.4, 0.9]
    store = ChromaStore(str(chroma))
    store.add_unit(
        "unit-a",
        "alpha knowledge for rehearsal",
        embedding,
        {"id": "unit-a", "title": "alpha"},
    )
    store.add_unit(
        "unit-b",
        "bravo knowledge for rehearsal",
        [0.1] * 8,
        {"id": "unit-b", "title": "bravo"},
    )
    store.close()

    started = time.perf_counter()
    direct = open_chroma_for_read(str(chroma))
    try:
        direct_rows = direct.query_units(embedding, 3)
    finally:
        direct.close()
    with open_serving_index_repository(cfg) as repo:
        gateway_rows = repo.query_units(embedding, 3)
        serving_count = repo.serving_count_units()
        physical_count = repo.physical_count_units()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    direct_ids = [row["id"] for row in direct_rows]
    gateway_ids = [row["id"] for row in gateway_rows]
    return {
        "schema": REHEARSAL_SCHEMA,
        "legacy_global": True,
        "direct_ids": direct_ids,
        "gateway_ids": gateway_ids,
        "equivalence_pass": direct_ids == gateway_ids,
        "serving_units": serving_count,
        "physical_units": physical_count,
        "elapsed_ms": round(elapsed_ms, 2),
    }


def failure_matrix_evidence() -> dict[str, list[str]]:
    """Test modules covering the T5 failure / recovery matrix."""

    return {
        "authority_races": [
            "tests/test_serving_authority.py",
            "tests/test_serving_index_repository.py",
        ],
        "source_races": [
            "tests/test_source_freshness_promotion.py",
            "tests/test_source_reconciler.py",
        ],
        "lost_notification": [
            "tests/test_source_reconciler.py::test_discover_legacy_drift_when_source_changes",
        ],
        "mixed_mode": [
            "tests/test_mixed_mode_proof.py",
            "tests/test_file_generation_read_paths.py",
        ],
        "logical_accounting": [
            "tests/test_logical_accounting.py",
            "tests/test_doctor_logical_projection.py",
        ],
        "boundary_inventory": [
            "tests/test_file_generation_read_path_inventory.py",
            "tests/test_shadow_writer_coverage_scan.py",
        ],
        "crash_recovery_pointer": [
            "tests/test_file_generation_validate.py",
            "tests/test_file_generation_pointer.py",
        ],
        "retention_restart": [
            "tests/test_mixed_mode_proof.py::test_retention_survives_restart",
            "tests/test_file_generation_store.py",
        ],
    }


def shadow_comparison_status() -> dict[str, Any]:
    return {
        "shadow_ledger": "disabled",
        "comparison_run": False,
        "reason": (
            "Shadow Phase 0 default is disabled; isolated rehearsal uses copied "
            "corpus only.  Shadow divergence gate applies at separately granted soak."
        ),
    }


def collect_execute_evidence(
    *,
    execution_plan_sha: str | None = None,
) -> dict[str, Any]:
    subject_tip = _git_sha()
    plan_sha = execution_plan_sha or _git_sha("plan/2026-08-14-cg2-production-activation")
    chroma_version = chromadb.__version__
    return {
        "schema": "convmem/cg2-execute-evidence-v1",
        "branch": subprocess.check_output(
            ["git", "branch", "--show-current"], text=True
        ).strip(),
        "subject_tip_sha": subject_tip,
        "architecture_sha": ARCHITECTURE_SHA,
        "execution_plan_sha": plan_sha,
        "chroma_version": chroma_version,
        "chroma_version_matches_pin": chroma_version == PINNED_CHROMA_VERSION,
        "property_map": build_property_map_report(),
        "budgets": measured_budgets(),
        "external_review": external_review_record(),
        "failure_matrix": failure_matrix_evidence(),
        "shadow": shadow_comparison_status(),
        "production_activation_performed": False,
        "automatic_gc_performed": False,
    }
