"""Fixture-only ANN repeatability command tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_ann_repeatability_cli_emits_stable_assessment(tmp_path):
    reports = []
    queries = {"q1": ["u1", "u2", "u3", "u4", "u5"]}
    for index in range(3):
        path = tmp_path / f"realization-{index}.json"
        path.write_text(
            json.dumps(
                {
                    "realization": f"realization-{index}",
                    "evidence_verdict": "BETTER",
                    "queries": queries,
                }
            ),
            encoding="utf-8",
        )
        reports.append(path)
    out = tmp_path / "ann.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/eval_ann_repeatability.py"),
            "--authorize-fixture",
            *[item for path in reports for item in ("--realization-report", str(path))],
            "--out",
            str(out),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["assessment"]["ann_stability"] == "STABLE"
