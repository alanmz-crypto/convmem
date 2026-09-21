"""T1 capability — collection-safe at T0a; red until T1 lands."""

from __future__ import annotations

import importlib.util


def test_strict_grounding_capability_present():
    spec = importlib.util.find_spec('strict_grounding')
    assert spec is not None, "[T1] module strict_grounding absent"
    module = importlib.import_module('strict_grounding')
    assert hasattr(module, 'qualify_grounding'), "[T1] strict_grounding.qualify_grounding capability absent"
