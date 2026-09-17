"""C0: freeze exposure-window probe semantics on deterministic Chroma fixtures."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from doctor import _exposure_window_probe
from tests.watch_oom_exposure_hermetic import (
    EXPOSURE_ROW,
    exposure_c0_scenarios,
    exposure_cfg,
    write_probe_chroma,
)

GOLDEN = (
    Path(__file__).resolve().parent / "golden" / "watch-oom-bound-exposure" / "c0-oracle.json"
)


def _run_scenarios() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for case in exposure_c0_scenarios():
        with tempfile.TemporaryDirectory() as td:
            chroma = Path(td) / "chroma"
            write_probe_chroma(chroma, [dict(m) for m in case["metas"]])
            row = dict(EXPOSURE_ROW, **(case.get("row") or {}))
            due, detail = _exposure_window_probe(row, exposure_cfg(chroma))
        out[case["name"]] = {"due": due, "detail": detail}
    return out


class ExposureC0OracleTests(unittest.TestCase):
    def test_scenarios_match_golden_oracle(self) -> None:
        actual = _run_scenarios()
        self.assertTrue(GOLDEN.is_file(), f"missing golden oracle at {GOLDEN}")
        expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)

    def test_scenario_detail_substrings(self) -> None:
        for case in exposure_c0_scenarios():
            with tempfile.TemporaryDirectory() as td:
                chroma = Path(td) / "chroma"
                write_probe_chroma(chroma, [dict(m) for m in case["metas"]])
                row = dict(EXPOSURE_ROW, **(case.get("row") or {}))
                due, detail = _exposure_window_probe(row, exposure_cfg(chroma))
            self.assertEqual(due, case["due"], case["name"])
            for fragment in case.get("detail_contains") or []:
                self.assertIn(fragment, detail, case["name"])


if __name__ == "__main__":
    unittest.main()
