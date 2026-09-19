"""Hermetic Gate 1 smoke launcher for Claude ``index --file``.

Synthetic scratch-only preparation for Arc Claude Watch Parity. Does not read,
list, or index live Claude transcripts. Uses deterministic fake providers and
reuses the reviewed jsonl production-integration isolation boundary.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from incremental_jsonl_isolation import (
    ISOLATION_ENV_ALLOWLIST,
    ISOLATION_MODE,
    ISOLATION_MODE_ENV,
    ISOLATION_ROOT_ENV,
    ISOLATION_TOKEN_ENV,
    IsolationBoundary,
    IsolationViolation,
    create_fresh_root,
    install_network_denial,
    known_production_roots,
    sanitized_worker_env,
)

REPO_ROOT = Path(__file__).resolve().parent
WORKER = REPO_ROOT / "tests" / "claude_gate1_smoke_worker.py"

_CREDENTIAL_MARKERS = ("API_KEY", "SECRET", "PASSWORD", "CREDENTIAL")
_SYNTHETIC_SESSION_ID = "sess-hermetic-gate1-001"
_SYNTHETIC_UNIT: dict[str, Any] = {
    "type": "explanation",
    "title": "Hermetic Claude Gate 1 unit",
    "summary": "Synthetic on-demand index smoke knowledge unit.",
    "keywords": ["claude", "hermetic", "gate1"],
    "confidence": 0.95,
    "domain": "general",
}

# Mirror config.py path keys without importing ConvMem runtime modules.
_CONFIG_PATH_KEYS = frozenset(
    {
        "chroma_dir",
        "processed_log",
        "units_export",
        "inventory",
        "state_dir",
        "ledger_path",
        "activation_manifest_path",
        "health_path",
    }
)
_DEFAULT_INCREMENTAL_STATE_DIR = "~/.local/share/convmem/incremental-jsonl"
_DEFAULT_WRITER_LOCK = "~/.local/share/convmem/locks/chroma_writer_gate.lock"
_DEFAULT_WRITER_ATTEST_DIR = "~/.local/share/convmem/writer_attestations"
_DEFAULT_WRITER_CENSUS_DIR = "~/.local/share/convmem/writer-census"
_DEFAULT_BRIEF_PATH = "~/.local/share/convmem/brief.md"

# Linux memfd / fcntl seal UAPI constants (stable when Python omits exports).
_MFD_CLOEXEC = 0x0001
_MFD_ALLOW_SEALING = 0x0002
_F_ADD_SEALS = 1033
_F_GET_SEALS = 1034
_F_SEAL_SEAL = 0x01
_F_SEAL_SHRINK = 0x02
_F_SEAL_GROW = 0x04
_F_SEAL_WRITE = 0x08
_REQUIRED_SEAL_FLAGS = (
    _F_SEAL_SEAL | _F_SEAL_SHRINK | _F_SEAL_GROW | _F_SEAL_WRITE
)
_SEALED_WRITE_BLOCK_ERRNOS = frozenset({errno.EPERM, errno.EACCES})
_MEMFD_PROBE_NAME = "convmem-gate1-memfd-probe"
_MEMFD_CONFIG_NAME = "convmem-gate1-sealed-config"


@dataclass(frozen=True)
class ConfigIdentity:
    """Immutable fingerprint of the validated scratch config."""

    path: str
    digest: str
    device: int
    inode: int
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class OutputContainmentPreflight:
    """Proof that scratch config and mutable targets are confined before imports."""

    config_path: Path
    config_bytes: bytes
    config_identity: ConfigIdentity
    validated_targets: tuple[str, ...]


@dataclass(frozen=True)
class SealedConfigBinding:
    """Validated config bytes bound to a kernel-sealed memfd descriptor."""

    digest: str
    raw: bytes
    fd: int
    descriptor_path: str

    def load(self) -> dict[str, Any]:
        """Read the sealed descriptor; never reopen the original pathname."""
        try:
            with open(self.descriptor_path, "rb") as handle:
                data = handle.read()
        except OSError as exc:
            raise IsolationViolation(
                f"sealed configuration descriptor unreadable: {exc}"
            ) from exc
        if data != self.raw:
            raise IsolationViolation("sealed configuration bytes diverged")
        if hashlib.sha256(data).hexdigest() != self.digest:
            raise IsolationViolation("sealed configuration digest diverged")
        return _parse_scratch_config(data)


@dataclass
class _ConfigLoaderRestoreState:
    """Captured process-global loader bindings replaced during indexing."""

    module_bindings: list[tuple[ModuleType, str, Callable[..., Any]]] = field(
        default_factory=list
    )
    config_path: Path | None = None
    ingest_load_config: Callable[..., Any] | None = None


@dataclass(frozen=True)
class HermeticEvidence:
    """Content-free smoke result for Ryan review."""

    files_processed: int
    files_skipped: int
    chunks_indexed: int
    units_indexed: int
    format_name: str
    scratch_root: str
    transcript_digest: str
    config_path: str
    exit_code: int

    @property
    def passed(self) -> bool:
        return (
            self.exit_code == 0
            and self.files_processed == 1
            and self.files_skipped == 0
            and self.units_indexed > 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_processed": self.files_processed,
            "files_skipped": self.files_skipped,
            "chunks_indexed": self.chunks_indexed,
            "units_indexed": self.units_indexed,
            "format_name": self.format_name,
            "scratch_root": self.scratch_root,
            "transcript_digest": self.transcript_digest,
            "config_path": self.config_path,
            "exit_code": self.exit_code,
            "passed": self.passed,
        }


def _claude_record(
    *,
    rtype: str,
    content: object,
    session_id: str = _SYNTHETIC_SESSION_ID,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "type": rtype,
        "sessionId": session_id,
        "uuid": f"uuid-{rtype}",
        "cwd": "/tmp/hermetic-project",
        "isSidechain": False,
        "timestamp": "2026-09-18T12:00:00.000Z",
    }
    if rtype in ("user", "assistant"):
        record["message"] = {"role": rtype, "content": content}
    return record


def write_synthetic_claude_transcript(home: Path) -> Path:
    """Place a Claude-shaped fixture under ``HOME/.claude/projects/...``."""
    transcript_dir = home / ".claude" / "projects" / "hermetic-gate1-slug"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript = transcript_dir / "session-uuid-hermetic.jsonl"
    rows = [
        _claude_record(rtype="system", content=""),
        _claude_record(
            rtype="user",
            content="Hello from the hermetic Gate 1 Claude smoke fixture.",
        ),
        _claude_record(
            rtype="assistant",
            content=[{"type": "text", "text": "Acknowledged hermetic fixture."}],
        ),
    ]
    transcript.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    return transcript.resolve(strict=True)


def scrub_credentials(env: dict[str, str]) -> dict[str, str]:
    """Drop inherited credential env vars while preserving isolation markers."""
    cleaned = dict(env)
    for name in list(cleaned):
        if name in ISOLATION_ENV_ALLOWLIST:
            continue
        if any(marker in name.upper() for marker in _CREDENTIAL_MARKERS):
            cleaned.pop(name, None)
    return cleaned


def prepare_hermetic_fixture(
    parent: Path | None = None,
    *,
    home: Path | None = None,
) -> tuple[Path, str, dict[str, str], Path]:
    """Create a fresh scratch root, env, and synthetic Claude transcript."""
    root, token = create_fresh_root(parent)
    env = scrub_credentials(
        sanitized_worker_env(
            root,
            token,
            forbidden_roots=known_production_roots(home=home),
        )
    )
    transcript = write_synthetic_claude_transcript(Path(env["HOME"]))
    return root, token, env, transcript


def install_fake_providers() -> None:
    """Replace paid/network providers with deterministic local transforms."""
    import ingest  # noqa: PLC0415

    if os.environ.get("CONVMEM_GATE1_FORCE_ZERO_UNITS") == "1":
        ingest.summarize = lambda *_a, **_k: "summary:forced-zero"
        ingest.ollama_embed = lambda *_a, **_k: [0.0] * 8
        ingest.distill = lambda *_a, **_k: []
        return

    def fake_summarize(
        text: str,
        model: str,
        ollama_host: str,
        deepseek_base_url: str = "https://api.deepseek.com",
    ) -> str:
        return f"summary:{hashlib.sha256(text.encode()).hexdigest()[:16]}"

    def fake_embed(text: str, model: str, host: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [((digest[index] / 255.0) * 2.0) - 1.0 for index in range(8)]

    def fake_distill(
        text: str,
        model: str,
        ollama_host: str,
        deepseek_base_url: str = "https://api.deepseek.com",
    ) -> list[dict[str, Any]]:
        return [dict(_SYNTHETIC_UNIT)]

    ingest.summarize = fake_summarize
    ingest.ollama_embed = fake_embed
    ingest.distill = fake_distill


def _expand_path_value(value: object) -> object:
    if isinstance(value, str):
        return str(Path(value).expanduser())
    if isinstance(value, list):
        return [_expand_path_value(item) for item in value]
    return value


def _expand_section_paths(section: dict[str, Any]) -> None:
    for key, value in list(section.items()):
        if isinstance(value, dict):
            _expand_section_paths(value)
        elif key in _CONFIG_PATH_KEYS:
            section[key] = _expand_path_value(value)


def _expand_config_paths(cfg: dict[str, Any]) -> None:
    sources = cfg.get("sources")
    if isinstance(sources, dict) and isinstance(sources.get("paths"), list):
        sources["paths"] = _expand_path_value(sources["paths"])
    for section in cfg.values():
        if isinstance(section, dict):
            _expand_section_paths(section)


def _require_env_path(name: str) -> Path:
    raw = os.environ.get(name, "")
    if not raw:
        raise IsolationViolation(f"{name} missing for scratch config discovery")
    return Path(raw)


def _resolved_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def validate_scratch_environment(boundary: IsolationBoundary) -> dict[str, Path]:
    """Bind scratch HOME/XDG roots to the isolated layout before config load."""
    layout = boundary.layout
    bindings = {
        "HOME": layout["home"],
        "XDG_CONFIG_HOME": layout["xdg_config"],
        "XDG_DATA_HOME": layout["xdg_data"],
        "XDG_CACHE_HOME": layout["xdg_cache"],
    }
    resolved: dict[str, Path] = {}
    for env_name, expected in bindings.items():
        actual = boundary.resolve_mutable(
            _require_env_path(env_name),
            label=env_name,
        )
        expected_resolved = boundary.resolve_mutable(
            expected,
            label=f"expected {env_name}",
        )
        if actual != expected_resolved:
            raise IsolationViolation(
                f"{env_name} does not match scratch isolation layout"
            )
        resolved[env_name.lower()] = actual
    config_path = layout["user_config"]
    if not config_path.is_file():
        raise IsolationViolation("scratch config missing under isolated HOME")
    resolved["config_path"] = boundary.resolve_mutable(
        config_path,
        label="effective config",
    )
    return resolved


def _read_scratch_config_bytes(config_path: Path) -> bytes:
    if config_path.is_symlink():
        raise IsolationViolation("scratch config must not be a symlink")
    try:
        return config_path.read_bytes()
    except OSError as exc:
        raise IsolationViolation(f"cannot read scratch config: {exc}") from exc


def _parse_scratch_config(raw: bytes) -> dict[str, Any]:
    try:
        cfg = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise IsolationViolation("scratch config is not valid TOML") from exc
    if not isinstance(cfg, dict):
        raise IsolationViolation("scratch config must be a TOML table")
    _expand_config_paths(cfg)
    return cfg


def _rewrite_config_text(text: str, key: str, value: Path) -> str:
    replacement = f'{key} = {json.dumps(str(value))}'
    updated, count = re.subn(
        rf"^{key} = .*$",
        replacement,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ValueError(f"could not rewrite config key {key}")
    return updated


def replace_config_scalar(config_path: Path, key: str, value: Path) -> None:
    """Rewrite one top-level scalar in the scratch TOML config."""
    text = config_path.read_text(encoding="utf-8")
    config_path.write_text(_rewrite_config_text(text, key, value), encoding="utf-8")


def _apply_config_pathname_tamper(
    config_path: Path,
    *,
    mode: str,
    key: str,
    target: Path,
) -> None:
    """Mutate the original config pathname after sealed bytes are bound."""
    text = config_path.read_text(encoding="utf-8")
    updated = _rewrite_config_text(text, key, target)
    if mode == "rewrite":
        config_path.write_text(updated, encoding="utf-8")
        return
    if mode == "replace":
        staging = config_path.with_name(f".{config_path.name}.tamper")
        staging.write_text(updated, encoding="utf-8")
        os.replace(staging, config_path)
        return
    if mode == "symlink":
        malicious = target.parent / "malicious-config.toml"
        malicious.write_text(updated, encoding="utf-8")
        os.chmod(malicious, 0o600)
        config_path.unlink()
        config_path.symlink_to(malicious)
        return
    raise ValueError(f"unknown post-binding tamper mode: {mode}")


def _assert_scratch_config_layout(cfg: dict[str, Any], boundary: IsolationBoundary) -> None:
    """Prove HOME-based discovery selected the generated scratch config."""
    layout = boundary.layout
    index = cfg.get("index")
    if not isinstance(index, dict):
        raise IsolationViolation("scratch config index table missing")
    expected_pairs = (
        ("chroma_dir", layout["chroma"]),
        ("processed_log", layout["processed"]),
        ("units_export", layout["export"]),
    )
    for key, expected in expected_pairs:
        actual = index.get(key)
        if not isinstance(actual, str) or not actual.strip():
            raise IsolationViolation(f"scratch config missing index.{key}")
        if _resolved_path(Path(actual)) != _resolved_path(expected):
            raise IsolationViolation(
                f"scratch config index.{key} does not match isolated layout"
            )
    incremental = index.get("incremental_jsonl")
    if not isinstance(incremental, dict):
        raise IsolationViolation("scratch config incremental_jsonl table missing")
    state_dir = incremental.get("state_dir", _DEFAULT_INCREMENTAL_STATE_DIR)
    if not isinstance(state_dir, str) or not state_dir.strip():
        raise IsolationViolation("scratch config state_dir must be a non-empty string")
    if _resolved_path(Path(state_dir)) != _resolved_path(layout["state"]):
        raise IsolationViolation(
            "scratch config state_dir does not match isolated layout"
        )


def collect_index_mutable_targets(cfg: dict[str, Any]) -> list[tuple[str, Path]]:
    """Return every path the index command may create or mutate."""
    targets: list[tuple[str, Path]] = []
    index = cfg.get("index")
    if isinstance(index, dict):
        for key in ("chroma_dir", "processed_log", "units_export", "inventory"):
            value = index.get(key)
            if isinstance(value, str) and value.strip():
                targets.append((f"index.{key}", Path(value)))
        incremental = index.get("incremental_jsonl")
        if isinstance(incremental, dict):
            state_dir = incremental.get("state_dir", _DEFAULT_INCREMENTAL_STATE_DIR)
            if isinstance(state_dir, str) and state_dir.strip():
                targets.append(
                    ("index.incremental_jsonl.state_dir", Path(state_dir))
                )
    sources = cfg.get("sources")
    if isinstance(sources, dict):
        inventory = sources.get("inventory")
        if isinstance(inventory, str) and inventory.strip():
            targets.append(("sources.inventory", Path(inventory)))
    shadow = cfg.get("shadow_ledger")
    if isinstance(shadow, dict):
        for key in ("ledger_path", "activation_manifest_path", "health_path"):
            value = shadow.get(key)
            if isinstance(value, str) and value.strip():
                targets.append((f"shadow_ledger.{key}", Path(value)))
    for label, raw in (
        ("writer_lock(default)", _DEFAULT_WRITER_LOCK),
        ("writer_attestations(default)", _DEFAULT_WRITER_ATTEST_DIR),
        ("writer_census(default)", _DEFAULT_WRITER_CENSUS_DIR),
        ("brief(default)", _DEFAULT_BRIEF_PATH),
    ):
        targets.append((label, Path(raw).expanduser()))
    expanded: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for label, path in targets:
        resolved = _resolved_path(path)
        token = str(resolved)
        if token in seen:
            continue
        seen.add(token)
        expanded.append((label, resolved))
        parent = resolved.parent
        parent_token = str(parent)
        if parent_token not in seen:
            seen.add(parent_token)
            expanded.append((f"{label}:parent", parent))
    return expanded


def validate_output_containment(boundary: IsolationBoundary) -> OutputContainmentPreflight:
    """Fail closed on config/env/output paths before ConvMem indexing imports."""
    env_paths = validate_scratch_environment(boundary)
    config_path = env_paths["config_path"]
    raw = _read_scratch_config_bytes(config_path)
    cfg = _parse_scratch_config(raw)
    _assert_scratch_config_layout(cfg, boundary)
    validated: list[str] = []
    seen: set[str] = set()
    for label, path in collect_index_mutable_targets(cfg):
        token = f"{label}:{path}"
        if token in seen:
            continue
        seen.add(token)
        boundary.resolve_mutable(path, label=label)
        validated.append(label)
    try:
        stat_result = config_path.stat()
    except OSError as exc:
        raise IsolationViolation(f"cannot stat scratch config: {exc}") from exc
    return OutputContainmentPreflight(
        config_path=config_path,
        config_bytes=raw,
        config_identity=ConfigIdentity(
            path=str(config_path),
            digest=hashlib.sha256(raw).hexdigest(),
            device=stat_result.st_dev,
            inode=stat_result.st_ino,
            size=stat_result.st_size,
            mtime_ns=stat_result.st_mtime_ns,
        ),
        validated_targets=tuple(validated),
    )


def _validate_index_output_containment(
    cfg: dict[str, Any],
    boundary: IsolationBoundary,
) -> None:
    seen: set[str] = set()
    for label, path in collect_index_mutable_targets(cfg):
        token = f"{label}:{path}"
        if token in seen:
            continue
        seen.add(token)
        boundary.resolve_mutable(path, label=label)


def _libc_memfd_create(name: str) -> int:
    """Create a sealable memfd via ``os`` or libc when Python omits the binding."""
    flags = _MFD_CLOEXEC | _MFD_ALLOW_SEALING
    if hasattr(os, "memfd_create"):
        mfd_cloexec = getattr(os, "MFD_CLOEXEC", _MFD_CLOEXEC)
        mfd_allow_sealing = getattr(os, "MFD_ALLOW_SEALING", _MFD_ALLOW_SEALING)
        return os.memfd_create(name, mfd_cloexec | mfd_allow_sealing)
    if not sys.platform.startswith("linux"):
        raise OSError(errno.ENOSYS, "memfd_create requires Linux")
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    libc.memfd_create.argtypes = [ctypes.c_char_p, ctypes.c_uint]
    libc.memfd_create.restype = ctypes.c_int
    fd = libc.memfd_create(name.encode(), flags)
    if fd < 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err), "memfd_create")
    return fd


def _write_fd(fd: int, raw: bytes) -> None:
    written = 0
    view = memoryview(raw)
    while written < len(raw):
        written += os.write(fd, view[written:])


def _apply_required_seals(fd: int) -> None:
    add_seals = getattr(fcntl, "F_ADD_SEALS", _F_ADD_SEALS)
    # Apply every required seal in one call; F_SEAL_SEAL must not be added first alone
    # because it blocks further seals from being added to the inode.
    fcntl.fcntl(fd, add_seals, _REQUIRED_SEAL_FLAGS)


def _read_applied_seals(fd: int) -> int:
    get_seals = getattr(fcntl, "F_GET_SEALS", _F_GET_SEALS)
    return int(fcntl.fcntl(fd, get_seals, 0))


def _verify_required_seals(fd: int) -> None:
    applied = _read_applied_seals(fd)
    if applied != _REQUIRED_SEAL_FLAGS:
        raise OSError(
            errno.EINVAL,
            f"memfd seal mask mismatch: got 0x{applied:02x}, "
            f"expected 0x{_REQUIRED_SEAL_FLAGS:02x}",
        )


def _attempt_write_blocked(fd: int, label: str) -> None:
    try:
        os.write(fd, b"tamper")
    except OSError as exc:
        if exc.errno in _SEALED_WRITE_BLOCK_ERRNOS:
            return
        raise IsolationViolation(
            f"unexpected errno writing sealed memfd via {label}: {exc}"
        ) from exc
    raise IsolationViolation(f"sealed memfd accepted write via {label}")


def verify_sealed_writes_blocked(sealed: SealedConfigBinding) -> None:
    """Prove writes through the retained fd and ``/proc/self/fd`` path fail."""
    _attempt_write_blocked(sealed.fd, "retained descriptor")
    proc_path = sealed.descriptor_path
    try:
        with open(proc_path, "r+b") as handle:
            handle.write(b"tamper")
    except OSError as exc:
        if exc.errno in _SEALED_WRITE_BLOCK_ERRNOS:
            return
        raise IsolationViolation(
            f"unexpected errno writing sealed memfd via proc path: {exc}"
        ) from exc
    raise IsolationViolation("sealed memfd accepted write via proc fd path")


def _attempt_ftruncate_blocked(fd: int, size: int, operation: str) -> None:
    try:
        os.ftruncate(fd, size)
    except OSError as exc:
        if exc.errno in _SEALED_WRITE_BLOCK_ERRNOS:
            return
        raise IsolationViolation(
            f"unexpected errno on ftruncate {operation} sealed memfd: {exc}"
        ) from exc
    raise IsolationViolation(f"sealed memfd accepted ftruncate {operation}")


def verify_sealed_ftruncate_blocked(fd: int, current_size: int) -> None:
    """Prove ftruncate cannot grow or shrink the sealed memfd."""
    _attempt_ftruncate_blocked(fd, current_size + 1, "grow")
    if current_size > 0:
        _attempt_ftruncate_blocked(fd, current_size - 1, "shrink")


def sealed_storage_available() -> bool:
    """Return whether this Linux runtime can create and verify a sealed memfd."""
    if not sys.platform.startswith("linux"):
        return False
    fd = -1
    try:
        fd = _libc_memfd_create(_MEMFD_PROBE_NAME)
        _apply_required_seals(fd)
        _verify_required_seals(fd)
        verify_sealed_ftruncate_blocked(fd, 0)
        verify_sealed_writes_blocked(
            SealedConfigBinding(
                digest="probe",
                raw=b"",
                fd=fd,
                descriptor_path=f"/proc/self/fd/{fd}",
            )
        )
        return True
    except OSError:
        return False
    finally:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass


def create_verified_sealed_binding(raw: bytes) -> SealedConfigBinding:
    """Create a kernel-sealed memfd and verify immutability before use."""
    digest = hashlib.sha256(raw).hexdigest()
    if not sealed_storage_available():
        raise IsolationViolation(
            "cannot seal validated configuration bytes: memfd unavailable"
        )
    fd = -1
    ownership_transferred = False
    try:
        fd = _libc_memfd_create(_MEMFD_CONFIG_NAME)
        _write_fd(fd, raw)
        os.lseek(fd, 0, os.SEEK_SET)
        size = len(raw)
        _apply_required_seals(fd)
        _verify_required_seals(fd)
        verify_sealed_ftruncate_blocked(fd, size)
        descriptor_path = f"/proc/self/fd/{fd}"
        sealed = SealedConfigBinding(
            digest=digest,
            raw=raw,
            fd=fd,
            descriptor_path=descriptor_path,
        )
        verify_sealed_writes_blocked(sealed)
        ownership_transferred = True
        return sealed
    except OSError as exc:
        raise IsolationViolation(
            f"cannot seal validated configuration bytes: {exc}"
        ) from exc
    finally:
        if fd >= 0 and not ownership_transferred:
            try:
                os.close(fd)
            except OSError:
                pass


def _validated_preflight_bytes(
    preflight: OutputContainmentPreflight,
    boundary: IsolationBoundary,
) -> bytes:
    raw = preflight.config_bytes
    digest = hashlib.sha256(raw).hexdigest()
    if digest != preflight.config_identity.digest:
        raise IsolationViolation("validated configuration bytes digest mismatch")
    cfg = _parse_scratch_config(raw)
    _assert_scratch_config_layout(cfg, boundary)
    _validate_index_output_containment(cfg, boundary)
    return raw


def bind_validated_config_bytes(
    preflight: OutputContainmentPreflight,
    boundary: IsolationBoundary,
) -> SealedConfigBinding:
    """Validate preflight bytes and return a verified sealed memfd binding."""
    return create_verified_sealed_binding(
        _validated_preflight_bytes(preflight, boundary)
    )


def sealed_fd_open(sealed: SealedConfigBinding) -> bool:
    """Return whether the sealed descriptor is still open in this process."""
    if sealed.fd < 0:
        return False
    try:
        os.fstat(sealed.fd)
    except OSError:
        return False
    return True


def close_sealed_config(sealed: SealedConfigBinding) -> None:
    """Close the sealed descriptor if it is still open."""
    if sealed.fd < 0:
        return
    try:
        os.close(sealed.fd)
    except OSError:
        pass


def _patch_config_loader(sealed: SealedConfigBinding) -> _ConfigLoaderRestoreState:
    """Replace every imported ``load_config`` with the sealed descriptor loader."""
    import config as config_mod  # noqa: PLC0415
    import ingest as ingest_mod  # noqa: PLC0415

    original = config_mod.load_config
    descriptor = Path(sealed.descriptor_path)
    restore = _ConfigLoaderRestoreState(
        config_path=config_mod.CONFIG_PATH,
        ingest_load_config=ingest_mod.load_config,
    )

    def load_sealed_config(_path: Path | str = descriptor) -> dict[str, Any]:
        return sealed.load()

    applied: list[tuple[ModuleType, str, Callable[..., Any]]] = []
    try:
        for module in list(sys.modules.values()):
            if module is None:
                continue
            try:
                current = getattr(module, "load_config", None)
            except Exception:  # pylint: disable=broad-exception-caught
                continue
            if current is original:
                setattr(module, "load_config", load_sealed_config)
                applied.append((module, "load_config", current))
                restore.module_bindings.append((module, "load_config", current))
        config_mod.load_config = load_sealed_config
        config_mod.CONFIG_PATH = descriptor
        ingest_mod.load_config = load_sealed_config
    except Exception:
        for module, attribute, prior in reversed(applied):
            try:
                setattr(module, attribute, prior)
            except (AttributeError, TypeError):
                continue
        raise
    return restore


def _restore_config_loader(restore: _ConfigLoaderRestoreState) -> None:
    """Restore every process-global loader binding captured during patching."""
    import config as config_mod  # noqa: PLC0415
    import ingest as ingest_mod  # noqa: PLC0415

    for module, attribute, original in restore.module_bindings:
        try:
            setattr(module, attribute, original)
        except (AttributeError, TypeError):
            continue
    if restore.config_path is not None:
        config_mod.CONFIG_PATH = restore.config_path
    if restore.ingest_load_config is not None:
        ingest_mod.load_config = restore.ingest_load_config


class sealed_config_session(AbstractContextManager[SealedConfigBinding]):
    """Own memfd creation, loader patching, and descriptor cleanup on every path."""

    def __init__(
        self,
        preflight: OutputContainmentPreflight,
        boundary: IsolationBoundary,
    ) -> None:
        self._preflight = preflight
        self._boundary = boundary
        self._sealed: SealedConfigBinding | None = None
        self._restore: _ConfigLoaderRestoreState | None = None

    def __enter__(self) -> SealedConfigBinding:
        raw = _validated_preflight_bytes(self._preflight, self._boundary)
        sealed = create_verified_sealed_binding(raw)
        self._sealed = sealed
        try:
            self._restore = _patch_config_loader(sealed)
        except Exception:
            close_sealed_config(sealed)
            self._sealed = None
            raise
        return sealed

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> bool:
        try:
            if self._restore is not None:
                _restore_config_loader(self._restore)
        finally:
            if self._sealed is not None:
                close_sealed_config(self._sealed)
                self._sealed = None
        return False


def maybe_apply_test_post_binding_tamper(config_path: Path) -> None:
    """Test-only hook: mutate the original pathname after immutable binding."""
    mode = os.environ.get("CONVMEM_GATE1_TEST_POST_BINDING_TAMPER", "")
    if not mode:
        return
    key = os.environ.get("CONVMEM_GATE1_TEST_POST_BINDING_TAMPER_KEY", "")
    target = os.environ.get("CONVMEM_GATE1_TEST_POST_BINDING_TAMPER_PATH", "")
    if not key or not target:
        raise IsolationViolation("post-binding tamper requested without key/path")
    _apply_config_pathname_tamper(
        config_path,
        mode=mode,
        key=key,
        target=Path(target),
    )


def assert_transcript_under_claude_projects(transcript: Path, home: Path) -> None:
    """Fail closed when the fixture is not under the scratch Claude tree."""
    projects_root = (home / ".claude" / "projects").resolve()
    try:
        transcript.resolve().relative_to(projects_root)
    except ValueError as exc:
        raise IsolationViolation(
            "transcript must live under HOME/.claude/projects for Gate 1 detection"
        ) from exc


def run_hermetic_index_cli(
    transcript: Path,
    *,
    preflight: OutputContainmentPreflight,
) -> tuple[int, dict[str, int], str]:
    """Invoke the real ``convmem index --file`` command in-process after guards."""
    if not isinstance(preflight, OutputContainmentPreflight):
        raise IsolationViolation(
            "output containment preflight required before index CLI"
        )
    boundary = IsolationBoundary.from_environment()
    install_network_denial()
    home = Path(os.environ["HOME"])
    resolved = boundary.resolve_mutable(transcript, label="claude transcript")
    assert_transcript_under_claude_projects(resolved, home)
    if not sealed_storage_available():
        raise IsolationViolation(
            "cannot seal validated configuration bytes: memfd unavailable"
        )
    from typer.testing import CliRunner  # noqa: PLC0415

    from convmem import app  # noqa: PLC0415

    install_fake_providers()
    with sealed_config_session(preflight, boundary):
        maybe_apply_test_post_binding_tamper(preflight.config_path)
        runner = CliRunner()
        result = runner.invoke(app, ["index", "--file", str(resolved)])
    stats = _parse_index_stats(result.stdout)
    return result.exit_code, stats, result.stdout


def _parse_index_stats(stdout: str) -> dict[str, int]:
    stats = {
        "files_processed": 0,
        "files_skipped": 0,
        "chunks_indexed": 0,
        "units_indexed": 0,
    }
    for line in stdout.splitlines():
        if not line.startswith("Done."):
            continue
        for key in stats:
            token = f"{key}="
            if token in line:
                fragment = line.split(token, 1)[1].split()[0]
                stats[key] = int(fragment)
    return stats


def capture_path_fingerprint(path: Path) -> dict[str, Any] | None:
    """Return inode/size/mtime facts for a path, or None when absent."""
    try:
        stat_result = path.stat()
    except OSError:
        return None
    return {
        "path": str(path),
        "device": stat_result.st_dev,
        "inode": stat_result.st_ino,
        "size": stat_result.st_size,
        "mtime_ns": stat_result.st_mtime_ns,
    }


def production_fingerprint_paths(home: Path | None = None) -> tuple[Path, ...]:
    """Paths that hermetic smoke must not mutate."""
    home = (home or Path.home()).expanduser()
    return (
        home / ".local/share/convmem/chroma",
        home / ".local/share/convmem/processed.json",
        home / ".local/share/convmem/knowledge_units.jsonl",
        home / ".config/convmem/config.toml",
    )


def production_fingerprints(home: Path | None = None) -> list[dict[str, Any]]:
    """Fingerprint default production paths that must remain unchanged."""
    fingerprints: list[dict[str, Any]] = []
    for path in production_fingerprint_paths(home=home):
        fp = capture_path_fingerprint(path)
        if fp is not None:
            fingerprints.append(fp)
    return fingerprints


def run_worker(
    command: str,
    transcript: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run the hermetic worker subprocess with a sanitized environment."""
    cmd = [sys.executable, "-I", str(WORKER), command, str(transcript)]
    return subprocess.run(
        cmd,
        env=env,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def run_hermetic_smoke(parent: Path | None = None) -> HermeticEvidence:
    """End-to-end hermetic smoke using the worker subprocess."""
    root, _token, env, transcript = prepare_hermetic_fixture(parent)
    before = production_fingerprints()
    completed = run_worker("run", transcript, env)
    after = production_fingerprints()
    if before != after:
        raise IsolationViolation("production fingerprint drift during hermetic smoke")
    worker_exit = completed.returncode
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    return HermeticEvidence(
        files_processed=int(payload.get("files_processed", 0)),
        files_skipped=int(payload.get("files_skipped", 0)),
        chunks_indexed=int(payload.get("chunks_indexed", 0)),
        units_indexed=int(payload.get("units_indexed", 0)),
        format_name=str(payload.get("format_name", "")),
        scratch_root=str(root),
        transcript_digest=hashlib.sha256(transcript.read_bytes()).hexdigest(),
        config_path=str(Path(env["HOME"]) / ".config" / "convmem" / "config.toml"),
        exit_code=worker_exit,
    )


def _main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    if not argv or argv[0] != "run":
        print(
            "Usage: python claude_gate1_smoke.py run\n"
            "Hermetic synthetic Gate 1 preparation only; no live Claude source.",
            file=sys.stderr,
        )
        return 2
    evidence = run_hermetic_smoke()
    print(json.dumps(evidence.to_dict(), indent=2, sort_keys=True))
    return 0 if evidence.passed else 1


if __name__ == "__main__":
    raise SystemExit(_main())
