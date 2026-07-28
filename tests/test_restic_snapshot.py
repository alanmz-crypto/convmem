"""Hermetic tests for restic_snapshot.py (complete-data backup correction v2).

Requires RESTIC_TEST_BIN (or restic on PATH) >= 0.19.0.
Every mutable path lives under ONE temporary parent; a path firewall aborts
if a mutable path escapes that parent.

Tests must NOT read live ~/.config/convmem or live data roots.
"""

# Imports follow a path-isolation bootstrap. The hermetic fixture deliberately
# owns many explicit path roles for firewall coverage.
# pylint: disable=wrong-import-position,too-many-instance-attributes
# pylint: disable=consider-using-with,duplicate-code

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from restic_snapshot import (  # noqa: E402
    EXIT_COPY_LINEAGE_FAILURE,
    EXIT_INVALID_CONFIG,
    EXIT_INVALID_ID,
    EXIT_NO_TAGGED_SNAPSHOT,
    EXIT_OK,
    EXIT_RESTIC_UNAVAILABLE,
    EXIT_WRONG_PATH,
    RESTIC_EXIT_LOCK,
    RESTIC_EXIT_PASSWORD,
    RESTIC_EXIT_REPOSITORY,
    BackupContext,
    BackupProfile,
    RepositoryRef,
    ResolverError,
    SnapshotRef,
    TAG_COMPLETE_DATA_V2,
    TAG_LEGACY_CHROMA,
    _is_current_local_day,
    _map_restic_exit,
    _run_restic,
    check_restic_available,
    normalize_data_root,
    parse_repository_ref,
    resolve_copy_destination,
    resolve_snapshot,
    validate_path_layout,
    verify_restic_capabilities,
)


# ---------------------------------------------------------------------------
# Path firewall + helpers
# ---------------------------------------------------------------------------
class PathFirewallError(RuntimeError):
    """Raised when a mutable test path escapes the hermetic parent."""


class PathFirewall:
    def __init__(self, parent: Path):
        self.parent = parent.resolve()
        self._checked: list[Path] = []

    def check(self, path: Path | str, *, label: str = "path") -> Path:
        resolved = Path(path).expanduser().resolve()
        try:
            resolved.relative_to(self.parent)
        except ValueError as exc:
            raise PathFirewallError(
                f"mutable {label} escaped hermetic parent: {resolved} "
                f"not under {self.parent}"
            ) from exc
        # Also reject live config / live data roots explicitly.
        live_forbidden = (
            Path.home().resolve() / ".config" / "convmem",
            Path.home().resolve() / ".local" / "share" / "convmem",
        )
        for forbidden in live_forbidden:
            try:
                resolved.relative_to(forbidden)
            except ValueError:
                continue
            raise PathFirewallError(
                f"mutable {label} resolved under live path {forbidden}: {resolved}"
            )
        self._checked.append(resolved)
        return resolved


def _restic_bin() -> str:
    return os.environ.get("RESTIC_TEST_BIN", "restic")


def _restic_available() -> bool:
    try:
        check_restic_available(_restic_bin())
        return True
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def _assert_not_live_reads() -> None:
    """Sanity: tests never open the live restic.env as input."""
    # We do not open it; this assertion documents the contract.
    assert "CONVMEM_RESTIC_ENV" not in os.environ or not str(
        Path(os.environ["CONVMEM_RESTIC_ENV"]).expanduser()
    ).startswith(str((Path.home() / ".config" / "convmem").resolve()))


