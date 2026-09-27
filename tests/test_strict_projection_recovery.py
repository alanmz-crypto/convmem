"""T2 capability — collection-safe at T0a; red until T2 lands."""

from __future__ import annotations

import importlib.util


def test_strict_projection_publisher_capability_present():
    spec = importlib.util.find_spec('strict_projection_publisher')
    assert spec is not None, "[T2] module strict_projection_publisher absent"
    module = importlib.import_module('strict_projection_publisher')
    assert hasattr(module, "recover_projection"), (
        "[T2] strict_projection_publisher.recover_projection capability absent"
    )
