"""Hermetic tests for R2b v2 zero-bypass coverage proof (I3)."""
# pylint: disable=duplicate-code

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from chroma_write_store import current_code_revision

from eval_corpus.r2b_v2.coverage.inventory import (
    REQUIRED_ROUTE_CATEGORIES,
    build_static_route_inventory,
    scan_repo_for_unlisted_chroma_ctor,
    verify_inventory_matches_tip,
    verify_shadow_inventory_unchanged,
)
from eval_corpus.r2b_v2.coverage.proof import (
    CoverageProofError,
    CoverageHoldClass,
    TrustedCoverageProof,
    attempt_forge_trusted_coverage_proof,
    mint_trusted_coverage_proof,
    prove_zero_bypass_coverage,
    source_authority_from_lease_and_coverage,
)
from eval_corpus.r2b_v2.lease import acquire_r2b_quiescence_lease
from eval_corpus.r2b_v2.trusted import _reset_for_tests
from tests.r2b_v2_helpers import (
    clean_coverage_bundle,
    hermetic_implementation_revision,
    sample_diagnostic_coverage_result,
)


class R2bV2CoverageInventoryTests(unittest.TestCase):
    def test_static_inventory_binds_revision(self):
        revision = hermetic_implementation_revision("tip-sha")
        inv = build_static_route_inventory(code_revision=revision)
        self.assertEqual(inv["code_revision"], revision)
        self.assertFalse(inv["missing_categories"])
        errs = verify_inventory_matches_tip(inv, code_revision=revision)
        self.assertEqual(errs, [])

    def test_stale_inventory_refuses(self):
        old = hermetic_implementation_revision("old-sha")
        new = hermetic_implementation_revision("new-sha")
        inv = build_static_route_inventory(code_revision=old)
        errs = verify_inventory_matches_tip(inv, code_revision=new)
        self.assertTrue(errs)

    def test_shadow_inventory_contract_preserved(self):
        errs = verify_shadow_inventory_unchanged()
        self.assertEqual(errs, [], msg=errs)

    def test_required_route_categories_present(self):
        inv = build_static_route_inventory(code_revision=hermetic_implementation_revision("tip"))
        categories = {route["category"] for route in inv["routes"]}
        for required in REQUIRED_ROUTE_CATEGORIES:
            self.assertIn(required, categories)

    def test_scan_matches_shadow_allowlist(self):
        """Direct ctor sites must remain within the C3 shadow allowlist."""
        import json

        from tests.test_shadow_writer_coverage_scan import ROOT as SCAN_ROOT

        allow = set(
            json.loads(
                (SCAN_ROOT / "docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json").read_text(
                    encoding="utf-8"
                )
            ).get("allowlisted_direct_sites", [])
        )
        hits = scan_repo_for_unlisted_chroma_ctor()
        extra = [h for h in hits if h not in allow]
        self.assertEqual(extra, [], msg=extra)


class R2bV2DiagnosticCoverageTests(unittest.TestCase):
    def test_diagnostic_result_separate_from_trusted(self):
        diag = sample_diagnostic_coverage_result()
        self.assertFalse(isinstance(diag, TrustedCoverageProof))

    def test_skip_runtime_cannot_mint_trusted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            revision = hermetic_implementation_revision("skip-test")
            inv = build_static_route_inventory(code_revision=revision)
            diag = prove_zero_bypass_coverage(
                chroma_dir=root / "chroma",
                processed_path=root / "processed.json",
                export_root=root / "export",
                test_gate_path=root / "gate.lock",
                code_revision=revision,
                static_inventory=inv,
                skip_runtime=True,
            )
            self.assertTrue(diag.runtime_census_skipped)
            with self.assertRaises(CoverageProofError) as ctx:
                mint_trusted_coverage_proof(diag)
            self.assertIn("skip_runtime", str(ctx.exception))

    def test_trusted_proof_not_caller_constructible(self):
        with self.assertRaises(CoverageProofError):
            attempt_forge_trusted_coverage_proof(
                code_revision="x",
                inventory_digest="i",
                runtime_census_digest="r",
                coverage_digest="c",
                gate_identity="g",
                gate_path="/tmp/g",
                gate_protocol=1,
            )


class R2bV2CoverageProofTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_empty_runtime_census_passes_when_clean(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            processed = root / "processed.json"
            export = root / "export"
            chroma.mkdir()
            export.mkdir()
            processed.write_text("{}", encoding="utf-8")
            gate = root / "gate.lock"
            revision = hermetic_implementation_revision("cov-test")
            inv = build_static_route_inventory(code_revision=revision)
            result = prove_zero_bypass_coverage(
                chroma_dir=chroma,
                processed_path=processed,
                export_root=export,
                test_gate_path=gate,
                code_revision=revision,
                static_inventory=inv,
                skip_runtime=False,
            )
            self.assertTrue(result.passed, msg=result.hold_classes)
            for cls in CoverageHoldClass:
                self.assertEqual(result.hold_classes[cls.value], [])

    def test_bypass_route_hold(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            revision = hermetic_implementation_revision("cov-bypass")
            inv = build_static_route_inventory(code_revision=revision)
            result = prove_zero_bypass_coverage(
                chroma_dir=root / "chroma",
                processed_path=root / "processed.json",
                export_root=root / "export",
                test_gate_path=root / "gate.lock",
                code_revision=revision,
                static_inventory=inv,
                bypass_capable_routes=[{"route": "rogue", "detail": "direct write"}],
                skip_runtime=True,
            )
            self.assertFalse(result.passed)
            self.assertTrue(result.hold_classes[CoverageHoldClass.BYPASS_CAPABLE_ROUTE.value])

    def test_gate_without_coverage_no_source_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            processed = root / "processed.json"
            export = root / "export"
            chroma.mkdir()
            export.mkdir()
            processed.write_text("{}", encoding="utf-8")
            gate = root / "gate.lock"
            inv = build_static_route_inventory(code_revision=current_code_revision())
            bad = prove_zero_bypass_coverage(
                chroma_dir=chroma,
                processed_path=processed,
                export_root=export,
                test_gate_path=gate,
                code_revision=current_code_revision(),
                static_inventory=inv,
                bypass_capable_routes=[{"route": "incomplete"}],
                skip_runtime=True,
            )
            lease = acquire_r2b_quiescence_lease(
                run_id="neg-run",
                grant_digest="g",
                authority_digest="a",
                test_lock_path=gate,
                writer_coverage_digest=bad.coverage_digest,
                open_evidence_digest="open",
                monotonic_deadline=time.monotonic() + 30,
                bound_source_paths=(str(export), str(processed), str(chroma)),
                timeout_ms=5000,
            )
            try:
                with self.assertRaises(CoverageProofError) as ctx:
                    mint_trusted_coverage_proof(bad)
                self.assertIn("skip_runtime", str(ctx.exception))
            finally:
                lease.release()

    def test_trusted_coverage_establishes_source_authority(self):
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(
                Path(td),
                current_code_revision(),
                run_id="pos-run",
                open_evidence_digest="open-ev",
            )
            try:
                auth = source_authority_from_lease_and_coverage(
                    lease,
                    trusted,
                    open_evidence_digest="open-ev",
                )
                self.assertEqual(auth.run_id, "pos-run")
                self.assertTrue(auth.gate_held)
            finally:
                lease.release()


if __name__ == "__main__":
    unittest.main()
