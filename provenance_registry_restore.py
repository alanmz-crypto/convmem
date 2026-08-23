"""Durable provenance-registry validation for complete-data-v3 recovery (T1).

Separate from capture-evidence validation. Validators classify only; they never
repair. Missing or partial registry authority fails closed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from complete_data_restore import (
    EVIDENCE_FILENAME,
    OUTCOME_BLOCKED,
    OUTCOME_VALID,
    _canonical_json_hash,
    _HEX64,
    _sha256_bytes,
    _sha256_file,
)

REGISTRY_MANIFEST_SCHEMA = "convmem/provenance-registry-manifest-v1"
REGISTRY_SELECTOR_SCHEMA = "convmem/provenance-selector-v1"
PROVENANCE_DIR = "provenance"
SELECTOR_REL = "provenance/selector.json"
GENERATIONS_DIR = "provenance/generations"

OUTCOME_QUARANTINED = "QUARANTINED"


@dataclass(frozen=True)
class ProvenanceTuple:
    """Exact binding tuple for a selected v3 recovery candidate."""

    generation_id: str
    manifest_commitment: str
    tree_commitment: str

    def as_dict(self) -> dict[str, str]:
        return {
            "generation_id": self.generation_id,
            "manifest_commitment": self.manifest_commitment,
            "tree_commitment": self.tree_commitment,
        }


@dataclass
class RegistryValidationResult:
    """Independent outcome of durable registry validation."""

    outcome: str
    detail: str = ""
    code: str = ""
    provenance_tuple: ProvenanceTuple | None = None
    manifest_path: str = ""
    checks: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.outcome == OUTCOME_VALID


def tree_commitment_excluded_relative_paths() -> frozenset[str]:
    return frozenset({EVIDENCE_FILENAME, SELECTOR_REL})


def _tree_commitment_excluded(root: Path, rel: str) -> bool:
    if rel in tree_commitment_excluded_relative_paths():
        return True
    # Manifest commits T_g and must not self-reference (Architecture §10).
    if rel.startswith("provenance/generations/") and rel.endswith("/manifest.json"):
        return True
    return False


def compute_tree_commitment(root: Path) -> str:
    """Canonical T_g over sorted (relative path, size, SHA-256) file entries."""
    root = root.expanduser().resolve()
    entries: list[tuple[str, int, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if _tree_commitment_excluded(root, rel):
            continue
        entries.append((rel, path.stat().st_size, _sha256_file(path)))
    payload = [{"path": p, "size": s, "sha256": h} for p, s, h in entries]
    return _canonical_json_hash(payload)


def _manifest_commitment(manifest_body: Mapping[str, Any]) -> str:
    body = {k: v for k, v in manifest_body.items() if k != "manifest_commitment"}
    return _canonical_json_hash(body)


def _read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    return data


def _generation_dir(root: Path, generation_id: str) -> Path:
    return root / GENERATIONS_DIR / generation_id


def _manifest_path(root: Path, generation_id: str) -> Path:
    return _generation_dir(root, generation_id) / "manifest.json"


def validate_provenance_registry(
    root: Path | str,
    *,
    expected_tree_commitment: str | None = None,
) -> RegistryValidationResult:
    """Validate immutable registry manifest/graph/history for a v3 candidate."""
    data_root = Path(root).expanduser().resolve()
    checks: list[dict[str, Any]] = []

    selector_path = data_root / SELECTOR_REL
    if not selector_path.is_file():
        return RegistryValidationResult(
            outcome=OUTCOME_BLOCKED,
            detail="provenance selector missing",
            code="BLOCKED_PROVENANCE_SELECTOR_MISSING",
            checks=checks,
        )

    try:
        selector = _read_json_object(selector_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return RegistryValidationResult(
            outcome=OUTCOME_QUARANTINED,
            detail=f"provenance selector unreadable: {exc}",
            code="QUARANTINED_PROVENANCE_SELECTOR_INVALID",
            checks=checks,
        )

    if selector.get("schema_version") != REGISTRY_SELECTOR_SCHEMA:
        return RegistryValidationResult(
            outcome=OUTCOME_QUARANTINED,
            detail="provenance selector schema mismatch",
            code="QUARANTINED_PROVENANCE_SELECTOR_SCHEMA",
            checks=checks,
        )

    generation_id = str(selector.get("generation_id") or "").strip()
    selector_manifest = str(selector.get("manifest_commitment") or "").strip()
    selector_tree = str(selector.get("tree_commitment") or "").strip()
    if not generation_id or not _HEX64.match(selector_manifest) or not _HEX64.match(selector_tree):
        return RegistryValidationResult(
            outcome=OUTCOME_QUARANTINED,
            detail="provenance selector missing P_g/M_g/T_g bindings",
            code="QUARANTINED_PROVENANCE_SELECTOR_INCOMPLETE",
            checks=checks,
        )

    gen_dir = _generation_dir(data_root, generation_id)
    if not gen_dir.is_dir():
        return RegistryValidationResult(
            outcome=OUTCOME_BLOCKED,
            detail=f"registry generation directory missing: {generation_id}",
            code="BLOCKED_PROVENANCE_GENERATION_MISSING",
            checks=checks,
        )

    manifest_path = _manifest_path(data_root, generation_id)
    if not manifest_path.is_file():
        return RegistryValidationResult(
            outcome=OUTCOME_BLOCKED,
            detail="registry manifest missing",
            code="BLOCKED_PROVENANCE_MANIFEST_MISSING",
            checks=checks,
        )

    try:
        manifest = _read_json_object(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return RegistryValidationResult(
            outcome=OUTCOME_QUARANTINED,
            detail=f"registry manifest unreadable: {exc}",
            code="QUARANTINED_PROVENANCE_MANIFEST_INVALID",
            checks=checks,
        )

    if manifest.get("schema_version") != REGISTRY_MANIFEST_SCHEMA:
        return RegistryValidationResult(
            outcome=OUTCOME_QUARANTINED,
            detail="registry manifest schema mismatch",
            code="QUARANTINED_PROVENANCE_MANIFEST_SCHEMA",
            checks=checks,
        )

    manifest_generation = str(manifest.get("generation_id") or "").strip()
    manifest_tree = str(manifest.get("tree_commitment") or "").strip()
    manifest_commitment = str(manifest.get("manifest_commitment") or "").strip()
    if manifest_generation != generation_id:
        return RegistryValidationResult(
            outcome=OUTCOME_QUARANTINED,
            detail="registry manifest generation_id mismatch",
            code="QUARANTINED_PROVENANCE_GENERATION_MISMATCH",
            checks=checks,
        )

    recomputed_manifest = _manifest_commitment(manifest)
    if recomputed_manifest != manifest_commitment:
        return RegistryValidationResult(
            outcome=OUTCOME_QUARANTINED,
            detail="registry manifest commitment mismatch",
            code="QUARANTINED_PROVENANCE_MANIFEST_COMMITMENT",
            checks=checks,
        )

    if manifest_tree != selector_tree or manifest_commitment != selector_manifest:
        return RegistryValidationResult(
            outcome=OUTCOME_QUARANTINED,
            detail="selector/manifest binding mismatch",
            code="QUARANTINED_PROVENANCE_SELECTOR_BINDING",
            checks=checks,
        )

    computed_tree = compute_tree_commitment(data_root)
    checks.append({"check": "tree_commitment", "computed": computed_tree, "expected": manifest_tree})
    if computed_tree != manifest_tree:
        return RegistryValidationResult(
            outcome=OUTCOME_QUARANTINED,
            detail="tree commitment T_g mismatch",
            code="QUARANTINED_PROVENANCE_TREE_COMMITMENT",
            checks=checks,
        )

    if expected_tree_commitment is not None and computed_tree != expected_tree_commitment:
        return RegistryValidationResult(
            outcome=OUTCOME_QUARANTINED,
            detail="tree commitment does not match expected snapshot binding",
            code="QUARANTINED_PROVENANCE_TREE_EXPECTED",
            checks=checks,
        )

    object_digests = manifest.get("object_digests")
    if not isinstance(object_digests, dict) or not object_digests:
        return RegistryValidationResult(
            outcome=OUTCOME_BLOCKED,
            detail="registry manifest missing object_digests",
            code="BLOCKED_PROVENANCE_MANIFEST_OBJECTS",
            checks=checks,
        )

    for rel, expected_digest in sorted(object_digests.items()):
        rel_str = str(rel)
        if not _HEX64.match(str(expected_digest)):
            return RegistryValidationResult(
                outcome=OUTCOME_QUARANTINED,
                detail=f"invalid digest for {rel_str}",
                code="QUARANTINED_PROVENANCE_OBJECT_DIGEST",
                checks=checks,
            )
        obj_path = gen_dir / rel_str
        if not obj_path.is_file():
            return RegistryValidationResult(
                outcome=OUTCOME_BLOCKED,
                detail=f"registry object missing: {rel_str}",
                code="BLOCKED_PROVENANCE_OBJECT_MISSING",
                checks=checks,
            )
        actual = _sha256_file(obj_path)
        checks.append({"check": "object_digest", "path": rel_str, "ok": actual == expected_digest})
        if actual != expected_digest:
            return RegistryValidationResult(
                outcome=OUTCOME_QUARANTINED,
                detail=f"registry object digest mismatch: {rel_str}",
                code="QUARANTINED_PROVENANCE_OBJECT_MISMATCH",
                checks=checks,
            )

    graph_path = gen_dir / "graph.json"
    if not graph_path.is_file():
        return RegistryValidationResult(
            outcome=OUTCOME_BLOCKED,
            detail="registry graph missing",
            code="BLOCKED_PROVENANCE_GRAPH_MISSING",
            checks=checks,
        )
    graph_commitment = str(manifest.get("graph_commitment") or "").strip()
    actual_graph = _sha256_file(graph_path)
    if not _HEX64.match(graph_commitment) or actual_graph != graph_commitment:
        return RegistryValidationResult(
            outcome=OUTCOME_QUARANTINED,
            detail="registry graph commitment mismatch",
            code="QUARANTINED_PROVENANCE_GRAPH_COMMITMENT",
            checks=checks,
        )

    history_commitments = manifest.get("history_commitments")
    if not isinstance(history_commitments, dict):
        return RegistryValidationResult(
            outcome=OUTCOME_BLOCKED,
            detail="registry manifest missing history_commitments",
            code="BLOCKED_PROVENANCE_HISTORY_MISSING",
            checks=checks,
        )
    required_history = ("schema_registry", "policy_registry", "recipe_registry")
    history_dir = gen_dir / "history"
    for key in required_history:
        rel = f"history/{key}.json"
        expected = str(history_commitments.get(key) or "").strip()
        hist_path = gen_dir / rel
        if not hist_path.is_file():
            return RegistryValidationResult(
                outcome=OUTCOME_BLOCKED,
                detail=f"registry history missing: {key}",
                code="BLOCKED_PROVENANCE_HISTORY_FILE",
                checks=checks,
            )
        actual = _sha256_file(hist_path)
        checks.append({"check": "history", "name": key, "ok": actual == expected})
        if not _HEX64.match(expected) or actual != expected:
            return RegistryValidationResult(
                outcome=OUTCOME_QUARANTINED,
                detail=f"registry history commitment mismatch: {key}",
                code="QUARANTINED_PROVENANCE_HISTORY_COMMITMENT",
                checks=checks,
            )

    assertion_ids = manifest.get("assertion_ids")
    if not isinstance(assertion_ids, list):
        return RegistryValidationResult(
            outcome=OUTCOME_BLOCKED,
            detail="registry manifest missing assertion_ids",
            code="BLOCKED_PROVENANCE_ASSERTION_INDEX",
            checks=checks,
        )
    for assertion_id in assertion_ids:
        aid = str(assertion_id).strip()
        rel = f"assertions/{aid}.json"
        if rel not in object_digests:
            return RegistryValidationResult(
                outcome=OUTCOME_QUARANTINED,
                detail=f"assertion not listed in object_digests: {aid}",
                code="QUARANTINED_PROVENANCE_ASSERTION_INDEX",
                checks=checks,
            )

    provenance_tuple = ProvenanceTuple(
        generation_id=generation_id,
        manifest_commitment=manifest_commitment,
        tree_commitment=manifest_tree,
    )
    return RegistryValidationResult(
        outcome=OUTCOME_VALID,
        detail=(
            f"registry valid generation={generation_id} "
            f"M_g={manifest_commitment[:12]} T_g={manifest_tree[:12]}"
        ),
        provenance_tuple=provenance_tuple,
        manifest_path=str(manifest_path.relative_to(data_root)),
        checks=checks,
    )


def build_registry_fixture(
    root: Path,
    *,
    generation_id: str = "pg-fixture-001",
    assertion_ids: tuple[str, ...] = ("assert-fixture-001",),
) -> ProvenanceTuple:
    """Write a minimal valid v3 provenance registry fixture (tests only)."""
    root = root.expanduser().resolve()
    gen_dir = _generation_dir(root, generation_id)
    assertions_dir = gen_dir / "assertions"
    history_dir = gen_dir / "history"
    assertions_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)

    graph_body = {"schema_version": "convmem/provenance-graph-v1", "edges": []}
    graph_path = gen_dir / "graph.json"
    graph_path.write_text(json.dumps(graph_body, sort_keys=True), encoding="utf-8")
    graph_commitment = _sha256_file(graph_path)

    history_files = {
        "schema_registry": {"schema_version": "convmem/provenance-schema-history-v1", "entries": []},
        "policy_registry": {"schema_version": "convmem/provenance-policy-history-v1", "entries": []},
        "recipe_registry": {"schema_version": "convmem/provenance-recipe-history-v1", "entries": []},
    }
    history_commitments: dict[str, str] = {}
    object_digests: dict[str, str] = {"graph.json": graph_commitment}
    for name, body in history_files.items():
        rel = f"history/{name}.json"
        path = gen_dir / rel
        path.write_text(json.dumps(body, sort_keys=True), encoding="utf-8")
        digest = _sha256_file(path)
        history_commitments[name] = digest
        object_digests[rel] = digest

    for aid in assertion_ids:
        rel = f"assertions/{aid}.json"
        envelope = {
            "schema_version": "convmem/provenance-envelope-v1",
            "assertion_id": aid,
            "provenance_commitment": _sha256_bytes(json.dumps({"assertion_id": aid}, sort_keys=True).encode()),
        }
        path = gen_dir / rel
        path.write_text(json.dumps(envelope, sort_keys=True), encoding="utf-8")
        object_digests[rel] = _sha256_file(path)

    tree_commitment = compute_tree_commitment(root)
    manifest_body: dict[str, Any] = {
        "schema_version": REGISTRY_MANIFEST_SCHEMA,
        "generation_id": generation_id,
        "tree_commitment": tree_commitment,
        "object_digests": object_digests,
        "assertion_ids": list(assertion_ids),
        "graph_commitment": graph_commitment,
        "history_commitments": history_commitments,
    }
    manifest_body["manifest_commitment"] = _manifest_commitment(manifest_body)
    manifest_path = gen_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest_body, sort_keys=True, indent=2),
        encoding="utf-8",
    )

    selector = {
        "schema_version": REGISTRY_SELECTOR_SCHEMA,
        "generation_id": generation_id,
        "manifest_commitment": manifest_body["manifest_commitment"],
        "tree_commitment": tree_commitment,
    }
    selector_path = root / SELECTOR_REL
    selector_path.parent.mkdir(parents=True, exist_ok=True)
    selector_path.write_text(json.dumps(selector, sort_keys=True, indent=2), encoding="utf-8")

    return ProvenanceTuple(
        generation_id=generation_id,
        manifest_commitment=manifest_body["manifest_commitment"],
        tree_commitment=tree_commitment,
    )
