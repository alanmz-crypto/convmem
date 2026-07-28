"""Hermetic offsite copy + integrated backup flow (complete-data v2 T5).

Real Restic repositories under ONE temporary parent + path firewall.
Never reads live ~/.config/convmem or live data/repos/timers.

Proofs:
  - copy S → D.original == S
  - reject newer wrong-path W (never copied / never selected)
  - shell wrapper restic-copy-external.sh under hermetic env
  - integrated: capture S → reject W → copy S → lineage → check → restore
    → validate evidence → retain reports
"""

# Imports follow a path-isolation bootstrap; repeated S/W assertions are
# intentional independent consumer proofs.
# pylint: disable=wrong-import-position,duplicate-code

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tests.test_restic_snapshot import (  # noqa: E402
    HermeticFixture,
    PathFirewallError,
    _assert_not_live_reads,
    _restic_available,
)

from backup_workflows import (  # noqa: E402
    STATUS_FAIL,
    STATUS_PASS,
    check_offsite_health,
    copy_current_snapshot_offsite,
    ensure_current_snapshot,
    restore_validated_snapshot,
    run_integrity_check,
)
from complete_data_restore import (  # noqa: E402
    EVIDENCE_FILENAME,
    OUTCOME_BLOCKED,
    RestoreReport,
    capture_backup_evidence,
    locate_restored_data_root,
    run_preflight_validation,
    writer_census_for_root,
)
from restic_snapshot import (  # noqa: E402
    EXIT_INVALID_ID,
    EXIT_WRONG_PATH,
    ResolverError,
    TAG_COMPLETE_DATA_V2,
    TAG_LEGACY_CHROMA,
    resolve_copy_destination,
    resolve_snapshot,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
        encoding="utf-8",
    )


