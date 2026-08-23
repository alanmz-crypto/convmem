"""Durable provenance-registry validation for complete-data-v3 recovery (T1).

Separate from capture-evidence validation. Validators classify only; they never
repair. Missing or partial registry authority fails closed.
"""

from __future__ import annotations

import json
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


@dataclass
class _RegistryValidationContext:
    data_root: Path
    checks: list[dict[str, Any]]
    expected_tree_commitment: str | None
    generation_id: str = ""
    manifest: dict[str, Any] | None = None
    selector_manifest: str = ""
    selector_tree: str = ""


def tree_commitment_excluded_relative_paths() -> frozenset[str]:
    return frozenset(
        {
            EVIDENCE_FILENAME,
            SELECTOR_REL,
            # Projection qualification sidecars (T2): carry M_g/binding without
            # entering the sealed tree commitment (avoids T_g↔M_g cycles).
            "chroma/projection_binding.json",
            "knowledge_units.projection.json",
        }
    )


def _tree_commitment_excluded(rel: str) -> bool:
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
        if _tree_commitment_excluded(rel):
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


def _blocked(detail: str, code: str, checks: list[dict[str, Any]]) -> RegistryValidationResult:
    return RegistryValidationResult(
        outcome=OUTCOME_BLOCKED,
        detail=detail,
        code=code,
        checks=checks,
    )


def _quarantined(detail: str, code: str, checks: list[dict[str, Any]]) -> RegistryValidationResult:
    return RegistryValidationResult(
        outcome=OUTCOME_QUARANTINED,
        detail=detail,
        code=code,
        checks=checks,
    )


