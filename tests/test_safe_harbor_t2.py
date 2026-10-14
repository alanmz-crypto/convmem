# pylint: disable=protected-access,too-many-lines,redefined-outer-name,too-many-instance-attributes
"""Isolated Safe Harbor T2 evidence: operation-bound Restic preflight.

Every test gets its own home, XDG, config, Restic profile, scratch repositories
and data root before any project code that could reach a user directory runs.
Production data, config and runtime-main paths are refused. Restic runs only
against scratch repositories under the test's temporary directory. Standard
pytest needs no pre-exported isolation flag.
"""

from __future__ import annotations

import json
import os
import pwd
import shutil
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import chromadb
import pytest

import backup_workflows
import restic_gate
import restic_snapshot
import runtime_guard
from backup_workflows import (
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_WARN,
    STATUS_WARN_LEGACY_ONLY,
    check_local_health,
    check_offsite_health,
    copy_current_snapshot_offsite,
    ensure_current_snapshot,
)
from complete_data_restore import EVIDENCE_FILENAME
from restic_gate import (
    REASON_CHROMA_TARGET_MISMATCH,
    REASON_DAY_BOUNDARY,
    REASON_OPERATION_CONFIG_CHANGED,
    REASON_PATH_OUTSIDE_DATA_ROOT,
    REASON_PROFILE_INPUTS_CHANGED,
    REASON_PROFILE_NOT_V2,
    REASON_SKIP_REFUSED,
    OperationAdmissionRefused,
    OperationTarget,
    preflight_operation,
    verify_preflight_inputs_unchanged,
)
from restic_snapshot import (
    EXIT_INVALID_CONFIG,
    EXIT_RESTIC_UNAVAILABLE,
    EXIT_STALE,
    EXIT_WRONG_PATH,
    REASON_FUTURE_SNAPSHOT_TIME,
    REASON_STALE_SNAPSHOT,
    TAG_COMPLETE_DATA_V2,
    TAG_COMPLETE_DATA_V3,
    BackupContext,
    ResolverError,
    resolve_snapshot,
    snapshot_freshness,
)

ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve().with_name("_safe_harbor_t2_cli.py")
PROD_HOME = Path("/home/lauer")
PROD_DATA = PROD_HOME / ".local/share/convmem"
PROD_CONFIG = PROD_HOME / ".config/convmem"
RUNTIME_MAIN = PROD_HOME / "Projects/convmem/.worktrees/runtime-main"
RESTIC = (
    os.environ.get("RESTIC_TEST_BIN")
    or shutil.which("restic")
    or str(PROD_HOME / ".local/bin/restic")
)

_SCRUBBED_ENV = (
    "CONVMEM_SKIP_RESTIC_GATE",
    "CONVMEM_RESTIC_GATE_EXCEPTION",
    "CONVMEM_CONFIRM_PROD",
    "CONVMEM_CONFIRM_LAB",
    "CONVMEM_SIGNER",
    "CONVMEM_T1_ISOLATED",
    "RESTIC_REPOSITORY",
    "RESTIC_PASSWORD_FILE",
    "RESTIC_PASSWORD",
    "RESTIC_TEST_BIN",
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "SAFE_HARBOR_T2_HOOK",
    "SAFE_HARBOR_T2_NOW",
)


def _production_roots() -> list[Path]:
    roots = [PROD_DATA, PROD_CONFIG, RUNTIME_MAIN]
    try:
        account = Path(pwd.getpwuid(os.getuid()).pw_dir)
        roots += [account / ".local/share/convmem", account / ".config/convmem"]
    except KeyError:
        pass
    return [r.resolve(strict=False) for r in roots]


def _refuse_production(path: Path) -> Path:
    resolved = Path(path).expanduser().resolve(strict=False)
    for banned in _production_roots():
        if resolved == banned or banned in resolved.parents or resolved in banned.parents:
            raise RuntimeError(f"refusing production-overlapping path {resolved}")
    return resolved