def _seed_minimal_valid_root(root: Path) -> None:
    """Populate a hermetic data root that passes restore matrix validators."""
    chroma = root / "chroma"
    chroma.mkdir(parents=True, exist_ok=True)
    db = chroma / "chroma.sqlite3"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        CREATE TABLE collections (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, dimension INTEGER,
            database_id TEXT NOT NULL, config_json_str TEXT, schema_str TEXT
        );
        CREATE TABLE segments (
            id TEXT PRIMARY KEY, type TEXT NOT NULL, scope TEXT NOT NULL,
            collection TEXT NOT NULL
        );
        CREATE TABLE embeddings (
            id INTEGER PRIMARY KEY, segment_id TEXT NOT NULL,
            embedding_id TEXT NOT NULL, seq_id BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE tenants (id TEXT);
        CREATE TABLE databases (id TEXT, name TEXT);
        """
    )
    collections = {
        "knowledge_units": ["ku-1", "ku-2"],
        "conversation_summaries": ["sum-1"],
    }
    for i, (name, ids) in enumerate(collections.items()):
        cid = f"c{i}"
        sid = f"s{i}"
        conn.execute(
            "INSERT INTO collections VALUES (?, ?, NULL, 'db', NULL, NULL)",
            (cid, name),
        )
        conn.execute(
            "INSERT INTO segments VALUES (?, 'vector', 'VECTOR', ?)",
            (sid, cid),
        )
        for j, eid in enumerate(ids):
            conn.execute(
                "INSERT INTO embeddings VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (i * 1000 + j, sid, eid, b"\x00"),
            )
    conn.commit()
    conn.close()

    _write_jsonl(
        root / "decisions-approved.jsonl",
        [
            {
                "id": "dec_prop_test_offsite_001",
                "ledger_id": "dec_prop_test_offsite_001",
                "kind": "decision",
                "status": "accepted",
                "summary": "offsite hermetic",
                "rationale": "t5",
                "proposal_id": "dec_prop_test_offsite_001",
                "domain": "testing",
                "confidence": 1.0,
            }
        ],
    )
    _write_jsonl(
        root / "knowledge_units.jsonl",
        [{"id": "ku-1"}, {"id": "ku-2"}],
    )
    (root / "processed.json").write_text(
        json.dumps({"abc": {"path": "/tmp/x", "units": 1}}),
        encoding="utf-8",
    )
    # Keep HermeticFixture seed.txt (known operational residue).


@unittest.skipUnless(_restic_available(), "restic >= 0.19.0 not available")
class TestResticOffsiteHermetic(unittest.TestCase):
    """Real offsite shell/workflow: copy S, D.original==S, reject W."""

    def setUp(self) -> None:
        self.fx = HermeticFixture()
        self.addCleanup(self.fx.cleanup)
        _assert_not_live_reads()
        self.fx.init_repos()
        _seed_minimal_valid_root(self.fx.data_root)

        self.snap_s = self.fx.make_snapshot(
            self.fx.data_root, [TAG_COMPLETE_DATA_V2, TAG_LEGACY_CHROMA]
        )
        self.s_id = self.snap_s["id"]
        self.snap_w = self.fx.make_snapshot(
            self.fx.wrong_root, [TAG_COMPLETE_DATA_V2, TAG_LEGACY_CHROMA]
        )
        self.w_id = self.snap_w["id"]
        self.ctx = self.fx.load_ctx(profile="complete-data-v2")
        self.assertEqual(len(self.s_id), 64)
        self.assertNotEqual(self.s_id, self.w_id)

    def test_workflow_copy_s_lineage_rejects_w(self) -> None:
        recorded: list[list[str]] = []
        real_run = subprocess.run

        def wrapped(cmd, *args, **kwargs):
            if cmd and "restic" in str(cmd[0]):
                recorded.append(list(cmd))
            kwargs.setdefault("check", False)
            return real_run(  # pylint: disable=subprocess-run-check
                cmd, *args, **kwargs
            )

        with mock.patch("restic_snapshot.subprocess.run", side_effect=wrapped):
            outcome = copy_current_snapshot_offsite(self.ctx)
        self.assertEqual(outcome.status, STATUS_PASS, outcome.message)
        self.assertIsNotNone(outcome.source)
        self.assertEqual(outcome.source.id, self.s_id)
        self.assertNotEqual(outcome.source.id, self.w_id)
        self.assertIsNotNone(outcome.destination)
        self.assertEqual(outcome.destination.original, self.s_id)
        self.assertNotEqual(outcome.destination.id, self.w_id)

        copy_cmds = [a for a in recorded if "copy" in a]
        self.assertTrue(copy_cmds, f"no copy argv: {recorded}")
        for argv in copy_cmds:
            self.assertIn(self.s_id, argv)
            self.assertNotIn(self.w_id, argv)
            self.assertNotIn("--latest", argv)

        # Destination resolver agrees.
        dest = resolve_copy_destination(self.ctx, outcome.source)
        self.assertEqual(dest.original, self.s_id)

        # Requesting W by full id must fail closed (wrong path).
        with self.assertRaises(ResolverError) as ctx:
            resolve_snapshot(self.ctx, requested_id=self.w_id)
        self.assertIn(ctx.exception.exit_code, {EXIT_WRONG_PATH, EXIT_INVALID_ID})

        health = check_offsite_health(self.ctx)
        self.assertEqual(health.status, STATUS_PASS, health.message)
        self.assertEqual(health.source.id, self.s_id)
        self.assertEqual(health.destination.original, self.s_id)

    def test_shell_wrapper_copy_under_hermetic_env(self) -> None:
        env_file = self.fx.write_env(profile="complete-data-v2")
        script = REPO_ROOT / "scripts" / "restic-copy-external.sh"
        self.assertTrue(script.is_file())

        run_env = {
            **self.fx.base_env,
            "CONVMEM_RESTIC_ENV": str(env_file),
            "PATH": os.environ.get("PATH", "/usr/bin"),
        }
        # Path firewall: env + repos + password stay under parent.
        self.fx.fw.check(env_file, label="env")
        self.fx.fw.check(self.fx.local_repo, label="local_repo")
        self.fx.fw.check(self.fx.external_repo, label="external_repo")
        self.fx.fw.check(self.fx.pass_file, label="password")

        proc = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            env=run_env,
            check=False,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"shell copy failed rc={proc.returncode} stdout={proc.stdout!r} "
            f"stderr={proc.stderr!r}",
        )

        # Re-load context and prove lineage.
        ctx = self.fx.load_ctx(profile="complete-data-v2")
        source = resolve_snapshot(ctx, require_current_local_day=True)
        self.assertEqual(source.id, self.s_id)
        dest = resolve_copy_destination(ctx, source)
        self.assertEqual(dest.original, self.s_id)
        self.assertNotEqual(dest.id, self.w_id)


@unittest.skipUnless(_restic_available(), "restic >= 0.19.0 not available")
class TestIntegratedHermeticBackupFlow(unittest.TestCase):
    """End-to-end hermetic flow under temporary HOME/XDG/cache/repos/…/systemd."""

    def setUp(self) -> None:
        self.fx = HermeticFixture()
        self.addCleanup(self.fx.cleanup)
        _assert_not_live_reads()

        # Extra hermetic dirs required by V7a.
        self.reports = self.fx.fw.check(self.fx.parent / "reports", label="reports")
        self.reports.mkdir()
        self.systemd = self.fx.fw.check(self.fx.parent / "systemd", label="systemd")
        self.systemd.mkdir()
        self.xdg_config = self.fx.fw.check(
            self.fx.home / ".config", label="xdg_config"
        )
        self.xdg_config.mkdir(parents=True, exist_ok=True)
        self.xdg_data = self.fx.fw.check(
            self.fx.home / ".local" / "share", label="xdg_data"
        )
        self.xdg_data.mkdir(parents=True, exist_ok=True)

        self.fx.init_repos()
        _seed_minimal_valid_root(self.fx.data_root)
        self.ctx = self.fx.load_ctx(profile="complete-data-v2")

    def test_integrated_flow_capture_to_retained_reports(self) -> None:
        # 1) Capture evidence then ensure/create current-day S.
        evidence = capture_backup_evidence(self.fx.data_root)
        self.fx.fw.check(
            self.fx.data_root / EVIDENCE_FILENAME, label="evidence"
        )
        self.assertIn("writer_census", evidence)
        census = writer_census_for_root(self.fx.data_root)
        self.assertEqual(census.get("chroma"), "tier1_authoritative")
        self.assertEqual(
            census.get("knowledge_units.jsonl"), "derived_export"
        )
        self.assertEqual(
            census.get("decisions-approved.jsonl"), "canonical_decisions"
        )

        ensure = ensure_current_snapshot(self.ctx)
        self.assertEqual(ensure.status, STATUS_PASS, ensure.message)
        self.assertIsNotNone(ensure.source)
        s_id = ensure.source.id
        self.assertEqual(len(s_id), 64)

        # 2) Create newer wrong-path W; selection must still name S.
        snap_w = self.fx.make_snapshot(
            self.fx.wrong_root, [TAG_COMPLETE_DATA_V2, TAG_LEGACY_CHROMA]
        )
        w_id = snap_w["id"]
        self.assertNotEqual(s_id, w_id)

        named = resolve_snapshot(self.ctx, require_current_local_day=True)
        self.assertEqual(named.id, s_id)
        self.assertNotEqual(named.id, w_id)
        with self.assertRaises(ResolverError):
            resolve_snapshot(self.ctx, requested_id=w_id)

        # 3) Copy S → D.original == S
        copy_out = copy_current_snapshot_offsite(self.ctx)
        self.assertEqual(copy_out.status, STATUS_PASS, copy_out.message)
        self.assertEqual(copy_out.source.id, s_id)
        self.assertEqual(copy_out.destination.original, s_id)
        self.assertNotEqual(copy_out.destination.id, w_id)

        dest = resolve_copy_destination(self.ctx, copy_out.source)
        self.assertEqual(dest.original, s_id)

        # 4) Integrity check explicit S
        check_out = run_integrity_check(self.ctx, snapshot_id=s_id)
        self.assertEqual(check_out.status, STATUS_PASS, check_out.message)
        self.assertEqual(check_out.source.id, s_id)
        self.assertIn(s_id, check_out.argv)
        self.assertNotIn("--latest", check_out.argv)
        self.assertNotIn("--tag", check_out.argv)

        # 5) Restore S under hermetic target
        restore_target = self.fx.fw.check(
            self.fx.parent / "restore-target", label="restore_target"
        )
        restore_target.mkdir()
        restore_out = restore_validated_snapshot(
            self.ctx, snapshot_id=s_id, target_dir=restore_target
        )
        self.assertEqual(restore_out.status, STATUS_PASS, restore_out.message)
        self.assertEqual(restore_out.source.id, s_id)

        # Reject W restore request
        bad_target = self.fx.fw.check(
            self.fx.parent / "restore-w", label="restore_w"
        )
        bad_target.mkdir()
        bad = restore_validated_snapshot(
            self.ctx, snapshot_id=w_id, target_dir=bad_target
        )
        self.assertEqual(bad.status, STATUS_FAIL)

        # 6) Validate evidence on restored tree
        restored_root = locate_restored_data_root(
            restore_target, self.fx.data_root
        )
        self.fx.fw.check(restored_root, label="restored_root")
        report_json = self.fx.fw.check(
            self.reports / f"restore-{s_id[:12]}.json", label="report_json"
        )
        report = RestoreReport(report_json)
        src = ensure.source
        assert src is not None
        inventory = run_preflight_validation(
            restored_root,
            expected_data_root=self.fx.data_root,
            report=report,
            snapshot_meta={
                "snapshot_id": s_id,
                "tree": src.tree,
                "original": None,
                "tags": list(src.tags),
                "paths": list(src.paths),
                "time": src.time.isoformat(),
                "restic_version": "0.19.0-test",
                "repository": src.repository,
            },
        )
        self.assertNotEqual(
            inventory.overall,
            OUTCOME_BLOCKED,
            f"overall={inventory.overall} classifications={inventory.classifications}",
        )
        # Evidence sidecar should have been restored with the snapshot.
        self.assertTrue((restored_root / EVIDENCE_FILENAME).is_file())

        # 7) Retain reports under hermetic reports dir (RestoreReport writes atomically)
        self.assertTrue(report_json.is_file())
        md_path = report_json.with_suffix(".md")
        self.assertTrue(md_path.is_file())
        self.fx.fw.check(md_path, label="report_md")

        # Path firewall: none of the mutable paths escaped.
        for label, path in (
            ("home", self.fx.home),
            ("cache", self.fx.cache),
            ("local_repo", self.fx.local_repo),
            ("external_repo", self.fx.external_repo),
            ("password", self.fx.pass_file),
            ("reports", self.reports),
            ("systemd", self.systemd),
        ):
            self.fx.fw.check(path, label=label)

        with self.assertRaises(PathFirewallError):
            self.fx.fw.check(Path.home() / ".config" / "convmem", label="live")


if __name__ == "__main__":
    unittest.main()
