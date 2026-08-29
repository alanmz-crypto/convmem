"""Hermetic tests for R2b v2 zero-bypass coverage proof (I3)."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from chroma_write_store import current_code_revision

from eval_corpus.r2b_v2.coverage.inventory import (
    build_static_route_inventory,
    scan_repo_for_unlisted_chroma_ctor,
    verify_inventory_matches_tip,
    verify_shadow_inventory_unchanged,
)
from eval_corpus.r2b_v2.coverage.proof import (
    CoverageProofError,
    CoverageHoldClass,
    prove_zero_bypass_coverage,
    source_authority_from_lease_and_coverage,
)
from eval_corpus.r2b_v2.lease import acquire_r2b_quiescence_lease


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
        for required in (
            "watch_f0",
            "refine",
            "monitor_reconciliation",
            "manual_production",
            "cg2_d4",
            "recovery_authority",
            "export_writers",
            "processed_state_writers",
            "chroma_writers",
        ):
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


class R2bV2CoverageProofTests(unittest.TestCase):
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
                gate_path=gate,
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
                gate_path=root / "gate.lock",
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
                gate_path=gate,
                code_revision=current_code_revision(),
                static_inventory=inv,
                bypass_capable_routes=[{"route": "incomplete"}],
                skip_runtime=True,
            )
            lease = acquire_r2b_quiescence_lease(
                run_id="neg-run",
                grant_digest="g",
                authority_digest="a",
                lock_path=gate,
                writer_coverage_digest=bad.coverage_digest,
                open_evidence_digest="open",
                monotonic_deadline=time.monotonic() + 30,
                bound_source_paths=(str(export), str(processed), str(chroma)),
                implementation_revision=current_code_revision(),
            )
            try:
                with self.assertRaises(CoverageProofError) as ctx:
                    source_authority_from_lease_and_coverage(
                        lease,
                        bad,
                        open_evidence_digest="open",
                    )
                self.assertIn("NO SOURCE AUTHORITY", str(ctx.exception))
            finally:
                lease.release()


if __name__ == "__main__":
    unittest.main()