class HermeticFixture:
    """ONE temporary parent holding all mutable paths for a test class."""

    def __init__(self) -> None:
        self.td = tempfile.TemporaryDirectory(prefix="convmem-restic-t1-")
        self.parent = Path(self.td.name).resolve()
        self.fw = PathFirewall(self.parent)

        self.home = self.fw.check(self.parent / "home", label="home")
        self.home.mkdir()
        self.cache = self.fw.check(self.parent / "cache", label="cache")
        self.cache.mkdir()
        self.secrets = self.fw.check(self.parent / "secrets", label="secrets")
        self.secrets.mkdir()
        self.pass_file = self.fw.check(
            self.secrets / "restic.password", label="password"
        )
        self.pass_file.write_text("test-restic-snapshot-password\n", encoding="utf-8")
        self.pass_file.chmod(0o600)

        self.data_root = self.fw.check(self.parent / "data-root", label="data_root")
        self.data_root.mkdir()
        self.chroma_dir = self.fw.check(
            self.data_root / "chroma", label="chroma_dir"
        )
        self.chroma_dir.mkdir()
        (self.chroma_dir / "seed.txt").write_text("chroma\n", encoding="utf-8")
        (self.data_root / "seed.txt").write_text("data\n", encoding="utf-8")

        self.wrong_root = self.fw.check(
            self.parent / "wrong-root", label="wrong_root"
        )
        self.wrong_root.mkdir()
        (self.wrong_root / "seed.txt").write_text("wrong\n", encoding="utf-8")

        self.local_repo = self.fw.check(
            self.parent / "local-repo", label="local_repo"
        )
        self.external_repo = self.fw.check(
            self.parent / "external-repo", label="external_repo"
        )
        self.env_file = self.fw.check(
            self.parent / "restic.env", label="env_file"
        )

        self.base_env = {
            **os.environ,
            "HOME": str(self.home),
            "RESTIC_CACHE_DIR": str(self.cache),
            "XDG_CACHE_HOME": str(self.cache),
            "TMPDIR": str(self.parent / "tmp"),
        }
        (self.parent / "tmp").mkdir(exist_ok=True)

    def cleanup(self) -> None:
        self.td.cleanup()

    def write_env(
        self,
        *,
        profile: str = "complete-data-v2",
        include_data_root: bool = True,
        data_root: Path | None = None,
        chroma_dir: Path | None = None,
        local_repo: Path | None = None,
        external_repo: Path | None = None,
        password_file: Path | None = None,
        restic_bin: str | None = None,
    ) -> Path:
        dr = data_root or self.data_root
        cd = chroma_dir or self.chroma_dir
        lr = local_repo or self.local_repo
        er = external_repo or self.external_repo
        pf = password_file or self.pass_file
        for p, label in (
            (dr, "data_root"),
            (cd, "chroma_dir"),
            (lr, "local_repo"),
            (er, "external_repo"),
            (pf, "password"),
        ):
            self.fw.check(p, label=label)

        lines = [
            f"CONVMEM_BACKUP_PROFILE={profile}",
            f"RESTIC_REPOSITORY={lr}",
            f"RESTIC_EXTERNAL_REPOSITORY={er}",
            f"RESTIC_PASSWORD_FILE={pf}",
            f"CONVMEM_CHROMA_DIR={cd}",
            f"RESTIC_CACHE_DIR={self.cache}",
            f"RESTIC_BIN={restic_bin or _restic_bin()}",
        ]
        if include_data_root:
            lines.insert(1, f"CONVMEM_DATA_ROOT={dr}")
        self.env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self.env_file

    def init_repos(self) -> None:
        self.fw.check(self.local_repo, label="local_repo")
        self.fw.check(self.external_repo, label="external_repo")
        for repo in (self.local_repo, self.external_repo):
            proc = subprocess.run(
                [
                    _restic_bin(),
                    "-r",
                    str(repo),
                    f"--password-file={self.pass_file}",
                    "init",
                ],
                capture_output=True,
                text=True,
                env=self.base_env,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"restic init failed: {proc.stderr or proc.stdout}"
                )

    def make_snapshot(self, data_dir: Path, tags: list[str], repo: Path | None = None) -> dict:
        target_repo = repo or self.local_repo
        self.fw.check(data_dir, label="snapshot_data")
        self.fw.check(target_repo, label="snapshot_repo")
        run_env = {**self.base_env, "RESTIC_PASSWORD_FILE": str(self.pass_file)}
        proc = subprocess.run(
            [
                _restic_bin(),
                "-r",
                str(target_repo),
                "backup",
                str(data_dir),
                *([f"--tag={t}" for t in tags]),
                "--json",
            ],
            capture_output=True,
            text=True,
            env=run_env,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"backup failed: {proc.stderr or proc.stdout}")
        for line in proc.stdout.strip().splitlines():
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("message_type") == "summary":
                return self.get_snapshot(msg["snapshot_id"], repo=target_repo)
        raise RuntimeError(f"no summary in backup output: {proc.stdout}")

    def get_snapshot(self, snap_id: str, repo: Path | None = None) -> dict:
        target_repo = repo or self.local_repo
        run_env = {**self.base_env, "RESTIC_PASSWORD_FILE": str(self.pass_file)}
        proc = subprocess.run(
            [
                _restic_bin(),
                "-r",
                str(target_repo),
                "snapshots",
                snap_id,
                "--json",
            ],
            capture_output=True,
            text=True,
            env=run_env,
            check=True,
        )
        snaps = json.loads(proc.stdout or "[]")
        if not snaps:
            raise RuntimeError(f"snapshot {snap_id} not found")
        return snaps[0]

    def load_ctx(self, **kwargs: Any) -> BackupContext:
        env_path = self.write_env(**kwargs)
        # Patch HOME so Path.home() rejects use live home as data root comparisons
        # still work, while from_env_file never reads live config.
        with mock.patch.dict(os.environ, self.base_env, clear=False):
            return BackupContext.from_env_file(env_path)


