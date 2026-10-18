"""Host isolation for Arc #286 tests — stdlib until env is installed."""

from __future__ import annotations

import json
import os
import secrets
import sys
import tempfile
from pathlib import Path

from tests.fixtures.issue_286_real_home_capture import REAL_HOME_ENV, capture_operator_home_now

INSTALLED_ENV = "CONVMEM_ISSUE_286_HOST_ISOLATION_INSTALLED"
HOST_ROOT_ENV = "CONVMEM_ISSUE_286_HOST_ROOT"
BWRAP_ACTIVE_ENV = "CONVMEM_ISSUE_286_BWRAP_ACTIVE"
FORCE_ENV = "CONVMEM_ISSUE_286_FORCE_HOST_ISOLATION"

ISOLATION_ROOT_ENV = "CONVMEM_INCREMENTAL_ROOT"
ISOLATION_TOKEN_ENV = "CONVMEM_INCREMENTAL_TOKEN"
ISOLATION_MODE_ENV = "CONVMEM_INCREMENTAL_MODE"
ISOLATION_FORBIDDEN_ENV = "CONVMEM_INCREMENTAL_FORBIDDEN"
ISOLATION_MODE_VALUE = "jsonl-production-integration-v1"
_SCRATCH_MARKER = ".convmem-jsonl-production-root"

_PATH_ENV_KEYS = (
    "HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_CACHE_HOME",
    "XDG_STATE_HOME",
    "XDG_RUNTIME_DIR",
    "TMPDIR",
    "TEMP",
    "TMP",
    ISOLATION_ROOT_ENV,
)

_OPTIONAL_PATH_ENV_KEYS = ("CONVMEM_CONFIG",)

_PASSTHROUGH_ENV_KEYS = _PATH_ENV_KEYS + _OPTIONAL_PATH_ENV_KEYS + (
    ISOLATION_TOKEN_ENV,
    ISOLATION_MODE_ENV,
    ISOLATION_FORBIDDEN_ENV,
    "CONVMEM_INCREMENTAL_SITE",
    REAL_HOME_ENV,
    HOST_ROOT_ENV,
    BWRAP_ACTIVE_ENV,
    INSTALLED_ENV,
)

_CONVMEM_PREIMPORT_BLOCKLIST = (
    "config",
    "incremental_jsonl",
    "incremental_jsonl_isolation",
    "watch",
    "convmem",
)


def _safe_scratch_parent() -> Path:
    parent = Path("/tmp")
    if not parent.is_dir():
        raise RuntimeError("issue_286_scratch_parent_missing: /tmp is not a directory")
    return parent.resolve()


def capture_real_home() -> Path:
    return capture_operator_home_now()


def _require_non_empty_real_home(raw: str | None) -> Path:
    if raw is None or str(raw).strip() == "":
        raise RuntimeError("issue_286_real_home_missing: CONVMEM_TEST_REAL_HOME not captured")
    return Path(raw).expanduser().resolve()


def production_path_prefixes(real_home: Path) -> tuple[Path, ...]:
    return (
        (real_home / ".config" / "convmem").resolve(),
        (real_home / ".local" / "share" / "convmem").resolve(),
        (real_home / ".codex" / "sessions").resolve(),
        (real_home / ".kiro" / "sessions").resolve(),
    )


def resolves_under_production_path(path: Path | str, *, real_home: Path) -> bool:
    resolved = Path(path).expanduser().resolve()
    for prefix in production_path_prefixes(real_home):
        try:
            resolved.relative_to(prefix)
            return True
        except ValueError:
            continue
    return False


def _require_absolute_path(raw: str, *, label: str) -> Path:
    if not raw or not str(raw).strip():
        raise RuntimeError(f"issue_286_env_missing: {label}")
    path = Path(raw)
    if not path.is_absolute():
        raise RuntimeError(f"issue_286_env_not_absolute: {label}={raw}")
    return path


def _forbidden_roots_json(real_home: Path) -> str:
    return json.dumps([str(p) for p in production_path_prefixes(real_home)])


