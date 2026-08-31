"""Fail-closed authority-content manifest for R2b v2 implementation identity."""

from __future__ import annotations

import ast
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from chroma_write_store import WRITER_GATE_PROTOCOL_VERSION

_IMPLEMENTATION_REVISION_PREFIX = "r2b-v2-authority-content:v1:"
ROOT = Path(__file__).resolve().parents[3]
SHADOW_INVENTORY = ROOT / "docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json"

# Explicit seeds: writer gate, coverage/proof/lease, minting, census, route entrypoints.
_AUTHORITY_CORE_SEEDS: tuple[str, ...] = (
    "chroma_write_store.py",
    "writer_census.py",
    "eval_corpus/r2b_v2/gate_policy.py",
    "eval_corpus/r2b_v2/coverage/inventory.py",
    "eval_corpus/r2b_v2/coverage/proof.py",
    "eval_corpus/r2b_v2/coverage/authority_manifest.py",
    "eval_corpus/r2b_v2/coverage_evidence.py",
    "eval_corpus/r2b_v2/lease.py",
    "eval_corpus/r2b_v2/lock_custodian.py",
    "eval_corpus/r2b_v2/_authority_vault.py",
    "eval_corpus/r2b_v2/_registry_mint.py",
    "eval_corpus/r2b_v2/authority_registry.py",
    "eval_corpus/r2b_v2/_authority_capability.py",
    "eval_corpus/r2b_v2/trusted.py",
    "eval_corpus/r2b_v2/contract.py",
    "eval_corpus/r2b_v2/authority_state.py",
)

_AUTHORITY_ROUTE_ENTRYPOINTS: tuple[str, ...] = (
    "watch.py",
    "refine.py",
    "convmem.py",
    "file_generation_pointer.py",
    "source_reconciler.py",
    "cg2_first_cutover.py",
    "file_generation_validate.py",
    "mixed_mode_control.py",
    "serving_index_repository.py",
    "cg2_rehearsal.py",
    "complete_data_restore.py",
    "source_purge.py",
    "exclude_cli.py",
    "propose_decision.py",
    "observe.py",
)

_BEHAVIOR_CONFIG_ARTIFACTS: tuple[str, ...] = (
    "docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json",
)


class AuthorityManifestError(RuntimeError):
    """Governed authority content could not be resolved fail-closed."""


def _repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def _hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_file_bytes(rel_path: str) -> bytes:
    path = ROOT / rel_path
    if not path.is_file():
        raise AuthorityManifestError(f"missing governed authority file: {rel_path}")
    return path.read_bytes()


def _module_name_for_path(rel_path: str) -> str:
    path = Path(rel_path)
    if path.name == "__init__.py":
        return ".".join(path.parent.parts)
    return path.with_suffix("").as_posix().replace("/", ".")


def _resolve_module_file(module: str) -> str | None:
    if not module or module.startswith("_"):
        return None
    dotted = module.split(".")
    candidates = [
        ROOT.joinpath(*dotted).with_suffix(".py"),
        ROOT.joinpath(*dotted, "__init__.py"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return _repo_relative(candidate)
    return None


def _resolve_relative_import(module: str, level: int, name: str | None) -> str | None:
    parts = module.split(".")
    if level > len(parts):
        raise AuthorityManifestError(
            f"unresolvable relative import in {module}: level={level} name={name}"
        )
    base = parts[: len(parts) - level]
    if name:
        return _resolve_module_file(".".join([*base, *name.split(".")]))
    if not base:
        return None
    return _resolve_module_file(".".join(base))


def _imports_from_source(rel_path: str, source: str) -> set[str]:
    module = _module_name_for_path(rel_path)
    tree = ast.parse(source, filename=rel_path)
    discovered: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = _resolve_module_file(alias.name)
                if resolved is not None:
                    discovered.add(resolved)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None and node.level:
                resolved = _resolve_relative_import(
                    module,
                    node.level,
                    node.names[0].name if len(node.names) == 1 else None,
                )
                if resolved is not None:
                    discovered.add(resolved)
                continue
            if node.level:
                resolved = _resolve_relative_import(module, node.level, node.module)
            else:
                resolved = _resolve_module_file(node.module or "")
            if resolved is not None:
                discovered.add(resolved)
    return discovered


def _dependency_closure(seed_paths: Iterable[str]) -> tuple[str, ...]:
    pending = list(dict.fromkeys(seed_paths))
    seen: set[str] = set()
    while pending:
        rel = pending.pop(0)
        if rel in seen:
            continue
        seen.add(rel)
        source = _read_file_bytes(rel).decode("utf-8", errors="replace")
        for imported in sorted(_imports_from_source(rel, source)):
            if imported not in seen:
                pending.append(imported)
    return tuple(sorted(seen))


def build_authority_content_manifest() -> dict[str, Any]:
    """Return inspectable governed content bindings for R2b writer authority."""
    seeds = (
        *_AUTHORITY_CORE_SEEDS,
        *_AUTHORITY_ROUTE_ENTRYPOINTS,
        *_BEHAVIOR_CONFIG_ARTIFACTS,
    )
    governed_files = _dependency_closure(seeds)
    entries = [
        {
            "path": rel,
            "content_digest": _hash_bytes(_read_file_bytes(rel)),
        }
        for rel in governed_files
    ]
    return {
        "manifest_class": "r2b_v2_authority_content",
        "manifest_version": 1,
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "seed_modules": list(seeds),
        "governed_files": entries,
    }


def clear_authority_manifest_cache() -> None:
    """Test seam: drop cached authority identity."""
    _cached_implementation_revision.cache_clear()


@lru_cache(maxsize=1)
def _cached_implementation_revision() -> str:
    manifest = build_authority_content_manifest()
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(
        f"{_IMPLEMENTATION_REVISION_PREFIX}{canonical}".encode("utf-8")
    ).hexdigest()
    return digest[:40]


def compute_implementation_revision() -> str:
    """Return authority-bound implementation identity derived from governed source content."""
    return _cached_implementation_revision()
