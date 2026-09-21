"""T1 capability — collection-safe at T0a; red until T1 lands."""

from __future__ import annotations

import importlib.util


def test_strict_evidence_state_capability_present():
    spec = importlib.util.find_spec('strict_evidence_state')
    assert spec is not None, "[T1] module strict_evidence_state absent"
    module = importlib.import_module('strict_evidence_state')
    assert hasattr(module, 'reduce_complete_bound_state'), "[T1] strict_evidence_state.reduce_complete_bound_state capability absent"
