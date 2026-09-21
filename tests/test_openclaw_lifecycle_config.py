"""T5 capability — collection-safe at T0a; red until T5 lands."""

from __future__ import annotations

import importlib.util


def test_openclaw_activation_controller_capability_present():
    spec = importlib.util.find_spec('openclaw_activation_controller')
    assert spec is not None, "[T5] module openclaw_activation_controller absent"
    module = importlib.import_module('openclaw_activation_controller')
    assert hasattr(module, 'lifecycle_config_core'), "[T5] openclaw_activation_controller.lifecycle_config_core capability absent"
