"""Shared hermetic fixtures for R2b v2 tests."""

from __future__ import annotations

import fcntl
import hashlib
import multiprocessing as mp
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from unittest import TestCase

from eval_corpus.r2b_v2.coverage.inventory import build_static_route_inventory
from eval_corpus.r2b_v2.coverage.proof import (
    CoverageProofError,
    DiagnosticCoverageResult,
    mint_trusted_coverage_proof,
    prove_zero_bypass_coverage,
    source_authority_from_lease_and_coverage,
)
from eval_corpus.r2b_v2.lease import (
    R2bQuiescenceLease,
    R2bQuiescenceLeaseError,
    acquire_r2b_quiescence_lease,
)
from eval_corpus.r2b_v2.lock_custodian import custodian_for_tests


def hermetic_implementation_revision(label: str) -> str:
    """Deterministic 40-char test revision for hermetic authority fixtures."""
    return hashlib.sha256(f"r2b-v2-test:{label}".encode()).hexdigest()[:40]


def acquire_test_lease(  # pylint: disable=too-many-arguments
    tmp_path: Path,
    *,
    run_id: str = "lease-run",
    grant_digest: str = "grant-a",
    authority_digest: str = "auth-a",
    coverage_digest: str = "cov-a",
    open_digest: str = "open-a",
    deadline_offset: float = 30.0,
    timeout_ms: int = 5000,
    implementation_revision: str | None = None,
) -> R2bQuiescenceLease:
    kwargs: dict = {
        "run_id": run_id,
        "grant_digest": grant_digest,
        "authority_digest": authority_digest,
        "test_lock_path": tmp_path / "gate.lock",
        "writer_coverage_digest": coverage_digest,
        "open_evidence_digest": open_digest,
        "monotonic_deadline": time.monotonic() + deadline_offset,
        "bound_source_paths": ("/tmp/export", "/tmp/processed", "/tmp/chroma"),
        "timeout_ms": timeout_ms,
    }
    if implementation_revision is not None:
        kwargs["implementation_revision"] = (
            hermetic_implementation_revision(implementation_revision)
            if len(implementation_revision) != 40
            else implementation_revision
        )
    return acquire_r2b_quiescence_lease(**kwargs)


def sample_diagnostic_coverage_result(**overrides: Any) -> DiagnosticCoverageResult:
    values = {
        "code_revision": "rev",
        "inventory_digest": "inv",
        "runtime_census_digest": "rt",
        "coverage_digest": "cov",
        "gate_identity": "gate-id",
        "gate_path": "/tmp/gate.lock",
        "gate_protocol": 1,
        "passed": True,
    }
    values.update(overrides)
    return DiagnosticCoverageResult(**values)


def _child_hold_foreign_lock(lock_path: str, ready: mp.Queue, done: mp.Queue) -> None:
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ready.put(os.getpid())
    done.get()
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


def foreign_lock_holder_process(lock_path: Path) -> tuple[mp.Process, mp.Queue, mp.Queue]:
    ready: mp.Queue = mp.Queue()
    done: mp.Queue = mp.Queue()
    proc = mp.Process(
        target=_child_hold_foreign_lock,
        args=(str(lock_path), ready, done),
    )
    return proc, ready, done


@contextmanager
def assert_source_authority_refused(
    testcase: TestCase,
    lease: R2bQuiescenceLease,
    trusted: Any,
    **kwargs: Any,
) -> Iterator[None]:
    with testcase.assertRaises(CoverageProofError):
        source_authority_from_lease_and_coverage(lease, trusted, **kwargs)
    yield


def refuse_source_authority(
    testcase: TestCase,
    root: Path,
    rev: str,
    *,
    open_evidence_digest: str = "open-bind",
    **kwargs: Any,
) -> None:
    lease, trusted, *_ = clean_coverage_bundle(root, rev)
    try:
        with assert_source_authority_refused(
            testcase,
            lease,
            trusted,
            open_evidence_digest=open_evidence_digest,
            **kwargs,
        ):
            pass
    finally:
        lease.release()


