"""Hermetic Claude incremental JSONL canary boundary.

Canary-only module for Arc Claude Watch Parity Gate 2. Not registered in the
normal CLI or watcher. Live-source execution requires a separate Ryan grant.
"""

# pylint: disable=too-many-lines,duplicate-code

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from adapters.claude_session_jsonl import parse_complete_prefix
from incremental_jsonl import DURABLE_TRANSITIONS, IncrementalJsonlCoordinator
from incremental_jsonl_isolation import (
    IsolationBoundary,
    IsolationViolation,
    create_fresh_root,
    known_production_roots,
    sanitized_worker_env,
)

CANARY_MODE = "claude-incremental-canary-v1"
CRASH_EXIT = 86
GATE0_DIGEST_ENV = "CONVMEM_CLAUDE_CANARY_GATE0_DIGEST"
_SOURCE_ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_EVIDENCE_STRING_MAX = 128
_EVIDENCE_SECTION_SCHEMA: dict[str, frozenset[str]] = {
    "gate0": frozenset({"watcher", "network", "mode"}),
    "matrix": frozenset(
        {
            "first_outcome",
            "second_outcome",
            "third_outcome",
            "third_mode",
            "append_summarize",
            "append_reused",
        }
    ),
    "capture": frozenset(
        {
            "alias",
            "canonical_path",
            "device",
            "inode",
            "size",
            "complete_boundary",
            "prefix_sha256",
            "sha256",
            "physical_lines",
        }
    ),
    "coordinator": frozenset({"outcome", "mode", "counters", "reused_artifacts"}),
    "source": frozenset({"alias", "validated", "size"}),
}
_EVIDENCE_NESTED_SCHEMA: dict[str, frozenset[str]] = {
    "watcher": frozenset({"status", "method", "pass", "detail"}),
    "network": frozenset({"pass", "detail"}),
    "counters": frozenset(
        {
            "summarize",
            "embed",
            "distill",
            "chroma_upsert",
            "total",
        }
    ),
}
EVIDENCE_SECTION_ALLOWLIST = frozenset(_EVIDENCE_SECTION_SCHEMA)
_CAPTURE_TRANSITIONS = (
    "before_snapshot_prepare",
    "after_snapshot_prepare",
    "before_snapshot_publish",
    "after_snapshot_publish",
    "before_source_revalidation",
    "after_source_revalidation",
)
_CREDENTIAL_MARKERS = ("API_KEY", "SECRET", "PASSWORD", "CREDENTIAL", "TOKEN")
PRODUCTION_ROOTS = known_production_roots()


@dataclass(frozen=True)
class FrozenSourceSpec:
    """Exact-source grant identity for read-only capture."""

    alias: str
    path: Path
    sha256: str
    size: int

    def __post_init__(self) -> None:
        validate_source_alias(self.alias)


@dataclass(frozen=True)
class SourceIdentityBinding:
    """Grant-bound source identity observed at capture entry."""

    canonical_path: str
    device: int
    inode: int
    size: int
    sha256: str


@dataclass(frozen=True)
class Gate0Result:
    """Successful Gate 0 report bound to a stable digest."""

    report: dict[str, Any]
    digest: str


@dataclass(frozen=True)
class SourceDescriptor:
    """Content-free source identity for evidence."""

    alias: str
    canonical_path: str
    device: int
    inode: int
    size: int
    complete_boundary: int
    prefix_sha256: str
    sha256: str
    physical_lines: int


@dataclass
class Gate0ProbeHooks:
    """Injectable probes for hermetic Gate 0 tests."""

    watcher_probe: Callable[[], dict[str, str]] | None = None
    network_self_test: Callable[[], dict[str, str]] | None = None