def _require_isolated_process() -> None:
    home = Path.home().resolve()
    if home == PROD_HOME:
        raise RuntimeError(f"refusing production HOME {home}")
    _refuse_production(home)
    for key in (
        "CONVMEM_CONFIG",
        "CONVMEM_ROOT",
        "CONVMEM_RESTIC_ENV",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
        "RESTIC_CACHE_DIR",
    ):
        raw = os.environ.get(key, "")
        if not raw or not Path(raw).is_absolute():
            raise RuntimeError(f"refusing unset/relative {key}={raw!r}")
        _refuse_production(Path(raw))
    for key in _SCRUBBED_ENV:
        if key in os.environ:
            raise RuntimeError(f"refusing inherited {key}")


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fresh home/XDG/config/Restic roots before any project call or child."""
    root = _refuse_production(tmp_path / "t2")
    home = root / "home"
    for path in (home, root / "xdg-config", root / "xdg-data", root / "xdg-cache",
                 root / "convmem-root", root / "restic-cache", root / "config"):
        path.mkdir(parents=True)
    for key in _SCRUBBED_ENV:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(root / "xdg-config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(root / "xdg-data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(root / "xdg-cache"))
    monkeypatch.setenv("CONVMEM_ROOT", str(root / "convmem-root"))
    monkeypatch.setenv("CONVMEM_CONFIG", str(root / "config" / "config.toml"))
    monkeypatch.setenv("CONVMEM_RESTIC_ENV", str(root / "restic.env"))
    monkeypatch.setenv("RESTIC_CACHE_DIR", str(root / "restic-cache"))
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    _require_isolated_process()
    return root


def _restic_ok() -> bool:
    try:
        restic_snapshot.check_restic_available(RESTIC)
        return True
    except ResolverError:
        return False


needs_restic = pytest.mark.skipif(not _restic_ok(), reason="restic >= 0.19.0 unavailable")


def local_noon(days: int = 0) -> datetime:
    now = datetime.now().astimezone()
    return now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=days)


@contextmanager
def pinned_clock(instant: datetime):
    """One fixed evaluation instant for resolver, workflows and gate."""

    def fixed() -> datetime:
        return instant

    with mock.patch.object(restic_snapshot, "evaluation_instant", fixed), mock.patch.object(
        backup_workflows, "evaluation_instant", fixed
    ), mock.patch.object(restic_gate, "evaluation_instant", fixed):
        yield


class Scratch:
    """Scratch data root, Restic repositories and profile under one test root."""

    def __init__(self, root: Path):
        self.root = _refuse_production(root)
        self.data = self.root / "data"
        self.chroma = self.data / "chroma"
        self.chroma.mkdir(parents=True)
        (self.data / "seed.txt").write_text("data\n", encoding="utf-8")
        self.repo = self.root / "repo"
        self.ext = self.root / "ext-repo"
        secrets = self.root / "secrets"
        secrets.mkdir()
        self.password = secrets / "restic.password"
        self.password.write_text("t2-scratch-password\n", encoding="utf-8")
        self.password.chmod(0o600)
        self.cache = Path(os.environ["RESTIC_CACHE_DIR"])
        self.env_file = Path(os.environ["CONVMEM_RESTIC_ENV"])

    def write_env(self, *, profile: str = "complete-data-v2", chroma: Path | None = None,
                  data_root: Path | None = None, include_data_root: bool = True,
                  external: bool = True, restic_bin: str = RESTIC) -> Path:
        lines = [
            f"CONVMEM_BACKUP_PROFILE={profile}",
            f"RESTIC_REPOSITORY={self.repo}",
            f"RESTIC_PASSWORD_FILE={self.password}",
            f"CONVMEM_CHROMA_DIR={chroma or self.chroma}",
            f"RESTIC_CACHE_DIR={self.cache}",
            f"RESTIC_BIN={restic_bin}",
        ]
        if include_data_root:
            lines.append(f"CONVMEM_DATA_ROOT={data_root or self.data}")
        if external:
            lines.append(f"RESTIC_EXTERNAL_REPOSITORY={self.ext}")
        self.env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self.env_file

    def restic(self, repo: Path, *args: str) -> subprocess.CompletedProcess:
        env = {**os.environ, "RESTIC_PASSWORD_FILE": str(self.password),
               "RESTIC_CACHE_DIR": str(self.cache)}
        return subprocess.run([RESTIC, "-r", str(_refuse_production(repo)), *args],
                              capture_output=True, text=True, env=env, check=False, timeout=120)

    def init(self, *, external: bool = True) -> None:
        for repo in (self.repo, self.ext) if external else (self.repo,):
            proc = self.restic(repo, "init")
            assert proc.returncode == 0, proc.stderr

    def snapshot(self, when: datetime | None = None, *, tag: str = TAG_COMPLETE_DATA_V2,
                 path: Path | None = None) -> str:
        args = ["backup", str(path or self.data), f"--tag={tag}", "--json"]
        if when is not None:
            args += ["--time", when.astimezone().strftime("%Y-%m-%d %H:%M:%S")]
        proc = self.restic(self.repo, *args)
        assert proc.returncode == 0, proc.stderr
        summaries = [json.loads(line) for line in proc.stdout.splitlines()
                     if '"message_type":"summary"' in line]
        assert len(summaries) == 1, proc.stdout
        return summaries[0]["snapshot_id"]

    def ids(self, repo: Path | None = None) -> list[str]:
        proc = self.restic(repo or self.repo, "snapshots", "--json")
        assert proc.returncode == 0, proc.stderr
        return sorted(s["id"] for s in json.loads(proc.stdout or "[]"))

    def ctx(self) -> BackupContext:
        return BackupContext.from_env_file(self.env_file)

    def target(self, *extra: Path, chroma: Path | None = None) -> OperationTarget:
        chroma = (chroma or self.chroma).resolve()
        return OperationTarget(
            entrypoint="test.t2",
            chroma_dir=chroma,
            affected_paths=(chroma, *(p.resolve() for p in extra)),
            config_path=Path(os.environ["CONVMEM_CONFIG"]),
        )


@pytest.fixture
def scratch(isolated: Path) -> Scratch:
    return Scratch(isolated / "scratch")


# ---------------------------------------------------------------------------
# B-E4.1 resolver freshness
# ---------------------------------------------------------------------------
def test_snapshot_freshness_one_instant_timezone_and_rollover():
    noon = local_noon()
    assert snapshot_freshness(noon - timedelta(hours=1), noon) is None
    assert snapshot_freshness(noon, noon) is None
    assert snapshot_freshness(noon + timedelta(seconds=1), noon) == REASON_FUTURE_SNAPSHOT_TIME
    assert snapshot_freshness(noon + timedelta(days=1), noon) == REASON_FUTURE_SNAPSHOT_TIME
    assert snapshot_freshness(noon - timedelta(days=1), noon) == REASON_STALE_SNAPSHOT
    # Same instant expressed in UTC compares on the evaluation timezone's date.
    from datetime import timezone

    utc_view = (noon - timedelta(hours=1)).astimezone(timezone.utc)
    assert snapshot_freshness(utc_view, noon) is None
    midnight = noon.replace(hour=0) + timedelta(days=1)
    just_before = midnight - timedelta(seconds=1)
    assert snapshot_freshness(just_before, midnight) == REASON_STALE_SNAPSHOT
    assert snapshot_freshness(just_before, just_before) is None


@needs_restic
@pytest.mark.parametrize("ahead", [timedelta(hours=1), timedelta(days=1)], ids=["same-day", "next-day"])
def test_resolver_refuses_future_newest_and_requested(scratch: Scratch, ahead: timedelta):
    scratch.write_env()
    scratch.init(external=False)
    noon = local_noon()
    future_id = scratch.snapshot(noon + ahead)
    ctx = scratch.ctx()
    with pinned_clock(noon):
        with pytest.raises(ResolverError) as newest:
            resolve_snapshot(ctx, require_current_local_day=True)
        with pytest.raises(ResolverError) as requested:
            resolve_snapshot(ctx, require_current_local_day=True, requested_id=future_id)
        assert resolve_snapshot(ctx).id == future_id  # unrestricted selection unchanged
    for exc in (newest.value, requested.value):
        assert exc.exit_code == EXIT_STALE
        assert exc.reason == REASON_FUTURE_SNAPSHOT_TIME


@needs_restic
def test_resolver_never_falls_back_to_older_current_snapshot(scratch: Scratch):
    scratch.write_env()
    scratch.init(external=False)
    noon = local_noon()
    older_current = scratch.snapshot(noon - timedelta(hours=1))
    scratch.snapshot(noon + timedelta(hours=1))
    ctx = scratch.ctx()
    with pinned_clock(noon):
        with pytest.raises(ResolverError) as exc:
            resolve_snapshot(ctx, require_current_local_day=True)
        assert exc.value.reason == REASON_FUTURE_SNAPSHOT_TIME
        # The older snapshot is current on its own; only the no-fallback rule refuses.
        assert resolve_snapshot(
            ctx, require_current_local_day=True, requested_id=older_current
        ).id == older_current


@needs_restic
def test_resolver_stale_reason(scratch: Scratch):
    scratch.write_env()
    scratch.init(external=False)
    noon = local_noon()
    scratch.snapshot(noon - timedelta(days=1))
    with pinned_clock(noon), pytest.raises(ResolverError) as exc:
        resolve_snapshot(scratch.ctx(), require_current_local_day=True)
    assert (exc.value.exit_code, exc.value.reason) == (EXIT_STALE, REASON_STALE_SNAPSHOT)


# ---------------------------------------------------------------------------
# The five approved consumer outcomes
# ---------------------------------------------------------------------------
@needs_restic
@pytest.mark.parametrize("ahead", [timedelta(hours=1), timedelta(days=1)], ids=["same-day", "next-day"])
def test_five_consumers_under_future_snapshot(scratch: Scratch, ahead: timedelta):
    scratch.write_env()
    scratch.init()
    noon = local_noon()
    scratch.snapshot(noon + ahead)
    ctx = scratch.ctx()
    local_before, ext_before = scratch.ids(), scratch.ids(scratch.ext)
    evidence = scratch.data / EVIDENCE_FILENAME
    with pinned_clock(noon):
        live = ensure_current_snapshot(ctx)
        dry = ensure_current_snapshot(ctx, dry_run=True)
        probe = ensure_current_snapshot(ctx, check_only=True)
        local = check_local_health(ctx)
        offsite = check_offsite_health(ctx)
        copy = copy_current_snapshot_offsite(ctx)
    for outcome in (live, dry, local):
        assert (outcome.status, outcome.exit_code, outcome.reason) == (
            STATUS_FAIL, EXIT_STALE, REASON_FUTURE_SNAPSHOT_TIME
        ), outcome
    assert (offsite.status, offsite.exit_code, offsite.reason) == (
        STATUS_WARN, EXIT_STALE, REASON_FUTURE_SNAPSHOT_TIME
    )
    assert (copy.status, copy.exit_code, copy.reason) == (
        STATUS_FAIL, EXIT_STALE, REASON_FUTURE_SNAPSHOT_TIME
    )
    assert probe.status == STATUS_PASS
    assert probe.details["eligibility"] == "unchecked"
    assert "eligibility unchecked" in probe.message
    assert scratch.ids() == local_before, "future snapshot must never trigger a backup"
    assert scratch.ids(scratch.ext) == ext_before == [], "no copy before the refusal"
    assert not evidence.exists(), "no pre-backup evidence capture on refusal"


@needs_restic
def test_five_consumers_same_day_current_pass(scratch: Scratch):
    scratch.write_env()
    scratch.init()
    noon = local_noon()
    sid = scratch.snapshot(noon - timedelta(hours=1))
    ctx = scratch.ctx()
    with pinned_clock(noon):
        live = ensure_current_snapshot(ctx)
        probe = ensure_current_snapshot(ctx, check_only=True)
        local = check_local_health(ctx)
        copy = copy_current_snapshot_offsite(ctx)
        offsite = check_offsite_health(ctx)
    assert live.status == STATUS_PASS and live.source.id == sid
    assert live.details["backed_up"] is False
    assert live.details["evaluated_at"] == noon.isoformat()
    assert probe.status == STATUS_PASS and probe.details["eligibility"] == "unchecked"
    assert local.status == STATUS_PASS
    assert copy.status == STATUS_PASS and copy.destination.original == sid
    assert offsite.status == STATUS_PASS
    assert scratch.ids() == [sid]


@needs_restic
def test_old_snapshot_backs_up_then_fresh_post_backup_resolution(scratch: Scratch):
    scratch.write_env(external=False)
    scratch.init(external=False)
    old = scratch.snapshot(datetime.now().astimezone() - timedelta(days=3))
    outcome = ensure_current_snapshot(scratch.ctx())
    assert outcome.status == STATUS_PASS, outcome
    assert outcome.details["backed_up"] is True
    assert outcome.details["evidence_captured"] is True
    assert outcome.source.id != old and outcome.source.id in scratch.ids()
    assert datetime.fromisoformat(outcome.details["evaluated_at"]) >= outcome.source.time


@needs_restic
def test_control_reusing_pre_backup_clock_fails_post_backup_resolution(scratch: Scratch):
    """Negative control: without a fresh post-backup instant the new snapshot is 'future'."""
    t0 = datetime.now().astimezone() - timedelta(seconds=120)
    if t0.date() != datetime.now().astimezone().date():
        pytest.skip("too close to local midnight for a stable control")
    scratch.write_env(external=False)
    scratch.init(external=False)
    scratch.snapshot(t0 - timedelta(days=3))
    with pinned_clock(t0):
        outcome = ensure_current_snapshot(scratch.ctx())
    assert outcome.status == STATUS_FAIL
    assert (outcome.exit_code, outcome.reason) == (EXIT_STALE, REASON_FUTURE_SNAPSHOT_TIME)
    assert len(scratch.ids()) == 2


@needs_restic
def test_legacy_warn_and_v3_resolution_stay_compatible(scratch: Scratch):
    scratch.init(external=False)
    noon = local_noon()
    scratch.write_env(profile="legacy-chroma", include_data_root=False, external=False)
    with pytest.warns(UserWarning):
        legacy = scratch.ctx()
    with pinned_clock(noon):
        assert check_local_health(legacy).status == STATUS_WARN_LEGACY_ONLY
    scratch.write_env(profile="complete-data-v3", external=False)
    sid = scratch.snapshot(noon - timedelta(hours=1), tag=TAG_COMPLETE_DATA_V3)
    with pinned_clock(noon):
        v3 = scratch.ctx()
        assert resolve_snapshot(v3, require_current_local_day=True).id == sid
        assert check_local_health(v3).status == STATUS_PASS


# ---------------------------------------------------------------------------
# Bound preflight (gate) — in process
# ---------------------------------------------------------------------------
def _refusal(target: OperationTarget) -> OperationAdmissionRefused:
    with pytest.raises(OperationAdmissionRefused) as exc:
        preflight_operation(target)
    return exc.value


@needs_restic
def test_gate_admits_bound_current_v2_target(scratch: Scratch):
    scratch.write_env(external=False)
    scratch.init(external=False)
    noon = local_noon()
    sid = scratch.snapshot(noon - timedelta(hours=1))
    with pinned_clock(noon):
        bound = preflight_operation(scratch.target(scratch.data / "knowledge_units.jsonl"))
    assert bound.status == "admitted" and bound.snapshot_id == sid
    assert bound.evaluated_at == noon.isoformat()
    verify_preflight_inputs_unchanged(bound)
    scratch.env_file.write_text(scratch.env_file.read_text() + "# changed\n", encoding="utf-8")
    with pytest.raises(OperationAdmissionRefused) as exc:
        verify_preflight_inputs_unchanged(bound)
    assert (exc.value.exit_code, exc.value.reason) == (EXIT_INVALID_CONFIG, REASON_PROFILE_INPUTS_CHANGED)


@needs_restic
@pytest.mark.parametrize("profile", ["legacy-chroma", "complete-data-v3"])
def test_gate_requires_explicit_v2_profile(scratch: Scratch, profile: str):
    scratch.write_env(profile=profile, include_data_root=profile != "legacy-chroma", external=False)
    scratch.init(external=False)
    with mock.patch.object(restic_gate, "ensure_current_snapshot") as ensure, warnings_ok():
        exc = _refusal(scratch.target())
    assert (exc.exit_code, exc.reason) == (EXIT_INVALID_CONFIG, REASON_PROFILE_NOT_V2)
    ensure.assert_not_called()
    assert scratch.ids() == []


@contextmanager
def warnings_ok():
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


@needs_restic
def test_gate_refuses_chroma_target_mismatch(scratch: Scratch):
    other = scratch.data / "chroma-b"
    other.mkdir()
    scratch.write_env(external=False)
    scratch.init(external=False)
    with mock.patch.object(restic_gate, "ensure_current_snapshot") as ensure:
        exc = _refusal(scratch.target(chroma=other))
    assert (exc.exit_code, exc.reason) == (EXIT_WRONG_PATH, REASON_CHROMA_TARGET_MISMATCH)
    ensure.assert_not_called()


@needs_restic
def test_gate_refuses_symlinked_export_escaping_data_root(scratch: Scratch):
    outside = scratch.root / "outside"
    outside.mkdir()
    victim = outside / "knowledge_units.jsonl"
    victim.write_text("outside\n", encoding="utf-8")
    link = scratch.data / "knowledge_units.jsonl"
    link.symlink_to(victim)
    scratch.write_env(external=False)
    scratch.init(external=False)
    with mock.patch.object(restic_gate, "ensure_current_snapshot") as ensure:
        exc = _refusal(scratch.target(link))
    assert (exc.exit_code, exc.reason) == (EXIT_WRONG_PATH, REASON_PATH_OUTSIDE_DATA_ROOT)
    ensure.assert_not_called()
    assert victim.read_text(encoding="utf-8") == "outside\n"


@needs_restic
@pytest.mark.parametrize("ahead", [timedelta(hours=1), timedelta(days=1)], ids=["same-day", "next-day"])
def test_gate_refuses_future_snapshot_without_backup(scratch: Scratch, ahead: timedelta):
    scratch.write_env(external=False)
    scratch.init(external=False)
    noon = local_noon()
    scratch.snapshot(noon + ahead)
    before = scratch.ids()
    with pinned_clock(noon):
        exc = _refusal(scratch.target())
    assert (exc.exit_code, exc.reason) == (EXIT_STALE, REASON_FUTURE_SNAPSHOT_TIME)
    assert scratch.ids() == before


@needs_restic
def test_gate_missing_restic_is_21(scratch: Scratch):
    scratch.write_env(restic_bin=str(scratch.root / "no-such-restic"), external=False)
    exc = _refusal(scratch.target())
    assert exc.exit_code == EXIT_RESTIC_UNAVAILABLE


@needs_restic
def test_gate_day_boundary_forces_one_fresh_resolution(scratch: Scratch):
    scratch.write_env(external=False)
    scratch.init(external=False)
    noon = local_noon()
    scratch.snapshot(noon - timedelta(hours=1))
    real_ensure = restic_gate.ensure_current_snapshot
    with pinned_clock(noon), mock.patch.object(
        restic_gate, "ensure_current_snapshot", side_effect=real_ensure
    ) as ensure, mock.patch.object(
        restic_gate, "_local_now", side_effect=[noon + timedelta(days=1), noon]
    ):
        bound = preflight_operation(scratch.target())
    assert bound.status == "admitted"
    assert ensure.call_count == 2

    with pinned_clock(noon), mock.patch.object(
        restic_gate, "ensure_current_snapshot", side_effect=real_ensure
    ) as ensure, mock.patch.object(
        restic_gate, "_local_now", return_value=noon + timedelta(days=1)
    ):
        exc = _refusal(scratch.target())
    assert (exc.exit_code, exc.reason) == (EXIT_STALE, REASON_DAY_BOUNDARY)
    assert ensure.call_count == 2


# ---------------------------------------------------------------------------
# Skip refusal and the explicit isolated exception
# ---------------------------------------------------------------------------
def test_skip_without_isolated_context_is_refused(scratch: Scratch, monkeypatch):
    monkeypatch.setenv("CONVMEM_SKIP_RESTIC_GATE", "1")
    lab_cwd = scratch.root / "convmem-lab"
    lab_cwd.mkdir()
    monkeypatch.chdir(lab_cwd)
    monkeypatch.setenv("CONVMEM_ROOT", str(lab_cwd))
    monkeypatch.setenv("CONVMEM_CONFIRM_PROD", "1")
    monkeypatch.setenv("CONVMEM_CONFIRM_LAB", "1")
    monkeypatch.setenv("CONVMEM_CONFIG", str(scratch.root / "convmem-lab" / "config.toml"))
    exc = _refusal(scratch.target())
    assert (exc.exit_code, exc.reason) == (EXIT_INVALID_CONFIG, REASON_SKIP_REFUSED)


@pytest.mark.parametrize("value", ["true", "yes", "0", " 1"])
def test_skip_unrecognized_value_is_refused(scratch: Scratch, monkeypatch, value: str):
    monkeypatch.setenv("CONVMEM_SKIP_RESTIC_GATE", value)
    monkeypatch.setenv("CONVMEM_RESTIC_GATE_EXCEPTION", "isolated-test")
    exc = _refusal(scratch.target())
    assert exc.reason == REASON_SKIP_REFUSED


def test_skip_with_unknown_context_is_refused(scratch: Scratch, monkeypatch):
    monkeypatch.setenv("CONVMEM_SKIP_RESTIC_GATE", "1")
    monkeypatch.setenv("CONVMEM_RESTIC_GATE_EXCEPTION", "lab")
    assert _refusal(scratch.target()).reason == REASON_SKIP_REFUSED


def test_skip_refused_when_target_is_production_shaped_under_home(scratch: Scratch, monkeypatch):
    monkeypatch.setenv("CONVMEM_SKIP_RESTIC_GATE", "1")
    monkeypatch.setenv("CONVMEM_RESTIC_GATE_EXCEPTION", "isolated-test")
    fake_prod = Path.home() / ".local/share/convmem/chroma"
    fake_prod.mkdir(parents=True)
    exc = _refusal(scratch.target(chroma=fake_prod))
    assert exc.reason == REASON_SKIP_REFUSED
    cfg_under_prod = Path.home() / ".config/convmem/config.toml"
    monkeypatch.setenv("CONVMEM_CONFIG", str(cfg_under_prod))
    exc = _refusal(scratch.target())
    assert exc.reason == REASON_SKIP_REFUSED


def test_skip_refused_for_passwd_home_production_root(scratch: Scratch, monkeypatch):
    account_home = scratch.root / "account-home"
    target_chroma = account_home / ".local/share/convmem/chroma"
    target_chroma.mkdir(parents=True)
    monkeypatch.setenv("CONVMEM_SKIP_RESTIC_GATE", "1")
    monkeypatch.setenv("CONVMEM_RESTIC_GATE_EXCEPTION", "isolated-test")
    fake = mock.Mock(pw_dir=str(account_home))
    with mock.patch.object(runtime_guard.pwd, "getpwuid", return_value=fake):
        exc = _refusal(scratch.target(chroma=target_chroma))
    assert exc.reason == REASON_SKIP_REFUSED
    assert "production root" in str(exc)


def test_isolated_lab_requires_lab_data_root(scratch: Scratch, monkeypatch):
    monkeypatch.setenv("CONVMEM_SKIP_RESTIC_GATE", "1")
    monkeypatch.setenv("CONVMEM_RESTIC_GATE_EXCEPTION", "isolated-lab")
    assert _refusal(scratch.target()).reason == REASON_SKIP_REFUSED
    lab_chroma = Path.home() / ".local/share/convmem-lab/chroma"
    lab_chroma.mkdir(parents=True)
    bound = preflight_operation(scratch.target(chroma=lab_chroma))
    assert bound.status == "isolated-exception"
    monkeypatch.setenv("CONVMEM_RESTIC_GATE_EXCEPTION", "isolated-test")
    assert _refusal(scratch.target(chroma=lab_chroma)).reason == REASON_SKIP_REFUSED


def test_isolated_test_exception_admits_without_restic(scratch: Scratch, monkeypatch):
    monkeypatch.setenv("CONVMEM_SKIP_RESTIC_GATE", "1")
    monkeypatch.setenv("CONVMEM_RESTIC_GATE_EXCEPTION", "isolated-test")
    assert not scratch.env_file.exists()
    with mock.patch.object(restic_gate, "ensure_current_snapshot") as ensure:
        bound = preflight_operation(scratch.target())
    assert bound.status == "isolated-exception"
    ensure.assert_not_called()


# ---------------------------------------------------------------------------
# CLI callers in fresh subprocesses (real admission, real Chroma, scratch Restic)
# ---------------------------------------------------------------------------
class Cli:
    def __init__(self, scratch: Scratch):
        self.s = scratch
        self.config = Path(os.environ["CONVMEM_CONFIG"])
        self.export = scratch.data / "knowledge_units.jsonl"
        self.write_config(self.config, scratch.chroma)
        self.view_a = self.write_config(scratch.root / "view-a.toml", scratch.chroma)

    def write_config(self, path: Path, chroma: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "[index]\n"
            f'chroma_dir = "{chroma}"\n'
            f'units_export = "{chroma.parent / "knowledge_units.jsonl"}"\n'
            "[models]\n"
            'embed_model = "nomic-embed-text"\n'
            'ollama_host = "http://127.0.0.1:9"\n',
            encoding="utf-8",
        )
        return path

    def governed_files(self) -> list[str]:
        d = self.s.data
        return [str(d / n) for n in (
            "knowledge_units.jsonl", "pending_decisions.jsonl", "decisions-approved.jsonl",
            "pending_decision_events.jsonl",
        )]

    def run(self, mode: str, *args: str, env: dict | None = None, stdin: str | None = None):
        _require_isolated_process()
        full = {**os.environ, **(env or {})}
        return subprocess.run(
            [sys.executable, str(RUNNER), mode, *args], cwd=ROOT, env=full,
            input=stdin, capture_output=True, text=True, timeout=300, check=False,
        )

    def convmem(self, *args: str, env: dict | None = None, stdin: str | None = None):
        return self.run("cli", *args, env=env, stdin=stdin)

    def dump(self, view: Path | None = None) -> dict:
        proc = self.run("dump", *self.governed_files(),
                        env={"CONVMEM_CONFIG": str(view or self.view_a)})
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def seed(self, view: Path | None = None) -> None:
        proc = self.run("seed", env={"CONVMEM_CONFIG": str(view or self.view_a)})
        assert proc.returncode == 0, proc.stderr

    def obs_file(self) -> str:
        path = self.s.root / "obs.jsonl"
        path.write_text(json.dumps({
            "id": "obs_t2_probe", "summary": "Safe Harbor T2 probe", "author_model": "cursor",
            "type": "observation", "domain": "coding.tooling",
        }) + "\n", encoding="utf-8")
        return str(path)

    def propose(self) -> None:
        proc = self.convmem(
            "record", "--relates-to", "dec_prop_t2_parent", "--summary", "T2 approval probe",
            "--rationale", "exercise the bound gate", "--author", "cursor",
            "--constraint", "none-identified",
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def pending_id(self) -> str:
        rows = [json.loads(line) for line in
                (self.s.data / "pending_decisions.jsonl").read_text().splitlines() if line.strip()]
        return rows[-1]["id"]

    @property
    def census_dir(self) -> Path:
        return _refuse_production(Path.home() / ".local/share/convmem/writer-census")

    def arm_census(self) -> dict:
        """Arm the real writer census bound to this home's writer gate."""
        proc = self.convmem("writer-census-start", "--chroma-root", str(self.s.chroma))
        assert proc.returncode == 0, proc.stdout + proc.stderr
        armed = json.loads(proc.stdout.strip().splitlines()[-1])
        assert armed["verdict"] == "ARMED"
        assert self.census_events() == []
        return armed

    def census_events(self) -> list[dict]:
        path = self.census_dir / "session-events.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