def clean_coverage_bundle(
    root: Path,
    rev: str,
    *,
    run_id: str = "bind-run",
    grant_digest: str = "grant-bind",
    authority_digest: str = "auth-bind",
    open_evidence_digest: str = "open-bind",
) -> tuple:
    revision = hermetic_implementation_revision(rev)
    chroma = root / "chroma"
    processed = root / "processed.json"
    export = root / "export"
    root.mkdir(parents=True, exist_ok=True)
    chroma.mkdir(exist_ok=True)
    export.mkdir(exist_ok=True)
    processed.write_text("{}", encoding="utf-8")
    gate = root / "gate.lock"
    inv = build_static_route_inventory(code_revision=revision)
    diag = prove_zero_bypass_coverage(
        chroma_dir=chroma,
        processed_path=processed,
        export_root=export,
        test_gate_path=gate,
        code_revision=revision,
        static_inventory=inv,
    )
    trusted = mint_trusted_coverage_proof(diag)
    lease = acquire_r2b_quiescence_lease(
        run_id=run_id,
        grant_digest=grant_digest,
        authority_digest=authority_digest,
        test_lock_path=gate,
        writer_coverage_digest=trusted.coverage_digest,
        open_evidence_digest=open_evidence_digest,
        monotonic_deadline=time.monotonic() + 30,
        bound_source_paths=(str(export), str(processed), str(chroma)),
        timeout_ms=5000,
        implementation_revision=revision,
    )
    return lease, trusted, chroma, processed, export, gate


def obtain_source_authority(lease: R2bQuiescenceLease, trusted: Any) -> Any:
    return source_authority_from_lease_and_coverage(
        lease,
        trusted,
        open_evidence_digest=lease.bindings.open_evidence_digest,
    )


def assert_legitimate_source_authority(
    testcase: TestCase,
    lease: R2bQuiescenceLease,
    trusted: Any,
    *,
    run_id: str = "bind-run",
) -> Any:
    auth = obtain_source_authority(lease, trusted)
    testcase.assertEqual(auth.run_id, run_id)
    testcase.assertTrue(auth.gate_held)
    return auth


def run_legitimate_source_authority_case(testcase: TestCase, rev: str) -> None:
    with tempfile.TemporaryDirectory() as td:
        lease, trusted, *_ = clean_coverage_bundle(Path(td), rev)
        try:
            assert_legitimate_source_authority(testcase, lease, trusted)
        finally:
            lease.release()


def refuse_wrong_open_evidence_case(testcase: TestCase) -> None:
    with tempfile.TemporaryDirectory() as td:
        refuse_source_authority(
            testcase,
            Path(td),
            "bind-open",
            open_evidence_digest="wrong-open",
        )


def run_dual_coverage_chain_case(testcase: TestCase, exercise: Any) -> None:
    with tempfile.TemporaryDirectory() as td:
        with dual_coverage_chains(Path(td), "rev-a", "rev-b") as chains:
            exercise(testcase, *chains)


def assert_custodian_force_unlock_breaks_verify(
    testcase: TestCase,
    lease: R2bQuiescenceLease,
) -> None:
    holder = lease._holder  # pylint: disable=protected-access
    custodian_for_tests(holder).force_unlock_for_tests()
    with testcase.assertRaises(R2bQuiescenceLeaseError):
        lease.verify()


@contextmanager
def dual_coverage_chains(
    root: Path,
    rev_a: str,
    rev_b: str,
    *,
    run_a: str = "run-a",
    run_b: str = "run-b",
) -> Iterator[tuple[R2bQuiescenceLease, Any, R2bQuiescenceLease, Any]]:
    lease_a, trusted_a, *_ = clean_coverage_bundle(root / "a", rev_a, run_id=run_a)
    lease_b, trusted_b, *_ = clean_coverage_bundle(root / "b", rev_b, run_id=run_b)
    try:
        yield lease_a, trusted_a, lease_b, trusted_b
    finally:
        lease_a.release()
        lease_b.release()


