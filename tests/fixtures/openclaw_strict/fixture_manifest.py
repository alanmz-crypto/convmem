"""Test-only fixture-manifest schema and machinery.

Complete five-component *source* manifests with positive source-component
hashes remain future-step red at M2 while future production members are
absent (Kiro ruling). Membership definitions and independent walkers live in
component_inventory / case58_oracle.
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


class ManifestNotAvailable(Exception):
    """Complete fixture manifest with component digests requires T0b."""


def mode_octal(path: Path) -> str:
    return f"{path.stat().st_mode & 0o7777:04o}"


def sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def inventory_fixture_artifacts(fixture_tree: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in sorted(fixture_tree.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "fixture-manifest.json":
            continue
        if path.suffix == ".pyc" or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(fixture_tree).as_posix()
        entries.append(
            {
                "mode": mode_octal(path),
                "path": f"tests/fixtures/openclaw_strict/{rel}",
                "sha256": sha256_file(path),
            }
        )
    entries.sort(key=lambda e: e["path"])
    return entries


def compute_manifest_payload_sha256(manifest: dict[str, Any]) -> str:
    body = {k: manifest[k] for k in REQUIRED_KEYS if k != "manifest_payload_sha256"}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
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


def emit_complete_manifest(*_args, **_kwargs) -> dict[str, Any]:
    """Fail-closed: positive five-component source hashes need real T1–T3 files."""
    raise ManifestNotAvailable(
        "complete five-component source manifest with positive source-component "
        "hashes remains future-step red at M2 while future production members are absent"
    )


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