def gate0_watcher_probe() -> dict[str, str]:
    """Probe watcher state; inactive stdout is PASS even with nonzero exit."""
    try:
        completed = subprocess.run(
            ["systemctl", "--user", "is-active", "convmem-watch.service"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
        stdout = (completed.stdout or "").strip()
        if stdout == "inactive":
            return {"status": "inactive", "method": "systemctl", "pass": "true"}
        if stdout in {"failed", "activating", "active"}:
            return {"status": stdout, "method": "systemctl", "pass": "false"}
        return {
            "status": stdout or "unknown",
            "method": "systemctl",
            "pass": "false",
            "detail": completed.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "unavailable",
            "method": "systemctl",
            "pass": "false",
            "detail": str(exc),
        }


def _default_network_self_test() -> dict[str, str]:
    import socket

    try:
        socket.create_connection(("203.0.113.1", 9), timeout=0.01)
        return {"pass": "false", "detail": "unexpected-success"}
    except OSError as exc:
        return {"pass": "true", "detail": type(exc).__name__}


def _path_under_roots(path: Path, roots: tuple[Path, ...]) -> bool:
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def _assert_regular_non_symlink(path: Path, *, label: str) -> None:
    if path.is_symlink():
        raise IsolationViolation(f"{label} is symlinked")
    if not path.is_file():
        raise IsolationViolation(f"{label} is not a regular file")


def validate_source_alias(alias: str) -> str:
    """Reject aliases that could escape snapshot containment."""
    if not alias or alias in {".", ".."}:
        raise IsolationViolation("invalid source alias")
    if "/" in alias or "\\" in alias or os.sep in alias:
        raise IsolationViolation("source alias contains path separator")
    if not _SOURCE_ALIAS_PATTERN.fullmatch(alias):
        raise IsolationViolation("source alias not allowlisted")
    return alias


def derive_snapshot_destination(
    boundary: IsolationBoundary, alias: str
) -> Path:
    """Derive the snapshot path exclusively from a validated isolation boundary."""
    validate_source_alias(alias)
    relative = Path("sources") / "claude-capture" / f"{alias}.jsonl"
    return boundary.resolve_mutable(relative, label="snapshot destination")


def bind_frozen_source(
    spec: FrozenSourceSpec,
) -> tuple[SourceIdentityBinding, bytes]:
    """Open one grant-bound source read-only and return identity plus bytes."""
    path = spec.path
    if path.is_symlink():
        raise IsolationViolation("frozen source is symlinked")
    if not path.is_absolute():
        raise IsolationViolation("frozen source path is not absolute")
    canonical = path.resolve(strict=True)
    if str(canonical) != str(path):
        raise IsolationViolation("frozen source canonical path substituted")
    _assert_regular_non_symlink(canonical, label="frozen source")
    if _path_under_roots(canonical, PRODUCTION_ROOTS):
        raise IsolationViolation("frozen source aliases production root")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(str(canonical), flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise IsolationViolation("frozen source is not regular")
        if before.st_size != spec.size:
            raise IsolationViolation("size drift")
        data = os.read(fd, spec.size)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    if len(data) != spec.size:
        raise IsolationViolation("size drift")
    if (before.st_dev, before.st_ino, before.st_size) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
    ):
        raise IsolationViolation("source identity changed during read")
    digest = hashlib.sha256(data).hexdigest()
    if digest != spec.sha256:
        raise IsolationViolation("digest drift")
    binding = SourceIdentityBinding(
        canonical_path=str(canonical),
        device=int(before.st_dev),
        inode=int(before.st_ino),
        size=int(before.st_size),
        sha256=digest,
    )
    return binding, data


def validate_frozen_source(spec: FrozenSourceSpec) -> bytes:
    """Open the granted source read-only and validate exact identity."""
    _binding, data = bind_frozen_source(spec)
    return data


def revalidate_source_identity(
    spec: FrozenSourceSpec, binding: SourceIdentityBinding
) -> None:
    """Re-open the live source and reject identity or digest drift."""
    fresh, _data = bind_frozen_source(spec)
    if fresh != binding:
        raise IsolationViolation("live source identity changed during capture")


def capture_source(
    boundary: IsolationBoundary,
    spec: FrozenSourceSpec,
    *,
    fault: Callable[[str], None] | None = None,
) -> SourceDescriptor:
    """Copy the complete prefix atomically under an isolation-bound snapshot path."""
    events: list[str] = []

    def emit(name: str) -> None:
        events.append(name)
        if fault is not None:
            fault(name)

    emit("before_snapshot_prepare")
    binding, data = bind_frozen_source(spec)
    emit("after_snapshot_prepare")
    view = parse_complete_prefix(binding.canonical_path, raw=data)
    emit("before_snapshot_publish")
    copied = derive_snapshot_destination(boundary, spec.alias)
    copied.parent.mkdir(parents=True, exist_ok=True)
    tmp = boundary.resolve_mutable(
        copied.with_name(f".{copied.name}.{os.urandom(4).hex()}.tmp"),
        label="snapshot temp",
    )
    with tmp.open("wb") as handle:
        handle.write(view.raw_prefix)
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(copied)
    dir_fd = os.open(str(copied.parent), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    emit("after_snapshot_publish")
    emit("before_source_revalidation")
    revalidate_source_identity(spec, binding)
    emit("after_source_revalidation")
    copied_stat = copied.stat()
    return SourceDescriptor(
        alias=spec.alias,
        canonical_path=str(copied.resolve()),
        device=int(copied_stat.st_dev),
        inode=int(copied_stat.st_ino),
        size=copied_stat.st_size,
        complete_boundary=view.complete_boundary,
        prefix_sha256=view.prefix_sha256,
        sha256=hashlib.sha256(view.raw_prefix).hexdigest(),
        physical_lines=view.raw_prefix.count(b"\n"),
    )


def _hermetic_gate0_hooks() -> Gate0ProbeHooks:
    return Gate0ProbeHooks(
        watcher_probe=lambda: {"status": "inactive", "method": "hermetic", "pass": "true"},
        network_self_test=lambda: {"pass": "true", "detail": "hermetic"},
    )


def gate0(*, hooks: Gate0ProbeHooks | None = None) -> dict[str, Any]:
    """Gate 0 checks before imports/writes; fail closed on indeterminate watcher."""
    hooks = hooks or Gate0ProbeHooks()
    watcher = (hooks.watcher_probe or gate0_watcher_probe)()
    if watcher.get("pass") != "true":
        raise IsolationViolation("watcher active or indeterminate")
    for name in os.environ:
        if any(marker in name.upper() for marker in _CREDENTIAL_MARKERS):
            if name not in {"CONVMEM_INCREMENTAL_TOKEN"}:
                raise IsolationViolation(f"credential inherited: {name}")
    for override in (
        "CONVMEM_CONFIG",
        "CONVMEM_CHROMA_DIR",
        "CONVMEM_PROCESSED_LOG",
    ):
        if override in os.environ:
            raise IsolationViolation(f"production override present: {override}")
    network = (hooks.network_self_test or _default_network_self_test)()
    if network.get("pass") != "true":
        raise IsolationViolation(f"network self-test failed: {network}")
    return {
        "watcher": watcher,
        "network": network,
        "mode": CANARY_MODE,
    }


def bind_gate0(report: Mapping[str, Any]) -> Gate0Result:
    """Bind a successful Gate 0 report to a stable digest."""
    canonical = json.dumps(dict(report), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return Gate0Result(report=dict(report), digest=digest)


def require_bound_gate0(*, hooks: Gate0ProbeHooks | None = None) -> Gate0Result:
    """Re-run Gate 0 and require a matching bound digest from the environment."""
    expected = os.environ.get(GATE0_DIGEST_ENV, "")
    if not expected:
        raise IsolationViolation("gate0 digest binding missing")
    fresh = bind_gate0(gate0(hooks=hooks))
    if fresh.digest != expected:
        raise IsolationViolation("gate0 binding mismatch")
    return fresh


def assert_transition_coverage(
    declared: tuple[str, ...],
    observed: tuple[str, ...],
    *,
    label: str,
) -> None:
    """Fail closed unless both sides of every durable transition are observed."""
    covered: dict[str, set[str]] = {}
    for point in observed:
        side, separator, transition = point.partition("_")
        if not separator or side not in {"before", "after"}:
            continue
        covered.setdefault(transition, set()).add(side)
    missing = {
        transition
        for transition in declared
        if covered.get(transition) != {"before", "after"}
    }
    if missing:
        names = ", ".join(sorted(missing))
        raise IsolationViolation(f"{label} transition coverage missing: {names}")


def scrub_credentials(env: dict[str, str]) -> dict[str, str]:
    cleaned = dict(env)
    for name in list(cleaned):
        if any(marker in name.upper() for marker in _CREDENTIAL_MARKERS):
            if name not in {"CONVMEM_INCREMENTAL_TOKEN"}:
                cleaned.pop(name, None)
    return cleaned


def prepare_fixture_env(
    parent: Path,
    *,
    count: int = 4,
    alias: str = "canary-fixture",
) -> tuple[Path, str, dict[str, str], Path, FrozenSourceSpec]:
    """Create scratch root, env, Claude fixture, and frozen spec."""
    parent_home = Path.home()
    root, token = create_fresh_root(parent)
    env = scrub_credentials(
        sanitized_worker_env(
            root,
            token,
            forbidden_roots=known_production_roots(home=parent_home),
        )
    )
    home = Path(env["HOME"])
    source = (
        home
        / ".claude"
        / "projects"
        / "canary-slug"
        / f"{alias}.jsonl"
    )
    source.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        json.dumps({"type": "system", "sessionId": "sess-claude-canary"}),
    ]
    for index in range(count):
        role = "user" if index % 2 == 0 else "assistant"
        content = f"canary-message-{index:05d}"
        row = {
            "type": role,
            "sessionId": "sess-claude-canary",
            "uuid": f"rec-{index:05d}",
            "cwd": "/tmp/canary",
            "isSidechain": False,
            "timestamp": f"2026-09-18T00:00:{index % 60:02d}Z",
            "message": {"role": role, "content": content},
        }
        rows.append(json.dumps(row, sort_keys=True))
    source.write_text("\n".join(rows) + "\n", encoding="utf-8")
    data = source.read_bytes()
    spec = FrozenSourceSpec(
        alias=alias,
        path=source,
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
    )
    return root, token, env, source, spec


def install_fake_providers() -> None:
    import ingest

    def fake_summarize(text: str, **_kwargs) -> str:
        return f"summary:{hashlib.sha256(text.encode()).hexdigest()[:16]}"

    def fake_embed(text: str, **_kwargs) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [((digest[index] / 255.0) * 2.0) - 1.0 for index in range(8)]

    def fake_distill(text: str, **_kwargs) -> list[dict[str, Any]]:
        del text
        return [
            {
                "type": "explanation",
                "title": "Hermetic Claude canary unit",
                "summary": "Synthetic knowledge unit for canary matrix.",
                "keywords": ["claude", "canary"],
                "confidence": 0.95,
                "domain": "general",
            }
        ]

    ingest.summarize = fake_summarize
    ingest.ollama_embed = fake_embed
    ingest.distill = fake_distill


def enable_incremental(boundary: IsolationBoundary) -> None:
    path = boundary.layout["user_config"]
    text = path.read_text(encoding="utf-8")
    text = text.replace("enabled = false", "enabled = true", 1)
    path.write_text(text, encoding="utf-8")


def run_coordinator(
    boundary: IsolationBoundary,
    source: Path,
    *,
    chunk_size: int = 2,
    overlap: int = 0,
) -> dict[str, Any]:
    install_fake_providers()
    enable_incremental(boundary)
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary,
        source,
        enabled=True,
        chunk_size=chunk_size,
        overlap=overlap,
    ).run()
    return {
        "outcome": result.outcome,
        "mode": result.mode,
        "counters": result.counters.as_dict(),
        "reused_artifacts": result.reused_artifacts,
    }


def run_hermetic_matrix(
    boundary: IsolationBoundary,
    source: Path,
) -> dict[str, Any]:
    """Exercise baseline, unchanged replay, and append under isolation."""
    install_fake_providers()
    enable_incremental(boundary)
    first = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=2, overlap=0
    ).run()
    second = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=2, overlap=0
    ).run()
    with source.open("ab") as handle:
        handle.write(
            json.dumps(
                {
                    "type": "user",
                    "sessionId": "sess-claude-canary",
                    "uuid": "rec-append",
                    "cwd": "/tmp/canary",
                    "isSidechain": False,
                    "timestamp": "2026-09-18T00:01:00Z",
                    "message": {
                        "role": "user",
                        "content": "canary-message-append",
                    },
                },
                sort_keys=True,
            ).encode()
            + b"\n"
        )
    third = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=2, overlap=0
    ).run()
    return {
        "first_outcome": first.outcome,
        "second_outcome": second.outcome,
        "third_outcome": third.outcome,
        "third_mode": third.mode,
        "append_summarize": third.counters.summarize,
        "append_reused": third.reused_artifacts,
    }