NOW_ENV_KEY = "SAFE_HARBOR_T2_NOW"


@pytest.fixture
def cli(scratch: Scratch) -> Cli:
    if not _restic_ok():
        pytest.skip("restic >= 0.19.0 unavailable")
    scratch.write_env(external=False)
    scratch.init(external=False)
    c = Cli(scratch)
    c.seed()
    return c


def _future(cli: Cli) -> dict:
    noon = local_noon()
    cli.s.snapshot(noon + timedelta(hours=1))
    return {NOW_ENV_KEY: noon.isoformat()}


def _current(cli: Cli) -> dict:
    noon = local_noon()
    cli.s.snapshot(noon - timedelta(hours=1))
    return {NOW_ENV_KEY: noon.isoformat()}


def _assert_refused(proc, code: int, reason: str) -> None:
    assert proc.returncode == code, proc.stdout + proc.stderr
    assert "Live write BLOCKED" in proc.stderr
    assert f"reason={reason}" in proc.stderr


def test_cli_add_upsert_refused_on_future_snapshot(cli: Cli):
    env = _future(cli)
    before, ids_before = cli.dump(), cli.s.ids()
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert", env=env)
    _assert_refused(proc, EXIT_STALE, REASON_FUTURE_SNAPSHOT_TIME)
    assert cli.dump() == before
    assert cli.s.ids() == ids_before


