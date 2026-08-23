"""Recovery Authority T3 — scratch-only bulk recovery workflow (V4j)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backup_workflows import (  # noqa: E402  # pylint: disable=wrong-import-position
    LIVE_AUTHORITY_REPLACEMENT,
    SCRATCH_CANDIDATE_PREPARE,
    STATUS_FAIL,
    STATUS_PASS,
    OperationalGrant,
    assert_scratch_target_isolated,
    fingerprint_data_root,
    prepare_scratch_recovery_candidate,
    refuse_live_authority_replacement,
    validate_item_import_not_registry_substitute,
    validate_operational_grant,
    validate_scratch_recovery_candidate,
)
from complete_data_restore import (  # noqa: E402  # pylint: disable=wrong-import-position
    RestoreProfile,
    RestoreReport,
)
from provenance_registry_restore import (  # noqa: E402  # pylint: disable=wrong-import-position
    build_registry_fixture,
)
from recovery_authority import (  # noqa: E402  # pylint: disable=wrong-import-position
    RecoveryState,
    write_matching_projections,
)
from restic_snapshot import (  # noqa: E402  # pylint: disable=wrong-import-position
    EXIT_BLOCKED,
    EXIT_ISOLATION_FAILURE,
    ResolverError,
    SnapshotRef,
    TAG_COMPLETE_DATA_V3,
)
from tests.test_recovery_authority_t1 import (  # noqa: E402  # pylint: disable=wrong-import-position
    _minimal_v2_root,
)
from tests.test_recovery_authority_t2 import (  # noqa: E402  # pylint: disable=wrong-import-position
    _seal_candidate,
)


def _snapshot_ref(*, snap_id: str = "a" * 64, tree: str = "b" * 64) -> SnapshotRef:
    return SnapshotRef(
        repository="test-repo",
        id=snap_id,
        original=None,
        tree=tree,
        time=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        paths=("/home/lauer/.local/share/convmem",),
        tags=frozenset({TAG_COMPLETE_DATA_V3}),
    )


class TestOperationalGrantAndIsolation(unittest.TestCase):
    def test_missing_grant_blocked(self):
        ok, reason = validate_operational_grant(
            None,
            operation=SCRATCH_CANDIDATE_PREPARE,
            target="/tmp/scratch",
        )
        self.assertFalse(ok)
        self.assertIn("grant required", reason)

    def test_wrong_grant_target_blocked(self):
        grant = OperationalGrant(
            grant_id="g1",
            operation=SCRATCH_CANDIDATE_PREPARE,
            authorized_target="/tmp/other",
        )
        ok, reason = validate_operational_grant(
            grant,
            operation=SCRATCH_CANDIDATE_PREPARE,
            target="/tmp/scratch",
        )
        self.assertFalse(ok)
        self.assertIn("target", reason)

    def test_scratch_overlap_live_raises(self):
        with tempfile.TemporaryDirectory() as td:
            live = Path(td) / "live"
            scratch = Path(td) / "live" / "scratch"
            live.mkdir()
            scratch.mkdir(parents=True)
            with self.assertRaises(ResolverError) as ctx:
                assert_scratch_target_isolated(scratch, live)
            self.assertEqual(ctx.exception.exit_code, EXIT_ISOLATION_FAILURE)


class TestItemImportRejection(unittest.TestCase):
    def test_foreign_assertion_ids_rejected(self):
        ok, reason = validate_item_import_not_registry_substitute(
            caller_assertion_ids=["forged-001", "assert-fixture-001"],
            registry_assertion_ids=["assert-fixture-001"],
        )
        self.assertFalse(ok)
        self.assertIn("forged-001", reason)

    def test_subset_ids_not_substitute(self):
        ok, reason = validate_item_import_not_registry_substitute(
            caller_assertion_ids=["assert-fixture-001"],
            registry_assertion_ids=["assert-fixture-001"],
        )
        self.assertTrue(ok)
        self.assertIn("cannot substitute", reason)


class TestScratchCandidateValidation(unittest.TestCase):
    def test_valid_v3_candidate_with_projections(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            ref = _snapshot_ref()
            outcome = validate_scratch_recovery_candidate(
                root, snapshot_ref=ref, profile=RestoreProfile.COMPLETE_DATA_V3
            )
            self.assertEqual(outcome.status, STATUS_PASS)
            self.assertFalse(outcome.details.get("serving_ready", True))
            self.assertIn(
                outcome.recovery_state,
                {
                    RecoveryState.PROJECTION_VALIDATED.value,
                    RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING.value,
                },
            )
            self.assertIsNotNone(outcome.provenance_tuple)

    def test_projection_pending_remains_non_serving(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root, include_jsonl=False, include_chroma=False, with_bindings=False)
            outcome = validate_scratch_recovery_candidate(root, profile=RestoreProfile.COMPLETE_DATA_V3)
            self.assertEqual(outcome.status, STATUS_PASS)
            self.assertEqual(
                outcome.recovery_state,
                RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING.value,
            )
            self.assertFalse(outcome.details["serving_ready"])

    def test_missing_registry_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_v2_root(root)
            outcome = validate_scratch_recovery_candidate(root, profile=RestoreProfile.COMPLETE_DATA_V3)
            self.assertEqual(outcome.status, STATUS_FAIL)
            self.assertEqual(outcome.exit_code, EXIT_BLOCKED)

    def test_partial_registry_quarantined(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_v2_root(root)
            selector = root / "provenance" / "selector.json"
            selector.parent.mkdir(parents=True)
            selector.write_text("{}", encoding="utf-8")
            outcome = validate_scratch_recovery_candidate(root, profile=RestoreProfile.COMPLETE_DATA_V3)
            self.assertEqual(outcome.status, STATUS_FAIL)
            self.assertEqual(
                outcome.recovery_state,
                RecoveryState.QUARANTINED.value,
            )

    def test_v2_presented_as_v3_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_v2_root(root)
            ref = _snapshot_ref()
            outcome = validate_scratch_recovery_candidate(
                root, snapshot_ref=ref, profile=RestoreProfile.COMPLETE_DATA_V3
            )
            self.assertEqual(outcome.status, STATUS_FAIL)
            self.assertEqual(outcome.details.get("code"), "BLOCKED_V2_AS_V3")

    def test_mismatched_selection_binding_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            ref = _snapshot_ref(tree="c" * 64)
            outcome = validate_scratch_recovery_candidate(
                root,
                snapshot_ref=ref,
                profile=RestoreProfile.COMPLETE_DATA_V3,
                expected_binding={
                    "restic_snapshot_id": ref.id,
                    "restic_root_tree_id": ref.tree,
                },
            )
            self.assertEqual(outcome.status, STATUS_FAIL)
            self.assertIn("binding mismatch", outcome.message)

    def test_live_fingerprint_unchanged_during_validation(self):
        with tempfile.TemporaryDirectory() as td:
            live = Path(td) / "live"
            scratch = Path(td) / "scratch"
            live.mkdir()
            scratch.mkdir()
            _seal_candidate(scratch)
            before = fingerprint_data_root(live, profile=RestoreProfile.COMPLETE_DATA_V3)
            validate_scratch_recovery_candidate(scratch, profile=RestoreProfile.COMPLETE_DATA_V3)
            after = fingerprint_data_root(live, profile=RestoreProfile.COMPLETE_DATA_V3)
            self.assertEqual(before, after)


class TestPrepareScratchWorkflow(unittest.TestCase):
    def test_prepare_without_grant_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            live = Path(td) / "live"
            scratch = Path(td) / "scratch"
            live.mkdir()
            scratch.mkdir()
            report = RestoreReport(Path(td) / "report.json")
            ctx = mock.Mock()
            ctx.data_root = live
            outcome = prepare_scratch_recovery_candidate(
                ctx,
                snapshot_id="a" * 64,
                scratch_target=scratch,
                grant=None,
                report=report,
                live_data_root=live,
            )
            self.assertEqual(outcome.status, STATUS_FAIL)
            self.assertEqual(outcome.exit_code, EXIT_BLOCKED)
            payload = json.loads(report.json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["meta"]["status"], "BLOCKED")

    def test_prepare_overlap_live_blocked_before_restic(self):
        with tempfile.TemporaryDirectory() as td:
            live = Path(td) / "live"
            scratch = Path(td) / "live" / "nested"
            live.mkdir()
            scratch.mkdir(parents=True)
            grant = OperationalGrant(
                grant_id="g1",
                operation=SCRATCH_CANDIDATE_PREPARE,
                authorized_target=str(scratch),
            )
            report = RestoreReport(Path(td) / "report.json")
            ctx = mock.Mock()
            ctx.data_root = live
            outcome = prepare_scratch_recovery_candidate(
                ctx,
                snapshot_id="a" * 64,
                scratch_target=scratch,
                grant=grant,
                report=report,
                live_data_root=live,
            )
            self.assertEqual(outcome.exit_code, EXIT_ISOLATION_FAILURE)

    def test_nonempty_scratch_blocked_before_restore(self):
        with tempfile.TemporaryDirectory() as td:
            live = Path(td) / "live"
            scratch = Path(td) / "scratch"
            live.mkdir()
            scratch.mkdir()
            (scratch / "decisions-approved.jsonl").write_text("{}\n", encoding="utf-8")
            grant = OperationalGrant(
                grant_id="g1",
                operation=SCRATCH_CANDIDATE_PREPARE,
                authorized_target=str(scratch),
            )
            report = RestoreReport(Path(td) / "report.json")
            ctx = mock.Mock()
            ctx.data_root = live
            outcome = prepare_scratch_recovery_candidate(
                ctx,
                snapshot_id="a" * 64,
                scratch_target=scratch,
                grant=grant,
                report=report,
                live_data_root=live,
            )
            self.assertEqual(outcome.exit_code, EXIT_ISOLATION_FAILURE)
            self.assertIn("empty", outcome.message.lower())

    def test_refuse_live_replacement_without_grant(self):
        with tempfile.TemporaryDirectory() as td:
            live = Path(td) / "live"
            live.mkdir()
            outcome = refuse_live_authority_replacement(None, live_target=live)
            self.assertEqual(outcome.exit_code, EXIT_BLOCKED)
            self.assertEqual(outcome.details["code"], "LIVE_REPLACEMENT_GRANT_REQUIRED")

    def test_refuse_live_replacement_even_with_grant(self):
        with tempfile.TemporaryDirectory() as td:
            live = Path(td) / "live"
            live.mkdir()
            grant = OperationalGrant(
                grant_id="live-1",
                operation=LIVE_AUTHORITY_REPLACEMENT,
                authorized_target=str(live),
            )
            outcome = refuse_live_authority_replacement(grant, live_target=live)
            self.assertEqual(outcome.details["code"], "LIVE_REPLACEMENT_NOT_IN_T3_GRANT")


class TestSidecarInvalidAuthority(unittest.TestCase):
    def test_valid_sidecar_cannot_repair_invalid_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            pt = build_registry_fixture(
                root, generation_id="pg-fixture-001", assertion_ids=("assert-fixture-001",)
            )
            write_matching_projections(
                root,
                pt,
                assertion_ids=("assert-fixture-001",),
                rewrite_bodies=False,
            )
            (root / "provenance/generations/pg-fixture-001/manifest.json").write_text(
                "{}", encoding="utf-8"
            )
            outcome = validate_scratch_recovery_candidate(root, profile=RestoreProfile.COMPLETE_DATA_V3)
            self.assertEqual(outcome.status, STATUS_FAIL)
            self.assertIn(
                outcome.recovery_state,
                {
                    RecoveryState.BLOCKED.value,
                    RecoveryState.QUARANTINED.value,
                    RecoveryState.PROVENANCE_STORE_UNAVAILABLE.value,
                },
            )


if __name__ == "__main__":
    unittest.main()