def _evidence_key_allowed(key: str, schema: frozenset[str]) -> bool:
    if key not in schema:
        return False
    upper = key.upper()
    if any(marker in upper for marker in _CREDENTIAL_MARKERS):
        return False
    return True


def _validate_evidence_string(value: str, *, label: str) -> str:
    if "\n" in value or "\r" in value or "\x00" in value:
        raise IsolationViolation(f"{label} contains disallowed content")
    if len(value) > _EVIDENCE_STRING_MAX:
        raise IsolationViolation(f"{label} exceeds evidence string limit")
    upper = value.upper()
    if any(marker in upper for marker in _CREDENTIAL_MARKERS):
        raise IsolationViolation(f"{label} contains credential-like value")
    if "canary-message" in value:
        raise IsolationViolation(f"{label} contains transcript-like content")
    return value


def _validate_evidence_value(
    value: Any,
    *,
    label: str,
    schema: frozenset[str] | None = None,
) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value < 0:
            raise IsolationViolation(f"{label} must be non-negative")
        return value
    if isinstance(value, str):
        return _validate_evidence_string(value, label=label)
    if isinstance(value, dict):
        if schema is None:
            raise IsolationViolation(f"{label} schema missing")
        unknown = set(value) - schema
        if unknown:
            names = ", ".join(sorted(unknown))
            raise IsolationViolation(f"{label} contains unknown keys: {names}")
        return {
            key: _validate_evidence_value(
                item,
                label=f"{label}.{key}",
                schema=_EVIDENCE_NESTED_SCHEMA.get(key),
            )
            for key, item in value.items()
            if _evidence_key_allowed(key, schema)
        }
    raise IsolationViolation(f"{label} has unsupported evidence type")


