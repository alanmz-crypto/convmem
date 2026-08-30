"""Authority-boundary adjudication and corrective regressions for R2b v2 I1-I3."""
# pylint: disable=duplicate-code

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from eval_corpus.r2b_v2._registry_mint import (
    DiagnosticMintTicket,
    mint_coverage_from_consumed_ticket,
    register_diagnostic_ticket,
)
from eval_corpus.r2b_v2.authority_registry import AuthorityRegistryError, invalidate_all_authority
from eval_corpus.r2b_v2.coverage.inventory import build_static_route_inventory, verify_inventory_matches_tip
from eval_corpus.r2b_v2.coverage.proof import (
    CoverageProofError,
    SourceAuthorityProof,
    attempt_forge_source_authority_proof,
    mint_trusted_coverage_proof,
    prove_zero_bypass_coverage,
    source_authority_from_lease_and_coverage,
)
from eval_corpus.r2b_v2.coverage_evidence import CoverageEvidenceIdentity
from eval_corpus.r2b_v2.lease import R2bQuiescenceLeaseError
from eval_corpus.r2b_v2.lock_custodian import custodian_for_tests
from eval_corpus.r2b_v2.trusted import _reset_for_tests
from tests.r2b_v2_helpers import (
    acquire_test_lease,
    assert_custodian_force_unlock_breaks_verify,
    clean_coverage_bundle,
    obtain_source_authority,
    refuse_wrong_open_evidence_case,
    run_dual_coverage_chain_case,
    run_legitimate_source_authority_case,
    sample_diagnostic_coverage_result,
    hermetic_implementation_revision,
)


class R2bV2AuthorityBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_public_mint_bypass_refused(self) -> None:
        """Probe 1: Kiro direct mint_coverage_handle bypass."""
        with tempfile.TemporaryDirectory() as td:
            lease, trusted_real, *_ = clean_coverage_bundle(Path(td), "rev-a", run_id="run-a")
            bindings = lease.bindings
            forged_ticket = DiagnosticMintTicket(
                ticket_id="forged-ticket",
                evidence=CoverageEvidenceIdentity(
                    code_revision=bindings.implementation_revision,
                    inventory_digest=trusted_real.inventory_digest,
                    runtime_census_digest=trusted_real.runtime_census_digest,
                    coverage_digest=bindings.writer_coverage_digest,
                    gate_identity=bindings.gate_identity,
                    gate_path=bindings.gate_path,
                    gate_protocol=bindings.gate_protocol,
                ),
            )
            with self.assertRaises(AuthorityRegistryError):
                register_diagnostic_ticket(forged_ticket, provenance_seal="forged-seal")
            with self.assertRaises(AuthorityRegistryError):
                mint_coverage_from_consumed_ticket(forged_ticket)
            lease.release()

    def test_fabricated_registry_ticket_without_provenance_refused(self) -> None:
        """Probe 2: fabricated diagnostic ticket cannot mint trusted coverage."""
        diag = sample_diagnostic_coverage_result(_mint_ticket="fake", _provenance_seal="fake")
        with self.assertRaises(CoverageProofError):
            mint_trusted_coverage_proof(diag)

    def test_direct_source_proof_construction_refused(self) -> None:
        """Probe 3: SourceAuthorityProof is not caller-constructible."""
        with self.assertRaises(CoverageProofError):
            attempt_forge_source_authority_proof(
                run_id="x",
                coverage_digest="y",
                gate_held=True,
                gate_identity="z",
                gate_path="/tmp/g",
            )
        with self.assertRaises(CoverageProofError):
            SourceAuthorityProof(
                run_id="x",
                coverage_digest="y",
                gate_held=True,
                gate_identity="z",
                gate_path="/tmp/g",
            )

    def test_custodian_substitution_refused(self) -> None:
        """Probe 4: mutable custodian reference cannot preserve authority."""
        with tempfile.TemporaryDirectory() as td:
            lease = acquire_test_lease(Path(td), run_id="cust-sub")
            assert_custodian_force_unlock_breaks_verify(self, lease)
            lease.release()

    def test_cross_chain_coverage_replay_refused(self) -> None:
        """Probe 5: trusted coverage from chain A cannot authorize lease B."""

        def exercise(
            testcase,
            _lease_a,
            trusted_a,
            lease_b,
            _trusted_b,
        ):
            with testcase.assertRaises((CoverageProofError, R2bQuiescenceLeaseError)):
                obtain_source_authority(lease_b, trusted_a)

        run_dual_coverage_chain_case(self, exercise)

    def test_runtime_attestation_without_gate_lease_is_not_source_authority(self) -> None:
        """Probe 6: trusted coverage without a live lease cannot become source authority."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            chroma.mkdir()
            (root / "processed.json").write_text("{}", encoding="utf-8")
            (root / "export").mkdir()
            revision = hermetic_implementation_revision("attest-only")
            inv = build_static_route_inventory(code_revision=revision)
            diag = prove_zero_bypass_coverage(
                chroma_dir=chroma,
                processed_path=root / "processed.json",
                export_root=root / "export",
                test_gate_path=root / "gate.lock",
                code_revision=revision,
                static_inventory=inv,
                skip_runtime=True,
            )
            with self.assertRaises(CoverageProofError):
                mint_trusted_coverage_proof(diag)

    def test_malformed_implementation_revision_refused(self) -> None:
        """Probe 7: arbitrary revision text cannot become authoritative."""
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
                    code_revision="definitely-not-a-git-commit",
                )

    def test_ungoverned_route_classification_fails_inventory(self) -> None:
        """Probe 8: declared routes must carry governed classification."""
        revision = hermetic_implementation_revision("tip-sha")
        inv = build_static_route_inventory(code_revision=revision)
        inv["routes"] = [
            {
                "route_id": "rogue",
                "category": "cg2_d4",
                "entrypoint": "rogue.py",
                "mutation_surfaces": ("chroma",),
                "gate_path": "/tmp/gate.lock",
                "gate_protocol": 1,
                "coverage_status": "declared_only",
                "code_revision": revision,
            }
        ]
        errs = verify_inventory_matches_tip(inv, code_revision=revision)
        self.assertTrue(any("ungoverned route classification" in err for err in errs))

    def test_old_source_proof_invalid_after_reload(self) -> None:
        """Probe 9: stale source proof cannot survive registry epoch invalidation."""
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "reload-src")
            auth = obtain_source_authority(lease, trusted)
            invalidate_all_authority()
            with self.assertRaises(AuthorityRegistryError):
                _ = auth.run_id
            _reset_for_tests()

    def test_source_authority_requires_live_lease_at_issuance(self) -> None:
        """Probe 10: issuance path revalidates lease; atomic kernel+census not claimed."""
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "toctou")
            holder = lease._holder  # pylint: disable=protected-access
            custodian_for_tests(holder).force_unlock_for_tests()
            with self.assertRaises(R2bQuiescenceLeaseError):
                source_authority_from_lease_and_coverage(
                    lease,
                    trusted,
                    open_evidence_digest=lease.bindings.open_evidence_digest,
                )
            lease.release()

    def test_legitimate_chain_still_obtains_source_authority(self) -> None:
        run_legitimate_source_authority_case(self, "good-chain")

    def test_cross_chain_open_evidence_refused(self) -> None:
        refuse_wrong_open_evidence_case(self)