def _load_selector(ctx: _RegistryValidationContext) -> RegistryValidationResult | None:
    selector_path = ctx.data_root / SELECTOR_REL
    if not selector_path.is_file():
        return _blocked(
            "provenance selector missing",
            "BLOCKED_PROVENANCE_SELECTOR_MISSING",
            ctx.checks,
        )
    try:
        selector = _read_json_object(selector_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return _quarantined(
            f"provenance selector unreadable: {exc}",
            "QUARANTINED_PROVENANCE_SELECTOR_INVALID",
            ctx.checks,
        )
    if selector.get("schema_version") != REGISTRY_SELECTOR_SCHEMA:
        return _quarantined(
            "provenance selector schema mismatch",
            "QUARANTINED_PROVENANCE_SELECTOR_SCHEMA",
            ctx.checks,
        )
    generation_id = str(selector.get("generation_id") or "").strip()
    selector_manifest = str(selector.get("manifest_commitment") or "").strip()
    selector_tree = str(selector.get("tree_commitment") or "").strip()
    if (
        not generation_id
        or not _HEX64.match(selector_manifest)
        or not _HEX64.match(selector_tree)
    ):
        return _quarantined(
            "provenance selector missing P_g/M_g/T_g bindings",
            "QUARANTINED_PROVENANCE_SELECTOR_INCOMPLETE",
            ctx.checks,
        )
    ctx.generation_id = generation_id
    ctx.selector_manifest = selector_manifest
    ctx.selector_tree = selector_tree
    return None


def _load_generation_manifest(ctx: _RegistryValidationContext) -> RegistryValidationResult | None:
    gen_dir = _generation_dir(ctx.data_root, ctx.generation_id)
    if not gen_dir.is_dir():
        return _blocked(
            f"registry generation directory missing: {ctx.generation_id}",
            "BLOCKED_PROVENANCE_GENERATION_MISSING",
            ctx.checks,
        )
    manifest_path = _manifest_path(ctx.data_root, ctx.generation_id)
    if not manifest_path.is_file():
        return _blocked(
            "registry manifest missing",
            "BLOCKED_PROVENANCE_MANIFEST_MISSING",
            ctx.checks,
        )
    try:
        manifest = _read_json_object(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return _quarantined(
            f"registry manifest unreadable: {exc}",
            "QUARANTINED_PROVENANCE_MANIFEST_INVALID",
            ctx.checks,
        )
    ctx.manifest = manifest
    return None


def _validate_manifest_header(ctx: _RegistryValidationContext) -> RegistryValidationResult | None:
    assert ctx.manifest is not None
    manifest = ctx.manifest
    if manifest.get("schema_version") != REGISTRY_MANIFEST_SCHEMA:
        return _quarantined(
            "registry manifest schema mismatch",
            "QUARANTINED_PROVENANCE_MANIFEST_SCHEMA",
            ctx.checks,
        )
    manifest_generation = str(manifest.get("generation_id") or "").strip()
    if manifest_generation != ctx.generation_id:
        return _quarantined(
            "registry manifest generation_id mismatch",
            "QUARANTINED_PROVENANCE_GENERATION_MISMATCH",
            ctx.checks,
        )
    manifest_commitment = str(manifest.get("manifest_commitment") or "").strip()
    if _manifest_commitment(manifest) != manifest_commitment:
        return _quarantined(
            "registry manifest commitment mismatch",
            "QUARANTINED_PROVENANCE_MANIFEST_COMMITMENT",
            ctx.checks,
        )
    manifest_tree = str(manifest.get("tree_commitment") or "").strip()
    if manifest_tree != ctx.selector_tree or manifest_commitment != ctx.selector_manifest:
        return _quarantined(
            "selector/manifest binding mismatch",
            "QUARANTINED_PROVENANCE_SELECTOR_BINDING",
            ctx.checks,
        )
    return None


def _validate_tree_commitment(ctx: _RegistryValidationContext) -> RegistryValidationResult | None:
    assert ctx.manifest is not None
    manifest_tree = str(ctx.manifest.get("tree_commitment") or "").strip()
    computed_tree = compute_tree_commitment(ctx.data_root)
    ctx.checks.append(
        {
            "check": "tree_commitment",
            "computed": computed_tree,
            "expected": manifest_tree,
        }
    )
    if computed_tree != manifest_tree:
        return _quarantined(
            "tree commitment T_g mismatch",
            "QUARANTINED_PROVENANCE_TREE_COMMITMENT",
            ctx.checks,
        )
    if (
        ctx.expected_tree_commitment is not None
        and computed_tree != ctx.expected_tree_commitment
    ):
        return _quarantined(
            "tree commitment does not match expected snapshot binding",
            "QUARANTINED_PROVENANCE_TREE_EXPECTED",
            ctx.checks,
        )
    return None


def _validate_object_digests(ctx: _RegistryValidationContext) -> RegistryValidationResult | None:
    assert ctx.manifest is not None
    gen_dir = _generation_dir(ctx.data_root, ctx.generation_id)
    object_digests = ctx.manifest.get("object_digests")
    if not isinstance(object_digests, dict) or not object_digests:
        return _blocked(
            "registry manifest missing object_digests",
            "BLOCKED_PROVENANCE_MANIFEST_OBJECTS",
            ctx.checks,
        )
    for rel, expected_digest in sorted(object_digests.items()):
        rel_str = str(rel)
        if not _HEX64.match(str(expected_digest)):
            return _quarantined(
                f"invalid digest for {rel_str}",
                "QUARANTINED_PROVENANCE_OBJECT_DIGEST",
                ctx.checks,
            )
        obj_path = gen_dir / rel_str
        if not obj_path.is_file():
            return _blocked(
                f"registry object missing: {rel_str}",
                "BLOCKED_PROVENANCE_OBJECT_MISSING",
                ctx.checks,
            )
        actual = _sha256_file(obj_path)
        ctx.checks.append(
            {"check": "object_digest", "path": rel_str, "ok": actual == expected_digest}
        )
        if actual != expected_digest:
            return _quarantined(
                f"registry object digest mismatch: {rel_str}",
                "QUARANTINED_PROVENANCE_OBJECT_MISMATCH",
                ctx.checks,
            )
    return None


def _validate_graph_and_history(ctx: _RegistryValidationContext) -> RegistryValidationResult | None:
    assert ctx.manifest is not None
    gen_dir = _generation_dir(ctx.data_root, ctx.generation_id)
    graph_path = gen_dir / "graph.json"
    if not graph_path.is_file():
        return _blocked(
            "registry graph missing",
            "BLOCKED_PROVENANCE_GRAPH_MISSING",
            ctx.checks,
        )
    graph_commitment = str(ctx.manifest.get("graph_commitment") or "").strip()
    actual_graph = _sha256_file(graph_path)
    if not _HEX64.match(graph_commitment) or actual_graph != graph_commitment:
        return _quarantined(
            "registry graph commitment mismatch",
            "QUARANTINED_PROVENANCE_GRAPH_COMMITMENT",
            ctx.checks,
        )

    history_commitments = ctx.manifest.get("history_commitments")
    if not isinstance(history_commitments, dict):
        return _blocked(
            "registry manifest missing history_commitments",
            "BLOCKED_PROVENANCE_HISTORY_MISSING",
            ctx.checks,
        )
    for key in ("schema_registry", "policy_registry", "recipe_registry"):
        rel = f"history/{key}.json"
        expected = str(history_commitments.get(key) or "").strip()
        hist_path = gen_dir / rel
        if not hist_path.is_file():
            return _blocked(
                f"registry history missing: {key}",
                "BLOCKED_PROVENANCE_HISTORY_FILE",
                ctx.checks,
            )
        actual = _sha256_file(hist_path)
        ctx.checks.append({"check": "history", "name": key, "ok": actual == expected})
        if not _HEX64.match(expected) or actual != expected:
            return _quarantined(
                f"registry history commitment mismatch: {key}",
                "QUARANTINED_PROVENANCE_HISTORY_COMMITMENT",
                ctx.checks,
            )
    return None


def _validate_assertion_index(ctx: _RegistryValidationContext) -> RegistryValidationResult | None:
    assert ctx.manifest is not None
    object_digests = ctx.manifest.get("object_digests")
    assertion_ids = ctx.manifest.get("assertion_ids")
    if not isinstance(assertion_ids, list):
        return _blocked(
            "registry manifest missing assertion_ids",
            "BLOCKED_PROVENANCE_ASSERTION_INDEX",
            ctx.checks,
        )
    if not isinstance(object_digests, dict):
        return _blocked(
            "registry manifest missing object_digests",
            "BLOCKED_PROVENANCE_MANIFEST_OBJECTS",
            ctx.checks,
        )
    for assertion_id in assertion_ids:
        aid = str(assertion_id).strip()
        rel = f"assertions/{aid}.json"
        if rel not in object_digests:
            return _quarantined(
                f"assertion not listed in object_digests: {aid}",
                "QUARANTINED_PROVENANCE_ASSERTION_INDEX",
                ctx.checks,
            )
    return None


def _success_result(ctx: _RegistryValidationContext) -> RegistryValidationResult:
    assert ctx.manifest is not None
    manifest_path = _manifest_path(ctx.data_root, ctx.generation_id)
    manifest_commitment = str(ctx.manifest.get("manifest_commitment") or "").strip()
    manifest_tree = str(ctx.manifest.get("tree_commitment") or "").strip()
    provenance_tuple = ProvenanceTuple(
        generation_id=ctx.generation_id,
        manifest_commitment=manifest_commitment,
        tree_commitment=manifest_tree,
    )
    return RegistryValidationResult(
        outcome=OUTCOME_VALID,
        detail=(
            f"registry valid generation={ctx.generation_id} "
            f"M_g={manifest_commitment[:12]} T_g={manifest_tree[:12]}"
        ),
        provenance_tuple=provenance_tuple,
        manifest_path=str(manifest_path.relative_to(ctx.data_root)),
        checks=ctx.checks,
    )


def validate_provenance_registry(
    root: Path | str,
    *,
    expected_tree_commitment: str | None = None,
) -> RegistryValidationResult:
    """Validate immutable registry manifest/graph/history for a v3 candidate."""
    ctx = _RegistryValidationContext(
        data_root=Path(root).expanduser().resolve(),
        checks=[],
        expected_tree_commitment=expected_tree_commitment,
    )
    for step in (
        _load_selector,
        _load_generation_manifest,
        _validate_manifest_header,
        _validate_tree_commitment,
        _validate_object_digests,
        _validate_graph_and_history,
        _validate_assertion_index,
    ):
        failure = step(ctx)
        if failure is not None:
            return failure
    return _success_result(ctx)


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
    assertions_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "history").mkdir(parents=True, exist_ok=True)

    graph_body = {"schema_version": "convmem/provenance-graph-v1", "edges": []}
    graph_path = gen_dir / "graph.json"
    graph_path.write_text(json.dumps(graph_body, sort_keys=True), encoding="utf-8")
    graph_commitment = _sha256_file(graph_path)

    history_files = {
        "schema_registry": {
            "schema_version": "convmem/provenance-schema-history-v1",
            "entries": [],
        },
        "policy_registry": {
            "schema_version": "convmem/provenance-policy-history-v1",
            "entries": [],
        },
        "recipe_registry": {
            "schema_version": "convmem/provenance-recipe-history-v1",
            "entries": [],
        },
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
            "provenance_commitment": _sha256_bytes(
                json.dumps({"assertion_id": aid}, sort_keys=True).encode()
            ),
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