def _validate_evidence_section(name: str, section: Any) -> dict[str, Any]:
    schema = _EVIDENCE_SECTION_SCHEMA.get(name)
    if schema is None:
        raise IsolationViolation(f"unknown evidence section: {name}")
    if not isinstance(section, dict):
        raise IsolationViolation(f"evidence section {name} must be a mapping")
    unknown = set(section) - schema
    if unknown:
        names = ", ".join(sorted(unknown))
        raise IsolationViolation(f"evidence section {name} has unknown keys: {names}")
    validated: dict[str, Any] = {}
    for key, value in section.items():
        if not _evidence_key_allowed(key, schema):
            raise IsolationViolation(f"evidence section {name} rejects key: {key}")
        nested_schema = _EVIDENCE_NESTED_SCHEMA.get(key)
        validated[key] = _validate_evidence_value(
            value,
            label=f"{name}.{key}",
            schema=nested_schema,
        )
    return validated


def assemble_evidence(**sections: Any) -> dict[str, Any]:
    """Return content-free evidence with a closed typed section allowlist."""
    unknown = set(sections) - EVIDENCE_SECTION_ALLOWLIST
    if unknown:
        names = ", ".join(sorted(unknown))
        raise IsolationViolation(f"unknown evidence sections: {names}")
    validated = {
        name: _validate_evidence_section(name, section)
        for name, section in sections.items()
    }
    payload = {"mode": CANARY_MODE, "sections": validated}
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["evidence_digest"] = digest
    return payload