# ---------------------------------------------------------------------------
# Unit / layout tests (no live paths)
# ---------------------------------------------------------------------------
class TestPathFirewallContract(unittest.TestCase):
    def test_firewall_rejects_escape(self):
        with tempfile.TemporaryDirectory() as td:
            fw = PathFirewall(Path(td))
            with self.assertRaises(PathFirewallError):
                fw.check("/etc/passwd", label="escape")

    def test_normalize_data_root_absolute(self):
        with tempfile.TemporaryDirectory() as td:
            p = normalize_data_root(td)
            self.assertTrue(p.is_absolute())


@unittest.skipUnless(_restic_available(), "restic >= 0.19.0 not available")
class TestUnsafeLayoutRejections(unittest.TestCase):
    def setUp(self):
        self.fx = HermeticFixture()
        self.addCleanup(self.fx.cleanup)
        _assert_not_live_reads()

    def test_reject_root_as_data_root(self):
        with self.assertRaises(ResolverError) as ctx:
            validate_path_layout(
                data_root=Path("/"),
                chroma_dir=self.fx.chroma_dir,
                local_repo=RepositoryRef(str(self.fx.local_repo), True),
                external_repo=None,
                password_file=self.fx.pass_file,
            )
        self.assertEqual(ctx.exception.exit_code, EXIT_INVALID_CONFIG)

    def test_reject_home_as_data_root(self):
        with self.assertRaises(ResolverError) as ctx:
            validate_path_layout(
                data_root=Path.home().resolve(),
                chroma_dir=self.fx.chroma_dir,
                local_repo=RepositoryRef(str(self.fx.local_repo), True),
                external_repo=None,
                password_file=self.fx.pass_file,
            )
        self.assertEqual(ctx.exception.exit_code, EXIT_INVALID_CONFIG)

    def test_reject_data_root_equals_chroma(self):
        with self.assertRaises(ResolverError) as ctx:
            validate_path_layout(
                data_root=self.fx.chroma_dir,
                chroma_dir=self.fx.chroma_dir,
                local_repo=RepositoryRef(str(self.fx.local_repo), True),
                external_repo=None,
                password_file=self.fx.pass_file,
            )
        self.assertEqual(ctx.exception.exit_code, EXIT_INVALID_CONFIG)

    def test_reject_password_inside_repo(self):
        # Place password inside a fake repo directory.
        bad_repo = self.fx.fw.check(self.fx.parent / "bad-repo", label="bad_repo")
        bad_repo.mkdir()
        pw_inside = self.fx.fw.check(bad_repo / "restic.password", label="pw_inside")
        pw_inside.write_text("x\n", encoding="utf-8")
        with self.assertRaises(ResolverError) as ctx:
            validate_path_layout(
                data_root=self.fx.data_root,
                chroma_dir=self.fx.chroma_dir,
                local_repo=RepositoryRef(str(bad_repo.resolve()), True),
                external_repo=None,
                password_file=pw_inside,
            )
        self.assertEqual(ctx.exception.exit_code, EXIT_INVALID_CONFIG)

    def test_reject_repo_overlap_data_root(self):
        nested = self.fx.fw.check(
            self.fx.data_root / "nested-repo", label="nested_repo"
        )
        nested.mkdir()
        with self.assertRaises(ResolverError) as ctx:
            validate_path_layout(
                data_root=self.fx.data_root,
                chroma_dir=self.fx.chroma_dir,
                local_repo=RepositoryRef(str(nested.resolve()), True),
                external_repo=None,
                password_file=self.fx.pass_file,
            )
        self.assertEqual(ctx.exception.exit_code, EXIT_INVALID_CONFIG)


