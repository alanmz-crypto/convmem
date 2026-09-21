"""T1 capability — collection-safe at T0a; red until T1 lands."""

from __future__ import annotations

import importlib.util


def test_bound_read_scope_capability_present():
    spec = importlib.util.find_spec('bound_read_scope')
    assert spec is not None, "[T1] module bound_read_scope absent"
    module = importlib.import_module('bound_read_scope')
    assert hasattr(module, 'resolve_scope'), "[T1] bound_read_scope.resolve_scope capability absent"
