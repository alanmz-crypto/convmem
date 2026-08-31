"""Corrective VIII — authority-content identity and writer attestation convergence."""
# pylint: disable=duplicate-code

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chroma_write_store import (
    build_writer_attestation,
    current_git_revision,
    shared_writer_lease,
)
from eval_corpus.r2b_v2.coverage.authority_manifest import build_authority_content_manifest
from eval_corpus.r2b_v2.coverage.inventory import (
    V2_INVENTORY,
    build_static_route_inventory,
    clear_inventory_scan_cache,
    load_committed_v2_inventory,
    resolve_r2b_implementation_revision,
    verify_inventory_matches_tip,
)
from eval_corpus.r2b_v2.coverage.proof import (
    CoverageHoldClass,
    inspect_runtime_writers,
    prove_zero_bypass_coverage,
)
from eval_corpus.r2b_v2.gate_policy import test_gate_policy as hermetic_gate_policy
from eval_corpus.r2b_v2.trusted import _reset_for_tests


def _patch_file_bytes(substitutions: dict[str, tuple[str, str]]) -> mock._patch[str]:
    original_read_bytes = Path.read_bytes

    def patched_read_bytes(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        payload = original_read_bytes(self, *args, **kwargs)
        rel = str(self)
        for suffix, (old, new) in substitutions.items():
            if rel.endswith(suffix):
                text = payload.decode("utf-8", errors="replace")
                if old in text:
                    return text.replace(old, new).encode("utf-8")
        return payload

    return mock.patch.object(Path, "read_bytes", patched_read_bytes)


class R2bV2CorrectiveVIIIIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()
        clear_inventory_scan_cache()

    def tearDown(self) -> None:
        clear_inventory_scan_cache()

    def test_gate_constant_mutation_rotates_identity_without_coordinate_change(self) -> None:
        baseline = resolve_r2b_implementation_revision()
        with _patch_file_bytes(
            {
                "chroma_write_store.py": (
                    "chroma_writer_gate.lock",
                    "rogue_writer_gate.lock",
                )
            }
        ):
            clear_inventory_scan_cache()
            rotated = resolve_r2b_implementation_revision()
        self.assertNotEqual(baseline, rotated)

    def test_proof_predicate_mutation_rotates_identity(self) -> None:
        baseline = resolve_r2b_implementation_revision()
        with _patch_file_bytes(
            {
                "eval_corpus/r2b_v2/coverage/proof.py": (
                    "CoverageHoldClass.STALE_REVISION.value",
                    "CoverageHoldClass.STALE_REVISION.value + '-mutated'",
                )
            }
        ):
            clear_inventory_scan_cache()
            rotated = resolve_r2b_implementation_revision()
        self.assertNotEqual(baseline, rotated)

    def test_writer_helper_mutation_rotates_identity(self) -> None:
        baseline = resolve_r2b_implementation_revision()
        with _patch_file_bytes(
            {
                "chroma_write_store.py": (
                    "def classify_legacy_writer_pids(",
                    "def classify_legacy_writer_pids_mutated(",
                )
            }
        ):
            clear_inventory_scan_cache()
            rotated = resolve_r2b_implementation_revision()
        self.assertNotEqual(baseline, rotated)

    def test_lease_logic_mutation_rotates_identity(self) -> None:
        baseline = resolve_r2b_implementation_revision()
        with _patch_file_bytes(
            {
                "eval_corpus/r2b_v2/lease.py": (
                    "expected_implementation_revision",
                    "expected_implementation_revision_mutated",
                )
            }
        ):
            clear_inventory_scan_cache()
            rotated = resolve_r2b_implementation_revision()
        self.assertNotEqual(baseline, rotated)

    def test_git_head_movement_preserves_identity(self) -> None:
        baseline = resolve_r2b_implementation_revision()
        with mock.patch(
            "chroma_write_store.current_git_revision",
            return_value="deadbeef" * 5,
        ):
            self.assertEqual(resolve_r2b_implementation_revision(), baseline)

    def test_committed_inventory_matches_authority_content_identity(self) -> None:
        revision = resolve_r2b_implementation_revision()
        inventory = load_committed_v2_inventory()
        self.assertIsNotNone(inventory)
        assert inventory is not None
        self.assertEqual(inventory.get("code_revision"), revision)
        errors = verify_inventory_matches_tip(inventory)
        self.assertEqual(errors, [], msg=errors)

    def test_stale_governed_content_fails_committed_inventory(self) -> None:
        inventory = load_committed_v2_inventory()
        self.assertIsNotNone(inventory)
        assert inventory is not None
        stale = dict(inventory)
        stale["code_revision"] = "0" * 40
        errors = verify_inventory_matches_tip(stale)
        self.assertTrue(errors)


class R2bV2CorrectiveVIIIConvergenceTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()
        clear_inventory_scan_cache()

    def tearDown(self) -> None:
        clear_inventory_scan_cache()

    def test_production_writer_attestation_matches_coverage_without_override(self) -> None:
        revision = resolve_r2b_implementation_revision()
        attestation = build_writer_attestation(entrypoint="production_chroma_write_session")
        self.assertEqual(attestation.code_revision, revision)
        self.assertNotEqual(attestation.git_revision, revision)
        self.assertEqual(attestation.git_revision, current_git_revision())

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            chroma.mkdir()
            processed = root / "processed.json"
            export = root / "export"
            export.mkdir()
            processed.write_text("{}", encoding="utf-8")
            gate = root / "gate.lock"
            attest_dir = root / "attest"
            mutable = chroma / "segment.bin"
            mutable.write_text("x", encoding="utf-8")
            inventory = build_static_route_inventory(code_revision=revision)
            fd = os.open(str(mutable), os.O_RDWR)
            try:
                with shared_writer_lease(
                    lock_path=gate,
                    attest_dir=attest_dir,
                    entrypoint="production_chroma_write_session",
                ) as held:
                    self.assertEqual(held.code_revision, revision)
                    policy = hermetic_gate_policy(gate)
                    writers, holds = inspect_runtime_writers(
                        chroma_dir=chroma,
                        processed_path=processed,
                        export_root=export,
                        gate_policy=policy,
                        attest_dir=attest_dir,
                    )
                    self.assertEqual(
                        holds[CoverageHoldClass.STALE_REVISION.value],
                        [],
                        msg=holds,
                    )
                    self.assertEqual(len(writers), 1)
                    self.assertEqual(writers[0].code_revision, revision)
                    result = prove_zero_bypass_coverage(
                        chroma_dir=chroma,
                        processed_path=processed,
                        export_root=export,
                        test_gate_path=gate,
                        attest_dir=attest_dir,
                        static_inventory=inventory,
                        skip_runtime=False,
                    )
                    self.assertEqual(
                        result.hold_classes[CoverageHoldClass.STALE_REVISION.value],
                        [],
                        msg=result.hold_classes,
                    )
            finally:
                os.close(fd)

    def test_authority_manifest_includes_writer_gate_module(self) -> None:
        manifest = build_authority_content_manifest()
        paths = {entry["path"] for entry in manifest["governed_files"]}
        self.assertIn("chroma_write_store.py", paths)
        self.assertIn("eval_corpus/r2b_v2/coverage/proof.py", paths)
        self.assertIn("docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json", paths)


class R2bV2CorrectiveVIIIRegressionGuard(unittest.TestCase):
    def test_inventory_artifact_exists_on_disk(self) -> None:
        self.assertTrue(V2_INVENTORY.is_file())
        revision = resolve_r2b_implementation_revision()
        inventory = build_static_route_inventory(code_revision=revision)
        on_disk = load_committed_v2_inventory()
        self.assertIsNotNone(on_disk)
        assert on_disk is not None
        self.assertEqual(inventory["code_revision"], on_disk["code_revision"])
        self.assertEqual(inventory["inventory_digest"], on_disk["inventory_digest"])


if __name__ == "__main__":
    unittest.main()
