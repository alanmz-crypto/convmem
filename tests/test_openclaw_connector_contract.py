"""Connector contract — T0a refusal green; T4 capability red."""

from __future__ import annotations

from pathlib import Path


def test_connector_package_files_exist():
    root = Path("integrations/openclaw-convmem-reader")
    assert (root / "index.js").is_file()
    assert (root / "package.json").is_file()
    assert (root / "openclaw.plugin.json").is_file()
    assert (root / "test" / "connector.test.mjs").is_file()


def test_t4_launch_tuple_validation_capability_absent():
    text = Path("integrations/openclaw-convmem-reader/index.js").read_text(encoding="utf-8")
    assert "validateLaunchTuple" in text, "[T4] connector launch-tuple validation capability absent"