def worker_env(
    root: Path,
    token: str,
    *,
    parent_home: Path | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    env = scrub_credentials(
        sanitized_worker_env(
            root,
            token,
            forbidden_roots=known_production_roots(
                home=parent_home or Path.home()
            ),
        )
    )
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
    env["CONVMEM_CLAUDE_CANARY_MODE"] = CANARY_MODE
    if extra:
        env.update(extra)
    return env


def run_worker(
    command: str,
    *,
    root: Path,
    token: str,
    source: Path | None = None,
    extra_env: dict[str, str] | None = None,
    gate0_digest: str | None = None,
) -> subprocess.CompletedProcess[str]:
    child_env = dict(extra_env or {})
    if command != "gate0":
        digest = gate0_digest or child_env.get(GATE0_DIGEST_ENV, "")
        if not digest:
            gate = run_worker("gate0", root=root, token=token, extra_env=extra_env)
            if gate.returncode != 0:
                return gate
            digest = bind_gate0(json.loads(gate.stdout)).digest
        child_env[GATE0_DIGEST_ENV] = digest
    worker = Path(__file__).resolve().parent / "tests" / "claude_incremental_canary_worker.py"
    args = [sys.executable, "-I", str(worker), command]
    if source is not None:
        args.append(str(source))
    return subprocess.run(
        args,
        cwd=root,
        env=worker_env(root, token, extra=child_env),
        close_fds=True,
        start_new_session=True,
        capture_output=True,
        text=True,
        check=False,
    )


__all__ = [
    "CANARY_MODE",
    "CRASH_EXIT",
    "DURABLE_TRANSITIONS",
    "EVIDENCE_SECTION_ALLOWLIST",
    "GATE0_DIGEST_ENV",
    "_CAPTURE_TRANSITIONS",
    "FrozenSourceSpec",
    "Gate0ProbeHooks",
    "Gate0Result",
    "PRODUCTION_ROOTS",
    "SourceDescriptor",
    "SourceIdentityBinding",
    "assemble_evidence",
    "assert_transition_coverage",
    "bind_frozen_source",
    "bind_gate0",
    "capture_source",
    "derive_snapshot_destination",
    "enable_incremental",
    "gate0",
    "gate0_watcher_probe",
    "_hermetic_gate0_hooks",
    "install_fake_providers",
    "prepare_fixture_env",
    "revalidate_source_identity",
    "require_bound_gate0",
    "run_coordinator",
    "run_hermetic_matrix",
    "run_worker",
    "scrub_credentials",
    "validate_frozen_source",
    "validate_source_alias",
    "worker_env",
]
