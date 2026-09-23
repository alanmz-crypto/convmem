"""Second independent case58 component walker (fixture-owned).

Literal membership is duplicated here — does not call component_inventory's
digest helpers. Agreement with the reference walker is asserted by tests.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Literal membership copied from Architecture §6.5.9 / Execution §3.1.
CORE = (
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

SCHEMAS_BC = (
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

MEMBERSHIP: dict[str, tuple[str, ...]] = {
    "builder": tuple(sorted(set(CORE) | set(SCHEMAS_BC) | {"strict_projection_publisher.py"})),
    "strict_server": tuple(sorted(set(CORE) | set(SCHEMAS_BC) | {"openclaw_strict_server.py"})),
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


class Case58OracleError(Exception):
    """Independent walker rejection."""


def independent_walk(root: Path, component: str) -> list[dict[str, str]]:
    if component not in MEMBERSHIP:
        raise Case58OracleError(f"unknown:{component}")
    expected = list(MEMBERSHIP[component])
    if len(expected) != len(set(expected)):
        raise Case58OracleError(f"dup:{component}")
    entries: list[dict[str, str]] = []
    missing: list[str] = []
    for rel in expected:
        path = root / rel
        if path.is_symlink():
            raise Case58OracleError(f"symlink:{rel}")
        if not path.is_file():
            missing.append(rel)
            continue
        mode = f"{path.stat().st_mode & 0o7777:04o}"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append({"path": rel, "mode": mode, "sha256": f"sha256:{digest}"})
    if missing:
        raise Case58OracleError(f"missing:{missing}")
    entries.sort(key=lambda e: e["path"])
    return entries


def independent_tree_digest(entries: list[dict[str, str]]) -> str:
    raw = json.dumps(
        entries, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


_EXCLUDED_FIXTURE_RELS = frozenset(
    {
        "fixture-manifest.json",
        "suite_results.json",
        "evidence/fixture-manifest.json",
    }
)
_EXCLUDED_SOURCE_RELS = frozenset(
    {
        "tests/fixtures/openclaw_strict/fixture-manifest.json",
        "tests/fixtures/openclaw_strict/suite_results.json",
        "tests/fixtures/openclaw_strict/evidence/fixture-manifest.json",
    }
)


def reference_fixture_artifact_walk(fixture_tree: Path) -> list[dict[str, str]]:
    """Independent fixture-tree walker — does not import fixture_manifest inventores."""

    root = fixture_tree.resolve()
    if not root.is_dir():
        raise Case58OracleError(f"fixture_missing:{root}")
    out: list[dict[str, str]] = []
    stack = [root]
    while stack:
        cur = stack.pop()
        try:
            children = sorted(cur.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            raise Case58OracleError(f"walk_failed:{cur}") from exc
        for child in children:
            if child.is_symlink():
                raise Case58OracleError(
                    f"symlink:{child.relative_to(root).as_posix()}"
                )
            if child.is_dir():
                stack.append(child)
                continue
            if not child.is_file():
                continue
            rel = child.relative_to(root).as_posix()
            if rel in _EXCLUDED_FIXTURE_RELS:
                continue
            mode = f"{child.stat().st_mode & 0o7777:04o}"
            digest = hashlib.sha256(child.read_bytes()).hexdigest()
            out.append(
                {
                    "mode": mode,
                    "path": f"tests/fixtures/openclaw_strict/{rel}",
                    "sha256": f"sha256:{digest}",
                }
            )
    out.sort(key=lambda e: e["path"])
    return out


def reference_source_export_walk(source_root: Path) -> list[dict[str, str]]:
    """Independent source-export walker — does not import fixture_manifest inventores."""

    root = source_root.resolve()
    if not root.is_dir():
        raise Case58OracleError(f"source_missing:{root}")
    out: list[dict[str, str]] = []
    stack = [root]
    while stack:
        cur = stack.pop()
        try:
            children = sorted(cur.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            raise Case58OracleError(f"walk_failed:{cur}") from exc
        for child in children:
            if child.name == ".git" and child.is_dir():
                continue
            if child.is_symlink():
                raise Case58OracleError(
                    f"symlink:{child.relative_to(root).as_posix()}"
                )
            if child.is_dir():
                stack.append(child)
                continue
            if not child.is_file():
                continue
            rel = child.relative_to(root).as_posix()
            if rel in _EXCLUDED_SOURCE_RELS:
                continue
            mode = f"{child.stat().st_mode & 0o7777:04o}"
            digest = hashlib.sha256(child.read_bytes()).hexdigest()
            out.append(
                {
                    "mode": mode,
                    "path": rel,
                    "sha256": f"sha256:{digest}",
                }
            )
    out.sort(key=lambda e: e["path"])
    return out