@unittest.skipUnless(_restic_available(), "restic >= 0.19.0 not available")
class TestProfileRules(unittest.TestCase):
    def setUp(self):
        self.fx = HermeticFixture()
        self.addCleanup(self.fx.cleanup)
        self.fx.init_repos()

    def test_complete_data_v2_rejects_missing_data_root(self):
        env = self.fx.write_env(profile="complete-data-v2", include_data_root=False)
        with self.assertRaises(ResolverError) as ctx:
            BackupContext.from_env_file(env)
        self.assertEqual(ctx.exception.exit_code, EXIT_INVALID_CONFIG)
        self.assertIn("CONVMEM_DATA_ROOT", str(ctx.exception))

    def test_legacy_allows_derived_data_root_with_warn(self):
        env = self.fx.write_env(profile="legacy-chroma", include_data_root=False)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ctx = BackupContext.from_env_file(env)
        self.assertEqual(ctx.profile, BackupProfile.LEGACY_CHROMA)
        self.assertTrue(ctx.data_root_derived)
        self.assertEqual(ctx.data_root, self.fx.chroma_dir.parent.resolve())
        self.assertTrue(
            any("WARN_LEGACY_ONLY" in str(w.message) for w in caught),
            f"expected WARN_LEGACY_ONLY, got {caught}",
        )

    def test_complete_data_v2_default_tag(self):
        ctx = self.fx.load_ctx(profile="complete-data-v2")
        self.assertEqual(ctx.default_tag(), TAG_COMPLETE_DATA_V2)

    def test_legacy_default_tag(self):
        ctx = self.fx.load_ctx(profile="legacy-chroma")
        self.assertEqual(ctx.default_tag(), TAG_LEGACY_CHROMA)

    def test_opaque_remote_stays_opaque(self):
        ref = parse_repository_ref("sftp:user@host:/path/to/repo")
        self.assertFalse(ref.is_local)
        self.assertEqual(ref.locator, "sftp:user@host:/path/to/repo")

    def test_local_repo_gets_realpath(self):
        link_parent = self.fx.fw.check(self.fx.parent / "link-parent", label="lp")
        link_parent.mkdir()
        real = self.fx.fw.check(link_parent / "real-repo", label="real")
        real.mkdir()
        link = self.fx.fw.check(self.fx.parent / "repo-link", label="link")
        link.symlink_to(real)
        ref = parse_repository_ref(str(link))
        self.assertTrue(ref.is_local)
        self.assertEqual(ref.locator, str(real.resolve()))


