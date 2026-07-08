"""Tests for Planning Guide Contract v1 enforcement."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from doctor import _check_planning_guide_contract
from planning_contract import (
    CONTRACT_VERSION,
    HITL_STOP_MARKERS,
    REQUIRED_HEADINGS,
    REQUIRED_METADATA,
    validate_planning_guides,
)


def _valid_guide() -> str:
    meta_rows = "\n".join(f"| **{f}** | x |" for f in REQUIRED_METADATA)
    headings = "\n\n".join(f"{h}\n\nbody" for h in REQUIRED_HEADINGS)
    return (
        f"{headings}\n\n"
        f"## Phase Initialization\n\n| Field | Value |\n|---|---|\n{meta_rows}\n\n"
        f"Cursor must stop here.\n\nAwait HITL.\n"
    )


class TestPlanningGuideContract(unittest.TestCase):
    def test_valid_guide_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            guides = root / "docs" / "planning"
            guides.mkdir(parents=True)
            (guides / "REVISE-PLANNING.md").write_text(_valid_guide(), encoding="utf-8")
            self.assertEqual(validate_planning_guides(root), [])

    def test_missing_heading_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            guides = root / "docs" / "planning"
            guides.mkdir(parents=True)
            text = _valid_guide().replace("## Exit Criteria", "## Done")
            (guides / "BAD.md").write_text(text, encoding="utf-8")
            problems = validate_planning_guides(root)
            self.assertTrue(any("missing heading" in p for p in problems))

    def test_missing_hitl_marker_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            guides = root / "docs" / "planning"
            guides.mkdir(parents=True)
            text = _valid_guide().replace(HITL_STOP_MARKERS[0], "")
            (guides / "BAD.md").write_text(text, encoding="utf-8")
            problems = validate_planning_guides(root)
            self.assertTrue(any("HITL marker" in p for p in problems))

    def test_missing_metadata_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            guides = root / "docs" / "planning"
            guides.mkdir(parents=True)
            text = _valid_guide().replace("**Functions**", "**Foo**")
            (guides / "BAD.md").write_text(text, encoding="utf-8")
            problems = validate_planning_guides(root)
            self.assertTrue(any("Functions" in p for p in problems))

    def test_doctor_check_passes_on_repo_guides(self):
        c = _check_planning_guide_contract()
        self.assertTrue(c.ok, c.detail)
        self.assertIn(CONTRACT_VERSION, c.detail)

    def test_contract_md_not_checked_as_guide(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            guides = root / "docs" / "planning"
            guides.mkdir(parents=True)
            (guides / "CONTRACT.md").write_text("no headings", encoding="utf-8")
            self.assertIn("no planning guides", validate_planning_guides(root)[0])


if __name__ == "__main__":
    unittest.main()
