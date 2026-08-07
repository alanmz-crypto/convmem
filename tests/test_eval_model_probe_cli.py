"""Fixture-only CLI smoke for the non-mutating model probe lane."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_fixture_model_probe_cli_writes_probe_only(tmp_path):
    out = tmp_path / "probe.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/eval_model_probe.py"),
            "--authorize-fixture",
            "--model-tag",
            "fixture-model",
            "--model-digest",
            "fixture:digest",
            "--dimensions",
            "8",
            "--probe-text",
            "fixture probe",
            "--transform-id",
            "production_swap_v1",
            "--transform-sha256",
            "a" * 64,
            "--out",
            str(out),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["schema_version"] == "model_probe_v1"
    assert report["model_digest"] == "fixture:digest"