@unittest.skipUnless(_restic_available(), "restic >= 0.19.0 not available")
class TestCapabilitiesAndReservedExits(unittest.TestCase):
    def setUp(self):
        self.fx = HermeticFixture()
        self.addCleanup(self.fx.cleanup)
        self.fx.init_repos()

    def test_empty_capability_binary_fails(self):
        # Fake restic that only prints a plausible version string.
        fake = self.fx.fw.check(self.fx.parent / "fake-restic", label="fake")
        fake.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "version" ]; then echo "restic 0.19.0 compiled with go"; exit 0; fi\n'
            'if [ "$1" = "help" ]; then echo "Usage: restic"; exit 0; fi\n'
            "echo missing capability >&2; exit 1\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        ctx = self.fx.load_ctx(restic_bin=str(fake))
        with self.assertRaises(ResolverError) as caught:
            verify_restic_capabilities(ctx)
        self.assertEqual(caught.exception.exit_code, EXIT_RESTIC_UNAVAILABLE)

    def test_missing_restic_fails(self):
        missing = self.fx.parent / "no-such-restic-binary"
        with self.assertRaises(ResolverError) as caught:
            check_restic_available(str(missing))
        self.assertEqual(caught.exception.exit_code, EXIT_RESTIC_UNAVAILABLE)

    def test_preserve_exit_10_missing_repository(self):
        missing_repo = self.fx.fw.check(
            self.fx.parent / "missing-repo", label="missing_repo"
        )
        # Do not create the directory — restic should exit 10.
        ctx = self.fx.load_ctx()
        # Point local repository at missing path via a patched RepositoryRef.
        bad_ctx = BackupContext(
            profile=ctx.profile,
            local_repository=RepositoryRef(str(missing_repo), True),
            external_repository=ctx.external_repository,
            password_file=ctx.password_file,
            data_root=ctx.data_root,
            chroma_dir=ctx.chroma_dir,
            restic_bin=ctx.restic_bin,
            subprocess_env=ctx.subprocess_env,
            data_root_derived=False,
        )
        with self.assertRaises(ResolverError) as caught:
            _run_restic(
                bad_ctx,
                ["snapshots", "--json"],
                domain_error_code=EXIT_NO_TAGGED_SNAPSHOT,
            )
        self.assertEqual(caught.exception.exit_code, RESTIC_EXIT_REPOSITORY)

    def test_preserve_exit_12_wrong_password(self):
        wrong = self.fx.fw.check(
            self.fx.secrets / "wrong.password", label="wrong_pw"
        )
        wrong.write_text("definitely-not-the-password\n", encoding="utf-8")
        ctx = self.fx.load_ctx()
        env = dict(ctx.subprocess_env)
        env["RESTIC_PASSWORD_FILE"] = str(wrong)
        bad_ctx = BackupContext(
            profile=ctx.profile,
            local_repository=ctx.local_repository,
            external_repository=ctx.external_repository,
            password_file=wrong,
            data_root=ctx.data_root,
            chroma_dir=ctx.chroma_dir,
            restic_bin=ctx.restic_bin,
            subprocess_env=env,
            data_root_derived=False,
        )
        with self.assertRaises(ResolverError) as caught:
            _run_restic(
                bad_ctx,
                ["snapshots", "--json"],
                domain_error_code=EXIT_NO_TAGGED_SNAPSHOT,
            )
        self.assertEqual(caught.exception.exit_code, RESTIC_EXIT_PASSWORD)

    def test_preserve_exit_11_via_mapper(self):
        # Holding a real lock across processes is flaky in CI; prove the
        # reserved-code mapper never rewrites 11 into a domain code.
        self.assertEqual(_map_restic_exit(11, EXIT_NO_TAGGED_SNAPSHOT), RESTIC_EXIT_LOCK)
        self.assertEqual(_map_restic_exit(10, 22), RESTIC_EXIT_REPOSITORY)
        self.assertEqual(_map_restic_exit(12, 22), RESTIC_EXIT_PASSWORD)
        self.assertEqual(_map_restic_exit(1, 22), 22)

    def test_capability_check_passes_on_real_restic(self):
        self.fx.make_snapshot(self.fx.data_root, [TAG_COMPLETE_DATA_V2])
        ctx = self.fx.load_ctx()
        verify_restic_capabilities(ctx)


