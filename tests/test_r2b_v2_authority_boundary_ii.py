"""Corrective II regressions for P0-A/P0-B authority-boundary closure."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import eval_corpus.r2b_v2._registry_mint as registry_mint
from eval_corpus.r2b_v2 import authority_registry
from eval_corpus.r2b_v2._registry_mint import (
    AuthorityRegistryError,
    SourceAuthorityRecord,
    compose_and_mint_source_authority,
    current_authority_epoch,
)
from eval_corpus.r2b_v2.coverage.proof import (
    _source_authority_from_handle,
)
from eval_corpus.r2b_v2.coverage_evidence import CoverageEvidenceIdentity
from eval_corpus.r2b_v2.lease import R2bQuiescenceLeaseError
from eval_corpus.r2b_v2.lock_custodian import custodian_for_tests
from eval_corpus.r2b_v2.trusted import _reset_for_tests
from tests.r2b_v2_helpers import (
    acquire_test_lease,
    clean_coverage_bundle,
    run_dual_coverage_chain_case,
    run_legitimate_source_authority_case,
)


class FakeCustodian:
    def verify(self) -> None:
        return None

    def release(self) -> None:
        return None


class R2bV2AuthorityBoundaryIITests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_public_registry_has_no_source_mint_or_custodian_register(self) -> None:
        self.assertNotIn("mint_source_authority_record", authority_registry.__all__)
        self.assertNotIn("register_custodian", authority_registry.__all__)
        self.assertFalse(hasattr(authority_registry, "mint_source_authority_record"))
        self.assertFalse(hasattr(authority_registry, "register_custodian"))

    def test_forged_source_record_cannot_mint_via_removed_api(self) -> None:
        self.assertFalse(hasattr(registry_mint, "mint_source_authority_record"))
        forged = SourceAuthorityRecord(
            lease_handle_id="fake-lease",
            coverage_handle_id="fake-coverage",
            authority_epoch=current_authority_epoch(),
            run_id="attacker-run",
            coverage_digest="attacker-cov",
            gate_identity="attacker-gate",
            gate_path="/tmp/attacker.lock",
            open_evidence_digest="attacker-open",
        )
        with self.assertRaises(AttributeError):
            getattr(registry_mint, "mint_source_authority_record")(forged)

    def test_compose_and_mint_requires_live_lease_and_coverage_handles(self) -> None:
        with self.assertRaises(AuthorityRegistryError):
            compose_and_mint_source_authority(
                lease_handle=registry_mint.AuthorityHandle("lease", "missing-lease"),
                coverage_handle=registry_mint.AuthorityHandle("coverage", "missing-coverage"),
                open_evidence_digest="open",
            )

    def test_forged_source_proof_via_handle_forge_still_fails(self) -> None:
        with self.assertRaises(AuthorityRegistryError):
            _source_authority_from_handle(
                registry_mint.AuthorityHandle("source", "forged-source"),
            )

    def test_custodian_overwrite_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = acquire_test_lease(Path(td), run_id="cust-overwrite")
            custodian_id = lease._holder.custodian_id  # pylint: disable=protected-access
            with self.assertRaises(AuthorityRegistryError):
                registry_mint._register_lease_custodian(  # pylint: disable=protected-access
                    custodian_id, FakeCustodian()
                )
            lease.release()

    def test_custodian_substitution_via_public_register_impossible(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = acquire_test_lease(Path(td), run_id="cust-sub-ii")
            holder = lease._holder  # pylint: disable=protected-access
            custodian_for_tests(holder).force_unlock_for_tests()
            with self.assertRaises(AttributeError):
                getattr(authority_registry, "register_custodian")(
                    holder.custodian_id, FakeCustodian()
                )
            with self.assertRaises(R2bQuiescenceLeaseError):
                lease.verify()
            lease.release()

    def test_legitimate_source_authority_still_obtained(self) -> None:
        run_legitimate_source_authority_case(self, "good-ii")

    def test_cross_chain_compose_and_mint_refused(self) -> None:
        def exercise(testcase, _lease_a, trusted_a, lease_b, _trusted_b):
            with testcase.assertRaises(AuthorityRegistryError):
                compose_and_mint_source_authority(
                    lease_handle=lease_b.authority_handle,
                    coverage_handle=trusted_a.authority_handle,
                    open_evidence_digest=lease_b.bindings.open_evidence_digest,
                )

        run_dual_coverage_chain_case(self, exercise)

    def test_registry_mutation_surface_audit(self) -> None:
        """Structural audit: public registry exports are read-only or test invalidation."""
        public_mutators = {
            name
            for name in authority_registry.__all__
            if any(
                verb in name
                for verb in ("mint", "register", "bind", "compose", "consume", "release")
            )
        }
        self.assertEqual(public_mutators, {"release_lease_handle"})

        internal_mutators = [
            name
            for name in dir(registry_mint)
            if callable(getattr(registry_mint, name, None))
            and not name.startswith("_")
            and any(
                verb in name
                for verb in (
                    "mint",
                    "register",
                    "bind",
                    "compose",
                    "consume",
                    "invalidate",
                )
            )
        ]
        self.assertIn("compose_and_mint_source_authority", internal_mutators)
        self.assertNotIn("mint_source_authority_record", internal_mutators)
        self.assertNotIn("register_custodian", internal_mutators)

    def test_kiro_coverage_mint_bypass_still_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "kiro-sanity", run_id="kiro")
            bindings = lease.bindings
            forged = registry_mint.DiagnosticMintTicket(
                ticket_id="forged",
                evidence=CoverageEvidenceIdentity(
                    code_revision=bindings.implementation_revision,
                    inventory_digest=trusted.inventory_digest,
                    runtime_census_digest=trusted.runtime_census_digest,
                    coverage_digest=bindings.writer_coverage_digest,
                    gate_identity=bindings.gate_identity,
                    gate_path=bindings.gate_path,
                    gate_protocol=bindings.gate_protocol,
                ),
            )
            registry_mint.register_diagnostic_ticket(forged, provenance_seal="forged")
            with self.assertRaises(AuthorityRegistryError):
                registry_mint.mint_coverage_from_consumed_ticket(forged)
            lease.release()