def _validate_token_and_mode() -> None:
    token = os.environ.get(ISOLATION_TOKEN_ENV, "")
    mode = os.environ.get(ISOLATION_MODE_ENV, "")
    if not token or not str(token).strip():
        raise RuntimeError("issue_286_env_missing: CONVMEM_INCREMENTAL_TOKEN")
    if mode != ISOLATION_MODE_VALUE:
        raise RuntimeError("issue_286_isolation_mode_mismatch")


def approved_scratch_root() -> Path:
    host_raw = os.environ.get(HOST_ROOT_ENV)
    root_raw = os.environ.get(ISOLATION_ROOT_ENV)
    if not host_raw and not root_raw:
        raise RuntimeError("issue_286_scratch_root_missing: host root not installed")
    if host_raw and root_raw and Path(host_raw).resolve() != Path(root_raw).resolve():
        raise RuntimeError("issue_286_scratch_root_mismatch: HOST_ROOT vs INCREMENTAL_ROOT")
    raw = host_raw or root_raw
    assert raw is not None
    root_path = _require_absolute_path(raw, label=ISOLATION_ROOT_ENV)
    root = root_path.resolve()
    tmp_parent = _safe_scratch_parent()
    try:
        root.relative_to(tmp_parent)
    except ValueError as exc:
        raise RuntimeError(
            f"issue_286_scratch_not_under_tmp: {root} is outside {tmp_parent}"
        ) from exc
    real_home = _require_non_empty_real_home(os.environ.get(REAL_HOME_ENV))
    if resolves_under_production_path(root, real_home=real_home):
        raise RuntimeError("issue_286_scratch_under_production_prefix")
    marker = root / _SCRATCH_MARKER
    if not marker.is_file():
        raise RuntimeError("issue_286_scratch_root_unmarked: isolation freshness token missing")
    marker_token = marker.read_text(encoding="ascii").strip()
    env_token = os.environ.get(ISOLATION_TOKEN_ENV, "").strip()
    if not env_token or env_token != marker_token:
        raise RuntimeError("issue_286_scratch_token_mismatch: env token does not match marker")
    return root


