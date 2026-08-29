"""Adversarial hermetic tests for R2b v2 opaque quiescence lease (I2)."""

from __future__ import annotations

import multiprocessing as mp
import os
import tempfile
import time
import unittest
from pathlib import Path

from chroma_write_store import current_code_revision

from eval_corpus.r2b_v2.lease import (
    R2bQuiescenceLeaseError,
    acquire_r2b_quiescence_lease,
    attempt_pickle_roundtrip,
    duplicate_lease_via_copy,
    extend_lease_deadline,
    lease_from_serialized_payload,
    verify_r2b_quiescence_lease,
)


def _acquire(
    tmp_path: Path,
    *,
    run_id: str = "lease-run",
    grant_digest: str = "grant-a",
    coverage_digest: str = "cov-a",
    open_digest: str = "open-a",
    revision: str | None = None,
    deadline_offset: float = 30.0,
) -> "R2bQuiescenceLease":
    from eval_corpus.r2b_v2.lease import R2bQuiescenceLease
    rev = revision or current_code_revision()
    return acquire_r2b_quiescence_lease(
        run_id=run_id,
        grant_digest=grant_digest,
        authority_digest="auth-a",
        lock_path=tmp_path / "gate.lock",
        writer_coverage_digest=coverage_digest,
        open_evidence_digest=open_digest,
        monotonic_deadline=time.monotonic() + deadline_offset,
        bound_source_paths=("/tmp/export", "/tmp/processed", "/tmp/chroma"),
        implementation_revision=rev,
    )


class R2bV2LeaseTests(unittest.TestCase):
    def test_acquire_and_verify_hermetic_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = _acquire(Path(td))
            verify_r2b_quiescence_lease(lease, expected_run_id="lease-run")
            lease.release()

    def test_forged_capability_type_refused(self) -> None:
        with self.assertRaises(R2bQuiescenceLeaseError):
            verify_r2b_quiescence_lease(object())  # type: ignore[arg-type]

    def test_serialized_reconstruction_refused(self) -> None:
        with self.assertRaises(R2bQuiescenceLeaseError):
            lease_from_serialized_payload({"run_id": "x", "gate_held": True})

    def test_boolean_authority_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = _acquire(Path(td))
            with self.assertRaises(R2bQuiescenceLeaseError):
                bool(lease)
            lease.release()

    def test_pickle_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = _acquire(Path(td))
            with self.assertRaises(R2bQuiescenceLeaseError):
                attempt_pickle_roundtrip(lease)
            lease.release()

    def test_copy_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = _acquire(Path(td))
            with self.assertRaises(R2bQuiescenceLeaseError):
                duplicate_lease_via_copy(lease)
            lease.release()

    def test_wrong_grant_digest_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = _acquire(Path(td), grant_digest="grant-a")
            with self.assertRaises(R2bQuiescenceLeaseError):
                verify_r2b_quiescence_lease(lease, expected_grant_digest="other")
            lease.release()

    def test_wrong_implementation_revision_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = _acquire(Path(td), revision="rev-a")
            with self.assertRaises(R2bQuiescenceLeaseError):
                verify_r2b_quiescence_lease(
                    lease, expected_implementation_revision="rev-b"
                )
            lease.release()

    def test_deadline_extension_refused(self) -> None:
        with self.assertRaises(R2bQuiescenceLeaseError):
            extend_lease_deadline()

    def test_expired_lease_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = _acquire(Path(td), deadline_offset=0.01)
            time.sleep(0.05)
            with self.assertRaises(R2bQuiescenceLeaseError):
                lease.verify()
            lease.release()

    def test_lost_kernel_ownership_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = _acquire(Path(td))
            lease.release()
            with self.assertRaises(R2bQuiescenceLeaseError):
                lease.verify()

    def test_cross_run_reuse_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = _acquire(Path(td), run_id="run-a")
            with self.assertRaises(R2bQuiescenceLeaseError):
                verify_r2b_quiescence_lease(lease, expected_run_id="run-b")
            lease.release()


def _child_hold_lock(lock_path: str, ready: mp.Queue, done: mp.Queue) -> None:
    import fcntl

    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ready.put(os.getpid())
    done.get()
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


class R2bV2LeaseProcessTests(unittest.TestCase):
    def test_alternate_holder_blocks_acquire(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "gate.lock"
            ready: mp.Queue = mp.Queue()
            done: mp.Queue = mp.Queue()
            proc = mp.Process(target=_child_hold_lock, args=(str(lock), ready, done))
            proc.start()
            try:
                ready.get(timeout=5)
                with self.assertRaises((TimeoutError, R2bQuiescenceLeaseError)):
                    acquire_r2b_quiescence_lease(
                        run_id="blocked",
                        grant_digest="g",
                        authority_digest="a",
                        lock_path=lock,
                        writer_coverage_digest="c",
                        open_evidence_digest="o",
                        monotonic_deadline=time.monotonic() + 5,
                        bound_source_paths=("/tmp/x",),
                        timeout_ms=200,
                    )
            finally:
                done.put(True)
                proc.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
