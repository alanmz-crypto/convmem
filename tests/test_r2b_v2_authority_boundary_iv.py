"""Corrective IV adversarial regressions — possession-based authority boundary."""
# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import importlib
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import eval_corpus.r2b_v2._registry_mint as registry_mint
from eval_corpus.r2b_v2._authority_capability import (
    AuthorityCapabilityError,
    AuthorityMintCapability,
    MintPhase,
    issue_census_capability,
)
from eval_corpus.r2b_v2._registry_mint import (
    AuthorityHandle,
    AuthorityRegistryError,
    DiagnosticMintTicket,
    LeaseAuthorityRecord,
    compose_and_mint_source_authority,
    current_authority_epoch,
    finalize_diagnostic_and_mint_coverage,
    mint_lease_handle,
    register_diagnostic_ticket,
)
from eval_corpus.r2b_v2.coverage.inventory import (
    clear_inventory_scan_cache,
    verify_route_sink_evidence,
)
from eval_corpus.r2b_v2.coverage.proof import (
    CoverageProofError,
    mint_trusted_coverage_proof,
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
    run_legitimate_source_authority_case,
    sample_diagnostic_coverage_result,
    obtain_source_authority,
)


class FakeCustodian:
    lock_path = "/tmp/gate.lock"
    inode = 1

    def verify(self) -> None:
        return None

    def release(self) -> None:
        return None


def _forged_capability() -> AuthorityMintCapability:
    """Attempt to manufacture a capability object without canonical issuance."""
    cap = object.__new__(AuthorityMintCapability)
    cap._issuer_secret = b"forged-secret"  # pylint: disable=attribute-defined-outside-init
    cap._phase = MintPhase.CENSUS  # pylint: disable=attribute-defined-outside-init
    cap._binding_digest = "forged"  # pylint: disable=attribute-defined-outside-init
    cap._capability_id = "forged-id"  # pylint: disable=attribute-defined-outside-init
    cap._trust_class = "production"  # pylint: disable=attribute-defined-outside-init
    cap._census_stage = 0  # pylint: disable=attribute-defined-outside-init
    return cap


class R2bV2CorrectiveIVAdversarialTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_01_ordinary_caller_cannot_invoke_census_mint_window(self) -> None:
        with self.assertRaises(AttributeError):
            getattr(registry_mint, "census_mint_window")(coverage_digest="cov")

    def test_02_ordinary_caller_cannot_invoke_lease_acquisition_window(self) -> None:
        with self.assertRaises(AttributeError):
            getattr(registry_mint, "lease_acquisition_window")()

    def test_03_ordinary_caller_cannot_invoke_source_composition_window(self) -> None:
        with self.assertRaises(AttributeError):
            getattr(registry_mint, "source_composition_window")()

    def test_04_direct_registry_backing_unreachable(self) -> None:
        with self.assertRaises(AttributeError):
            _ = registry_mint._REGISTRY  # type: ignore[attr-defined]
        with self.assertRaises(AttributeError):
            _ = registry_mint._TRUSTED_REGISTRY  # type: ignore[attr-defined]
        with self.assertRaises(AttributeError):
            _ = registry_mint._FACADE  # type: ignore[attr-defined]
        isolated = registry_mint._TrustedRegistry()  # type: ignore[attr-defined]
        store = isolated._lease_records  # pylint: disable=protected-access
        with self.assertRaises(AuthorityRegistryError):
            store["attacker"] = "payload"

    def test_05_fake_gate_policy_cannot_mint_production_equivalent_authority(self) -> None:
        attacker_policy = GatePolicy(
            canonical_path=Path("/tmp/attacker-gate.lock"),
            canonical_identity="attacker-gate",
            protocol=1,
            policy_class="production",
        )
        with tempfile.TemporaryDirectory():
            with self.assertRaises(R2bQuiescenceLeaseError):
                acquire_r2b_quiescence_lease(
                    run_id="fake-gate",
                    grant_digest="g",
                    authority_digest="a",
                    gate_policy=attacker_policy,
                    writer_coverage_digest="cov",
                    open_evidence_digest="open",
                    monotonic_deadline=time.monotonic() + 30,
                    bound_source_paths=("/tmp",),
                    timeout_ms=1000,
                )

    def test_06_arbitrary_revision_override_cannot_mint_production_equivalent(self) -> None:
        with tempfile.TemporaryDirectory():
            with self.assertRaises(R2bQuiescenceLeaseError):
                acquire_r2b_quiescence_lease(
                    run_id="rev-override",
                    grant_digest="g",
                    authority_digest="a",
                    writer_coverage_digest="cov",
                    open_evidence_digest="open",
                    monotonic_deadline=time.monotonic() + 30,
                    bound_source_paths=("/tmp",),
                    timeout_ms=1000,
                    implementation_revision="not-a-full-sha",
                )

    def test_07_fake_custodian_installation_cannot_preserve_authority(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = acquire_test_lease(Path(td), run_id="fake-custodian")
            holder = lease._holder  # pylint: disable=protected-access
            with self.assertRaises(AttributeError):
                getattr(registry_mint, "_register_lease_custodian")(
                    _forged_capability(), holder.custodian_id, FakeCustodian()
                )
            custodian_for_tests(holder).force_unlock_for_tests()
            with self.assertRaises(R2bQuiescenceLeaseError):
                lease.verify()
            lease.release()

    def test_08_source_authority_fails_after_kernel_lock_loss(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "lock-loss")
            auth = obtain_source_authority(lease, trusted)
            custodian_for_tests(lease._holder).force_unlock_for_tests()  # pylint: disable=protected-access
            with self.assertRaises((AuthorityRegistryError, LockCustodianError)):
                _ = auth.run_id
            lease.release()

    def test_09_source_authority_fails_after_custodian_release(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "cust-release")
            auth = obtain_source_authority(lease, trusted)
            lease.release()
            with self.assertRaises((AuthorityRegistryError, LockCustodianError)):
                _ = auth.run_id

    def test_10_forged_capability_cannot_mint_lease_coverage_or_source(self) -> None:
        forged = _forged_capability()
        ticket = DiagnosticMintTicket(
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
        with self.assertRaises(AuthorityCapabilityError):
            register_diagnostic_ticket(forged, ticket, provenance_seal="seal")
        with self.assertRaises(AuthorityCapabilityError):
            finalize_diagnostic_and_mint_coverage(
                forged,
                "ticket",
                coverage_digest="cov",
                provenance_seal="seal",
                gate_identity="gate",
                code_revision="a" * 40,
            )
        record = LeaseAuthorityRecord(
            run_id="r",
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
            custodian_id="c",
            mint_epoch=current_authority_epoch(),
            trust_class="hermetic_test",
        )
        with self.assertRaises(AuthorityCapabilityError):
            mint_lease_handle(forged, record, custodian=FakeCustodian())
        with self.assertRaises(AuthorityCapabilityError):
            compose_and_mint_source_authority(
                forged,
                lease_handle=AuthorityHandle("lease", "l"),
                coverage_handle=AuthorityHandle("coverage", "c"),
                open_evidence_digest="open",
            )

    def test_11_capability_cannot_be_constructed_copied_or_replayed(self) -> None:
        with self.assertRaises(AuthorityCapabilityError):
            AuthorityMintCapability()
        cap = _forged_capability()
        with self.assertRaises(AuthorityCapabilityError):
            cap.__copy__()
        with self.assertRaises(AuthorityCapabilityError):
            cap.__reduce__()
        with self.assertRaises(AuthorityCapabilityError):
            issue_census_capability(
                coverage_digest="cov",
                gate_identity="gate",
                code_revision="a" * 40,
                trust_class="production",
            )

    def test_12_new_mutation_sink_in_known_file_detected(self) -> None:
        clear_inventory_scan_cache()
        with mock.patch(
            "eval_corpus.r2b_v2.coverage.inventory._scan_route_entrypoint_mutation_sinks",
            return_value=[
                "cg2_rehearsal.py:199",
                "cg2_rehearsal.py:332",
                "cg2_rehearsal.py:382",
                "cg2_rehearsal.py:951",
                "cg2_rehearsal.py:888",
            ],
        ):
            errors = verify_route_sink_evidence()
        self.assertTrue(
            any("888" in err for err in errors),
            errors,
        )

    def test_13_ordinary_import_surface_adversarial_audit(self) -> None:
        pkg = importlib.import_module("eval_corpus.r2b_v2")
        mint_mod = importlib.import_module("eval_corpus.r2b_v2._registry_mint")
        forbidden = (
            "census_mint_window",
            "lease_acquisition_window",
            "source_composition_window",
            "_REGISTRY",
            "_TRUSTED_REGISTRY",
        )
        for name in forbidden:
            with self.assertRaises(AttributeError):
                getattr(mint_mod, name)
        self.assertNotIn("census_mint_window", pkg.__all__ if hasattr(pkg, "__all__") else [])

    def test_14_diagnostic_without_canonical_capability_cannot_mint(self) -> None:
        diag = sample_diagnostic_coverage_result(
            _mint_ticket="ticket",
            _provenance_seal="seal",
        )
        with self.assertRaises(CoverageProofError):
            mint_trusted_coverage_proof(diag)

    def test_15_legitimate_canonical_lifecycle_still_succeeds(self) -> None:
        run_legitimate_source_authority_case(self, "good-iv")

    def test_16_source_survival_reaudit_after_prerequisite_loss(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "survival")
            auth = obtain_source_authority(lease, trusted)
            self.assertEqual(auth.run_id, "bind-run")
            registry_mint.invalidate_coverage_handle(trusted.authority_handle)
            with self.assertRaises(AuthorityRegistryError):
                _ = auth.coverage_digest
            lease.release()


class R2bV2CorrectiveIVScannerIntegrationTests(unittest.TestCase):
    def test_current_main_inventory_has_no_route_sink_drift(self) -> None:
        clear_inventory_scan_cache()
        errors = verify_route_sink_evidence()
        self.assertFalse(errors, errors)


if __name__ == "__main__":
    unittest.main()
