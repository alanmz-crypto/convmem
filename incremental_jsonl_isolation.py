"""Pre-import isolation boundary for Kiro JSONL production-integration tests.

This module imports only the standard library. Crash workers activate it before
importing any ConvMem adapter, ingest, or Chroma module.
"""

from __future__ import annotations

import fcntl
import json
import os
import signal
import socket
import stat
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar


class IsolationViolation(RuntimeError):
    """The requested operation escaped the hermetic production-integration boundary."""


class SourceCaptureError(RuntimeError):
    """The selected source could not be captured safely."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


_T = TypeVar("_T")
_MARKER = ".convmem-jsonl-production-root"
_CREDENTIAL_MARKERS = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
PRODUCTION_OVERRIDE_ENV = frozenset(
    {
        "CONVMEM_CONFIG",
        "CONVMEM_CONFIG_PATH",
        "CONVMEM_CHROMA_DIR",
        "CONVMEM_DATA_DIR",
        "CONVMEM_PROCESSED_LOG",
    }
)
ISOLATION_ROOT_ENV = "CONVMEM_INCREMENTAL_ROOT"
ISOLATION_TOKEN_ENV = "CONVMEM_INCREMENTAL_TOKEN"
ISOLATION_MODE_ENV = "CONVMEM_INCREMENTAL_MODE"
ISOLATION_FORBIDDEN_ENV = "CONVMEM_INCREMENTAL_FORBIDDEN"
ISOLATION_MODE = "jsonl-production-integration-v1"
_WATCH_MARKERS = (
    "convmem-watch",
    "convmem_watch",
    "convmem watch",
)
_SERVICE_MARKERS = (
    "systemctl",
    "systemd-run",
    "service convmem",
)


def known_production_roots(*, home: Path | None = None) -> tuple[Path, ...]:
    """Return production defaults that hermetic tests must never open."""
    home = (home or Path.home()).expanduser()
    roots = [
        home / ".local/share/convmem",
        home / ".config/convmem",
        home / ".kiro",
        Path("/home/lauer/.local/share/convmem"),
        Path("/home/lauer/.config/convmem"),
        Path("/home/lauer/.kiro"),
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for path in roots:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return tuple(unique)


def create_fresh_root(parent: Path | None = None) -> tuple[Path, str]:
    """Create a tokenized root whose freshness can be proven by a worker."""
    token = os.urandom(24).hex()
    root = Path(tempfile.mkdtemp(prefix="convmem-jsonl-prod-", dir=parent))
    (root / _MARKER).write_text(token, encoding="ascii")
    return root.resolve(strict=True), token


def _layout(root: Path) -> dict[str, Path]:
    home = root / "home"
    xdg_config = root / "xdg-config"
    xdg_data = root / "xdg-data"
    xdg_cache = root / "xdg-cache"
    return {
        "home": home,
        "xdg_config": xdg_config,
        "xdg_data": xdg_data,
        "xdg_cache": xdg_cache,
        "user_config": home / ".config" / "convmem" / "config.toml",
        "chroma": home / ".local/share/convmem/chroma",
        "processed": home / ".local/share/convmem/processed.json",
        "export": home / ".local/share/convmem/knowledge_units.jsonl",
        "state": home / ".local/share/convmem/incremental-jsonl",
        "dedupe": home / ".local/share/convmem",
        "locks": home / ".local/share/convmem/locks",
        "attest": home / ".local/share/convmem/writer_attestations",
        "census": home / ".local/share/convmem/writer_census",
        "sources": root / "sources",
    }


def write_hermetic_config(root: Path) -> Path:
    """Write a default-off config whose every path is under ``root``."""
    layout = _layout(root)
    for key in (
        "home",
        "xdg_config",
        "xdg_data",
        "xdg_cache",
        "chroma",
        "state",
        "locks",
        "attest",
        "census",
        "sources",
    ):
        layout[key].mkdir(parents=True, exist_ok=True)
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


def sanitized_worker_env(
    root: Path,
    token: str,
    *,
    forbidden_roots: tuple[Path, ...] | None = None,
) -> dict[str, str]:
    """Return an allowlisted environment with relocated discovery roots."""
    root = root.resolve(strict=True)
    layout = _layout(root)
    write_hermetic_config(root)
    forbidden = forbidden_roots or known_production_roots()
    return {
        "PATH": os.defpath,
        "HOME": str(layout["home"]),
        "XDG_CONFIG_HOME": str(layout["xdg_config"]),
        "XDG_DATA_HOME": str(layout["xdg_data"]),
        "XDG_CACHE_HOME": str(layout["xdg_cache"]),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "LC_ALL": "C.UTF-8",
        ISOLATION_ROOT_ENV: str(root),
        ISOLATION_TOKEN_ENV: token,
        ISOLATION_MODE_ENV: ISOLATION_MODE,
        ISOLATION_FORBIDDEN_ENV: json.dumps(
            [str(path.expanduser()) for path in forbidden]
        ),
    }


def _has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.exists() and current.is_symlink():
            return True
    return False


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _command_text(args: Any) -> str:
    if isinstance(args, (list, tuple)):
        return " ".join(str(part) for part in args)
    return str(args)


def _is_denied_service_command(args: Any) -> bool:
    text = _command_text(args).lower()
    if any(marker in text for marker in _WATCH_MARKERS):
        return True
    if any(marker in text for marker in _SERVICE_MARKERS) and "convmem" in text:
        return True
    return False


@dataclass(frozen=True)
class IsolationBoundary:
    """Canonical path/provider guard established before resource construction."""

    root: Path
    token: str
    forbidden_roots: tuple[Path, ...] = ()
    service_invocations: list[str] | None = None

    @classmethod
    def from_environment(
        cls, *, forbidden_roots: tuple[Path, ...] | None = None
    ) -> "IsolationBoundary":
        for name in PRODUCTION_OVERRIDE_ENV:
            if os.environ.get(name):
                raise IsolationViolation(f"production configuration override set: {name}")
        for name in os.environ:
            if name in {ISOLATION_TOKEN_ENV, ISOLATION_FORBIDDEN_ENV}:
                continue
            if any(marker in name.upper() for marker in _CREDENTIAL_MARKERS):
                raise IsolationViolation(f"credential inherited by worker: {name}")
        raw_root = os.environ.get(ISOLATION_ROOT_ENV, "")
        token = os.environ.get(ISOLATION_TOKEN_ENV, "")
        if not raw_root or not token:
            raise IsolationViolation("incremental isolation root/token missing")
        if os.environ.get(ISOLATION_MODE_ENV, "") != ISOLATION_MODE:
            raise IsolationViolation("incremental isolation mode mismatch")
        root_path = Path(raw_root).absolute()
        if _has_symlink_component(root_path):
            raise IsolationViolation("isolation root contains a symlink")
        root = root_path.resolve(strict=True)
        marker = root / _MARKER
        if not marker.is_file() or marker.read_text(encoding="ascii") != token:
            raise IsolationViolation("isolation freshness token mismatch")
        loaded: list[Path] = []
        raw_forbidden = os.environ.get(ISOLATION_FORBIDDEN_ENV, "")
        if raw_forbidden:
            try:
                payload = json.loads(raw_forbidden)
            except json.JSONDecodeError as exc:
                raise IsolationViolation("malformed forbidden-root list") from exc
            if not isinstance(payload, list):
                raise IsolationViolation("malformed forbidden-root list")
            loaded.extend(Path(item) for item in payload if isinstance(item, str))
        if forbidden_roots:
            loaded.extend(forbidden_roots)
        resolved_forbidden = tuple(
            path.expanduser().resolve(strict=False) for path in loaded
        )
        return cls(root=root, token=token, forbidden_roots=resolved_forbidden)

    @property
    def layout(self) -> dict[str, Path]:
        return _layout(self.root)

    def resolve_mutable(self, path: Path | str, *, label: str) -> Path:
        """Resolve and contain a mutable path, rejecting aliases and symlinks."""
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate
        candidate = candidate.absolute()
        if _has_symlink_component(candidate):
            raise IsolationViolation(f"{label} contains a symlink: {candidate}")
        resolved = candidate.resolve(strict=False)
        if not _is_relative_to(resolved, self.root):
            raise IsolationViolation(f"{label} escapes isolation root: {resolved}")
        for forbidden in self.forbidden_roots:
            if _is_relative_to(resolved, forbidden) or _is_relative_to(forbidden, resolved):
                raise IsolationViolation(f"{label} aliases production root: {resolved}")
        return resolved

    def construct(
        self, path: Path | str, *, label: str, factory: Callable[[Path], _T]
    ) -> _T:
        """Validate before invoking a resource constructor."""
        return factory(self.resolve_mutable(path, label=label))

    @staticmethod
    def require_fake_provider(provider: str, endpoint: str | None = None) -> None:
        if provider != "deterministic-fake" or endpoint:
            raise IsolationViolation(
                "production-integration tests permit only deterministic-fake with no endpoint"
            )


def install_network_denial() -> None:
    """Deny ordinary Python outbound networking for this worker process."""

    def denied(*_args, **_kwargs):
        raise IsolationViolation("outbound network denied in production-integration tests")

    socket.create_connection = denied  # type: ignore[assignment]
    socket.getaddrinfo = denied  # type: ignore[assignment]
    socket.socket.connect = denied  # type: ignore[assignment]
    socket.socket.connect_ex = denied  # type: ignore[assignment]


def install_service_denial(invocations: list[str] | None = None) -> None:
    """Refuse watcher/service commands that could touch live process state."""
    real_popen = subprocess.Popen
    real_run = subprocess.run

    def _guard(args: Any) -> None:
        if invocations is not None:
            invocations.append(_command_text(args))
        if _is_denied_service_command(args):
            raise IsolationViolation("watcher/service command denied")

    def popen(args, *rest, **kwargs):  # noqa: ANN001
        _guard(args)
        return real_popen(args, *rest, **kwargs)

    def run(args, *rest, **kwargs):  # noqa: ANN001
        _guard(args)
        return real_run(args, *rest, **kwargs)

    subprocess.Popen = popen  # type: ignore[assignment]
    subprocess.run = run  # type: ignore[assignment]


class SourceAdvisoryLock:
    """Per-source advisory flock. Crash releases the kernel lock."""

    def __init__(self, boundary: IsolationBoundary, path: Path | str):
        self.path = boundary.resolve_mutable(path, label="incremental lock")
        self._fd: int | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
        except OSError:
            os.close(fd)
            raise
        self._fd = fd

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> "SourceAdvisoryLock":
        self.acquire()
        return self

    def __exit__(self, *_exc) -> None:
        self.release()


def terminate_process_group(pgid: int, *, timeout: float = 2.0) -> None:
    """Terminate a crash worker and every descendant in its process group."""
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.02)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def open_source_readonly(path: Path) -> int:
    """Open a source file read-only without following a final symlink."""
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        return os.open(str(path), flags)
    except OSError as exc:
        raise SourceCaptureError("source_open_failed", str(exc)) from exc


def validate_regular_source(fd: int, *, expected_uid: int | None = None) -> os.stat_result:
    """Reject non-regular files and unexpected ownership/mode."""
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        raise SourceCaptureError("source_not_regular", "source is not a regular file")
    owner = expected_uid if expected_uid is not None else os.getuid()
    if info.st_uid != owner:
        raise SourceCaptureError("source_wrong_owner", f"uid {info.st_uid} != {owner}")
    if info.st_mode & stat.S_IWOTH:
        raise SourceCaptureError("source_wrong_mode", "source is world-writable")
    return info
