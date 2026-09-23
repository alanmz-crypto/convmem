"""Lifecycle config core — T5 capability + closed disable invariants (M6)."""

from __future__ import annotations

import importlib.util

import pytest


def test_openclaw_activation_controller_capability_present():
    spec = importlib.util.find_spec("openclaw_activation_controller")
    assert spec is not None, "[T5] module openclaw_activation_controller absent"
    module = importlib.import_module("openclaw_activation_controller")
    assert hasattr(
        module, "lifecycle_config_core"
    ), "[T5] openclaw_activation_controller.lifecycle_config_core capability absent"


def test_lifecycle_config_core_requires_all_disables():
    import openclaw_activation_controller as ctl

    core = ctl.lifecycle_config_core({})
    assert core["native_memory"] is False
    assert core["automatic_memory_flush"] is False
    assert core["heartbeat"] is False
    assert core["acp"] is False
    assert core["automatic_transcript_capture"] is False
    assert core["provider_fallback"] is False
    with pytest.raises(ValueError, match="lifecycle_not_disabled:heartbeat"):
        ctl.lifecycle_config_core({"heartbeat": True})
    with pytest.raises(ValueError, match="provider_fallback"):
        ctl.lifecycle_config_core({"provider_fallback": True})
