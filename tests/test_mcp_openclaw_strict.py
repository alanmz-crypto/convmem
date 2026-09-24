"""M4/T3 Gate B — dedicated strict server, profile refusal, tool enumeration.

Parent cases (overlay 581de2a / parent 9a7891fd Gate B):
1–4 (strict-server portion of 47), legacy profile refusal effects.
Exact three tools / zero resources / templates; closed env allowlist;
canonical closed result/error serialization; closed request-arg dispatch.
T4/T5 expectations remain declared red only where the overlay says so.
"""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]

_ALLOWLIST = frozenset(
    {
        "CONVMEM_MCP_PROFILE",
        "CONVMEM_BOUND_READ_SCOPE_FILE",
        "CONVMEM_PROJECT_BINDING_REGISTRY_FILE",
        "CONVMEM_STRICT_CONFIG_FILE",
        "HOME",
        "PATH",
        "LANG",
        "LC_ALL",
        "TMPDIR",
    }
)


def _exact_child_env(tmp_path: Path, **overrides: str) -> dict[str, str]:
    """Exact closed child environment — no PYTHONPATH or other extras."""

    env = {
        "CONVMEM_MCP_PROFILE": "openclaw-strict",
        "CONVMEM_BOUND_READ_SCOPE_FILE": str(tmp_path / "scope.json"),
        "CONVMEM_PROJECT_BINDING_REGISTRY_FILE": str(tmp_path / "registry.json"),
        "CONVMEM_STRICT_CONFIG_FILE": str(tmp_path / "config.json"),
        "HOME": str(tmp_path),
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TMPDIR": str(tmp_path),
    }
    env.update(overrides)
    return env


def test_openclaw_strict_server_capability_present():
    spec = importlib.util.find_spec("openclaw_strict_server")
    assert spec is not None, "[T3] module openclaw_strict_server absent"
    module = importlib.import_module("openclaw_strict_server")
    assert hasattr(module, "serve_strict_mcp")
    assert hasattr(module, "require_closed_strict_environment")
    assert hasattr(module, "build_strict_mcp_server")
    assert hasattr(module, "construct_strict_mcp_after_gate")
    assert hasattr(module, "main")
    assert module.ALLOWED_ENV_KEYS == _ALLOWLIST


def test_strict_server_allowlist_object_has_no_forbidden_publication_env():
    """Item 5: test the allowlist object/AST — not comment substring absence."""

    module = importlib.import_module("openclaw_strict_server")
    assert "CONVMEM_EXPECTED_PUBLICATION_SHA256" not in module.ALLOWED_ENV_KEYS
    tree = ast.parse((REPO / "openclaw_strict_server.py").read_text(encoding="utf-8"))
    assigned: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ALLOWED_ENV_KEYS":
                    if isinstance(node.value, ast.Call):
                        for arg in node.value.args:
                            if isinstance(arg, (ast.Set, ast.Tuple, ast.List)):
                                for elt in arg.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(
                                        elt.value, str
                                    ):
                                        assigned.add(elt.value)
    assert assigned == set(_ALLOWLIST)
    assert "CONVMEM_EXPECTED_PUBLICATION_SHA256" not in assigned


def test_strict_server_lazy_imports_after_env_gate():
    """MCP / ConvMem loaders are not imported at module import time."""

    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/tmp",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TMPDIR": "/tmp",
        "PYTHONPATH": str(REPO),
    }
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import openclaw_strict_server as m; "
            "assert m.require_closed_strict_environment; "
            "print('imported_ok')",
        ],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "imported_ok"


def test_strict_server_env_gate_positive_exact_and_missing_key_negatives(
    tmp_path: Path,
):
    """Item 1: positive exact-env gate; missing-key negatives without extra keys."""

    module = importlib.import_module("openclaw_strict_server")

    exact = _exact_child_env(tmp_path)
    module.require_closed_strict_environment(exact)

    for missing in (
        "CONVMEM_BOUND_READ_SCOPE_FILE",
        "CONVMEM_PROJECT_BINDING_REGISTRY_FILE",
        "CONVMEM_STRICT_CONFIG_FILE",
        "HOME",
        "PATH",
        "LANG",
        "LC_ALL",
        "TMPDIR",
    ):
        env = dict(exact)
        env[missing] = ""
        with pytest.raises(SystemExit) as ei:
            module.require_closed_strict_environment(env)
        assert ei.value.code == 2

    bad = dict(exact)
    bad["CONVMEM_MCP_PROFILE"] = "full"
    with pytest.raises(SystemExit) as ei:
        module.require_closed_strict_environment(bad)
    assert ei.value.code == 2

    extra = dict(exact)
    extra["DEEPSEEK_API_KEY"] = "should-not-leak"
    with pytest.raises(SystemExit) as ei:
        module.require_closed_strict_environment(extra)
    assert ei.value.code == 2


