"""Corrective V adversarial regressions — structural authority-boundary closure."""
# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import copy
import importlib
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import eval_corpus.r2b_v2._authority_vault as authority_vault
import eval_corpus.r2b_v2._registry_mint as registry_mint
from eval_corpus.r2b_v2._authority_capability import (
    AuthorityCapabilityError,
    AuthorityMintCapability,
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
)
from eval_corpus.r2b_v2.coverage_evidence import CoverageEvidenceIdentity
from eval_corpus.r2b_v2.gate_policy import production_gate_policy
from eval_corpus.r2b_v2.lease import R2bQuiescenceLeaseError, acquire_r2b_quiescence_lease
from eval_corpus.r2b_v2.lock_custodian import LockCustodianError, custodian_for_tests
from eval_corpus.r2b_v2.trusted import _reset_for_tests
from tests.r2b_v2_helpers import (
    acquire_test_lease,
    clean_coverage_bundle,
    run_legitimate_source_authority_case,
    obtain_source_authority,
    sample_diagnostic_coverage_result,
)


class FakeCustodian:
    lock_path = "/tmp/gate.lock"
    inode = 1

    def verify(self) -> None:
        return None

    def release(self) -> None:
        return None


def _forged_capability() -> AuthorityMintCapability:
    """Attempt to manufacture a capability object without vault issuance."""
    cap = object.__new__(AuthorityMintCapability)
    cap._capability_id = "forged-id"  # pylint: disable=attribute-defined-outside-init
    return cap


class R2bV2CorrectiveVAdversarialTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_01_ordinary_import_cannot_manufacture_production_mint_capability(self) -> None:
        with self.assertRaises(AuthorityCapabilityError):
            AuthorityMintCapability()
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
            issue_census_capability(
                coverage_digest="cov",
                gate_identity="gate",
                code_revision="a" * 40,
                trust_class="production",
            )

    def test_02_reflection_cannot_obtain_mutable_production_registry(self) -> None:
        mint_forbidden = (
            "_TrustedRegistry",
            "_REGISTRY",
            "_VAULT",
        )
        for name in mint_forbidden:
            with self.assertRaises(AttributeError):
                getattr(registry_mint, name)
        with self.assertRaises(AttributeError):
            getattr(authority_vault, "_build_vault")
        self.assertIsNone(authority_vault.vault_dispatch("probe_closure_registry_mutation"))

    def test_03_caller_substitutes_cannot_become_production_custodians(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = acquire_test_lease(Path(td), run_id="fake-custodian-v")
            holder = lease._holder  # pylint: disable=protected-access
            with self.assertRaises(AttributeError):
                getattr(registry_mint, "_register_lease_custodian")(
                    _forged_capability(), holder.custodian_id, FakeCustodian()
                )
            custodian_for_tests(holder).force_unlock_for_tests()
            with self.assertRaises(R2bQuiescenceLeaseError):
                lease.verify()
            lease.release()

    def test_04_production_authority_cannot_bind_to_stale_inventory_revision(self) -> None:
        stale = "0" * 40
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            chroma.mkdir()
            (root / "processed.json").write_text("{}", encoding="utf-8")
            (root / "export").mkdir()
            with mock.patch(
                "eval_corpus.r2b_v2.coverage.proof.load_v2_implementation_tip",
                return_value=stale,
            ), mock.patch(
                "eval_corpus.r2b_v2.coverage.proof.current_code_revision",
                return_value="f" * 40,
            ):
                with self.assertRaises(CoverageProofError):
                    prove_zero_bypass_coverage(
                        chroma_dir=chroma,
                        processed_path=root / "processed.json",
                        export_root=root / "export",
                        gate_policy=production_gate_policy(),
                        skip_runtime=True,
                    )
            with mock.patch(
                "eval_corpus.r2b_v2.lease.load_v2_implementation_tip",
                return_value=stale,
            ), mock.patch(
                "eval_corpus.r2b_v2.lease.current_code_revision",
                return_value="f" * 40,
            ):
                with self.assertRaises(R2bQuiescenceLeaseError):
                    acquire_r2b_quiescence_lease(
                        run_id="stale-rev",
                        grant_digest="g",
                        authority_digest="a",
                        writer_coverage_digest="cov",
                        open_evidence_digest="open",
                        monotonic_deadline=time.monotonic() + 30,
                        bound_source_paths=("/tmp",),
                        timeout_ms=1000,
                    )

    def test_05_new_mutation_sink_in_governed_file_detected_not_suppressed(self) -> None:
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
        self.assertTrue(any("888" in err for err in errors), errors)

    def test_06_lock_loss_and_issuance_toctou_properties_remain_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "lock-loss-v")
            auth = obtain_source_authority(lease, trusted)
            custodian_for_tests(lease._holder).force_unlock_for_tests()  # pylint: disable=protected-access
            with self.assertRaises((AuthorityRegistryError, LockCustodianError)):
                _ = auth.run_id
            lease.release()

        _reset_for_tests()
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(
                Path(td), "toctou-v", run_id="toctou-run-v"
            )
            holder = lease._holder  # pylint: disable=protected-access
            original = registry_mint.verify_live_custodian_lock
            calls = {"count": 0}

            def race_verify(custodian):
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
                    obtain_source_authority(lease, trusted)
            try:
                lease.release()
            except (R2bQuiescenceLeaseError, AuthorityRegistryError, LockCustodianError):
                pass

    def test_07_forged_capability_cannot_mint_lease_coverage_or_source(self) -> None:
        forged = _forged_capability()
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
        with self.assertRaises(AuthorityCapabilityError):
            finalize_diagnostic_and_mint_coverage(
                forged,
                "ticket",
                coverage_digest="cov",
                provenance_seal="seal",
                gate_identity="gate",
                code_revision="a" * 40,
            )

    def test_08_capability_cannot_be_copied_or_serialized(self) -> None:
        forged = _forged_capability()
        with self.assertRaises(AuthorityCapabilityError):
            copy.copy(forged)
        with self.assertRaises(AuthorityCapabilityError):
            forged.__reduce__()

    def test_09_ordinary_import_surface_adversarial_audit(self) -> None:
        pkg = importlib.import_module("eval_corpus.r2b_v2")
        mint_mod = importlib.import_module("eval_corpus.r2b_v2._registry_mint")
        forbidden = (
            "census_mint_window",
            "lease_acquisition_window",
            "source_composition_window",
            "_REGISTRY",
            "_TRUSTED_REGISTRY",
            "_TrustedRegistry",
            "_VAULT",
        )
        for name in forbidden:
            with self.assertRaises(AttributeError):
                getattr(mint_mod, name)
        self.assertNotIn("census_mint_window", pkg.__all__ if hasattr(pkg, "__all__") else [])

    def test_10_hermetic_revision_still_works_for_canonical_lifecycle(self) -> None:
        run_legitimate_source_authority_case(self, "good-v")

    def test_11_diagnostic_without_canonical_capability_cannot_mint(self) -> None:
        diag = sample_diagnostic_coverage_result(
            _mint_ticket="ticket",
            _provenance_seal="seal",
        )
        with self.assertRaises(CoverageProofError):
            mint_trusted_coverage_proof(diag)

    def test_12_no_module_level_issuer_secret(self) -> None:
        cap_mod = importlib.import_module("eval_corpus.r2b_v2._authority_capability")
        vault_mod = importlib.import_module("eval_corpus.r2b_v2._authority_vault")
        self.assertFalse(hasattr(cap_mod, "_CAPABILITY_ISSUER_SECRET"))
        self.assertFalse(hasattr(vault_mod, "_CAPABILITY_ISSUER_SECRET"))


class R2bV2CorrectiveVScannerIntegrationTests(unittest.TestCase):
    def test_current_main_inventory_has_no_route_sink_drift(self) -> None:
        clear_inventory_scan_cache()
        errors = verify_route_sink_evidence()
        self.assertFalse(errors, errors)


if __name__ == "__main__":
    unittest.main()
