"""Shared hermetic fixtures for R2b v2 tests."""

from __future__ import annotations

import fcntl
import multiprocessing as mp
import os
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
from eval_corpus.r2b_v2.lease import R2bQuiescenceLease, acquire_r2b_quiescence_lease


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
        kwargs["implementation_revision"] = implementation_revision
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
    chroma = root / "chroma"
    processed = root / "processed.json"
    export = root / "export"
    root.mkdir(parents=True, exist_ok=True)
    chroma.mkdir(exist_ok=True)
    export.mkdir(exist_ok=True)
    processed.write_text("{}", encoding="utf-8")
    gate = root / "gate.lock"
    inv = build_static_route_inventory(code_revision=rev)
    diag = prove_zero_bypass_coverage(
        chroma_dir=chroma,
        processed_path=processed,
        export_root=export,
        test_gate_path=gate,
        code_revision=rev,
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
        implementation_revision=rev,
    )
    return lease, trusted, chroma, processed, export, gate
