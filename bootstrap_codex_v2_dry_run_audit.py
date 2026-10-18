"""Dry-run audit counters and filesystem oracle for Codex bootstrap v2 (T1)."""

from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

AUDIT_ENV = "CONVMEM_BOOTSTRAP_V2_DRY_RUN_AUDIT"


def audit_active() -> bool:
    return os.environ.get(AUDIT_ENV, "").strip() in {"1", "true", "yes"}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    out: dict[str, str] = {}
    if root.is_file():
        return {".": _sha256_file(root)}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(root))
            out[rel] = _sha256_file(path)
    return out


def mutation_surface(cfg: dict, state_root: Path) -> dict[str, Path]:
    index = cfg["index"]
    chroma = Path(index["chroma_dir"])
    data_root = chroma.parent
    return {
        "state_root": state_root,
        "chroma": chroma,
        "processed": Path(index["processed_log"]),
        "export": Path(index["units_export"]),
        "locks": data_root / "locks",
        "incremental_state_parent": state_root,
    }


def snapshot_surface(cfg: dict, state_root: Path) -> dict[str, dict[str, str]]:
    surfaces = mutation_surface(cfg, state_root)
    return {name: snapshot_tree(path) for name, path in surfaces.items()}




def _surface_roots(cfg: dict, state_root: Path) -> list[Path]:
    return [path.resolve() for path in mutation_surface(cfg, state_root).values()]


def _path_touches_surface(candidate: Path, roots: list[Path]) -> bool:
    try:
        resolved = candidate.resolve()
    except OSError:
        return False
    for root in roots:
        if resolved == root or root in resolved.parents or resolved in root.parents:
            return True
    return False

@dataclass
class DryRunAudit:
    provider_permit_attempts: int = 0
    coordinator_constructions: int = 0
    journal_constructions: int = 0
    mkdir_attempts: int = 0
    before: dict[str, dict[str, str]] = field(default_factory=dict)
    after: dict[str, dict[str, str]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_permit_attempts": self.provider_permit_attempts,
            "coordinator_constructions": self.coordinator_constructions,
            "journal_constructions": self.journal_constructions,
            "mkdir_attempts": self.mkdir_attempts,
            "surface_unchanged": self.before == self.after,
        }


@contextmanager
def audited_dry_run(cfg: dict, state_root: Path):
    audit = DryRunAudit()
    audit.before = snapshot_surface(cfg, state_root)
    import bootstrap_safety
    import incremental_jsonl
    import llm

    real_permit = llm._permit_provider_http_attempt
    real_coord = incremental_jsonl.IncrementalJsonlCoordinator.__init__
    real_journal = bootstrap_safety.BootstrapOperationJournal.__init__

    def counting_permit(*args, **kwargs):
        audit.provider_permit_attempts += 1
        return real_permit(*args, **kwargs)

    def block_coordinator(self, *args, **kwargs):
        audit.coordinator_constructions += 1
        raise RuntimeError("coordinator_construction_forbidden_in_dry_run")

    def block_journal(self, *args, **kwargs):
        audit.journal_constructions += 1
        raise RuntimeError("journal_construction_forbidden_in_dry_run")

    roots = _surface_roots(cfg, state_root)
    real_mkdir = Path.mkdir

    def guarded_mkdir(self, mode=0o777, parents=False, exist_ok=False):
        if _path_touches_surface(self, roots):
            audit.mkdir_attempts += 1
            raise RuntimeError("mkdir_forbidden_in_dry_run")
        return real_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)

    llm._permit_provider_http_attempt = counting_permit
    Path.mkdir = guarded_mkdir
    incremental_jsonl.IncrementalJsonlCoordinator.__init__ = block_coordinator
    bootstrap_safety.BootstrapOperationJournal.__init__ = block_journal
    try:
        yield audit
    finally:
        llm._permit_provider_http_attempt = real_permit
        Path.mkdir = real_mkdir
        incremental_jsonl.IncrementalJsonlCoordinator.__init__ = real_coord
        bootstrap_safety.BootstrapOperationJournal.__init__ = real_journal
        audit.after = snapshot_surface(cfg, state_root)


def run_audited(callable_: Callable[[], dict[str, Any]], *, cfg: dict, state_root: Path) -> dict[str, Any]:
    with audited_dry_run(cfg, state_root) as audit:
        packet = callable_()
    packet["dry_run_audit"] = audit.as_dict()
    if not audit.before == audit.after:
        raise RuntimeError("dry_run_mutated_surface")
    if audit.provider_permit_attempts:
        raise RuntimeError("dry_run_provider_permit_attempted")
    if audit.coordinator_constructions or audit.journal_constructions or audit.mkdir_attempts:
        raise RuntimeError("dry_run_forbidden_construction")
    return packet