def scratch_benchmark_candidate_policy() -> "DurationPolicy":
    """Sol conditional candidates for scratch tests only — not production acceptance."""
    from eval_corpus.r2b_v2.duration_policy import DurationPolicy

    return DurationPolicy(
        acquisition_bound=30.0,
        hitl_reservation_bound=600.0,
        capture_bound=120.0,
        release_close_bound=20.0,
        transaction_deadline=800.0,
    )


def scratch_transaction_fixture(
    tmp_path: Path,
    *,
    run_id: str = "scratch-i456",
    rev: str = "i456-rev",
) -> dict[str, Any]:
    """Hermetic I4–I6 scratch bundle under tmp_path."""
    from eval_corpus.capture import recompute_source_snapshot
    from tests.r2b_hermetic import capture_runtime, r2b_auth_dir, r2b_source_paths

    root = tmp_path
    paths = r2b_source_paths(root, run_id=run_id)
    lease, trusted, *_ = clean_coverage_bundle(
        root / "bundle",
        rev,
        run_id=run_id,
        open_evidence_digest="open-scratch",
    )
    revision = hermetic_implementation_revision(rev)
    return {
        "root": root,
        "run_id": run_id,
        "paths": paths,
        "auth_dir": r2b_auth_dir(root, run_id),
        "runtime": capture_runtime(paths),
        "lease": lease,
        "trusted": trusted,
        "open_evidence_digest": "open-scratch",
        "gate_identity": trusted.gate_identity,
        "implementation_revision": revision,
        "future_argv": ["convmem", "capture", "--scratch"],
        "snapshot_recompute_fn": recompute_source_snapshot,
    }


def advance_to_packet_accepted(
    fx: dict[str, Any],
    sm: "AuthorityStateMachine",
) -> Path:
    """Hermetic helper: COVERAGE_PROVEN through PACKET_ACCEPTED (no materialize)."""
    from eval_corpus.r2b_v2.authority_state import (
        AuthorityState,
        transition_to_coverage_proven,
        transition_to_q_held,
    )
    from eval_corpus.r2b_v2.packet import (
        accept_capture_packet,
        compute_trusted_snapshot,
        draft_capture_packet,
        transition_snapshot_bound,
    )

    sm.transition(AuthorityState.PREPARED, reason="test prepare")
    sm.transition(AuthorityState.Q_AUTHORIZED, reason="test authorize")
    transition_to_q_held(sm, fx["lease"], reason="test held")
    transition_to_coverage_proven(
        sm, fx["lease"], fx["trusted"], reason="test coverage"
    )
    transition_snapshot_bound(
        sm,
        fx["lease"],
        obtain_source_authority(fx["lease"], fx["trusted"]),
        reason="bind",
    )
    snap = compute_trusted_snapshot(
        fx["lease"],
        export=Path(fx["paths"]["export"]),
        processed=Path(fx["paths"]["processed"]),
        chroma_dir=Path(fx["paths"]["chroma_dir"]),
        snapshot_recompute_fn=fx["snapshot_recompute_fn"],
    )
    manifest_path = draft_capture_packet(
        sm,
        fx["lease"],
        fx["trusted"],
        auth_dir=fx["auth_dir"],
        paths=fx["paths"],
        source_snapshot=snap,
        duration_policy=scratch_benchmark_candidate_policy(),
        future_argv=fx["future_argv"],
        open_evidence_digest=fx["open_evidence_digest"],
        gate_identity=fx["gate_identity"],
        implementation_revision=fx["implementation_revision"],
    )
    accept_capture_packet(sm, fx["lease"], manifest_path)
    return manifest_path


def advance_to_materialized(
    fx: dict[str, Any],
    sm: "AuthorityStateMachine",
) -> tuple[Path, "V2MaterializationResult"]:
    """Hermetic helper: COVERAGE_PROVEN through MATERIALIZED."""
    from eval_corpus.r2b_v2.materialization import V2MaterializationResult, materialize_v2_packet

    manifest_path = advance_to_packet_accepted(fx, sm)
    mat = materialize_v2_packet(
        sm,
        fx["lease"],
        manifest_path,
        runtime=fx["runtime"],
        snapshot_recompute_fn=fx["snapshot_recompute_fn"],
        restic_gate_fn=lambda: None,
    )
    return manifest_path, mat
