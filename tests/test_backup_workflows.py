"""Consumer-wide S/W challenge for backup_workflows (complete-data v2 T2).

Shared older-correct S / newer-wrong W fixture. Every consumer must name S,
never W. Resolver failure under configured setup → WARN or FAIL — never
PASS/SKIP via legacy fallback.

Hermetic: one temp parent + path firewall. No live config reads.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backup_workflows import (  # noqa: E402
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_SKIP_DISABLED,
    STATUS_WARN,
    STATUS_WARN_LEGACY_ONLY,
    check_local_health,
    check_offsite_health,
    copy_current_snapshot_offsite,
    ensure_current_snapshot,
    restore_validated_snapshot,
    run_integrity_check,
)
from restic_snapshot import (  # noqa: E402
    EXIT_INVALID_ID,
    EXIT_NO_TAGGED_SNAPSHOT,
    EXIT_WRONG_PATH,
    BackupContext,
    BackupProfile,
    TAG_COMPLETE_DATA_V2,
    TAG_LEGACY_CHROMA,
    resolve_snapshot,
)

# Reuse hermetic helpers from T1 suite.
import importlib.util as _ilu

_t1_path = Path(__file__).resolve().parent / "test_restic_snapshot.py"
_t1_spec = _ilu.spec_from_file_location("test_restic_snapshot", _t1_path)
assert _t1_spec and _t1_spec.loader
_t1 = _ilu.module_from_spec(_t1_spec)
sys.modules["test_restic_snapshot"] = _t1
_t1_spec.loader.exec_module(_t1)
HermeticFixture = _t1.HermeticFixture
_restic_available = _t1._restic_available
_restic_bin = _t1._restic_bin


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(_restic_available(), "restic >= 0.19.0 not available")
class TestBackupWorkflowsSWChallenge(unittest.TestCase):
    """Older correct-path S beats newer wrong-path W for every consumer."""

    def setUp(self):
        self.fx = HermeticFixture()
        self.addCleanup(self.fx.cleanup)
        self.fx.init_repos()
        self.snap_s = self.fx.make_snapshot(
            self.fx.data_root, [TAG_COMPLETE_DATA_V2, TAG_LEGACY_CHROMA]
        )
        self.s_id = self.snap_s["id"]
        self.snap_w = self.fx.make_snapshot(
            self.fx.wrong_root, [TAG_COMPLETE_DATA_V2, TAG_LEGACY_CHROMA]
        )
        self.w_id = self.snap_w["id"]
        self.ctx = self.fx.load_ctx(profile="complete-data-v2")
        self.assertNotEqual(self.s_id, self.w_id)
        self.assertEqual(len(self.s_id), 64)

    def _assert_names_s(self, outcome, *, also_dest: bool = False):
        self.assertIsNotNone(outcome.source)
        self.assertEqual(outcome.source.id, self.s_id)
        self.assertNotEqual(outcome.source.id, self.w_id)
        if also_dest:
            self.assertIsNotNone(outcome.destination)
            self.assertEqual(outcome.destination.original, self.s_id)
            self.assertNotEqual(outcome.destination.id, self.w_id)

    def test_ensure_current_snapshot_names_s(self):
        outcome = ensure_current_snapshot(self.ctx)
        self.assertEqual(outcome.status, STATUS_PASS)
        self._assert_names_s(outcome)

    def test_gate_module_names_s(self):
        # restic_gate → ensure_current_snapshot
        recorded = []
        real = ensure_current_snapshot

        def wrapped(ctx, **kwargs):
            out = real(ctx, **kwargs)
            recorded.append(out)
            return out

        with mock.patch("restic_gate.ensure_current_snapshot", side_effect=wrapped):
            # Call workflow the gate would call
            out = ensure_current_snapshot(self.ctx)
        self._assert_names_s(out)

        # Also exercise gate module with env pointing at hermetic fixture
        import restic_gate

        with mock.patch.dict(
            os.environ,
            {
                **self.fx.base_env,
                "CONVMEM_RESTIC_ENV": str(self.fx.env_file),
            },
            clear=False,
        ):
            # Should not SystemExit
            restic_gate.ensure_chroma_snapshot_for_live_write()

    def test_copy_offsite_names_s_and_lineage(self):
        recorded: list[list[str]] = []
        real_run = subprocess.run

        def wrapped(cmd, *args, **kwargs):
            if cmd and "restic" in str(cmd[0]):
                recorded.append(list(cmd))
            return real_run(cmd, *args, **kwargs)

        with mock.patch("restic_snapshot.subprocess.run", side_effect=wrapped):
            outcome = copy_current_snapshot_offsite(self.ctx)
        self.assertEqual(outcome.status, STATUS_PASS, outcome.message)
        self._assert_names_s(outcome, also_dest=True)
        # Copy argv must name full S and never --latest
        copy_cmds = [a for a in recorded if len(a) > 2 and a[3] == "copy"]
        self.assertTrue(copy_cmds, f"no copy argv in {recorded}")
        for argv in copy_cmds:
            self.assertIn(self.s_id, argv)
            self.assertNotIn(self.w_id, argv)
            self.assertNotIn("--latest", argv)
        self.assertIn(self.s_id, outcome.argv)

    def test_check_local_health_names_s(self):
        outcome = check_local_health(self.ctx)
        self.assertEqual(outcome.status, STATUS_PASS)
        self._assert_names_s(outcome)

    def test_check_offsite_health_names_s_and_d(self):
        # Need a copy present for PASS
        prep = copy_current_snapshot_offsite(self.ctx)
        self.assertEqual(prep.status, STATUS_PASS, prep.message)
        outcome = check_offsite_health(self.ctx)
        self.assertEqual(outcome.status, STATUS_PASS, outcome.message)
        self._assert_names_s(outcome, also_dest=True)

    def test_integrity_check_uses_explicit_s(self):
        recorded: list[list[str]] = []
        real_run = subprocess.run

        def wrapped(cmd, *args, **kwargs):
            if cmd and "restic" in str(cmd[0]):
                recorded.append(list(cmd))
            return real_run(cmd, *args, **kwargs)

        with mock.patch("restic_snapshot.subprocess.run", side_effect=wrapped):
            outcome = run_integrity_check(self.ctx)
        self.assertEqual(outcome.status, STATUS_PASS, outcome.message)
        self._assert_names_s(outcome)
        check_cmds = [a for a in recorded if "check" in a]
        self.assertTrue(check_cmds)
        for argv in check_cmds:
            self.assertIn(self.s_id, argv)
            self.assertNotIn(self.w_id, argv)
            self.assertNotIn("--latest", argv)
            # No tag-based reselection
            self.assertNotIn("--tag", argv)

    def test_restore_validated_snapshot_accepts_s_rejects_w(self):
        target_s = self.fx.fw.check(self.fx.parent / "restore-s", label="restore_s")
        target_s.mkdir()
        ok = restore_validated_snapshot(
            self.ctx, snapshot_id=self.s_id, target_dir=target_s
        )
        self.assertEqual(ok.status, STATUS_PASS, ok.message)
        self._assert_names_s(ok)

        target_w = self.fx.fw.check(self.fx.parent / "restore-w", label="restore_w")
        target_w.mkdir()
        bad = restore_validated_snapshot(
            self.ctx, snapshot_id=self.w_id, target_dir=target_w
        )
        self.assertEqual(bad.status, STATUS_FAIL)
        self.assertEqual(bad.exit_code, EXIT_WRONG_PATH)
        self.assertIsNone(bad.source)

    def test_preflight_cli_names_s_rejects_w(self):
        mod = _load_script(
            "complete_data_restore_preflight",
            REPO_ROOT / "scripts" / "complete_data_restore_preflight.py",
        )
        target = self.fx.fw.check(self.fx.parent / "preflight-s", label="pf_s")
        target.mkdir()
        code = mod.main(
            [
                "--env-file",
                str(self.fx.env_file),
                "--snapshot-id",
                self.s_id,
                "--target",
                str(target),
                "--json",
                "--report-dir",
                str(self.fx.parent / "preflight-reports"),
            ]
        )
        # Hermetic seed-only data roots are not replacement-ready; preflight must
        # still restore S and write a durable report (exit may be BLOCKED/30).
        self.assertNotEqual(code, EXIT_WRONG_PATH)
        self.assertIn(code, (0, 30, 31))
        report = next((self.fx.parent / "preflight-reports").glob("restore-*.json"))
        payload = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(payload["meta"]["snapshot"]["id"], self.s_id)

        target_w = self.fx.fw.check(self.fx.parent / "preflight-w", label="pf_w")
        target_w.mkdir()
        code_w = mod.main(
            [
                "--env-file",
                str(self.fx.env_file),
                "--snapshot-id",
                self.w_id,
                "--target",
                str(target_w),
            ]
        )
        self.assertEqual(code_w, EXIT_WRONG_PATH)

    def test_drill_selection_path_names_s(self):
        # Selection via resolve_snapshot (same path drill uses)
        ref = resolve_snapshot(self.ctx, requested_id=self.s_id)
        self.assertEqual(ref.id, self.s_id)
        with self.assertRaises(Exception):
            resolve_snapshot(self.ctx, requested_id=self.w_id)

        # restore_validated_snapshot as drill does
        target = self.fx.fw.check(self.fx.parent / "drill-s", label="drill_s")
        target.mkdir()
        outcome = restore_validated_snapshot(
            self.ctx, snapshot_id=self.s_id, target_dir=target
        )
        self.assertEqual(outcome.status, STATUS_PASS)
        self._assert_names_s(outcome)

    def test_resolver_failure_never_false_greens(self):
        # Configured setup with no matching snapshots for a fresh tag demand
        outcome = run_integrity_check(self.ctx, snapshot_id="0" * 64)
        self.assertEqual(outcome.status, STATUS_FAIL)
        self.assertNotIn(outcome.status, {STATUS_PASS, STATUS_SKIP_DISABLED})
        self.assertIn(outcome.exit_code, {EXIT_INVALID_ID})

        # Offsite health with configured external but no copy → WARN not PASS/SKIP
        # (S exists locally; D missing)
        health = check_offsite_health(self.ctx)
        self.assertEqual(health.status, STATUS_WARN)
        self.assertNotEqual(health.status, STATUS_PASS)
        self.assertNotEqual(health.status, STATUS_SKIP_DISABLED)

        # Ensure with require_current after wiping tags conceptually: wrong tag
        # Use a context that expects a nonexistent tag by temporarily backing
        # up nothing matching — force resolve failure via wrong data_root.
        other = self.fx.fw.check(self.fx.parent / "empty-root", label="empty")
        other.mkdir()
        (other / "x").write_text("x\n", encoding="utf-8")
        bad_ctx = BackupContext(
            profile=BackupProfile.COMPLETE_DATA_V2,
            local_repository=self.ctx.local_repository,
            external_repository=self.ctx.external_repository,
            password_file=self.ctx.password_file,
            data_root=other,
            chroma_dir=self.ctx.chroma_dir,
            restic_bin=self.ctx.restic_bin,
            subprocess_env=self.ctx.subprocess_env,
        )
        ensured = ensure_current_snapshot(bad_ctx, require_current=True)
        self.assertEqual(ensured.status, STATUS_FAIL)
        self.assertIn(ensured.exit_code, {EXIT_WRONG_PATH, EXIT_NO_TAGGED_SNAPSHOT})

    def test_unconfigured_external_is_skip_disabled(self):
        ctx = BackupContext(
            profile=self.ctx.profile,
            local_repository=self.ctx.local_repository,
            external_repository=None,
            password_file=self.ctx.password_file,
            data_root=self.ctx.data_root,
            chroma_dir=self.ctx.chroma_dir,
            restic_bin=self.ctx.restic_bin,
            subprocess_env=self.ctx.subprocess_env,
        )
        copy_out = copy_current_snapshot_offsite(ctx)
        self.assertEqual(copy_out.status, STATUS_SKIP_DISABLED)
        health = check_offsite_health(ctx)
        self.assertEqual(health.status, STATUS_SKIP_DISABLED)

    def test_legacy_profile_health_is_warn_legacy_only(self):
        legacy = self.fx.load_ctx(profile="legacy-chroma", include_data_root=True)
        local = check_local_health(legacy)
        self.assertEqual(local.status, STATUS_WARN_LEGACY_ONLY)
        self.assertIn("WARN_LEGACY_ONLY", local.message)
        self.assertNotIn("complete-data protected", local.message.lower())
        # Even with external configured, legacy offsite never claims v2 protection
        off = check_offsite_health(legacy)
        self.assertEqual(off.status, STATUS_WARN_LEGACY_ONLY)

    def test_argv_never_latest_across_workflows(self):
        recorded: list[list[str]] = []
        real_run = subprocess.run

        def wrapped(cmd, *args, **kwargs):
            if cmd and "restic" in str(cmd[0]):
                recorded.append(list(cmd))
            return real_run(cmd, *args, **kwargs)

        with mock.patch("restic_snapshot.subprocess.run", side_effect=wrapped):
            ensure_current_snapshot(self.ctx)
            run_integrity_check(self.ctx)
            copy_current_snapshot_offsite(self.ctx)
            target = self.fx.fw.check(self.fx.parent / "argv-restore", label="ar")
            target.mkdir()
            restore_validated_snapshot(
                self.ctx, snapshot_id=self.s_id, target_dir=target
            )
        self.assertTrue(recorded)
        for argv in recorded:
            self.assertNotIn("--latest", argv)
            self.assertFalse(any(str(a).startswith("--latest=") for a in argv))

    def test_no_live_config_reads(self):
        live = Path.home() / ".config" / "convmem" / "restic.env"
        # Env for this test points only at hermetic file
        self.assertTrue(str(self.fx.env_file).startswith(str(self.fx.parent)))
        opened = []
        real_open = open

        def guard(file, *args, **kwargs):
            path = str(file)
            if "restic.env" in path and str(Path.home() / ".config" / "convmem") in path:
                opened.append(path)
            return real_open(file, *args, **kwargs)

        with mock.patch("builtins.open", side_effect=guard):
            ensure_current_snapshot(self.ctx)
            check_local_health(self.ctx)
        self.assertEqual(opened, [])


@unittest.skipUnless(_restic_available(), "restic >= 0.19.0 not available")
class TestEnsureCreatesSnapshot(unittest.TestCase):
    def setUp(self):
        self.fx = HermeticFixture()
        self.addCleanup(self.fx.cleanup)
        self.fx.init_repos()
        self.ctx = self.fx.load_ctx(profile="complete-data-v2")

    def test_ensure_backs_up_when_missing(self):
        outcome = ensure_current_snapshot(self.ctx)
        self.assertEqual(outcome.status, STATUS_PASS, outcome.message)
        self.assertIsNotNone(outcome.source)
        self.assertEqual(len(outcome.source.id), 64)
        self.assertTrue(outcome.details.get("backed_up"))


if __name__ == "__main__":
    unittest.main()
