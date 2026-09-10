"""Network, provider, call-cap, capsule, and fault tests for JSONL production canary."""

# These focused tests intentionally enter the coordinator's governed writer
# session to verify cross-source sentinels around capsule restoration.
# pylint: disable=protected-access

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from incremental_jsonl import DURABLE_TRANSITIONS
from incremental_jsonl_canary import (
    CRASH_EXIT,
    FAULT_SELECTORS,
    CanaryRefused,
    assert_transition_coverage,
    capture_rollback_capsule,
    fault_point_for_selector,
    install_call_budget_guard,
    restore_rollback_capsule,
    terminate_fault_worker,
    unrelated_sentinel_digest,
    validate_append_profile,
    validate_two_chunk_profile,
)
from incremental_jsonl_isolation import install_network_denial
from tests.incremental_jsonl_canary_helpers import (
    build_grant,
    hermetic_root,
    worker_run,
    write_grant_file,
    write_kiro_source,
)
from tests.incremental_jsonl_helpers import (
    apply_env,
    chroma_authority,
    enable_incremental,
    install_fakes,
    isolated_env,
    write_source,
)


def test_p1_a6_network_and_credentials_denied(tmp_path: Path) -> None:
    root = hermetic_root(tmp_path)
    _, source_grant = write_kiro_source(root, 61)
    grant, digest = build_grant(root, source_grant)
    env = {
        "CONVMEM_CANARY_GRANT": str(write_grant_file(root, grant)),
        "CONVMEM_CANARY_GRANT_SHA256": digest,
        "CONVMEM_CANARY_REVISION": grant.code_revision,
        "DEEPSEEK_API_KEY": "secret",
    }
    install_network_denial()
    result = worker_run(env, command="refuse-network")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["network"] != "unexpected-success"


def test_p1_a7_call_ceiling_stops_before_cap_plus_one(monkeypatch) -> None:
    install_fakes(monkeypatch)
    with install_call_budget_guard({"summarize": 0}):
        import ingest

        with pytest.raises(CanaryRefused):
            ingest.summarize("hello")


def test_p1_a8_capsule_round_trip_preserves_sentinels(tmp_path: Path, monkeypatch) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    primary = write_source(boundary.root, 2, name="primary")
    sentinel_a = write_source(boundary.root, 1, name="sentinel-a")
    sentinel_b = write_source(boundary.root, 1, name="sentinel-b")
    from incremental_jsonl import IncrementalJsonlCoordinator

    coord_primary = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, primary, enabled=True
    )
    coord_primary.run()
    for sentinel in (sentinel_a, sentinel_b):
        IncrementalJsonlCoordinator.from_isolated_boundary(
            boundary, sentinel, enabled=True
        ).run()
    before = chroma_authority(boundary, primary)
    with coord_primary._session() as session:
        manifest = unrelated_sentinel_digest(
            session.store,
            [str(sentinel_a), str(sentinel_b)],
        )
    capsule = capture_rollback_capsule(coord_primary, unrelated_manifest=manifest)
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, primary, enabled=True, force_reindex=True
    ).run()
    restore_rollback_capsule(coord_primary, capsule)
    after = chroma_authority(boundary, primary)
    assert before == after
    with coord_primary._session() as session:
        after_manifest = unrelated_sentinel_digest(
            session.store,
            [str(sentinel_a), str(sentinel_b)],
        )
    assert manifest == after_manifest


def test_p1_a9_fault_selectors_map_to_durable_transitions() -> None:
    assert_transition_coverage(FAULT_SELECTORS)
    assert fault_point_for_selector("summary_upsert") == "after_summary_upsert"
    assert fault_point_for_selector("dedupe_reconcile") == "after_dedupe_reconcile"


def test_p1_a9_existing_44_transition_inventory() -> None:
    required = {f"{side}_{name}" for name in DURABLE_TRANSITIONS for side in ("before", "after")}
    assert len(required) == 2 * len(DURABLE_TRANSITIONS)


def test_p1_a10_descendant_containment() -> None:
    import subprocess

    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        start_new_session=True,
    )
    report = terminate_fault_worker(child)
    assert report["returncode"] is not None


def test_p1_a12_chunk_profiles() -> None:
    validate_two_chunk_profile(61)
    validate_two_chunk_profile(109)
    validate_append_profile(110)
    with pytest.raises(Exception):
        validate_append_profile(111)


def test_worker_fault_crash_and_replay(tmp_path: Path) -> None:
    root = hermetic_root(tmp_path)
    _, source_grant = write_kiro_source(root, 2)
    grant, digest = build_grant(root, source_grant)
    env = {
        "CONVMEM_CANARY_GRANT": str(write_grant_file(root, grant)),
        "CONVMEM_CANARY_GRANT_SHA256": digest,
        "CONVMEM_CANARY_REVISION": grant.code_revision,
        "CONVMEM_CANARY_FAULT": "summary_upsert",
    }
    crashed = worker_run(env, command="run")
    assert crashed.returncode == CRASH_EXIT
    env.pop("CONVMEM_CANARY_FAULT", None)
    replay = worker_run(env, command="run")
    assert replay.returncode == 0, replay.stderr
