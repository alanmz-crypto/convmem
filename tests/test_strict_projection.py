"""T3 capability — collection-safe at T0a; red until T3 lands."""

from __future__ import annotations

import importlib.util


def test_strict_projection_capability_present():
    spec = importlib.util.find_spec('strict_projection')
    assert spec is not None, "[T3] module strict_projection absent"
    module = importlib.import_module('strict_projection')
    assert hasattr(module, 'open_public_projection'), "[T3] strict_projection.open_public_projection capability absent"
