"""R2b v2 implementation-revision binding (I3/I7 Interpretation B)."""
# pylint: disable=duplicate-code

from __future__ import annotations

import json
import unittest
from unittest import mock

from chroma_write_store import current_code_revision

from eval_corpus.r2b_v2.coverage.inventory import (
    ROOT,
    V2_INVENTORY,
    build_static_route_inventory,
    load_committed_v2_inventory,
    resolve_r2b_implementation_revision,
    verify_inventory_matches_tip,
)
from eval_corpus.r2b_v2.coverage.proof import (
    CoverageHoldClass,
    prove_zero_bypass_coverage,
)


class R2bV2ImplementationRevisionTests(unittest.TestCase):
    def test_resolver_is_deterministic_40_hex(self) -> None:
        first = resolve_r2b_implementation_revision()
        second = resolve_r2b_implementation_revision()
        self.assertEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{40}$")

    def test_implementation_identity_independent_of_git_head(self) -> None:
        resolved = resolve_r2b_implementation_revision()
        with mock.patch(
            "chroma_write_store.current_code_revision",
            return_value="deadbeef" * 5,
        ):
            spoofed = resolve_r2b_implementation_revision()
        self.assertEqual(resolved, spoofed)
        self.assertNotEqual(current_code_revision(), resolved)

    def test_committed_inventory_matches_resolved_implementation_identity(self) -> None:
        inventory = load_committed_v2_inventory()
        self.assertIsNotNone(inventory, "committed inventory artifact must exist")
        assert inventory is not None
        revision = resolve_r2b_implementation_revision()
        self.assertEqual(inventory.get("code_revision"), revision)
        errors = verify_inventory_matches_tip(inventory)
        self.assertEqual(errors, [], msg=errors)

    def test_committed_inventory_includes_inter_model_index_301(self) -> None:
        inventory = load_committed_v2_inventory()
        self.assertIsNotNone(inventory)
        assert inventory is not None
        entrypoints = {route.get("entrypoint") for route in inventory.get("routes", [])}
        self.assertIn("inter_model_index.py:301", entrypoints)

    def test_production_coverage_uses_committed_inventory_without_dual_mock(self) -> None:
        inventory = load_committed_v2_inventory()
        self.assertIsNotNone(inventory)
        assert inventory is not None
        revision = resolve_r2b_implementation_revision()
        self.assertEqual(inventory["code_revision"], revision)
        result = prove_zero_bypass_coverage(
            chroma_dir=ROOT / ".git",
            processed_path=ROOT / "pyproject.toml",
            export_root=ROOT / "docs",
            static_inventory=inventory,
            skip_runtime=True,
        )
        static_holds = result.hold_classes[
            CoverageHoldClass.INCOMPLETE_STATIC_COVERAGE.value
        ]
        stale_details = [
            item.get("detail", "")
            for item in static_holds
            if "stale inventory revision" in item.get("detail", "")
        ]
        self.assertEqual(stale_details, [], msg=static_holds)

    def test_governed_route_drift_fails_committed_inventory(self) -> None:
        inventory = load_committed_v2_inventory()
        self.assertIsNotNone(inventory)
        assert inventory is not None
        with mock.patch(
            "eval_corpus.r2b_v2.coverage.inventory._scan_route_entrypoint_mutation_sinks",
            return_value=["cg2_rehearsal.py:199", "cg2_rehearsal.py:9999"],
        ):
            errors = verify_inventory_matches_tip(inventory)
        self.assertTrue(errors, errors)

    def test_squash_simulation_preserves_identity_when_content_unchanged(self) -> None:
        """Hermetic proof: history-only movement must not rotate implementation identity."""
        baseline = resolve_r2b_implementation_revision()
        pre_squash_head = "a5888968cf51c17652de44bb6dd5c6e23e0fc809"
        post_squash_head = "squash000000000000000000000000000000000000"
        for fake_head in (pre_squash_head, post_squash_head, "b" * 40):
            with mock.patch(
                "chroma_write_store.current_code_revision",
                return_value=fake_head,
            ):
                self.assertEqual(
                    resolve_r2b_implementation_revision(),
                    baseline,
                    fake_head,
                )

    def test_regenerated_inventory_matches_on_disk_artifact(self) -> None:
        fresh = build_static_route_inventory()
        on_disk = json.loads(V2_INVENTORY.read_text(encoding="utf-8"))
        self.assertEqual(fresh["code_revision"], on_disk["code_revision"])
        self.assertEqual(fresh["inventory_digest"], on_disk["inventory_digest"])


if __name__ == "__main__":
    unittest.main()