def test_strict_server_mcp_protocol_inventory_enumeration():
    """Item 2: real MCP 1.28.1 session — initialize + tools/list ordered names."""

    module = importlib.import_module("openclaw_strict_server")
    from mcp.server.lowlevel import Server
    from mcp.shared.memory import create_connected_server_and_client_session
    from mcp.types import CallToolResult, TextContent, Tool
    from strict_grounding import strict_canonical_bytes
    from strict_projection import StrictPublicError

    class FakeReader:
        pass

    def fake_dispatch(reader, name, arguments):
        return {
            "schema": "convmem.raw-evidence.v3",
            "instruction_authority": "none",
            "snapshot": {
                "authority_snapshot_id": "snap2_" + ("0" * 64),
                "projection_generation_id": "gen2_" + ("0" * 64),
                "as_of": "2026-09-21T00:00:00Z",
                "expires_at": "2027-09-21T00:00:00Z",
            },
            "selection_complete": True,
            "display_basis": "ranked_selection",
            "results": [],
        }

    server = module.build_strict_mcp_server(
        reader=FakeReader(),
        Server=Server,
        Tool=Tool,
        CallToolResult=CallToolResult,
        TextContent=TextContent,
        dispatch_tool=fake_dispatch,
        StrictPublicError=StrictPublicError,
        strict_canonical_bytes=strict_canonical_bytes,
    )

    async def _enumerate() -> dict[str, Any]:
        async with create_connected_server_and_client_session(server) as session:
            tools = await session.list_tools()
            resources = await session.list_resources()
            templates = await session.list_resource_templates()
            read_err: str | None = None
            try:
                await session.read_resource("convmem://anything")  # type: ignore[arg-type]
            except Exception as exc:  # noqa: BLE001 — protocol error surface
                read_err = type(exc).__name__ + ":" + str(exc)
            return {
                "tool_names": [t.name for t in tools.tools],
                "resources": list(resources.resources),
                "templates": list(templates.resourceTemplates),
                "read_err": read_err,
            }

    result = asyncio.run(_enumerate())
    assert result["tool_names"] == ["search", "unresolved", "related"]
    assert result["resources"] == []
    assert result["templates"] == []
    assert result["read_err"] is not None
    assert "resource_not_found" in result["read_err"] or "Error" in result["read_err"]


def _load_sibling_test_module(name: str):
    """Load a sibling tests/*.py by path — frozen pytest does not put tests/ on sys.path."""

    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_strict_server_closed_argument_containers_via_protocol():
    """Extra mapping keys via in-memory MCP; non-mapping via server-side guard."""

    module = importlib.import_module("openclaw_strict_server")
    from mcp.server.lowlevel import Server
    from mcp.shared.memory import create_connected_server_and_client_session
    from mcp.types import CallToolResult, TextContent, Tool
    from strict_grounding import strict_canonical_bytes
    from strict_projection import StrictPublicError

    class FakeReader:
        pass

    def boom_dispatch(reader, name, arguments):
        raise AssertionError("dispatch must not run on invalid args")

    server = module.build_strict_mcp_server(
        reader=FakeReader(),
        Server=Server,
        Tool=Tool,
        CallToolResult=CallToolResult,
        TextContent=TextContent,
        dispatch_tool=boom_dispatch,
        StrictPublicError=StrictPublicError,
        strict_canonical_bytes=strict_canonical_bytes,
    )

    async def _call(name: str, arguments: Any) -> Any:
        async with create_connected_server_and_client_session(server) as session:
            return await session.call_tool(name, arguments)

    # Extra key (MCP client delivers mappings; exercise the real in-memory path).
    res = asyncio.run(_call("search", {"query": "x", "unknown_prop": 1}))
    assert res.isError is True
    text = res.content[0].text if res.content else ""
    assert "invalid_request" in text
    assert text.count("\n") == 0 or text.endswith("}")

    # Non-mapping: MCP 1.28.1 client Pydantic rejects lists before the server.
    # Exercise the server-side guard directly; do not claim protocol delivery.
    with pytest.raises(StrictPublicError) as exc_info:
        module._closed_tool_arguments(
            "search",
            ["not", "a", "mapping"],
            StrictPublicError=StrictPublicError,
        )
    assert exc_info.value.code == "invalid_request"


