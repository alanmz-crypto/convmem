"""Corrective III adversarial regressions — authority-boundary closure."""
# pylint: disable=duplicate-code,protected-access,no-value-for-parameter,missing-kwoa

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import eval_corpus.r2b_v2._registry_mint as registry_mint
from eval_corpus.r2b_v2._registry_mint import (
    AuthorityHandle,
    AuthorityRegistryError,
    DiagnosticMintTicket,
    LeaseAuthorityRecord,
    compose_and_mint_source_authority,
    current_authority_epoch,
    invalidate_coverage_handle,
    invalidate_lease_handle,
    mint_lease_handle,
    register_diagnostic_ticket,
)
from eval_corpus.r2b_v2.coverage.inventory import (
    clear_inventory_scan_cache,
    verify_route_sink_evidence,
)
from eval_corpus.r2b_v2._authority_capability import verify_live_custodian_lock
from eval_corpus.r2b_v2.coverage.proof import (
    CoverageProofError,
    _source_authority_from_handle,
    prove_zero_bypass_coverage,
    source_authority_from_lease_and_coverage,
)
from eval_corpus.r2b_v2.coverage_evidence import CoverageEvidenceIdentity
from eval_corpus.r2b_v2.gate_policy import GatePolicy
from eval_corpus.r2b_v2.lease import R2bQuiescenceLeaseError, acquire_r2b_quiescence_lease
from eval_corpus.r2b_v2.lock_custodian import LockCustodianError, custodian_for_tests
from eval_corpus.r2b_v2.trusted import _reset_for_tests
from tests.r2b_v2_helpers import (
    acquire_test_lease,
    clean_coverage_bundle,
    obtain_source_authority,
    run_legitimate_source_authority_case,
)


class FakeCustodian:
    def verify(self) -> None:
        return None

    def release(self) -> None:
        return None


class R2bV2CorrectiveIIIAdversarialTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_01_forged_diagnostic_ticket_cannot_mint_trusted_coverage(self) -> None:
        forged = DiagnosticMintTicket(
            ticket_id="forged",
            evidence=CoverageEvidenceIdentity(
                code_revision="a" * 40,
                inventory_digest="inv",
                runtime_census_digest="rt",
                coverage_digest="cov",
                gate_identity="gate",
                gate_path="/tmp/gate.lock",
                gate_protocol=1,
            ),
        )
        with self.assertRaises(TypeError):
            register_diagnostic_ticket(forged, provenance_seal="forged-seal")
        with self.assertRaises(AttributeError):
            getattr(registry_mint, "mint_coverage_from_consumed_ticket")(forged)

    def test_02_fabricated_lease_record_cannot_mint_trusted_lease(self) -> None:
        record = LeaseAuthorityRecord(
            run_id="attacker",
            grant_digest="g",
            authority_digest="a",
            gate_path="/tmp/gate.lock",
            gate_inode=1,
            gate_identity="gate",
            gate_protocol=1,
            coordinator_pid=1,
            coordinator_start_time="1",
            implementation_revision="b" * 40,
            writer_coverage_digest="cov",
            open_evidence_digest="open",
            monotonic_deadline=time.monotonic() + 60,
            bound_source_paths=("/tmp",),
            phase_bounds=(),
            custodian_id="fake-custodian",
            mint_epoch=current_authority_epoch(),
            trust_class="hermetic_test",
        )
        with self.assertRaises(TypeError):
            mint_lease_handle(record)

    def test_03_fabricated_lease_and_coverage_cannot_compose_source_authority(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "fabricated-compose")
            with self.assertRaises(TypeError):
                compose_and_mint_source_authority(
                    lease_handle=AuthorityHandle("lease", "missing"),
                    coverage_handle=trusted.authority_handle,
                    open_evidence_digest=lease.bindings.open_evidence_digest,
                )
            lease.release()

    def test_04_caller_selected_gate_policy_cannot_mint_production_shaped_authority(self) -> None:
        custom = GatePolicy(
            canonical_path=Path("/tmp/attacker-gate.lock"),
            canonical_identity="attacker-gate-id",
            protocol=1,
            policy_class="production",
        )
        with tempfile.TemporaryDirectory():
            with self.assertRaises(R2bQuiescenceLeaseError):
                acquire_r2b_quiescence_lease(
                    run_id="gate-bypass",
                    grant_digest="g",
                    authority_digest="a",
                    gate_policy=custom,
                    writer_coverage_digest="cov",
                    open_evidence_digest="open",
                    monotonic_deadline=time.monotonic() + 30,
                    bound_source_paths=("/tmp",),
                    timeout_ms=1000,
                )

    def test_05_custodian_substitution_cannot_preserve_lease_verification(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = acquire_test_lease(Path(td), run_id="cust-sub-iii")
            holder = lease._holder  # pylint: disable=protected-access
            with self.assertRaises(AttributeError):
                getattr(registry_mint, "_register_lease_custodian")(
                    "cap", holder.custodian_id, FakeCustodian()
                )
            custodian_for_tests(holder).force_unlock_for_tests()
            with self.assertRaises(R2bQuiescenceLeaseError):
                lease.verify()
            lease.release()

    def test_06_coverage_lease_binding_rebind_replay_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lease_a, trusted_a, *_ = clean_coverage_bundle(root / "a", "rev-a", run_id="run-a")
            lease_b, trusted_b, *_ = clean_coverage_bundle(root / "b", "rev-b", run_id="run-b")
            try:
                obtain_source_authority(lease_a, trusted_a)
                with self.assertRaises((CoverageProofError, R2bQuiescenceLeaseError)):
                    source_authority_from_lease_and_coverage(
                        lease_b,
                        trusted_a,
                        open_evidence_digest=lease_b.bindings.open_evidence_digest,
                    )
                obtain_source_authority(lease_b, trusted_b)
            finally:
                lease_a.release()
                lease_b.release()

    def test_07_source_authority_invalid_after_lease_invalidation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "lease-cascade")
            auth = obtain_source_authority(lease, trusted)
            invalidate_lease_handle(lease.authority_handle)
            with self.assertRaises(AuthorityRegistryError):
                _ = auth.run_id

    def test_08_source_authority_invalid_after_coverage_invalidation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "cov-cascade")
            auth = obtain_source_authority(lease, trusted)
            invalidate_coverage_handle(trusted.authority_handle)
            with self.assertRaises(AuthorityRegistryError):
                _ = auth.run_id
            lease.release()

    def test_09_source_issuance_race_window_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "toctou-iii")
            holder = lease._holder  # pylint: disable=protected-access
            original = verify_live_custodian_lock
            calls = {"count": 0}

            def race_verify(custodian: Any) -> None:
                calls["count"] += 1
                if calls["count"] > 1:
                    custodian_for_tests(holder).force_unlock_for_tests()
                original(custodian)

            with mock.patch(
                "eval_corpus.r2b_v2._authority_vault.verify_live_custodian_lock",
                race_verify,
            ):
                with self.assertRaises(
                    (R2bQuiescenceLeaseError, AuthorityRegistryError, LockCustodianError)
                ):
                    source_authority_from_lease_and_coverage(
                        lease,
                        trusted,
                        open_evidence_digest=lease.bindings.open_evidence_digest,
                    )
            try:
                lease.release()
            except (R2bQuiescenceLeaseError, AuthorityRegistryError, LockCustodianError):
                pass

    def test_10_abbreviated_implementation_revision_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            chroma.mkdir()
            (root / "processed.json").write_text("{}", encoding="utf-8")
            (root / "export").mkdir()
            with self.assertRaises(CoverageProofError):
                prove_zero_bypass_coverage(
                    chroma_dir=chroma,
                    processed_path=root / "processed.json",
                    export_root=root / "export",
                    test_gate_path=root / "gate.lock",
                    code_revision="539a1cf",
                )

    def test_11_caller_manufactured_handle_cannot_reconstruct_trusted_source_proof(self) -> None:
        with self.assertRaises(AuthorityRegistryError):
            _source_authority_from_handle(AuthorityHandle("source", "forged-handle"))
        with self.assertRaises(TypeError):
            compose_and_mint_source_authority(
                lease_handle=AuthorityHandle("lease", "forged-lease"),
                coverage_handle=AuthorityHandle("coverage", "forged-coverage"),
                open_evidence_digest="open",
            )

    def test_12_new_mutation_sink_in_known_route_detected(self) -> None:
        clear_inventory_scan_cache()
        with mock.patch(
            "eval_corpus.r2b_v2.coverage.inventory._scan_route_entrypoint_mutation_sinks",
            return_value=[
                "cg2_rehearsal.py:199",
                "cg2_rehearsal.py:332",
                "cg2_rehearsal.py:382",
                "cg2_rehearsal.py:951",
                "cg2_rehearsal.py:999",
            ],
        ):
            errors = verify_route_sink_evidence()
        self.assertTrue(
            any("cg2_rehearsal" in err and "999" in err for err in errors),
            errors,
        )

    def test_direct_registry_store_mutation_forbidden(self) -> None:
        with self.assertRaises(AttributeError):
            _ = registry_mint._LEASE_RECORDS  # type: ignore[attr-defined]
        with self.assertRaises(AttributeError):
            _ = registry_mint._CUSTODIAN_REF  # type: ignore[attr-defined]
        with self.assertRaises(AttributeError):
            _ = registry_mint._REGISTRY  # type: ignore[attr-defined]
        with self.assertRaises(AttributeError):
            _ = registry_mint._TRUSTED_REGISTRY  # type: ignore[attr-defined]

    def test_legitimate_hermetic_authority_lifecycle_still_succeeds(self) -> None:
        run_legitimate_source_authority_case(self, "good-iii")

    def test_production_revision_binding_uses_full_sha(self) -> None:
        with tempfile.TemporaryDirectory():
            with self.assertRaises(R2bQuiescenceLeaseError):
                acquire_r2b_quiescence_lease(
                    run_id="rev-bind",
                    grant_digest="g",
                    authority_digest="a",
                    writer_coverage_digest="cov",
                    open_evidence_digest="open",
                    monotonic_deadline=time.monotonic() + 30,
                    bound_source_paths=("/tmp",),
                    timeout_ms=1000,
                    implementation_revision="not-a-full-sha",
                )


class R2bV2CorrectiveIIIScannerIntegrationTests(unittest.TestCase):
    def test_current_main_inventory_has_no_route_sink_drift(self) -> None:
        clear_inventory_scan_cache()
        errors = verify_route_sink_evidence()
        self.assertFalse(errors, errors)


if __name__ == "__main__":
    unittest.main()