def path_must_live_under_scratch(path: Path | str, scratch: Path, *, label: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    scratch_resolved = scratch.resolve()
    try:
        resolved.relative_to(scratch_resolved)
    except ValueError as exc:
        raise RuntimeError(
            f"issue_286_scratch_violation: {label} {resolved} is outside {scratch_resolved}"
        ) from exc
    return resolved


def _scratch_layout(root: Path) -> dict[str, Path]:
    home = root / "home"
    return {
        "home": home,
        "xdg_config": root / "xdg-config",
        "xdg_data": root / "xdg-data",
        "xdg_cache": root / "xdg-cache",
        "tmpdir": root / "tmp",
        "xdg_state": root / "xdg-state",
        "xdg_runtime": root / "xdg-run",
        "user_config": home / ".config" / "convmem" / "config.toml",
        "chroma": home / ".local/share/convmem/chroma",
        "processed": home / ".local/share/convmem/processed.json",
        "export": home / ".local/share/convmem/knowledge_units.jsonl",
        "state": home / ".local/share/convmem/incremental-jsonl",
        "locks": home / ".local/share/convmem/locks",
        "sources": root / "sources",
    }


def _write_stdlib_hermetic_config(layout: dict[str, Path]) -> Path:
    for key in (
        "home",
        "xdg_config",
        "xdg_data",
        "xdg_cache",
        "chroma",
        "state",
        "locks",
        "sources",
    ):
        layout[key].mkdir(parents=True, exist_ok=True)
        if key in {"locks", "state", "chroma"}:
            os.chmod(layout[key], 0o700)
    layout["processed"].parent.mkdir(parents=True, exist_ok=True)
    layout["export"].parent.mkdir(parents=True, exist_ok=True)
    layout["user_config"].parent.mkdir(parents=True, exist_ok=True)
    payload = (
        "[index]\n"
        f'chroma_dir = {json.dumps(str(layout["chroma"]))}\n'
        f'processed_log = {json.dumps(str(layout["processed"]))}\n'
        f'units_export = {json.dumps(str(layout["export"]))}\n'
        "chunk_size = 2\n"
        "chunk_overlap = 0\n"
        "\n"
        "[index.incremental_jsonl]\n"
        "enabled = false\n"
        f'state_dir = {json.dumps(str(layout["state"]))}\n'
        "allow_full_rebuild = false\n"
        "\n"
        "[models]\n"
        'embed_model = "deterministic-fake"\n'
        'summarize_model = "deterministic-fake"\n'
        'distill_model = "deterministic-fake"\n'
        'ollama_host = ""\n'
        "\n"
        "[distill]\n"
        "min_confidence = 0.6\n"
    )
    layout["user_config"].write_text(payload, encoding="utf-8")
    os.chmod(layout["user_config"], 0o600)
    return layout["user_config"]


def _ensure_layout_dirs(layout: dict[str, Path]) -> None:
    for key in (
        "home",
        "xdg_config",
        "xdg_data",
        "xdg_cache",
        "tmpdir",
        "xdg_state",
        "xdg_runtime",
    ):
        layout[key].mkdir(parents=True, exist_ok=True)
    layout["user_config"].parent.mkdir(parents=True, exist_ok=True)


def _reset_tempfile_cache() -> None:
    tempfile.tempdir = None


def _apply_layout_env(root: Path, layout: dict[str, Path], token: str) -> None:
    real_home = capture_real_home()
    os.environ["HOME"] = str(layout["home"])
    os.environ["XDG_CONFIG_HOME"] = str(layout["xdg_config"])
    os.environ["XDG_DATA_HOME"] = str(layout["xdg_data"])
    os.environ["XDG_CACHE_HOME"] = str(layout["xdg_cache"])
    os.environ["XDG_STATE_HOME"] = str(layout["xdg_state"])
    os.environ["XDG_RUNTIME_DIR"] = str(layout["xdg_runtime"])
    os.environ["TMPDIR"] = str(layout["tmpdir"])
    os.environ["TEMP"] = str(layout["tmpdir"])
    os.environ["TMP"] = str(layout["tmpdir"])
    os.environ.pop("CONVMEM_CONFIG", None)
    os.environ[ISOLATION_ROOT_ENV] = str(root)
    os.environ[ISOLATION_TOKEN_ENV] = token
    os.environ[ISOLATION_MODE_ENV] = ISOLATION_MODE_VALUE
    os.environ[ISOLATION_FORBIDDEN_ENV] = _forbidden_roots_json(real_home)
    os.environ[HOST_ROOT_ENV] = str(root)
    os.environ[INSTALLED_ENV] = "1"
    _reset_tempfile_cache()


def validate_derived_live_paths(*, scratch: Path, real_home: Path) -> None:
    import config

    cfg_path = config.CONFIG_PATH.expanduser().resolve()
    path_must_live_under_scratch(cfg_path, scratch, label="config.CONFIG_PATH")
    if resolves_under_production_path(cfg_path, real_home=real_home):
        raise RuntimeError("issue_286_production_path_leak: config.CONFIG_PATH")
    if not cfg_path.is_file():
        raise RuntimeError("issue_286_config_missing: isolated default config not present")
    cfg = config.load_config(cfg_path)
    index = cfg.get("index") or {}
    for key in ("chroma_dir", "processed_log", "units_export"):
        value = index.get(key)
        if not value:
            raise RuntimeError(f"issue_286_config_path_missing: index.{key}")
        path_must_live_under_scratch(value, scratch, label=f"index.{key}")
        if resolves_under_production_path(value, real_home=real_home):
            raise RuntimeError(f"issue_286_production_path_leak: index.{key}")
    inc = index.get("incremental_jsonl") or {}
    state_dir = inc.get("state_dir")
    if state_dir:
        path_must_live_under_scratch(state_dir, scratch, label="incremental_jsonl.state_dir")
        if resolves_under_production_path(state_dir, real_home=real_home):
            raise RuntimeError("issue_286_production_path_leak: incremental_jsonl.state_dir")
    home = Path(os.environ["HOME"]).resolve()
    codex_sessions = home / ".codex" / "sessions"
    path_must_live_under_scratch(codex_sessions, scratch, label="codex.sessions")
    synthesis = home / ".local" / "share" / "convmem" / "synthesis_failures.jsonl"
    path_must_live_under_scratch(synthesis.parent, scratch, label="synthesis_failures.parent")
    path_must_live_under_scratch(
        Path(config.DEFAULT_INCREMENTAL_JSONL_STATE_DIR).expanduser(),
        scratch,
        label="DEFAULT_INCREMENTAL_JSONL_STATE_DIR",
    )


def validate_isolated_env(*, strict: bool = True) -> None:
    real_home = _require_non_empty_real_home(os.environ.get(REAL_HOME_ENV))
    if strict and os.environ.get(INSTALLED_ENV) != "1":
        raise RuntimeError("issue_286_host_isolation_missing: isolation not installed")
    _validate_token_and_mode()
    scratch = approved_scratch_root()

    home_raw = os.environ.get("HOME")
    if not home_raw:
        raise RuntimeError("issue_286_env_missing: HOME")
    home = path_must_live_under_scratch(
        _require_absolute_path(home_raw, label="HOME"), scratch, label="HOME"
    )
    if home == real_home:
        raise RuntimeError("issue_286_production_path_leak: HOME equals operator real home")

    for key in _PATH_ENV_KEYS:
        path_must_live_under_scratch(
            _require_absolute_path(os.environ[key], label=key), scratch, label=key
        )

    optional = os.environ.get("CONVMEM_CONFIG")
    if optional:
        path_must_live_under_scratch(
            _require_absolute_path(optional, label="CONVMEM_CONFIG"), scratch, label="CONVMEM_CONFIG"
        )
        if resolves_under_production_path(optional, real_home=real_home):
            raise RuntimeError("issue_286_production_path_leak: CONVMEM_CONFIG")

    validate_derived_live_paths(scratch=scratch, real_home=real_home)


def _fail_if_convmem_imported_before_isolation() -> None:
    for name in _CONVMEM_PREIMPORT_BLOCKLIST:
        if name in sys.modules:
            raise RuntimeError(
                f"issue_286_late_bootstrap: module {name!r} imported before host isolation"
            )


def _create_fresh_scratch_root(parent: Path) -> tuple[Path, str]:
    token = secrets.token_hex(24)
    root = Path(tempfile.mkdtemp(prefix="convmem-jsonl-prod-", dir=str(parent)))
    (root / _SCRATCH_MARKER).write_text(token, encoding="ascii")
    return root.resolve(strict=True), token


def install_host_isolation_from_scratch() -> Path:
    capture_real_home()
    _fail_if_convmem_imported_before_isolation()
    parent = _safe_scratch_parent()
    root, token = _create_fresh_scratch_root(parent)
    layout = _scratch_layout(root)
    _ensure_layout_dirs(layout)
    _write_stdlib_hermetic_config(layout)
    _apply_layout_env(root, layout, token)
    return root


def align_bwrap_worker_isolation() -> None:
    capture_real_home()
    raw_root = os.environ.get(ISOLATION_ROOT_ENV, "")
    token = os.environ.get(ISOLATION_TOKEN_ENV, "")
    if not raw_root or not token:
        raise RuntimeError("issue_286_bwrap_isolation_missing: root/token not in worker env")
    if os.environ.get(ISOLATION_MODE_ENV, "") != ISOLATION_MODE_VALUE:
        raise RuntimeError("issue_286_bwrap_isolation_mode_mismatch")
    root = _require_absolute_path(raw_root, label=ISOLATION_ROOT_ENV).resolve(strict=True)
    marker = root / _SCRATCH_MARKER
    if not marker.is_file() or marker.read_text(encoding="ascii").strip() != token.strip():
        raise RuntimeError("issue_286_bwrap_token_mismatch")
    layout = _scratch_layout(root)
    _ensure_layout_dirs(layout)
    _apply_layout_env(root, layout, token.strip())


def should_bootstrap_host_isolation() -> bool:
    if os.environ.get(FORCE_ENV) == "1":
        return True
    if os.environ.get(BWRAP_ACTIVE_ENV) == "1":
        return True
    args = sys.argv[1:]
    for idx, arg in enumerate(args):
        if "issue_286" in arg or "codex_bootstrap" in arg:
            return True
        if arg.rstrip("/") in {"tests", "test"}:
            return True
        if arg in ("-k", "-m") and idx + 1 < len(args):
            return True
    return False


def _ensure_host_isolation_installed() -> None:
    if os.environ.get(INSTALLED_ENV) == "1":
        try:
            validate_isolated_env(strict=False)
        except RuntimeError:
            raise RuntimeError("issue_286_isolation_marker_forged_or_stale") from None
        return
    _fail_if_convmem_imported_before_isolation()
    if os.environ.get(BWRAP_ACTIVE_ENV) == "1":
        align_bwrap_worker_isolation()
    else:
        install_host_isolation_from_scratch()


def bootstrap_issue_286_host_isolation_at_import() -> None:
    if os.environ.get(INSTALLED_ENV) == "1":
        try:
            validate_isolated_env(strict=False)
        except RuntimeError:
            raise RuntimeError("issue_286_isolation_marker_forged_or_stale") from None
        return
    if not should_bootstrap_host_isolation():
        return
    _fail_if_convmem_imported_before_isolation()
    _ensure_host_isolation_installed()
    validate_isolated_env(strict=True)


def enforce_issue_286_import_guard() -> None:
    if os.environ.get("CONVMEM_ISSUE_286_INNER_BWRAP_WORKER") == "1":
        return
    if os.environ.get("CONVMEM_ISSUE_286_OUTER_BWRAP_ACTIVE") != "1":
        raise RuntimeError(
            "issue_286_unguarded_entry: use scripts/issue_286_guarded_pytest_launcher.py"
        )
    _ensure_host_isolation_installed()
    validate_isolated_env(strict=True)


def _subprocess_env_for_inner_bwrap_worker(*, extra: dict[str, str] | None = None) -> dict[str, str]:
    from incremental_jsonl_isolation import _layout

    root = Path(os.environ[ISOLATION_ROOT_ENV]).resolve()
    layout = _layout(root)
    env: dict[str, str] = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": str(layout["home"]),
        "XDG_CONFIG_HOME": str(layout["xdg_config"]),
        "XDG_DATA_HOME": str(layout["xdg_data"]),
        "XDG_CACHE_HOME": str(layout["xdg_cache"]),
        "XDG_STATE_HOME": str(root / "xdg-state"),
        "XDG_RUNTIME_DIR": str(root / "xdg-run"),
        "TMPDIR": str(root / "tmp"),
        "TEMP": str(root / "tmp"),
        "TMP": str(root / "tmp"),
        ISOLATION_ROOT_ENV: str(root),
        ISOLATION_TOKEN_ENV: os.environ[ISOLATION_TOKEN_ENV],
        ISOLATION_MODE_ENV: os.environ.get(ISOLATION_MODE_ENV, ISOLATION_MODE_VALUE),
        ISOLATION_FORBIDDEN_ENV: os.environ.get(ISOLATION_FORBIDDEN_ENV, "[]"),
        REAL_HOME_ENV: os.environ.get(REAL_HOME_ENV, ""),
    }
    if extra:
        env.update(extra)
    return env


