"""Test-only fixture-manifest schema and machinery.

Architecture §6.5.8 (parent cd9d2698):
- ``artifacts`` inventories every test helper/scenario/schema/specimen under
  ``tests/fixtures/openclaw_strict``, excluding only the fixture manifest and
  generated run outputs.
- ``source_tree_sha256`` hashes the exact tracked source export with the same
  exclusions; the exported inventory is returned alongside the manifest.
- ``components`` remain the five §6.5.9 digests (independent of artifact/source
  inventories). Two independent inventory/hash verification paths are required.
- Generated ``fixture-manifest.json`` is test-owned output only and must not
  mutate the repository.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from component_inventory import (  # noqa: F401 — re-export for packet contract
    FUTURE_PRODUCTION_MEMBERS,
    InventoryError,
    assert_omitted_canonical_json_mutant_fails,
    assert_present_member_mutation_changes_digest,
    build_component_inventories,
    component_tree_digest,
    missing_future_production_members,
    reference_walk_component,
    reject_supplied_inventory_extra_entry,
    reject_symlink_member,
    source_component_digest_available,
    unrelated_on_disk_file_leaves_digest_unchanged,
)
from constants import (
    CODE_BASELINE_SHA,
    EXPECTED_TEST_RUNTIME_TREE_SHA256,
    GENERATED_EVIDENCE_FIXTURE_RELS,
    GENERATED_EVIDENCE_SOURCE_RELS,
    SEMANTIC_PARENT_SHA,
)

SCHEMA_ID = "convmem.strict-fixture-manifest.v1"
ARTIFACT_KIND = "protocol_fixture"

REQUIRED_KEYS = (
    "schema",
    "artifact_kind",
    "plan_sha",
    "code_baseline_sha",
    "source_tree_sha256",
    "test_runtime_tree_sha256",
    "components",
    "artifacts",
    "manifest_payload_sha256",
)

COMPONENT_NAMES = (
    "builder",
    "strict_server",
    "supervisor",
    "controller",
    "plugin",
)

# Generated run outputs excluded from inventories by exact relative path only.
# Never use a global basename exclusion (would hide a tracked file elsewhere).
_EXCLUDED_FIXTURE_RELS = GENERATED_EVIDENCE_FIXTURE_RELS
_EXCLUDED_SOURCE_RELS = GENERATED_EVIDENCE_SOURCE_RELS


class ManifestNotAvailable(Exception):
    """Complete fixture manifest with component digests is unavailable."""


def mode_octal(path: Path) -> str:
    return f"{path.stat().st_mode & 0o7777:04o}"


def sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _is_excluded_fixture_rel(rel: str) -> bool:
    """Exclude only exact generated relative paths under the fixture tree."""

    return rel in _EXCLUDED_FIXTURE_RELS


def _is_excluded_source_rel(rel: str) -> bool:
    """Exclude only exact generated relative paths under the source export."""

    return rel in _EXCLUDED_SOURCE_RELS


def inventory_fixture_artifacts(fixture_tree: Path) -> list[dict[str, str]]:
    """Inventory every helper/scenario/schema/specimen under the fixture tree.

    Excludes only exact generated relative paths (fixture manifest / suite results).
    """

    root = fixture_tree.resolve()
    if not root.is_dir():
        raise ManifestNotAvailable(f"fixture_tree_missing:{root}")
    entries: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"fixture_symlink_forbidden:{path.relative_to(root).as_posix()}")
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if _is_excluded_fixture_rel(rel):
            continue
        entries.append(
            {
                "mode": mode_octal(path),
                "path": f"tests/fixtures/openclaw_strict/{rel}",
                "sha256": sha256_file(path),
            }
        )
    entries.sort(key=lambda e: e["path"])
    return entries


def inventory_source_export(source_root: Path) -> list[dict[str, str]]:
    """Exact tracked source-export inventory (exact generated paths excluded).

    This is the parent source-tree path — not a component-membership substitute.
    """

    root = source_root.resolve()
    if not root.is_dir():
        raise ManifestNotAvailable(f"source_root_missing:{root}")
    entries: list[dict[str, str]] = []
    for dirpath, dirnames, filenames in __import__("os").walk(root, followlinks=False):
        # Do not invent broad directory exclusions; only skip VCS metadata.
        dirnames[:] = [d for d in dirnames if d != ".git"]
        base = Path(dirpath)
        for name in list(dirnames) + list(filenames):
            p = base / name
            if p.is_symlink():
                raise ValueError(
                    f"source_symlink_forbidden:{p.relative_to(root).as_posix()}"
                )
        for name in filenames:
            p = base / name
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if _is_excluded_source_rel(rel):
                continue
            entries.append(
                {
                    "mode": mode_octal(p),
                    "path": rel,
                    "sha256": sha256_file(p),
                }
            )
    entries.sort(key=lambda e: e["path"])
    return entries


def hash_inventory_entries(entries: list[dict[str, str]]) -> str:
    """Hash of a sorted ``{path,mode,sha256}`` inventory array."""

    payload = json.dumps(
        entries, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def independent_fixture_artifact_digest(fixture_tree: Path) -> tuple[list[dict[str, str]], str]:
    """Second verification path — does not call ``inventory_fixture_artifacts``."""

    import case58_oracle as oracle

    entries = oracle.reference_fixture_artifact_walk(fixture_tree)
    return entries, oracle.independent_tree_digest(entries)


def independent_source_tree_digest(source_root: Path) -> tuple[list[dict[str, str]], str]:
    """Second verification path — does not call ``inventory_source_export``."""

    import case58_oracle as oracle

    entries = oracle.reference_source_export_walk(source_root)
    return entries, oracle.independent_tree_digest(entries)


def compute_manifest_payload_sha256(manifest: dict[str, Any]) -> str:
    body = {k: manifest[k] for k in REQUIRED_KEYS if k != "manifest_payload_sha256"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def validate_manifest_structure(manifest: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in manifest]
    extra = [k for k in manifest if k not in REQUIRED_KEYS]
    if missing or extra:
        raise ValueError(f"manifest_keys invalid missing={missing} extra={extra}")
    if manifest["schema"] != SCHEMA_ID:
        raise ValueError("schema")
    if manifest["artifact_kind"] != ARTIFACT_KIND:
        raise ValueError("artifact_kind")
    comps = manifest["components"]
    if not isinstance(comps, list) or [c.get("name") for c in comps] != list(COMPONENT_NAMES):
        raise ValueError("components")
    for c in comps:
        digest = c.get("sha256", "")
        if not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
            raise ValueError("component_digest")
        if digest == "sha256:" + ("0" * 64):
            raise ValueError("placeholder_component_digest_forbidden")
    expected = compute_manifest_payload_sha256(manifest)
    if manifest["manifest_payload_sha256"] != expected:
        raise ValueError("manifest_payload_sha256")


def emit_complete_manifest(
    root: Path | None = None,
    *,
    source_root: Path | None = None,
    fixture_tree: Path | None = None,
    plan_sha: str = SEMANTIC_PARENT_SHA,
    code_baseline_sha: str = CODE_BASELINE_SHA,
    test_runtime_tree_sha256: str = EXPECTED_TEST_RUNTIME_TREE_SHA256,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Emit the complete manifest and return ``(manifest, source_export_inventory)``.

    Does not write ``fixture-manifest.json`` into the repository. Callers that
    materialize the JSON for a disposable fixture root own that output.
    """

    repo = Path(".") if root is None else Path(root)
    src = Path(source_root) if source_root is not None else repo
    fixtures = (
        Path(fixture_tree)
        if fixture_tree is not None
        else (src / "tests" / "fixtures" / "openclaw_strict")
    )

    missing = missing_future_production_members(repo)
    if missing:
        raise ManifestNotAvailable(f"future_production_members_absent:{missing}")

    components: list[dict[str, str]] = []
    for name in COMPONENT_NAMES:
        if not source_component_digest_available(repo, name):
            raise ManifestNotAvailable(f"component_unavailable:{name}")
        entries = reference_walk_component(repo, name)
        components.append({"name": name, "sha256": component_tree_digest(entries)})

    artifacts = inventory_fixture_artifacts(fixtures)
    source_inventory = inventory_source_export(src)
    source_tree_sha256 = hash_inventory_entries(source_inventory)

    manifest: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "artifact_kind": ARTIFACT_KIND,
        "plan_sha": plan_sha,
        "code_baseline_sha": code_baseline_sha,
        "source_tree_sha256": source_tree_sha256,
        "test_runtime_tree_sha256": test_runtime_tree_sha256,
        "components": components,
        "artifacts": artifacts,
        "manifest_payload_sha256": "sha256:" + ("0" * 64),
    }
    manifest["manifest_payload_sha256"] = compute_manifest_payload_sha256(manifest)
    validate_manifest_structure(manifest)
    return manifest, source_inventory


SCHEMA_DOCUMENT = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "convmem.strict-fixture-manifest.v1",
    "title": "ConvMem strict fixture manifest (test-only)",
    "type": "object",
    "additionalProperties": False,
    "required": list(REQUIRED_KEYS),
    "properties": {
        "schema": {"const": SCHEMA_ID},
        "artifact_kind": {"const": ARTIFACT_KIND},
        "plan_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
        "code_baseline_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
        "source_tree_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
        "test_runtime_tree_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
        "components": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "sha256"],
                "properties": {
                    "name": {"enum": list(COMPONENT_NAMES)},
                    "sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                },
            },
        },
        "artifacts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["path", "mode", "sha256"],
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "mode": {"type": "string", "pattern": "^[0-7]{4}$"},
                    "sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
                },
            },
        },
        "manifest_payload_sha256": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"},
    },
}
