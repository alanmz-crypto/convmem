"""Pre-import isolation boundary for the scratch JSONL prototype.

This module imports only the standard library. Crash workers activate it before
importing any ConvMem adapter or infrastructure module.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar


class IsolationViolation(RuntimeError):
    """The requested operation escaped the reviewed scratch boundary."""


_T = TypeVar("_T")
_MARKER = ".convmem-jsonl-scratch-root"
_CREDENTIAL_MARKERS = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
PRODUCTION_OVERRIDE_ENV = frozenset({
    "CONVMEM_CONFIG",
    "CONVMEM_CONFIG_PATH",
    "CONVMEM_CHROMA_DIR",
    "CONVMEM_DATA_DIR",
    "CONVMEM_PROCESSED_LOG",
})


def create_fresh_root(parent: Path | None = None) -> tuple[Path, str]:
    """Create a tokenized root whose freshness can be proven by a worker."""
    token = os.urandom(24).hex()
    root = Path(tempfile.mkdtemp(prefix="convmem-jsonl-scratch-", dir=parent))
    (root / _MARKER).write_text(token, encoding="ascii")
    return root.resolve(strict=True), token


def sanitized_worker_env(root: Path, token: str) -> dict[str, str]:
    """Return an allowlisted environment with scratch-only discovery roots."""
    root = root.resolve(strict=True)
    home = root / "home"
    config = root / "config"
    data = root / "data"
    cache = root / "cache"
    for path in (home, config, data, cache):
        path.mkdir(parents=True, exist_ok=True)
    return {
        "PATH": os.defpath,
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(config),
        "XDG_DATA_HOME": str(data),
        "XDG_CACHE_HOME": str(cache),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "LC_ALL": "C.UTF-8",
        "CONVMEM_SCRATCH_ROOT": str(root),
        "CONVMEM_SCRATCH_TOKEN": token,
        "CONVMEM_SCRATCH_MODE": "jsonl-prototype-v1",
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


@dataclass(frozen=True)
class ScratchBoundary:
    """Canonical path/provider guard established before resource construction."""

    root: Path
    token: str
    forbidden_roots: tuple[Path, ...] = ()

    @classmethod
    def from_environment(
        cls, *, forbidden_roots: tuple[Path, ...] = ()
    ) -> "ScratchBoundary":
        for name in PRODUCTION_OVERRIDE_ENV:
            if os.environ.get(name):
                raise IsolationViolation(f"production configuration override set: {name}")
        for name in os.environ:
            if name == "CONVMEM_SCRATCH_TOKEN":
                continue
            if any(marker in name.upper() for marker in _CREDENTIAL_MARKERS):
                raise IsolationViolation(f"credential inherited by scratch worker: {name}")
        raw_root = os.environ.get("CONVMEM_SCRATCH_ROOT", "")
        token = os.environ.get("CONVMEM_SCRATCH_TOKEN", "")
        if not raw_root or not token:
            raise IsolationViolation("scratch root/token missing")
        root_path = Path(raw_root).absolute()
        if _has_symlink_component(root_path):
            raise IsolationViolation("scratch root contains a symlink")
        root = root_path.resolve(strict=True)
        marker = root / _MARKER
        if not marker.is_file() or marker.read_text(encoding="ascii") != token:
            raise IsolationViolation("scratch freshness token mismatch")
        return cls(
            root=root,
            token=token,
            forbidden_roots=tuple(p.expanduser().resolve() for p in forbidden_roots),
        )

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
            raise IsolationViolation(f"{label} escapes scratch root: {resolved}")
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
                "scratch prototype permits only deterministic-fake with no endpoint"
            )


def install_network_denial() -> None:
    """Deny ordinary Python outbound networking for this worker process."""
    def denied(*_args, **_kwargs):
        raise IsolationViolation("outbound network denied in scratch prototype")

    socket.create_connection = denied  # type: ignore[assignment]
    socket.getaddrinfo = denied  # type: ignore[assignment]
    socket.socket.connect = denied  # type: ignore[assignment]
    socket.socket.connect_ex = denied  # type: ignore[assignment]


class ScratchPidLock:
    """Scratch-only PID lock with deterministic stale-owner recovery."""

    def __init__(self, boundary: ScratchBoundary, path: Path | str):
        self.path = boundary.resolve_mutable(path, label="scratch lock")
        self._owned = False

    @staticmethod
    def _alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        recovered = False
        while True:
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError as exc:
                try:
                    payload = json.loads(self.path.read_text(encoding="utf-8"))
                    owner = int(payload.get("pid", -1))
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    owner = -1
                if self._alive(owner):
                    raise IsolationViolation(
                        f"scratch lock held by live pid {owner}"
                    ) from exc
                self.path.unlink(missing_ok=True)
                recovered = True
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"pid": os.getpid(), "created_ns": time.time_ns()}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            self._owned = True
            return recovered

    def release(self) -> None:
        if self._owned:
            self.path.unlink(missing_ok=True)
            self._owned = False

    def __enter__(self) -> "ScratchPidLock":
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
