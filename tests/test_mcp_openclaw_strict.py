"""T3 capability — collection-safe at T0a; red until T3 lands."""

from __future__ import annotations

import importlib.util


def test_openclaw_strict_server_capability_present():
    spec = importlib.util.find_spec('openclaw_strict_server')
    assert spec is not None, "[T3] module openclaw_strict_server absent"
    module = importlib.import_module('openclaw_strict_server')
    assert hasattr(module, 'serve_strict_mcp'), "[T3] openclaw_strict_server.serve_strict_mcp capability absent"
