"""Literal Architecture §6.5.9 component inventories — reference-owned (T0b).

Defines membership and independent walks only. Missing future production members
reject. Positive source-component digests and the complete five-component source
manifest remain future-step reds while those members are absent. No placeholder
production bytes are invented under /src.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

# Exact CORE (Architecture §6.5.9 / Execution §3.1).
CORE: tuple[str, ...] = (
    "canonical_json.py",
    "provenance.py",
    "provenance_binding.py",
    "domains.py",
    "bound_read_scope.py",
    "strict_grounding.py",
    "strict_evidence_state.py",
    "strict_projection.py",
    "requirements.txt",
)

SCHEMAS_BC: tuple[str, ...] = (
    "schemas/convmem-bound-read-scope-v2.schema.json",
    "schemas/convmem-project-binding-registry-v3.schema.json",
    "schemas/convmem-bound-authority-record-v3.schema.json",
    "schemas/convmem-authority-disposition-v1.schema.json",
    "schemas/convmem-strict-provenance-context-v2.schema.json",
    "schemas/convmem-strict-grounding-v1.schema.json",
    "schemas/convmem-capture-receipt-v1.schema.json",
    "schemas/convmem-strict-fixture-bundle-v2.schema.json",
    "schemas/convmem-strict-citation-map-v1.schema.json",
    "schemas/convmem-bound-authority-manifest-v3.schema.json",
    "schemas/convmem-bound-projection-row-v2.schema.json",
    "schemas/convmem-strict-graph-v1.schema.json",
    "schemas/convmem-bound-projection-manifest-v3.schema.json",
    "schemas/convmem-strict-generation-layout-v2.schema.json",
    "schemas/convmem-strict-publication-v2.schema.json",
    "schemas/convmem-strict-enrollment-v1.schema.json",
    "schemas/convmem-strict-slot-v1.schema.json",
    "schemas/convmem-strict-source-cutoff-v1.schema.json",
    "schemas/convmem-strict-semantic-contract-v1.schema.json",
    "schemas/convmem-strict-state-v2.schema.json",
    "schemas/convmem-clock-review-v1.schema.json",
    "schemas/convmem-raw-evidence-v3.schema.json",
    "schemas/convmem-error-v1.schema.json",
    "schemas/convmem-strict-config-v2.schema.json",
    "schemas/convmem-openclaw-connector-launch-v2.schema.json",
    "schemas/convmem-openclaw-activation-v2.schema.json",
    "schemas/convmem-activation-control-v1.schema.json",
    "schemas/convmem-activation-retirement-v1.schema.json",
    "schemas/convmem-activation-launch-policy-v1.schema.json",
    "schemas/convmem-activation-manager-policy-v1.schema.json",
    "schemas/convmem-controller-socket-policy-v1.schema.json",
)

FUTURE_PRODUCTION_MEMBERS: tuple[str, ...] = (
    "bound_read_scope.py",
    "strict_grounding.py",
    "strict_evidence_state.py",
    "strict_projection.py",
    "strict_projection_publisher.py",
    "openclaw_strict_server.py",
)

COMPONENT_MEMBERSHIP: dict[str, tuple[str, ...]] = {
    "builder": tuple(
        sorted(set(CORE) | set(SCHEMAS_BC) | {"strict_projection_publisher.py"})
    ),
    "strict_server": tuple(
        sorted(set(CORE) | set(SCHEMAS_BC) | {"openclaw_strict_server.py"})
    ),
    "supervisor": tuple(
        sorted(set(CORE) | set(SCHEMAS_BC) | {"openclaw_activation_supervisor.py"})
    ),
    "controller": tuple(
        sorted(
            set(CORE)
            | set(SCHEMAS_BC)
            | {
                "openclaw_activation_controller.py",
                "openclaw_activation_supervisor.py",
            }
        )
    ),
    "plugin": (
        "integrations/openclaw-convmem-reader/index.js",
        "integrations/openclaw-convmem-reader/openclaw.plugin.json",
        "integrations/openclaw-convmem-reader/package.json",
    ),
}


class InventoryError(Exception):
    """Fail-closed inventory rejection."""


def build_component_inventories() -> dict[str, tuple[str, ...]]:
    """Return the literal five inventory membership sets (reference-owned)."""
    return {name: paths for name, paths in COMPONENT_MEMBERSHIP.items()}


def _mode_octal(path: Path) -> str:
    return f"{path.stat().st_mode & 0o7777:04o}"


def _sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def reference_walk_component(root: Path, component: str) -> list[dict[str, str]]:
    """Literal membership only; never asks implementation for set/digest."""
    if component not in COMPONENT_MEMBERSHIP:
        raise InventoryError(f"unknown_component:{component}")
    expected = list(COMPONENT_MEMBERSHIP[component])
    if len(expected) != len(set(expected)):
        raise InventoryError(f"duplicate_membership:{component}")
    entries: list[dict[str, str]] = []
    missing: list[str] = []
    for rel in expected:
        path = root / rel
        if path.is_symlink():
            raise InventoryError(f"symlink:{rel}")
        if not path.is_file():
            missing.append(rel)
            continue
        entries.append(
            {
                "path": rel,
                "mode": _mode_octal(path),
                "sha256": _sha256_file(path),
            }
        )
    if missing:
        raise InventoryError(f"missing_member:{missing}")
    entries.sort(key=lambda e: e["path"])
    return entries


def component_tree_digest(entries: list[dict[str, str]]) -> str:
    payload = json.dumps(
        entries, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return _sha256_bytes(payload)


def reject_supplied_inventory_extra_entry(
    component: str, supplied_entries: list[dict[str, str]]
) -> None:
    """Additional entries in a supplied inventory/manifest must reject."""
    if component not in COMPONENT_MEMBERSHIP:
        raise InventoryError(f"unknown_component:{component}")
    allowed = set(COMPONENT_MEMBERSHIP[component])
    paths = [e.get("path") for e in supplied_entries]
    if len(paths) != len(set(paths)):
        raise InventoryError("duplicate_supplied_path")
    extra = [p for p in paths if p not in allowed]
    if extra:
        raise InventoryError(f"extra_supplied_member:{extra}")
    missing = [p for p in allowed if p not in set(paths)]
    if missing:
        raise InventoryError(f"missing_supplied_member:{missing}")


def missing_future_production_members(root: Path) -> list[str]:
    """Inventory members that remain absent until later T milestones."""
    return sorted(rel for rel in FUTURE_PRODUCTION_MEMBERS if not (root / rel).is_file())


def source_component_digest_available(root: Path, component: str) -> bool:
    """True only when every literal member exists as a regular non-symlink file."""
    try:
        reference_walk_component(root, component)
    except InventoryError:
        return False
    return True


def disposable_copy_members(src_root: Path, rel_paths: list[str]) -> Path:
    """Copy named present membership paths into a disposable directory."""
    dest = Path(tempfile.mkdtemp(prefix="convmem-openclaw-invmut.", dir="/tmp"))
    os.chmod(dest, 0o700)
    for rel in rel_paths:
        src = src_root / rel
        if not src.is_file() or src.is_symlink():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        os.chmod(target, src.stat().st_mode & 0o7777)
    return dest


def assert_present_member_mutation_changes_digest(
    root: Path, component: str, rel_path: str
) -> dict[str, Any]:
    """Mutate a disposable copy of a present included file; digest must change."""
    members = list(COMPONENT_MEMBERSHIP[component])
    if rel_path not in members:
        raise InventoryError(f"not_a_member:{rel_path}")
    if not (root / rel_path).is_file():
        raise InventoryError(f"missing_member:[{rel_path!r}]")
    # Only complete components (today: plugin) may be mutated for digest evidence.
    if any(not (root / m).is_file() for m in members):
        raise InventoryError(f"component_incomplete_future_red:{component}")
    base = disposable_copy_members(root, members)
    before = reference_walk_component(base, component)
    before_digest = component_tree_digest(before)
    target = base / rel_path
    target.write_bytes(target.read_bytes() + b"\n#mut\n")
    after = reference_walk_component(base, component)
    after_digest = component_tree_digest(after)
    if after_digest == before_digest:
        raise InventoryError(f"mutation_digest_unchanged:{rel_path}")
    shutil.rmtree(base, ignore_errors=True)
    return {
        "component": component,
        "path": rel_path,
        "before": before_digest,
        "after": after_digest,
    }


def assert_omitted_canonical_json_mutant_fails(root: Path) -> None:
    """Omitting canonical_json.py must fail even if a wrong digest agrees."""
    present = [p for p in COMPONENT_MEMBERSHIP["builder"] if (root / p).is_file()]
    if "canonical_json.py" not in present:
        raise InventoryError("canonical_json_missing_from_checkout")
    base = disposable_copy_members(root, present)
    (base / "canonical_json.py").unlink()
    fake_entries: list[dict[str, str]] = []
    fake_digest = component_tree_digest(fake_entries)
    fake_manifest = {"builder": fake_digest}
    try:
        reference_walk_component(base, "builder")
    except InventoryError as exc:
        if "missing_member" not in str(exc):
            raise
        assert fake_manifest["builder"] == fake_digest
        shutil.rmtree(base, ignore_errors=True)
        return
    shutil.rmtree(base, ignore_errors=True)
    raise InventoryError("omitted_canonical_json_accepted")


def unrelated_on_disk_file_leaves_digest_unchanged(root: Path, component: str) -> None:
    """Unrelated files outside literal membership are excluded; hash unchanged.

    Distinct from reject_supplied_inventory_extra_entry: on-disk extras are
    ignored by the literal walker; supplied inventory extras must reject.
    """
    members = list(COMPONENT_MEMBERSHIP[component])
    if any(not (root / m).is_file() for m in members):
        raise InventoryError(f"component_incomplete_future_red:{component}")
    base = disposable_copy_members(root, members)
    before = component_tree_digest(reference_walk_component(base, component))
    (base / "UNLISTED_EXTRA.txt").write_text("extra\n", encoding="utf-8")
    after = component_tree_digest(reference_walk_component(base, component))
    if "UNLISTED_EXTRA.txt" in {e["path"] for e in reference_walk_component(base, component)}:
        raise InventoryError("unlisted_entered_membership")
    if after != before:
        raise InventoryError("unrelated_file_changed_digest")
    shutil.rmtree(base, ignore_errors=True)


def reject_symlink_member(root: Path, component: str, rel_path: str) -> None:
    members = list(COMPONENT_MEMBERSHIP[component])
    if any(not (root / m).is_file() for m in members):
        raise InventoryError(f"component_incomplete_future_red:{component}")
    if rel_path not in members:
        raise InventoryError(f"not_a_member:{rel_path}")
    base = disposable_copy_members(root, members)
    target = base / rel_path
    data = target.read_bytes()
    target.unlink()
    alt = base / (rel_path + ".real")
    alt.write_bytes(data)
    target.symlink_to(alt.name)
    try:
        reference_walk_component(base, component)
    except InventoryError as exc:
        if "symlink" not in str(exc):
            raise
        shutil.rmtree(base, ignore_errors=True)
        return
    shutil.rmtree(base, ignore_errors=True)
    raise InventoryError("symlink_accepted")