@unittest.skipUnless(_restic_available(), "restic >= 0.19.0 not available")
class TestResolverDecisiveFixture(unittest.TestCase):
    """Older correct-path S beats newer wrong-path W."""

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

    def test_resolver_returns_s_full_id(self):
        ref = resolve_snapshot(self.ctx, require_current_local_day=True)
        self.assertEqual(len(ref.id), 64)
        self.assertEqual(ref.id, self.s_id)
        self.assertNotEqual(ref.id, self.w_id)
        self.assertEqual(set(ref.paths), {str(self.fx.data_root.resolve())})

    def test_argv_never_contains_latest(self):
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
            ref = resolve_snapshot(self.ctx)
        self.assertEqual(ref.id, self.s_id)
        self.assertTrue(recorded, "expected restic invocations")
        for argv in recorded:
            self.assertNotIn("--latest", argv)
            self.assertFalse(any(str(a).startswith("--latest=") for a in argv))

    def test_no_tag_returns_23(self):
        with self.assertRaises(ResolverError) as ctx:
            resolve_snapshot(self.ctx, required_tag="nonexistent-tag")
        self.assertEqual(ctx.exception.exit_code, EXIT_NO_TAGGED_SNAPSHOT)

    def test_wrong_path_returns_24(self):
        other = self.fx.fw.check(self.fx.parent / "other-root", label="other")
        other.mkdir()
        (other / "x").write_text("x\n", encoding="utf-8")
        # Rebuild context with different data_root expectation.
        bad = BackupContext(
            profile=self.ctx.profile,
            local_repository=self.ctx.local_repository,
            external_repository=self.ctx.external_repository,
            password_file=self.ctx.password_file,
            data_root=other,
            chroma_dir=self.ctx.chroma_dir,
            restic_bin=self.ctx.restic_bin,
            subprocess_env=self.ctx.subprocess_env,
        )
        with self.assertRaises(ResolverError) as caught:
            resolve_snapshot(bad)
        self.assertEqual(caught.exception.exit_code, EXIT_WRONG_PATH)

    def test_invalid_and_abbreviated_id(self):
        with self.assertRaises(ResolverError) as caught:
            resolve_snapshot(
                self.ctx,
                requested_id="0" * 64,
            )
        self.assertEqual(caught.exception.exit_code, EXIT_INVALID_ID)

        with self.assertRaises(ResolverError) as caught:
            resolve_snapshot(self.ctx, requested_id=self.s_id[:8])
        self.assertEqual(caught.exception.exit_code, EXIT_INVALID_ID)

    def test_explicit_id_validation(self):
        ref = resolve_snapshot(self.ctx, requested_id=self.s_id)
        self.assertEqual(ref.id, self.s_id)

    def test_explicit_wrong_path_id_fails(self):
        with self.assertRaises(ResolverError):
            resolve_snapshot(self.ctx, requested_id=self.w_id)

    def test_legacy_chroma_tag_never_proves_v2(self):
        # Resolve with v2 profile must not accept only convmem-chroma tags.
        chroma_only_root = self.fx.fw.check(
            self.fx.parent / "chroma-only-root", label="cor"
        )
        chroma_only_root.mkdir()
        (chroma_only_root / "f").write_text("c\n", encoding="utf-8")
        # Fresh repo contents already have v2 tags on S/W; create another snap
        # with only legacy tag on a third path, then ask v2 resolver for that root.
        self.fx.make_snapshot(chroma_only_root, [TAG_LEGACY_CHROMA])
        bad = BackupContext(
            profile=BackupProfile.COMPLETE_DATA_V2,
            local_repository=self.ctx.local_repository,
            external_repository=self.ctx.external_repository,
            password_file=self.ctx.password_file,
            data_root=chroma_only_root,
            chroma_dir=self.ctx.chroma_dir,
            restic_bin=self.ctx.restic_bin,
            subprocess_env=self.ctx.subprocess_env,
        )
        with self.assertRaises(ResolverError) as caught:
            resolve_snapshot(bad)  # default tag convmem-data-v2
        self.assertIn(
            caught.exception.exit_code,
            {EXIT_NO_TAGGED_SNAPSHOT, EXIT_WRONG_PATH},
        )