def subprocess_env_for_issue_286(*, extra: dict[str, str] | None = None) -> dict[str, str]:
    if os.environ.get("CONVMEM_ISSUE_286_INNER_BWRAP_WORKER") == "1":
        return _subprocess_env_for_inner_bwrap_worker(extra=extra)
    validate_isolated_env(strict=True)
    real_home = _require_non_empty_real_home(os.environ.get(REAL_HOME_ENV))
    scratch = approved_scratch_root()
    _validate_token_and_mode()
    env: dict[str, str] = {"PATH": os.environ.get("PATH", os.defpath)}
    for key in _PATH_ENV_KEYS:
        value = os.environ.get(key)
        if not value:
            raise RuntimeError(f"issue_286_child_env_missing: {key}")
        env[key] = value
    for key in (ISOLATION_TOKEN_ENV, ISOLATION_MODE_ENV, ISOLATION_FORBIDDEN_ENV):
        value = os.environ.get(key)
        if not value:
            raise RuntimeError(f"issue_286_child_env_missing: {key}")
        env[key] = value
    for key in _PASSTHROUGH_ENV_KEYS:
        if key in env:
            continue
        value = os.environ.get(key)
        if value:
            env[key] = value
    if extra:
        for key, value in extra.items():
            if key == "HOME":
                if Path(value).expanduser().resolve() == real_home:
                    raise RuntimeError("issue_286_child_env_leak: HOME equals operator real home")
                path_must_live_under_scratch(
                    _require_absolute_path(value, label="child.extra:HOME"),
                    scratch,
                    label="child.extra:HOME",
                )
            if key == ISOLATION_TOKEN_ENV and value.strip() != (scratch / _SCRATCH_MARKER).read_text(encoding="ascii").strip():
                raise RuntimeError("issue_286_scratch_token_mismatch")
            if key in _PATH_ENV_KEYS and value == "":
                raise RuntimeError(f"issue_286_child_env_missing: {key}")
        env.update(extra)
    layout_home = isolated_layout_home()
    env["HOME"] = str(layout_home)
    root = approved_scratch_root()
    env["XDG_CONFIG_HOME"] = str(root / "xdg-config")
    env["XDG_DATA_HOME"] = str(root / "xdg-data")
    env["XDG_CACHE_HOME"] = str(root / "xdg-cache")
    env["XDG_STATE_HOME"] = str(root / "xdg-state")
    env["XDG_RUNTIME_DIR"] = str(root / "xdg-run")
    env["TMPDIR"] = str(root / "tmp")
    env["TEMP"] = env["TMPDIR"]
    env["TMP"] = env["TMPDIR"]
    if env.get(ISOLATION_MODE_ENV) != ISOLATION_MODE_VALUE:
        raise RuntimeError("issue_286_child_env_mode_mismatch")
    marker_token = (scratch / _SCRATCH_MARKER).read_text(encoding="ascii").strip()
    if env.get(ISOLATION_TOKEN_ENV, "").strip() != marker_token:
        raise RuntimeError("issue_286_scratch_token_mismatch")
    for key, value in env.items():
        if key == "PATH":
            continue
        if key in _PATH_ENV_KEYS or key in _OPTIONAL_PATH_ENV_KEYS:
            path_must_live_under_scratch(
                _require_absolute_path(value, label=f"child:{key}"), scratch, label=f"child:{key}"
            )
        if key == "HOME" and Path(value).resolve() == real_home:
            raise RuntimeError("issue_286_child_env_leak: HOME equals operator real home")
        if key in {"HOME", "CONVMEM_CONFIG", "TMPDIR", ISOLATION_ROOT_ENV} and value:
            if resolves_under_production_path(value, real_home=real_home):
                raise RuntimeError(f"issue_286_child_env_leak: {key} points at production path")
    return env


def subprocess_negative_must_reject_operator_home() -> None:
    """Callable from guard tests: building child env with operator HOME must fail."""
    real_home = capture_real_home()
    try:
        subprocess_env_for_issue_286(extra={"HOME": str(real_home)})
    except RuntimeError:
        return
    raise AssertionError("subprocess_env_for_issue_286 must reject operator HOME in extra")




def isolated_layout_home() -> Path:
    return approved_scratch_root() / "home"


def isolated_default_config_path() -> Path:
    return isolated_layout_home() / ".config" / "convmem" / "config.toml"

def isolated_codex_sessions_root() -> Path:
    validate_isolated_env(strict=True)
    root = Path(os.environ["HOME"]).expanduser().resolve() / ".codex" / "sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root


def configure_issue_286_isolation_for_pytest() -> None:
    bootstrap_issue_286_host_isolation_at_import()
