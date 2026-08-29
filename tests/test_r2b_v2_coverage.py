"""Hermetic tests for R2b v2 zero-bypass coverage proof (I3)."""

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
    DiagnosticCoverageResult,
    TrustedCoverageProof,
    mint_trusted_coverage_proof,
    prove_zero_bypass_coverage,
    source_authority_from_lease_and_coverage,
)
from eval_corpus.r2b_v2.lease import acquire_r2b_quiescence_lease
from eval_corpus.r2b_v2.trusted import _reset_for_tests


class R2bV2CoverageInventoryTests(unittest.TestCase):
    def test_static_inventory_binds_revision(self):
        inv = build_static_route_inventory(code_revision="tip-sha")
        self.assertEqual(inv["code_revision"], "tip-sha")
        self.assertFalse(inv["missing_categories"])
        errs = verify_inventory_matches_tip(inv, code_revision="tip-sha")
        self.assertEqual(errs, [])

    def test_stale_inventory_refuses(self):
        inv = build_static_route_inventory(code_revision="old-sha")
        errs = verify_inventory_matches_tip(inv, code_revision="new-sha")
        self.assertTrue(errs)

    def test_shadow_inventory_contract_preserved(self):
        errs = verify_shadow_inventory_unchanged()
        self.assertEqual(errs, [], msg=errs)

    def test_required_route_categories_present(self):
        inv = build_static_route_inventory(code_revision="tip")
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
        diag = DiagnosticCoverageResult(
            code_revision="rev",
            inventory_digest="inv",
            runtime_census_digest="rt",
            coverage_digest="cov",
            gate_identity="gate-id",
            gate_path="/tmp/gate.lock",
            gate_protocol=1,
            passed=True,
        )
        self.assertFalse(isinstance(diag, TrustedCoverageProof))

    def test_skip_runtime_cannot_mint_trusted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv = build_static_route_inventory(code_revision="skip-test")
            diag = prove_zero_bypass_coverage(
                chroma_dir=root / "chroma",
                processed_path=root / "processed.json",
                export_root=root / "export",
                test_gate_path=root / "gate.lock",
                code_revision="skip-test",
                static_inventory=inv,
                skip_runtime=True,
            )
            self.assertTrue(diag.runtime_census_skipped)
            with self.assertRaises(CoverageProofError) as ctx:
                mint_trusted_coverage_proof(diag)
            self.assertIn("skip_runtime", str(ctx.exception))

    def test_trusted_proof_not_caller_constructible(self):
        with self.assertRaises(CoverageProofError):
            TrustedCoverageProof(
                code_revision="x",
                inventory_digest="i",
                runtime_census_digest="r",
                coverage_digest="c",
                gate_identity="g",
                gate_path="/tmp/g",
                gate_protocol=1,
                token=b"forged",
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
            inv = build_static_route_inventory(code_revision="cov-test")
            result = prove_zero_bypass_coverage(
                chroma_dir=chroma,
                processed_path=processed,
                export_root=export,
                test_gate_path=gate,
                code_revision="cov-test",
                static_inventory=inv,
                skip_runtime=False,
            )
            self.assertTrue(result.passed, msg=result.hold_classes)
            for cls in CoverageHoldClass:
                self.assertEqual(result.hold_classes[cls.value], [])

    def test_bypass_route_hold(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inv = build_static_route_inventory(code_revision="cov-bypass")
            result = prove_zero_bypass_coverage(
                chroma_dir=root / "chroma",
                processed_path=root / "processed.json",
                export_root=root / "export",
                test_gate_path=root / "gate.lock",
                code_revision="cov-bypass",
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
            root = Path(td)
            chroma = root / "chroma"
            processed = root / "processed.json"
            export = root / "export"
            chroma.mkdir()
            export.mkdir()
            processed.write_text("{}", encoding="utf-8")
            gate = root / "gate.lock"
            rev = current_code_revision()
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
                run_id="pos-run",
                grant_digest="g",
                authority_digest="a",
                test_lock_path=gate,
                writer_coverage_digest=trusted.coverage_digest,
                open_evidence_digest="open-ev",
                monotonic_deadline=time.monotonic() + 30,
                bound_source_paths=(str(export), str(processed), str(chroma)),
                timeout_ms=5000,
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