def test_cli_add_upsert_succeeds_on_current_snapshot(cli: Cli):
    env = _current(cli)
    before = cli.dump()
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert", env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    after = cli.dump()
    assert after != before
    assert any(u["metadata"].get("ledger_id") == "obs_t2_probe" for u in after["chroma"]["units"])


def test_control_noop_preflight_lets_mutation_through(cli: Cli):
    """Negative control: the unchanged-state assertion detects a forbidden write."""
    env = {**_future(cli), "SAFE_HARBOR_T2_HOOK": "noop_preflight"}
    before = cli.dump()
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert", env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert cli.dump() != before


def test_cli_plain_add_stays_ungated(cli: Cli):
    env = _future(cli)
    before = cli.dump()
    proc = cli.convmem("add", "--file", cli.obs_file(), env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "BLOCKED" not in proc.stderr
    assert cli.dump() != before


def test_cli_approve_refused_before_any_approval_state(cli: Cli):
    cli.propose()
    env = _future(cli)
    before = cli.dump()
    proc = cli.convmem("record", "--approve-last", env=env, stdin="y\n")
    _assert_refused(proc, EXIT_STALE, REASON_FUTURE_SNAPSHOT_TIME)
    assert cli.dump() == before


def test_cli_approve_succeeds_on_current_snapshot(cli: Cli):
    cli.propose()
    env = _current(cli)
    before = cli.dump()
    proc = cli.convmem("record", "--approve-last", env=env, stdin="y\n")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    after = cli.dump()
    assert len(after["chroma"]["units"]) == len(before["chroma"]["units"]) + 1
    events = (cli.s.data / "pending_decision_events.jsonl").read_text()
    assert '"APPROVED"' in events


def test_cli_no_index_approve_stays_ungated(cli: Cli):
    cli.propose()
    env = _future(cli)
    before = cli.dump()
    proc = cli.convmem("record", "--approve-last", "--no-index", env=env, stdin="y\n")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    after = cli.dump()
    assert after["chroma"] == before["chroma"]
    assert after["files"] != before["files"]


def _approval_started(cli: Cli) -> str:
    cli.propose()
    pid = cli.pending_id()
    proc = cli.convmem("record", "--approve", pid, "--no-index", stdin="y\n")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return pid


def test_cli_recover_refused_on_future_snapshot(cli: Cli):
    pid = _approval_started(cli)
    env = _future(cli)
    before = cli.dump()
    proc = cli.convmem("propose_decision", "--recover", pid, env=env)
    _assert_refused(proc, EXIT_STALE, REASON_FUTURE_SNAPSHOT_TIME)
    assert cli.dump() == before


def test_cli_recover_succeeds_on_current_snapshot(cli: Cli):
    pid = _approval_started(cli)
    env = _current(cli)
    before = cli.dump()
    proc = cli.convmem("propose_decision", "--recover", pid, env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    after = cli.dump()
    assert len(after["chroma"]["units"]) == len(before["chroma"]["units"]) + 1
    assert after["files"] != before["files"]


def _pid_events(cli: Cli, pid: str) -> list[dict]:
    path = cli.s.data / "pending_decision_events.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [row for row in rows if row.get("proposal_id") == pid]


def _event_only_state(cli: Cli) -> str:
    """Interrupt a real indexed approval after its Chroma write, before APPROVED."""
    cli.propose()
    pid = cli.pending_id()
    env = {**_current(cli), "SAFE_HARBOR_T2_HOOK": "fail_after_chroma_ingest"}
    proc = cli.convmem("record", "--approve", pid, env=env, stdin="y\n")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "BLOCKED" not in proc.stderr
    assert "Approval apply deferred for recovery" in proc.stdout
    return pid


def _assert_census_admitted(events: list[dict], armed: dict) -> None:
    """Telemetry: the outer admission opened and closed in the armed census."""
    opens = [e for e in events if e["event"] == "open"]
    closes = [e for e in events if e["event"] == "close"]
    assert opens, events
    assert {e["entrypoint"] for e in opens} == {"propose_decision.write"}
    assert {e["census_id"] for e in events} == {armed["census_id"]}
    assert sorted(e["nonce"] for e in closes) == sorted(e["nonce"] for e in opens)


def _assert_recovered(proc, cli: Cli, pid: str, before: dict) -> None:
    """Logical effect: one new marked unit and exactly one APPROVED event."""
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"Recovered {pid}: retry_chroma" in proc.stdout
    after = cli.dump()
    assert len(after["chroma"]["units"]) == len(before["chroma"]["units"]) + 1
    assert [u for u in after["chroma"]["units"] if u["metadata"].get("proposal_id") == pid]
    assert [e["event_type"] for e in _pid_events(cli, pid)].count("APPROVED") == 1


def test_cli_recover_with_armed_census_succeeds_on_current_snapshot(cli: Cli):
    pid = _approval_started(cli)
    env = _current(cli)
    armed = cli.arm_census()
    before = cli.dump()
    proc = cli.convmem("propose_decision", "--recover", pid, env=env)
    _assert_recovered(proc, cli, pid, before)
    _assert_census_admitted(cli.census_events(), armed)


def test_cli_recover_with_armed_census_refused_on_future_snapshot(cli: Cli):
    pid = _approval_started(cli)
    env = _future(cli)
    armed = cli.arm_census()
    before = cli.dump()
    proc = cli.convmem("propose_decision", "--recover", pid, env=env)
    _assert_refused(proc, EXIT_STALE, REASON_FUTURE_SNAPSHOT_TIME)
    # Census telemetry records the admitted session; logical state is unchanged.
    _assert_census_admitted(cli.census_events(), armed)
    assert cli.dump() == before
    assert "APPROVED" not in [e["event_type"] for e in _pid_events(cli, pid)]


def test_control_old_recover_label_refused_by_armed_census(cli: Cli):
    """Negative control: the pre-correction label fails the same workflow."""
    pid = _approval_started(cli)
    env = _current(cli)
    armed = cli.arm_census()
    before = cli.dump()
    old = cli.convmem("propose_decision", "--recover", pid,
                      env={**env, "SAFE_HARBOR_T2_HOOK": "recover_old_label"})
    assert old.returncode == 1, old.stdout + old.stderr
    assert "writer entrypoint is not allowlisted" in old.stdout + old.stderr
    assert cli.census_events() == []
    assert cli.dump() == before
    with pytest.raises(AssertionError):
        _assert_recovered(old, cli, pid, before)
    with pytest.raises(AssertionError):
        _assert_census_admitted(cli.census_events(), armed)

    fixed = cli.convmem("propose_decision", "--recover", pid, env=env)
    _assert_recovered(fixed, cli, pid, before)
    _assert_census_admitted(cli.census_events(), armed)


def test_cli_event_only_recovery_completes_approved_event(cli: Cli):
    pid = _event_only_state(cli)
    types = [e["event_type"] for e in _pid_events(cli, pid)]
    assert "APPROVAL_STARTED" in types and "APPROVED" not in types
    approved = (cli.s.data / "decisions-approved.jsonl").read_text().splitlines()
    assert any(json.loads(line).get("proposal_id") == pid for line in approved if line.strip())
    live = [u["metadata"] for u in cli.dump()["chroma"]["units"]
            if u["metadata"].get("proposal_id") == pid]
    assert len(live) == 1
    env = _future(cli)
    before = cli.dump()
    proc = cli.convmem("propose_decision", "--recover", pid, env=env)
    _assert_refused(proc, EXIT_STALE, REASON_FUTURE_SNAPSHOT_TIME)
    assert cli.dump() == before

    later = {NOW_ENV_KEY: (local_noon() + timedelta(hours=2)).isoformat()}
    proc = cli.convmem("propose_decision", "--recover", pid, env=later)
    assert "BLOCKED" not in proc.stderr
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"Recovered {pid}: approve" in proc.stdout
    after = cli.dump()
    assert [e["event_type"] for e in _pid_events(cli, pid)].count("APPROVED") == 1
    assert len(after["chroma"]["units"]) == len(before["chroma"]["units"])
    assert [u for u in after["chroma"]["units"] if u["metadata"].get("proposal_id") == pid]


def test_cli_event_only_recovery_refused_before_approved_event(cli: Cli):
    """T4 completes event-only recovery on current snapshot (no longer refused)."""
    pid = _event_only_state(cli)
    env = _current(cli)
    before = cli.dump()
    proc = cli.convmem("propose_decision", "--recover", pid, env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"Recovered {pid}: approve" in proc.stdout
    after = cli.dump()
    assert len(after["chroma"]["units"]) == len(before["chroma"]["units"])
    assert [e["event_type"] for e in _pid_events(cli, pid)].count("APPROVED") == 1


def test_cli_config_swap_after_preflight_refused_on_both_targets(cli: Cli):
    chroma_b = cli.s.data / "chroma-b"
    chroma_b.mkdir()
    view_b = cli.write_config(cli.s.root / "view-b.toml", chroma_b)
    cli.seed(view_b)
    env = {**_current(cli), "SAFE_HARBOR_T2_HOOK": "swap_config_after_preflight",
           "SAFE_HARBOR_T2_ALT_CHROMA": str(chroma_b)}
    before_a, before_b = cli.dump(), cli.dump(view_b)
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert", env=env)
    _assert_refused(proc, EXIT_WRONG_PATH, "operation_config_changed")
    assert cli.dump() == before_a
    assert cli.dump(view_b) == before_b


def test_cli_profile_edit_after_preflight_refused(cli: Cli):
    env = {**_current(cli), "SAFE_HARBOR_T2_HOOK": "touch_env_after_preflight"}
    before = cli.dump()
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert", env=env)
    _assert_refused(proc, EXIT_INVALID_CONFIG, REASON_PROFILE_INPUTS_CHANGED)
    assert cli.dump() == before


def test_cli_profile_target_mismatch_refused(cli: Cli):
    other = cli.s.data / "chroma-other"
    other.mkdir()
    cli.s.write_env(chroma=other, external=False)
    env = _current(cli)
    before = cli.dump()
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert", env=env)
    _assert_refused(proc, EXIT_WRONG_PATH, REASON_CHROMA_TARGET_MISMATCH)
    assert cli.dump() == before


def test_cli_skip_spoof_refused_and_isolated_exception_allowed(cli: Cli):
    env = {**_future(cli), "CONVMEM_SKIP_RESTIC_GATE": "1", "CONVMEM_CONFIRM_PROD": "1",
           "CONVMEM_CONFIRM_LAB": "1"}
    before = cli.dump()
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert", env=env)
    _assert_refused(proc, EXIT_INVALID_CONFIG, REASON_SKIP_REFUSED)
    assert cli.dump() == before
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert",
                       env={**env, "CONVMEM_RESTIC_GATE_EXCEPTION": "isolated-test"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert cli.dump() != before


def test_cli_missing_restic_is_21(cli: Cli):
    cli.s.write_env(restic_bin=str(cli.s.root / "no-such-restic"), external=False)
    before = cli.dump()
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert")
    assert proc.returncode == EXIT_RESTIC_UNAVAILABLE, proc.stdout + proc.stderr
    assert cli.dump() == before


def _cross_parent_governed_paths(alias: Path, store_chroma: Path) -> tuple[dict[str, Path], dict[str, Path]]:
    """Governed paths under the alias parent vs the faulty canonical parent."""
    from conflict_events import event_path, lock_path
    from hash_schema_gate import deploy_path, migration_report_path
    from propose_decision import approved_path, queue_path

    alias_cfg = {"index": {"chroma_dir": str(alias)}}
    canonical_cfg = {"index": {"chroma_dir": str(store_chroma)}}
    intended = {
        "queue": queue_path(alias_cfg),
        "approved": approved_path(alias_cfg),
        "events": event_path(alias_cfg),
        "lock": lock_path(alias_cfg),
        "deploy": deploy_path(alias_cfg),
        "migration": migration_report_path(alias_cfg),
    }
    alternate = {
        "queue": queue_path(canonical_cfg),
        "approved": approved_path(canonical_cfg),
        "events": event_path(canonical_cfg),
        "lock": lock_path(canonical_cfg),
        "deploy": deploy_path(canonical_cfg),
        "migration": migration_report_path(canonical_cfg),
    }
    for name, path in intended.items():
        assert path.is_relative_to(alias.parent), path
        assert alternate[name].is_relative_to(store_chroma.parent), alternate[name]
        assert path != alternate[name]
    return intended, alternate


def _cross_parent_chroma_alias_setup(cli: Cli) -> tuple[Path, Path]:
    """Stable alias under data root; canonical Chroma lives in a child directory."""
    store_chroma = cli.s.data / "store" / "chroma"
    store_chroma.mkdir(parents=True)
    alias = cli.s.data / "chroma-link"
    if alias.exists() or alias.is_symlink():
        alias.unlink()
    alias.symlink_to(store_chroma, target_is_directory=True)
    cli.s.write_env(chroma=alias, data_root=cli.s.data, external=False)
    cli.write_config(cli.config, alias)
    cli.view_a = cli.write_config(cli.s.root / "view-a.toml", alias)
    cli.seed()
    assert alias.resolve() == store_chroma.resolve()
    assert store_chroma.parent != cli.s.data
    return alias, store_chroma


def _chroma_snapshot(cli: Cli, chroma_path: Path) -> dict:
    view = cli.write_config(cli.s.root / f"chroma-probe-{chroma_path.name}.toml", chroma_path)
    proc = cli.run("dump", env={"CONVMEM_CONFIG": str(view)})
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    return payload["chroma"]


def _file_hashes(cli: Cli, paths: dict[str, Path]) -> dict[str, str | None]:
    proc = cli.run("dump", *[str(p) for p in paths.values()])
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    return {name: payload["files"].get(str(path)) for name, path in paths.items()}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _queue_row(intended: dict[str, Path], pid: str) -> dict:
    rows = _read_jsonl(intended["queue"])
    return next(row for row in rows if row.get("id") == pid)


def _approved_rows(intended: dict[str, Path], pid: str) -> list[dict]:
    return [row for row in _read_jsonl(intended["approved"]) if row.get("proposal_id") == pid]


def _canonical_client_paths(cli: Cli) -> list[str]:
    return json.loads((cli.s.root / "chroma-client-path.txt").read_text(encoding="utf-8"))


def _assert_canonical_client_paths(cli: Cli, expected_path: str) -> None:
    paths = _canonical_client_paths(cli)
    assert paths, "expected at least one PersistentClient construction"
    for logged in paths:
        assert logged == expected_path


def _assert_intended_proposal_ledger(
    cli: Cli,
    pid: str,
    intended: dict[str, Path],
    store_chroma: Path,
    *,
    require_chroma_unit: bool,
) -> None:
    row = _queue_row(intended, pid)
    assert row["id"] == pid
    assert row.get("status") == "APPROVED"
    approved = _approved_rows(intended, pid)
    assert approved, pid
    events = [
        row
        for row in _read_jsonl(intended["events"])
        if row.get("proposal_id") == pid
    ]
    assert events, pid
    assert [event["event_type"] for event in events].count("APPROVED") == 1
    if require_chroma_unit:
        chroma = _chroma_snapshot(cli, store_chroma)
        matched = [unit for unit in chroma["units"] if unit["metadata"].get("proposal_id") == pid]
        assert matched, pid


def _preflight_env(cli: Cli, base: dict) -> dict:
    return {
        **base,
        "SAFE_HARBOR_T2_HOOK": "record_cross_parent_admission",
        "SAFE_HARBOR_T2_PREFLIGHT_LOG": str(cli.s.root / "preflight-target.json"),
        "SAFE_HARBOR_T2_CHROMA_CLIENT_LOG": str(cli.s.root / "chroma-client-path.txt"),
    }


def _read_preflight(cli: Cli) -> dict:
    return json.loads((cli.s.root / "preflight-target.json").read_text(encoding="utf-8"))


def _assert_preflight_covers_governed(
    cli: Cli, intended: dict[str, Path], store_chroma: Path
) -> None:
    recorded = _read_preflight(cli)
    admitted = {Path(p).resolve() for p in recorded["affected_paths"]}
    for _name, path in intended.items():
        assert path.resolve() in admitted, (path, admitted)
    assert recorded["chroma_dir"] == str(store_chroma)


def _assert_alternate_governed_unchanged(
    before: dict[str, str | None], after: dict[str, str | None]
) -> None:
    for name, digest in before.items():
        assert after[name] == digest, name


def _assert_cross_parent_indexed_approval_effects(
    cli: Cli,
    *,
    pid: str,
    store_chroma: Path,
    intended: dict[str, Path],
    alternate: dict[str, Path],
    before_chroma: dict,
    before_files: dict[str, str | None],
    before_alt: dict[str, str | None],
) -> None:
    after_files = _file_hashes(cli, intended)
    after_alt = _file_hashes(cli, alternate)
    assert after_files["events"] != before_files["events"]
    assert after_files["approved"] != before_files["approved"]
    _assert_intended_proposal_ledger(
        cli, pid, intended, store_chroma, require_chroma_unit=True
    )
    after_chroma = _chroma_snapshot(cli, store_chroma)
    assert after_chroma["exists"]
    assert len(after_chroma["units"]) == len(before_chroma["units"]) + 1
    _assert_alternate_governed_unchanged(before_alt, after_alt)
    _assert_canonical_client_paths(cli, str(store_chroma))
    _assert_preflight_covers_governed(cli, intended, store_chroma)


def _assert_cross_parent_recovery_effects(
    cli: Cli,
    *,
    pid: str,
    store_chroma: Path,
    intended: dict[str, Path],
    alternate: dict[str, Path],
    before_chroma: dict,
    before_files: dict[str, str | None],
    before_alt: dict[str, str | None],
) -> None:
    after_files = _file_hashes(cli, intended)
    after_alt = _file_hashes(cli, alternate)
    assert after_files["events"] != before_files["events"]
    assert after_files["approved"] == before_files["approved"]
    _assert_intended_proposal_ledger(
        cli, pid, intended, store_chroma, require_chroma_unit=True
    )
    after_chroma = _chroma_snapshot(cli, store_chroma)
    assert len(after_chroma["units"]) == len(before_chroma["units"]) + 1
    _assert_alternate_governed_unchanged(before_alt, after_alt)
    _assert_canonical_client_paths(cli, str(store_chroma))
    _assert_preflight_covers_governed(cli, intended, store_chroma)


def _assert_proposal_not_found(proc) -> None:
    text = (proc.stdout + proc.stderr).lower()
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert "not found" in text or "proposal" in text and "absent" in text


def _chroma_alias_setup(cli: Cli) -> tuple[Path, Path, Path]:
    """Config names a symlink; target A is backed up, target B is the redirect."""
    chroma_b = cli.s.data / "chroma-b"
    chroma_b.mkdir()
    view_b = cli.write_config(cli.s.root / "view-b.toml", chroma_b)
    cli.seed(view_b)
    alias = cli.s.data / "chroma-link"
    if alias.exists() or alias.is_symlink():
        alias.unlink()
    alias.symlink_to(cli.s.chroma, target_is_directory=True)
    cli.s.write_env(chroma=alias, external=False)
    cli.write_config(cli.config, alias)
    cli.seed()
    return alias, cli.s.chroma, chroma_b


def test_cross_parent_chroma_alias_indexed_approval_succeeds(cli: Cli):
    alias, store_chroma = _cross_parent_chroma_alias_setup(cli)
    intended, alternate = _cross_parent_governed_paths(alias, store_chroma)
    cli.propose()
    pid = cli.pending_id()
    before_chroma = _chroma_snapshot(cli, store_chroma)
    before_files = _file_hashes(cli, intended)
    before_alt = _file_hashes(cli, alternate)
    proc = cli.convmem(
        "record",
        "--approve-last",
        env=_preflight_env(cli, _current(cli)),
        stdin="y\n",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    _assert_cross_parent_indexed_approval_effects(
        cli,
        pid=pid,
        store_chroma=store_chroma,
        intended=intended,
        alternate=alternate,
        before_chroma=before_chroma,
        before_files=before_files,
        before_alt=before_alt,
    )


def test_cross_parent_chroma_alias_retry_chroma_recovery_succeeds(cli: Cli):
    alias, store_chroma = _cross_parent_chroma_alias_setup(cli)
    intended, alternate = _cross_parent_governed_paths(alias, store_chroma)
    pid = _approval_started(cli)
    armed = cli.arm_census()
    before_chroma = _chroma_snapshot(cli, store_chroma)
    before_files = _file_hashes(cli, intended)
    before_alt = _file_hashes(cli, alternate)
    proc = cli.convmem(
        "propose_decision",
        "--recover",
        pid,
        env=_preflight_env(cli, _current(cli)),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"Recovered {pid}: retry_chroma" in proc.stdout
    _assert_cross_parent_recovery_effects(
        cli,
        pid=pid,
        store_chroma=store_chroma,
        intended=intended,
        alternate=alternate,
        before_chroma=before_chroma,
        before_files=before_files,
        before_alt=before_alt,
    )
    _assert_census_admitted(cli.census_events(), armed)


@pytest.mark.parametrize("workflow", ["approve_last", "recover"])
def test_cross_parent_chroma_alias_canonical_substitution_negative_control(cli: Cli, workflow: str):
    alias, store_chroma = _cross_parent_chroma_alias_setup(cli)
    intended, alternate = _cross_parent_governed_paths(alias, store_chroma)
    cli.propose()
    pid = cli.pending_id()
    if workflow == "recover":
        started = cli.convmem("record", "--approve", pid, "--no-index", stdin="y\n")
        assert started.returncode == 0, started.stdout + started.stderr
    before_chroma = _chroma_snapshot(cli, store_chroma)
    before_files = _file_hashes(cli, intended)
    before_alt = _file_hashes(cli, alternate)
    hook_env = {
        **_current(cli),
        "SAFE_HARBOR_T2_HOOK": "canonical_chroma_config_substitution",
    }
    if workflow == "approve_last":
        proc = cli.convmem("record", "--approve-last", env=hook_env, stdin="y\n")
    else:
        proc = cli.convmem("propose_decision", "--recover", pid, env=hook_env)
    if workflow == "recover":
        assert proc.returncode == EXIT_WRONG_PATH, proc.stdout + proc.stderr
        assert "operation_config_changed" in (proc.stdout + proc.stderr)
        assert "APPROVED" not in [e["event_type"] for e in _pid_events(cli, pid)]
    else:
        _assert_proposal_not_found(proc)
    with pytest.raises(AssertionError):
        if workflow == "approve_last":
            _assert_cross_parent_indexed_approval_effects(
                cli,
                pid=pid,
                store_chroma=store_chroma,
                intended=intended,
                alternate=alternate,
                before_chroma=before_chroma,
                before_files=before_files,
                before_alt=before_alt,
            )
        else:
            _assert_cross_parent_recovery_effects(
                cli,
                pid=pid,
                store_chroma=store_chroma,
                intended=intended,
                alternate=alternate,
                before_chroma=before_chroma,
                before_files=before_files,
                before_alt=before_alt,
            )
    after_chroma = _chroma_snapshot(cli, store_chroma)
    assert after_chroma == before_chroma
    after_files = _file_hashes(cli, intended)
    after_alt = _file_hashes(cli, alternate)
    assert after_files == before_files
    if workflow == "recover":
        # T4 refuses the injected wrong config before opening any alternate lock.
        # The independent successful-completion checker above must still fail.
        assert after_alt == before_alt
    else:
        assert alternate["lock"].exists() or after_alt["lock"] != before_alt["lock"]


def test_cli_add_succeeds_with_unchanged_chroma_alias(cli: Cli):
    alias, _real_a, chroma_b = _chroma_alias_setup(cli)
    assert alias.resolve() == cli.s.chroma.resolve()
    env = _current(cli)
    before_a, before_b = cli.dump(), cli.dump(cli.write_config(cli.s.root / "view-b.toml", chroma_b))
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert", env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert cli.dump() != before_a
    after_b = cli.dump(cli.write_config(cli.s.root / "view-b.toml", chroma_b))
    assert after_b["chroma"] == before_b["chroma"]


def test_cli_chroma_alias_retarget_refused_after_preflight(cli: Cli):
    alias, _real_a, chroma_b = _chroma_alias_setup(cli)
    view_b = cli.write_config(cli.s.root / "view-b.toml", chroma_b)
    env = {
        **_current(cli),
        "SAFE_HARBOR_T2_HOOK": "retarget_chroma_alias_after_preflight",
        "SAFE_HARBOR_T2_CHROMA_ALIAS": str(alias),
        "SAFE_HARBOR_T2_ALT_CHROMA": str(chroma_b),
    }
    before_a, before_b = cli.dump(), cli.dump(view_b)
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert", env=env)
    _assert_refused(proc, EXIT_WRONG_PATH, REASON_OPERATION_CONFIG_CHANGED)
    assert cli.dump() == before_a
    assert cli.dump(view_b) == before_b


def test_control_unbound_target_lets_alias_retarget_mutate(cli: Cli):
    """Negative control: unbound binding lets retarget write corpus B while A stays put."""
    alias, _real_a, chroma_b = _chroma_alias_setup(cli)
    view_b = cli.write_config(cli.s.root / "view-b.toml", chroma_b)
    env = {
        **_current(cli),
        "SAFE_HARBOR_T2_HOOK": "unbound_retarget_chroma_alias",
        "SAFE_HARBOR_T2_CHROMA_ALIAS": str(alias),
        "SAFE_HARBOR_T2_ALT_CHROMA": str(chroma_b),
    }
    before_a, before_b = cli.dump(), cli.dump(view_b)
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert", env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    after_a = cli.dump()
    after_b = cli.dump(view_b)
    assert after_a["chroma"] == before_a["chroma"]
    assert after_b["chroma"] != before_b["chroma"]


def _client_open_spy() -> tuple[dict[str, bool], mock.MagicMock]:
    state = {"opened": False}
    real_client = chromadb.PersistentClient

    def _spy_client(*args, **kwargs):
        state["opened"] = True
        return real_client(*args, **kwargs)

    return state, mock.patch.object(chromadb, "PersistentClient", _spy_client)


def _competing_alias_guard_setup(scratch: Scratch) -> tuple[Path, Path, bytes]:
    alias = scratch.data / "chroma-link"
    if alias.exists() or alias.is_symlink():
        alias.unlink()
    alias.symlink_to(scratch.chroma, target_is_directory=True)
    lexical_guard = scratch.data / "chroma-link.write-guard"
    lexical_guard.mkdir()
    marker = b'{"reason":"old","segment":"seg"}\n'
    (lexical_guard / "QUARANTINE.json").write_bytes(marker)
    canonical_guard = scratch.chroma.parent / f"{scratch.chroma.name}.write-guard"
    return alias, canonical_guard, marker


@needs_restic
def test_cli_add_refuses_competing_alias_guard_location(cli: Cli):
    alias, canonical_guard, marker = _competing_alias_guard_setup(cli.s)
    lexical_guard = cli.s.data / "chroma-link.write-guard"
    cli.s.write_env(chroma=alias, external=False)
    cli.write_config(cli.config, alias)
    cli.seed()
    before = cli.dump()
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert")
    assert proc.returncode != 0
    assert "competing guard locations" in (proc.stderr + proc.stdout).lower()
    assert cli.dump() == before
    assert not canonical_guard.exists()
    assert (lexical_guard / "QUARANTINE.json").read_bytes() == marker


@needs_restic
def test_open_production_write_store_refuses_competing_alias_guard(scratch: Scratch):
    from chroma_write_store import (
        admitted_write_operation,
        open_production_write_store,
    )
    from chroma_write_guard import ChromaWriteGuardError

    scratch.write_env(external=False)
    scratch.init(external=False)
    noon = local_noon()
    scratch.snapshot(noon - timedelta(hours=1))
    alias, canonical_guard, marker = _competing_alias_guard_setup(scratch)
    lexical_guard = scratch.data / "chroma-link.write-guard"
    cfg_path = Path(os.environ["CONVMEM_CONFIG"])
    cfg_path.write_text(
        "[index]\n"
        f'chroma_dir = "{alias}"\n'
        f'units_export = "{scratch.data / "knowledge_units.jsonl"}"\n'
        "[models]\n"
        'embed_model = "nomic-embed-text"\n'
        'ollama_host = "http://127.0.0.1:9"\n',
        encoding="utf-8",
    )
    client_state, client_patch = _client_open_spy()
    with pinned_clock(noon), client_patch:
        with admitted_write_operation(entrypoint="test.factory", config_path=cfg_path):
            with pytest.raises(ChromaWriteGuardError, match="competing guard locations"):
                open_production_write_store(config_path=cfg_path, entrypoint="test.factory")
    assert client_state["opened"] is False
    assert not canonical_guard.exists()
    assert (lexical_guard / "QUARANTINE.json").read_bytes() == marker


@needs_restic
def test_production_chroma_write_session_refuses_competing_alias_guard(scratch: Scratch):
    from chroma_write_store import (
        admitted_write_operation,
        production_chroma_write_session,
    )
    from chroma_write_guard import ChromaWriteGuardError

    scratch.write_env(external=False)
    scratch.init(external=False)
    noon = local_noon()
    scratch.snapshot(noon - timedelta(hours=1))
    alias, canonical_guard, marker = _competing_alias_guard_setup(scratch)
    lexical_guard = scratch.data / "chroma-link.write-guard"
    cfg_path = Path(os.environ["CONVMEM_CONFIG"])
    cfg_path.write_text(
        "[index]\n"
        f'chroma_dir = "{alias}"\n'
        f'units_export = "{scratch.data / "knowledge_units.jsonl"}"\n'
        "[models]\n"
        'embed_model = "nomic-embed-text"\n'
        'ollama_host = "http://127.0.0.1:9"\n',
        encoding="utf-8",
    )
    client_state, client_patch = _client_open_spy()
    with pinned_clock(noon), client_patch:
        with admitted_write_operation(entrypoint="test.factory", config_path=cfg_path):
            with pytest.raises(ChromaWriteGuardError, match="competing guard locations"):
                with production_chroma_write_session(
                    config_path=cfg_path, entrypoint="test.factory"
                ):
                    pass
    assert client_state["opened"] is False
    assert not canonical_guard.exists()
    assert (lexical_guard / "QUARANTINE.json").read_bytes() == marker


def test_cli_export_alias_retarget_refused_after_preflight(cli: Cli):
    outside = cli.s.root / "outside.jsonl"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("", encoding="utf-8")
    export_link = cli.s.data / "export-link.jsonl"
    inside = cli.s.data / "knowledge_units.jsonl"
    if export_link.exists():
        export_link.unlink()
    export_link.symlink_to(inside)
    cli.config.write_text(
        "[index]\n"
        f'chroma_dir = "{cli.s.chroma}"\n'
        f'units_export = "{export_link}"\n'
        "[models]\n"
        'embed_model = "nomic-embed-text"\n'
        'ollama_host = "http://127.0.0.1:9"\n',
        encoding="utf-8",
    )
    cli.s.write_env(external=False)
    cli.seed()
    env = {
        **_current(cli),
        "SAFE_HARBOR_T2_HOOK": "retarget_export_alias_after_preflight",
        "SAFE_HARBOR_T2_EXPORT_ALIAS": str(export_link),
        "SAFE_HARBOR_T2_ALT_EXPORT": str(outside),
    }
    before = cli.dump()
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert", env=env)
    _assert_refused(proc, EXIT_WRONG_PATH, REASON_OPERATION_CONFIG_CHANGED)
    assert cli.dump() == before
    assert not outside.read_text().strip()


def test_cli_export_alias_retarget_refused_after_store_open(cli: Cli):
    outside = cli.s.root / "outside.jsonl"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("", encoding="utf-8")
    export_link = cli.s.data / "export-link.jsonl"
    inside = cli.s.data / "knowledge_units.jsonl"
    if export_link.exists():
        export_link.unlink()
    export_link.symlink_to(inside)
    cli.config.write_text(
        "[index]\n"
        f'chroma_dir = "{cli.s.chroma}"\n'
        f'units_export = "{export_link}"\n'
        "[models]\n"
        'embed_model = "nomic-embed-text"\n'
        'ollama_host = "http://127.0.0.1:9"\n',
        encoding="utf-8",
    )
    cli.s.write_env(external=False)
    cli.seed()
    env = {
        **_current(cli),
        "SAFE_HARBOR_T2_HOOK": "retarget_export_alias_after_store",
        "SAFE_HARBOR_T2_EXPORT_ALIAS": str(export_link),
        "SAFE_HARBOR_T2_ALT_EXPORT": str(outside),
    }
    before = cli.dump()
    proc = cli.convmem("add", "--file", cli.obs_file(), "--upsert", env=env)
    _assert_refused(proc, EXIT_WRONG_PATH, REASON_OPERATION_CONFIG_CHANGED)
    assert cli.dump() == before
    assert not outside.read_text().strip()


@needs_restic
def test_open_production_write_store_refuses_retargeted_alias(scratch: Scratch):
    """Alternate production-store factory uses the same bound target check."""
    from chroma_write_store import (
        admitted_write_operation,
        open_production_write_store,
    )

    scratch.write_env(external=False)
    scratch.init(external=False)
    noon = local_noon()
    scratch.snapshot(noon - timedelta(hours=1))
    alias = scratch.data / "chroma-link"
    other = scratch.data / "chroma-other"
    other.mkdir()
    alias.symlink_to(scratch.chroma, target_is_directory=True)
    cfg_path = Path(os.environ["CONVMEM_CONFIG"])
    cfg_path.write_text(
        "[index]\n"
        f'chroma_dir = "{alias}"\n'
        f'units_export = "{scratch.data / "knowledge_units.jsonl"}"\n'
        "[models]\n"
        'embed_model = "nomic-embed-text"\n'
        'ollama_host = "http://127.0.0.1:9"\n',
        encoding="utf-8",
    )
    with pinned_clock(noon):
        with admitted_write_operation(entrypoint="test.factory", config_path=cfg_path):
            alias.unlink()
            alias.symlink_to(other, target_is_directory=True)
            with pytest.raises(OperationAdmissionRefused) as exc:
                open_production_write_store(config_path=cfg_path, entrypoint="test.factory")
    assert exc.value.exit_code == EXIT_WRONG_PATH
