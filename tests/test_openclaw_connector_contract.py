"""Connector contract — T0a refusal green; T4 launch/alias/transport green."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("integrations/openclaw-convmem-reader")
INDEX = ROOT / "index.js"
TEST = ROOT / "test" / "connector.test.mjs"


def test_connector_package_files_exist():
    assert (ROOT / "index.js").is_file()
    assert (ROOT / "package.json").is_file()
    assert (ROOT / "openclaw.plugin.json").is_file()
    assert TEST.is_file()


def test_t4_validate_launch_tuple_present():
    text = INDEX.read_text(encoding="utf-8")
    assert "validateLaunchTuple" in text, "[T4] connector launch-tuple validation capability absent"
    assert "createConnectorSession" in text
    assert "createStrictFdRoles" in text
    assert "launch_payload_sha256" in text


def test_t4_frozen_aliases_and_mcp_methods():
    text = INDEX.read_text(encoding="utf-8")
    for alias, method in (
        ("convmem_search", "search"),
        ("convmem_unresolved", "unresolved"),
        ("convmem_related", "related"),
    ):
        assert alias in text
        assert method in text
    assert "TOOL_ALIASES" in text
    # No dynamic fourth alias surface.
    assert "convmem_ask" not in text
    assert "convmem_search_fast" not in text


def test_t4_bounds_and_injected_transport_markers():
    text = INDEX.read_text(encoding="utf-8")
    assert "128" in text and "1024" in text
    assert "64" in text
    assert "MAX_PENDING" in text or "pending" in text.lower()
    assert "temporarily_unavailable" in text
    assert "typeof spawn" in text
    assert "nextEvent" in text
    assert "createStrictFdRoles" in text
    assert "runtime_not_qualified" in text
    assert "exitCode = 78" in text or "exitCode: 78" in text or "err.exitCode = 78" in text


def test_t4_node_suite_covers_required_cases():
    text = TEST.read_text(encoding="utf-8")
    for marker in (
        "case2",
        "case33",
        "case35",
        "case48",
        "case57",
        "case58",
        "writeTrace",
        "tools/call",
        "temporarily_unavailable",
        "instruction_authority",
        "validateLaunchTuple",
        "fd_roles",
    ):
        assert marker in text, f"missing non-vacuous marker {marker}"


def test_t4_no_new_plugin_dependencies():
    pkg = (ROOT / "package.json").read_text(encoding="utf-8")
    assert "dependencies" not in pkg or re.search(r'"dependencies"\s*:\s*\{\s*\}', pkg)
    assert "node_modules" not in [p.name for p in ROOT.iterdir()]
