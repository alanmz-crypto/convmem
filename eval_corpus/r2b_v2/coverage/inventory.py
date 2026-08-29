"""Revision-bound static mutation-route inventory for R2b v2 (I3)."""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from chroma_write_store import WRITER_GATE_PROTOCOL_VERSION, current_code_revision

ROOT = Path(__file__).resolve().parents[3]
SHADOW_INVENTORY = ROOT / "docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json"
V2_INVENTORY = ROOT / "docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json"

_GENERATION_STORE_CTOR = re.compile(r"FileGenerationStore\s*\(")
_GENERATION_POINTER_WRITE = re.compile(
    r"\b(?:write_qualified_pointer|write_unqualified_pointer|promote_generation|"
    r"commit_generation_pointer|set_active_generation)\s*\("
)

REQUIRED_ROUTE_CATEGORIES: tuple[str, ...] = (
    "watch_f0",
    "refine",
    "monitor_reconciliation",
    "manual_production",
    "cg2_d4",
    "recovery_authority",
    "export_writers",
    "processed_state_writers",
    "chroma_writers",
)

# Trusted revision-bound route table — entrypoints and mutation surfaces.
_STATIC_ROUTES: tuple[dict[str, Any], ...] = (
    {
        "route_id": "watch_f0_ingest",
        "category": "watch_f0",
        "entrypoint": "watch.py:watch_index_event",
        "mutation_surfaces": ("export", "processed", "chroma"),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "refine_job",
        "category": "refine",
        "entrypoint": "refine.py:run_refine_job",
        "mutation_surfaces": ("chroma", "processed"),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "monitor_reconcile",
        "category": "monitor_reconciliation",
        "entrypoint": "watch.py:run_startup_reconciliation",
        "mutation_surfaces": ("processed", "chroma"),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "convmem_cli_index",
        "category": "manual_production",
        "entrypoint": "convmem.py:index_command",
        "mutation_surfaces": ("export", "processed", "chroma"),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "cg2_file_generation_pointer",
        "category": "cg2_d4",
        "entrypoint": "file_generation_pointer.py",
        "mutation_surfaces": ("chroma", "processed", "generation_store"),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "cg2_source_reconciler",
        "category": "cg2_d4",
        "entrypoint": "source_reconciler.py",
        "mutation_surfaces": ("processed", "chroma"),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "cg2_first_cutover",
        "category": "cg2_d4",
        "entrypoint": "cg2_first_cutover.py",
        "mutation_surfaces": ("chroma", "processed", "generation_store"),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "cg2_file_generation_validate",
        "category": "cg2_d4",
        "entrypoint": "file_generation_validate.py",
        "mutation_surfaces": ("chroma", "generation_store"),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "cg2_mixed_mode_control",
        "category": "cg2_d4",
        "entrypoint": "mixed_mode_control.py",
        "mutation_surfaces": ("chroma", "generation_store"),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "cg2_serving_index_repository",
        "category": "cg2_d4",
        "entrypoint": "serving_index_repository.py",
        "mutation_surfaces": ("chroma", "generation_store"),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "recovery_authority_restore",
        "category": "recovery_authority",
        "entrypoint": "complete_data_restore.py",
        "mutation_surfaces": ("export", "processed", "chroma"),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "source_purge",
        "category": "export_writers",
        "entrypoint": "source_purge.py",
        "mutation_surfaces": ("export", "processed", "chroma"),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "exclude_cli",
        "category": "processed_state_writers",
        "entrypoint": "exclude_cli.py",
        "mutation_surfaces": ("processed",),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "propose_decision",
        "category": "chroma_writers",
        "entrypoint": "propose_decision.py",
        "mutation_surfaces": ("chroma",),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
    {
        "route_id": "observe_monitor",
        "category": "monitor_reconciliation",
        "entrypoint": "observe.py",
        "mutation_surfaces": ("chroma",),
        "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "coverage_status": "gated",
    },
)


def _load_shadow_chroma_sites() -> list[dict[str, Any]]:
    if not SHADOW_INVENTORY.is_file():
        return []
    data = json.loads(SHADOW_INVENTORY.read_text(encoding="utf-8"))
    sites: list[dict[str, Any]] = []
    for key in (
        "production_chroma_write_session_call_sites",
        "open_production_write_store_call_sites",
    ):
        for site in data.get(key, []):
            file_part, line_part = site.split(":", 1)
            sites.append(
                {
                    "route_id": f"chroma_site_{file_part.replace('/', '_')}_{line_part}",
                    "category": "chroma_writers",
                    "entrypoint": site,
                    "mutation_surfaces": ("chroma",),
                    "gate_path": "~/.local/share/convmem/locks/chroma_writer_gate.lock",
                    "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
                    "coverage_status": "gated",
                    "shadow_inventory_ref": site,
                }
            )
    return sites


def load_v2_implementation_tip() -> str:
    """Return the committed implementation tip bound by the v2 inventory artifact."""
    if not V2_INVENTORY.is_file():
        return current_code_revision()
    data = json.loads(V2_INVENTORY.read_text(encoding="utf-8"))
    tip = str(data.get("code_revision") or data.get("implementation_tip") or "")
    return tip or current_code_revision()


_SKIP_SCAN_PREFIXES = (
    "tests/",
    "docs/",
    ".worktrees/",
    ".tmp/",
    ".git/",
    "node_modules/",
)


def _scan_repo_pattern(
    pattern: re.Pattern[str],
    *,
    skip_tests: bool = True,
) -> list[str]:
    hits: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = str(path.relative_to(ROOT))
        if skip_tests and any(rel.startswith(prefix) for prefix in _SKIP_SCAN_PREFIXES):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{rel}:{i}")
    return hits


def clear_inventory_scan_cache() -> None:
    """Test seam: drop cached repository scans."""
    _cached_chroma_ctor_scan.cache_clear()
    _cached_generation_store_ctor_scan.cache_clear()
    _cached_generation_pointer_write_scan.cache_clear()
    _cached_undocumented_mutation_sink_scan.cache_clear()


@lru_cache(maxsize=1)
def _cached_chroma_ctor_scan() -> tuple[str, ...]:
    return tuple(_scan_chroma_ctor_uncached())


@lru_cache(maxsize=1)
def _cached_generation_store_ctor_scan() -> tuple[str, ...]:
    return tuple(_scan_generation_store_ctor_uncached())


@lru_cache(maxsize=1)
def _cached_generation_pointer_write_scan() -> tuple[str, ...]:
    return tuple(_scan_generation_pointer_write_uncached())


@lru_cache(maxsize=1)
def _cached_undocumented_mutation_sink_scan() -> tuple[str, ...]:
    combined = (
        _cached_chroma_ctor_scan()
        + _cached_generation_store_ctor_scan()
        + _cached_generation_pointer_write_scan()
    )
    return tuple(sorted(set(combined)))


def scan_repo_for_unlisted_generation_store_ctor() -> list[str]:
    """Detect FileGenerationStore construction outside inventory-declared routes."""
    return list(_cached_generation_store_ctor_scan())


def _listed_generation_store_files() -> set[str]:
    files = {"file_generation_store.py", "mixed_mode_proof.py"}
    for route in _STATIC_ROUTES:
        files.add(route["entrypoint"].split(":")[0])
    return files


def _scan_generation_store_ctor_uncached() -> list[str]:
    listed_files = _listed_generation_store_files()
    hits: list[str] = []
    for site in _scan_repo_pattern(_GENERATION_STORE_CTOR):
        rel = site.split(":", 1)[0]
        if rel not in listed_files and not rel.startswith("eval_corpus/"):
            hits.append(site)
    return hits


def scan_repo_for_unlisted_generation_pointer_writes() -> list[str]:
    """Detect generation-pointer mutation calls outside declared CG-2 routes."""
    return list(_cached_generation_pointer_write_scan())


def _scan_generation_pointer_write_uncached() -> list[str]:
    listed_files = {
        route["entrypoint"].split(":")[0]
        for route in _STATIC_ROUTES
        if route.get("category") == "cg2_d4"
    }
    hits: list[str] = []
    for site in _scan_repo_pattern(_GENERATION_POINTER_WRITE):
        rel = site.split(":", 1)[0]
        if rel not in listed_files:
            hits.append(site)
    return hits


def scan_repo_for_undocumented_mutation_sinks() -> list[str]:
    """Independent discovery of mutation sinks beyond hardcoded route labels."""
    return list(_cached_undocumented_mutation_sink_scan())


def scan_repo_for_unlisted_chroma_ctor() -> list[str]:
    """Detect direct ChromaStore construction outside allowlisted shadow inventory."""
    return list(_cached_chroma_ctor_scan())


def _scan_chroma_ctor_uncached() -> list[str]:
    """Detect direct ChromaStore construction outside allowlisted shadow inventory."""
    if not SHADOW_INVENTORY.is_file():
        return ["shadow inventory missing"]
    allow = set(
        json.loads(SHADOW_INVENTORY.read_text(encoding="utf-8")).get(
            "allowlisted_direct_sites", []
        )
    )
    ctor = re.compile(r"ChromaStore\s*\(")
    hits: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = str(path.relative_to(ROOT))
        if any(rel.startswith(prefix) for prefix in _SKIP_SCAN_PREFIXES):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if not ctor.search(line):
                continue
            if line.strip().startswith("class ChromaStore"):
                continue
            site = f"{rel}:{i}"
            if site not in allow:
                hits.append(site)
    return hits


def build_static_route_inventory(
    *,
    code_revision: str | None = None,
) -> dict[str, Any]:
    """Derive the revision-bound static inventory from trusted route evidence."""
    revision = code_revision or current_code_revision()
    routes = [dict(route, code_revision=revision) for route in _STATIC_ROUTES]
    routes.extend(_load_shadow_chroma_sites())
    for route in routes:
        route.setdefault("code_revision", revision)
    categories = {route["category"] for route in routes}
    missing_categories = sorted(set(REQUIRED_ROUTE_CATEGORIES) - categories)
    unlisted_ctor_sites = scan_repo_for_unlisted_chroma_ctor()
    unlisted_generation_store_sites = scan_repo_for_unlisted_generation_store_ctor()
    unlisted_generation_pointer_sites = scan_repo_for_unlisted_generation_pointer_writes()
    undocumented_mutation_sinks = scan_repo_for_undocumented_mutation_sinks()
    payload = {
        "proof_class": "r2b_v2_static_route_inventory",
        "code_revision": revision,
        "gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "required_categories": list(REQUIRED_ROUTE_CATEGORIES),
        "missing_categories": missing_categories,
        "unlisted_chroma_ctor_sites": unlisted_ctor_sites,
        "unlisted_generation_store_ctor_sites": unlisted_generation_store_sites,
        "unlisted_generation_pointer_write_sites": unlisted_generation_pointer_sites,
        "undocumented_mutation_sinks": undocumented_mutation_sinks,
        "routes": sorted(routes, key=lambda r: r["route_id"]),
        "shadow_inventory_path": str(SHADOW_INVENTORY.relative_to(ROOT)),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["inventory_digest"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def verify_inventory_matches_tip(
    inventory: dict[str, Any],
    *,
    code_revision: str | None = None,
) -> list[str]:
    """Refuse stale or incomplete static inventories."""
    revision = code_revision or current_code_revision()
    errors: list[str] = []
    if inventory.get("code_revision") != revision:
        errors.append("stale inventory revision")
    if inventory.get("missing_categories"):
        errors.append(f"incomplete category coverage: {inventory['missing_categories']}")
    unlisted = scan_repo_for_unlisted_chroma_ctor()
    if unlisted:
        errors.append(f"unlisted direct ChromaStore ctor sites: {unlisted}")
    inventory_unlisted = inventory.get("unlisted_chroma_ctor_sites") or []
    if inventory_unlisted:
        errors.append(f"inventory records unlisted ctor sites: {inventory_unlisted}")
    for label, scanner in (
        ("generation store ctor", scan_repo_for_unlisted_generation_store_ctor),
        ("generation pointer write", scan_repo_for_unlisted_generation_pointer_writes),
        ("undocumented mutation sink", scan_repo_for_undocumented_mutation_sinks),
    ):
        found = scanner()
        if found:
            errors.append(f"unlisted {label} sites: {found}")
    expected = build_static_route_inventory(code_revision=revision)
    if inventory.get("inventory_digest") != expected["inventory_digest"]:
        errors.append("inventory digest mismatch vs current tip")
    return errors


def verify_shadow_inventory_unchanged() -> list[str]:
    """Ensure shadow C3 inventory contract is not weakened."""
    if not SHADOW_INVENTORY.is_file():
        return ["shadow inventory missing"]
    data = json.loads(SHADOW_INVENTORY.read_text(encoding="utf-8"))
    if data.get("must_use_factory_count") != 0:
        return ["shadow inventory must_use_factory_count must remain 0"]
    if data.get("must_use_factory_bypass_sites"):
        return ["shadow inventory bypass sites must remain empty"]
    return []


def write_v2_inventory_file(path: Path | None = None) -> Path:
    """Persist the derived inventory for revision-bound evidence (optional)."""
    target = path or V2_INVENTORY
    payload = build_static_route_inventory()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
