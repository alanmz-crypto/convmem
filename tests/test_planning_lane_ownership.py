"""Fitness tests for Codex planning / Cursor implementation lane ownership."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from tests.protocol_slice_helpers import REPO_ROOT, canonical_slice_body

LIVE_SOURCES = (
    REPO_ROOT / "docs/inter-model/TEAM-CHARTER-2026-07-06.md",
    REPO_ROOT / "docs/AGENT-ROLES.md",
    REPO_ROOT / "docs/PLANNING-PROTOCOL.md",
    REPO_ROOT / "docs/MODEL-WORKFLOW.md",
    REPO_ROOT / "config/agent-protocol.md",
    REPO_ROOT / "docs/planning/ARCHITECTURE-PLANNING.md",
    REPO_ROOT / "docs/planning/EXECUTION-PLANNING.md",
    REPO_ROOT / "docs/planning/EXECUTE-TASK.md",
    REPO_ROOT / "docs/planning/VERIFY-PLANNING.md",
    REPO_ROOT / "docs/planning/REVISE-PLANNING.md",
)

STALE_LIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Cursor creates architecture plan"),
    re.compile(r"Cursor creates execution plan"),
    re.compile(r"Cursor revises architecture"),
    re.compile(r"Cursor revises execution plan"),
    re.compile(r"Cursor owns architecture, execution planning, and implementation"),
    re.compile(r"Codex read-only if Ryan requests direction audit"),
    re.compile(r"Codex read-only if Ryan requests plan audit"),
    re.compile(r"Codex audit is post-handoff only"),
    re.compile(
        r"Architecture, planning, cross-doc, long reasoning — default lead"
    ),
)

POSITIVE_ANCHORS: tuple[tuple[str, Path, str], ...] = (
    (
        "Codex authors approved architecture and execution plans",
        REPO_ROOT / "docs/PLANNING-PROTOCOL.md",
        "planning doctrine",
    ),
    (
        "OpenAI Codex authors Architecture Direction",
        REPO_ROOT / "docs/planning/ARCHITECTURE-PLANNING.md",
        "architecture planning lane",
    ),
    (
        "OpenAI Codex authors execution plan",
        REPO_ROOT / "docs/planning/EXECUTION-PLANNING.md",
        "execution planning lane",
    ),
    (
        "rejection routes to Ryan before Codex revises",
        REPO_ROOT / "docs/planning/EXECUTION-PLANNING.md",
        "Kiro rejection routing",
    ),
    (
        "Codex is upstream planner, not default post-handoff auditor",
        REPO_ROOT / "docs/planning/EXECUTE-TASK.md",
        "execute task Codex boundary",
    ),
    (
        "PR Steward requires separate Ryan grant",
        REPO_ROOT / "docs/planning/EXECUTE-TASK.md",
        "PR Steward separation",
    ),
    (
        "Codex predeclares VERIFY checks/stub during planning",
        REPO_ROOT / "docs/planning/VERIFY-PLANNING.md",
        "verify predeclare lane",
    ),
    (
        "Codex owns plan revision",
        REPO_ROOT / "docs/planning/REVISE-PLANNING.md",
        "revise planning owner",
    ),
    (
        "Kiro rejection of an Execution Plan goes to Ryan before Codex may revise",
        REPO_ROOT / "docs/inter-model/TEAM-CHARTER-2026-07-06.md",
        "charter rejection routing",
    ),
    (
        "does not substitute for Kiro design sign-off on the governing plan",
        REPO_ROOT / "docs/inter-model/TEAM-CHARTER-2026-07-06.md",
        "Copilot non-substitution",
    ),
    (
        "never inferred",
        REPO_ROOT / "docs/inter-model/TEAM-CHARTER-2026-07-06.md",
        "PR Steward never inferred",
    ),
    (
        "Crush proposes defect classification",
        REPO_ROOT / "docs/inter-model/TEAM-CHARTER-2026-07-06.md",
        "three-arc classification",
    ),
    (
        "No arrow grants the receiving lane permission to merge, deploy, write the ledger, or self-advance the phase",
        REPO_ROOT / "docs/inter-model/TEAM-CHARTER-2026-07-06.md",
        "no inferred authority arrow rule",
    ),
    (
        "Default author of approved **architecture and execution plans**",
        REPO_ROOT / "docs/AGENT-ROLES.md",
        "Codex planning in lane registry",
    ),
    (
        "Architecture and execution planning → OpenAI Codex",
        REPO_ROOT / "docs/AGENT-ROLES.md",
        "lane routing prose",
    ),
    (
        "Architecture and execution planning (Kiro review; Ryan approves)",
        REPO_ROOT / "docs/MODEL-WORKFLOW.md",
        "Codex default planning route",
    ),
    (
        "Ryan-selected (e.g. Grok)",
        REPO_ROOT / "docs/MODEL-WORKFLOW.md",
        "Cursor model choice",
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class PlanningLaneOwnershipTests(unittest.TestCase):
    def test_positive_anchors_present(self):
        for phrase, path, label in POSITIVE_ANCHORS:
            with self.subTest(label=label, path=path.name):
                self.assertIn(phrase, _read(path), f"missing anchor in {label}")

    def test_stale_live_phrases_absent(self):
        for path in LIVE_SOURCES:
            text = _read(path)
            for pattern in STALE_LIVE_PATTERNS:
                with self.subTest(path=path.name, pattern=pattern.pattern):
                    self.assertIsNone(
                        pattern.search(text),
                        f"stale lane text {pattern.pattern!r} in {path}",
                    )

    def test_compact_charter_planning_route(self):
        body = canonical_slice_body("TEAM_CHARTER")
        self.assertIn(
            "Codex authors approved architecture and execution plans",
            body,
        )
        self.assertIn("Cursor implements after Ryan authorization", body)


if __name__ == "__main__":
    unittest.main()