def test_strict_server_startup_boundary_after_exact_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Positive startup boundary: exact env + sealed public mount reaches construction."""

    m4 = _load_sibling_test_module("test_strict_projection")

    items, resolved, scope_path, registry_path = m4._m4_two_serving_roots(tmp_path)
    item = items[0]
    m4._m4_patch_clocks(monkeypatch)

    # Point env at operator files + public-only configured root.
    env = _exact_child_env(tmp_path)
    env["CONVMEM_BOUND_READ_SCOPE_FILE"] = str(scope_path)
    env["CONVMEM_PROJECT_BINDING_REGISTRY_FILE"] = str(registry_path)
    env["CONVMEM_STRICT_CONFIG_FILE"] = str(item["config_path"])
    for key in list(os.environ):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    module = importlib.import_module("openclaw_strict_server")
    module.require_closed_strict_environment(os.environ)
    server = module.construct_strict_mcp_after_gate()
    assert server.name == "convmem-openclaw-strict"


def _legacy_profile_subprocess(profile: str | None) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(REPO),
    }
    if profile is not None:
        env["CONVMEM_MCP_PROFILE"] = profile
    code = (
        "import sys\n"
        "sys.path.insert(0, %r)\n"
        "try:\n"
        "    import mcp_server  # noqa: F401\n"
        "except SystemExit as exc:\n"
        "    raise SystemExit(exc.code)\n"
        "print('REGISTERED')\n"
    ) % str(REPO)
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_legacy_mcp_refuses_openclaw_strict_before_loader_effects():
    """Case/profile: nonzero exit, empty stdout, dedicated-entrypoint instruction.

    Exact stderr bytes and numeric code are noncontractual (Ryan refusal ruling).
    Must not disclose the raw env value; must not register/start.
    """

    raw = "  OpenClaw-Strict \t"
    proc = _legacy_profile_subprocess(raw)
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "REGISTERED" not in proc.stdout
    assert "dedicated" in proc.stderr.lower() or "openclaw_strict_server" in proc.stderr
    assert raw not in proc.stderr
    assert "OpenClaw-Strict" not in proc.stderr


def test_legacy_mcp_refuses_unknown_profile_fail_closed():
    raw = "not-a-real-profile-XYZ"
    proc = _legacy_profile_subprocess(raw)
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "REGISTERED" not in proc.stdout
    assert raw not in proc.stderr


def test_legacy_mcp_profile_gate_precedes_env_loader_and_fastmcp_in_source():
    """Refuse before _load_convmem_env_files() call and FastMCP import."""

    src = (REPO / "mcp_server.py").read_text(encoding="utf-8")
    gate = src.index("_raw_mcp_profile")
    after_def = src.index("def _load_convmem_env_files")
    # Module-level call only (not the def header or comment mentions of the name).
    module_call = src.index("\n_load_convmem_env_files()\n", after_def)
    assert gate < module_call
    fastmcp = src.index("from mcp.server.fastmcp import FastMCP")
    assert module_call < fastmcp
    assert gate < fastmcp


def test_strict_server_serializes_via_canonical_closed_envelope():
    """Server must use strict_canonical_bytes — not invented json.dumps convention."""

    src = (REPO / "openclaw_strict_server.py").read_text(encoding="utf-8")
    assert "strict_canonical_bytes" in src
    assert "json.dumps(err" not in src
    assert "json.dumps(payload)" not in src
    assert "json.dumps(exc" not in src


def test_t4_t5_surfaces_remain_declared_absent_or_refusing():
    """Overlay: T4/T5 not implemented in M4 — connector/activation stay refuse-only."""

    for rel in (
        "openclaw_activation_controller.py",
        "openclaw_activation_supervisor.py",
    ):
        path = REPO / rel
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert (
            "refuse" in text.lower()
            or "not_qualified" in text.lower()
            or "runtime_not_qualified" in text
        )