@unittest.skipUnless(_restic_available(), "restic >= 0.19.0 not available")
class TestCopyLineage(unittest.TestCase):
    def setUp(self):
        self.fx = HermeticFixture()
        self.addCleanup(self.fx.cleanup)
        self.fx.init_repos()
        self.snap_s = self.fx.make_snapshot(
            self.fx.data_root, [TAG_COMPLETE_DATA_V2]
        )
        self.s_id = self.snap_s["id"]
        self.ctx = self.fx.load_ctx()

    def test_copy_lineage_original_equals_source(self):
        envc = {**self.fx.base_env, "RESTIC_PASSWORD_FILE": str(self.fx.pass_file)}
        proc = subprocess.run(
            [
                _restic_bin(),
                "-r",
                str(self.fx.external_repo),
                "copy",
                self.s_id,
                "--from-repo",
                str(self.fx.local_repo),
                "--from-password-file",
                str(self.fx.pass_file),
            ],
            capture_output=True,
            text=True,
            env=envc,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        source = SnapshotRef.from_snapshot_json(
            str(self.fx.local_repo.resolve()), self.snap_s
        )
        dest = resolve_copy_destination(self.ctx, source)
        self.assertEqual(dest.original, source.id)
        self.assertNotEqual(dest.id, source.id)
        self.assertEqual(dest.tree, source.tree)
        self.assertEqual(dest.time, source.time)
        self.assertEqual(set(dest.paths), set(source.paths))
        self.assertIn(TAG_COMPLETE_DATA_V2, dest.tags)

    def test_copy_lineage_missing_returns_27(self):
        source = SnapshotRef.from_snapshot_json(
            str(self.fx.local_repo.resolve()), self.snap_s
        )
        with self.assertRaises(ResolverError) as caught:
            resolve_copy_destination(self.ctx, source)
        self.assertEqual(caught.exception.exit_code, EXIT_COPY_LINEAGE_FAILURE)


@unittest.skipUnless(_restic_available(), "restic >= 0.19.0 not available")
class TestCLI(unittest.TestCase):
    def setUp(self):
        self.fx = HermeticFixture()
        self.addCleanup(self.fx.cleanup)
        self.fx.init_repos()
        self.snap = self.fx.make_snapshot(self.fx.data_root, [TAG_COMPLETE_DATA_V2])
        self.env_file = self.fx.write_env()

    def test_cli_resolve_json(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "restic_snapshot.py"),
                "resolve",
                "--env-file",
                str(self.env_file),
            ],
            capture_output=True,
            text=True,
            env=self.fx.base_env,
            check=False,
        )
        self.assertEqual(proc.returncode, EXIT_OK, proc.stderr)
        data = json.loads(proc.stdout.strip())
        self.assertEqual(data["id"], self.snap["id"])
        self.assertEqual(len(data["id"]), 64)

    def test_cli_show_context_json(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "restic_snapshot.py"),
                "show-context",
                "--env-file",
                str(self.env_file),
            ],
            capture_output=True,
            text=True,
            env=self.fx.base_env,
            check=False,
        )
        self.assertEqual(proc.returncode, EXIT_OK, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["profile"], "complete-data-v2")
        self.assertEqual(data["default_tag"], TAG_COMPLETE_DATA_V2)

    def test_cli_check_capabilities(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "restic_snapshot.py"),
                "check-capabilities",
                "--env-file",
                str(self.env_file),
            ],
            capture_output=True,
            text=True,
            env=self.fx.base_env,
            check=False,
        )
        self.assertEqual(proc.returncode, EXIT_OK, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertTrue(data["ok"])


class TestCurrentLocalDay(unittest.TestCase):
    def test_now_is_current(self):
        self.assertTrue(_is_current_local_day(datetime.now(timezone.utc)))

    def test_yesterday_is_not_current(self):
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        self.assertFalse(_is_current_local_day(yesterday))


class TestSnapshotRef(unittest.TestCase):
    def test_roundtrip(self):
        ref = SnapshotRef(
            repository="/tmp/repo",
            id="a" * 64,
            original=None,
            tree="b" * 64,
            time=datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc),
            paths=("/data/root",),
            tags=frozenset([TAG_COMPLETE_DATA_V2]),
        )
        data = json.loads(ref.to_json())
        self.assertEqual(data["id"], ref.id)
        self.assertIsNone(data["original"])


if __name__ == "__main__":
    unittest.main()
