"""Fitness checks for the TEAM_CHARTER protocol slice.

Protects against:
- Token bloat (word ceiling 360)
- Surface drift (exact body once on all five execution surfaces)
- ChatGPT strategy-pack omission
- Five-field Sol-High gate semantics (exact field names, not generic)
- `defer` treated as a valid opposing verdict (must be excluded)
- Lifecycle prose / mermaid / embedding worked-example leaking into compact body
"""

from __future__ import annotations

import re
import unittest

from tests.protocol_slice_helpers import (
    SSOT,
    assert_absent_from_chatgpt_pack,
    assert_exact_body_once_on_surfaces,
    canonical_slice_body,
)

WORD_CEILING = 360
_SECTION = "TEAM_CHARTER"

# Five-field semantic anchors — these are the exact field names required in the
# Sol-High conflict summary template. Generic label checks (e.g. "Verdict A")
# are insufficient; the test asserts the semantically correct names.
FIVE_FIELD_ANCHORS = (
    "Artifact:",  # field 1 — exact review target
    "GitHub Copilot audit-lane verdict:",  # field 2 — Copilot audit lane PASS/FAIL
    "Kiro verdict:",  # field 3 — Kiro PASS/FAIL
    "Material proposition in conflict:",  # field 4 — the specific factual claim
    "Negative confirmation:",  # field 5 — not single-FAIL/deferral/etc.
)

# Phrases that must NOT appear in the compact body (lifecycle prose / mermaid /
# embedding worked-example content belongs only in the full charter).
BANNED_IN_COMPACT = (
    "mermaid",
    "flowchart",
    "Stage 0",
    "Stage 1",
    "Auth-R1",
    "Auth-R2",
    "B-Accept",
    "nine-stage",
    "worked example",
)

# `defer` must be explicitly excluded as a valid verdict — the gate requires
# PASS or FAIL. If the compact body contains a template line allowing defer,
# the gate is broken.
DEFER_VALID_VERDICT_PATTERN = re.compile(
    r"PASS\|FAIL\|defer",  # old template form that allowed defer as verdict
)


def _canonical_body() -> str:
    return canonical_slice_body(_SECTION)


class TeamCharterWordCeilingTests(unittest.TestCase):
    def test_canonical_body_word_ceiling(self):
        body = _canonical_body()
        words = body.split()
        self.assertLessEqual(
            len(words),
            WORD_CEILING,
            f"TEAM_CHARTER body is {len(words)} words (ceiling {WORD_CEILING})",
        )

    def test_single_charter_start_end_markers(self):
        text = SSOT.read_text(encoding="utf-8")
        self.assertEqual(
            text.count("<!-- TEAM_CHARTER_START -->"),
            1,
            "Expected exactly one TEAM_CHARTER_START marker in agent-protocol.md",
        )
        self.assertEqual(
            text.count("<!-- TEAM_CHARTER_END -->"),
            1,
            "Expected exactly one TEAM_CHARTER_END marker in agent-protocol.md",
        )

    def test_canonical_body_nonempty(self):
        body = _canonical_body()
        self.assertTrue(body, "TEAM_CHARTER canonical body is empty")


class TeamCharterSurfaceTests(unittest.TestCase):
    def test_exact_body_once_on_all_execution_surfaces(self):
        assert_exact_body_once_on_surfaces(
            self,
            _canonical_body(),
            label="TEAM_CHARTER",
        )

    def test_absent_from_chatgpt_strategy_pack(self):
        assert_absent_from_chatgpt_pack(
            self,
            _canonical_body(),
            forbidden_phrases=("Sol-High hard gate",),
        )


class TeamCharterSolHighGateTests(unittest.TestCase):
    def test_five_field_anchors_present(self):
        """All five semantic field names must appear in the compact body."""
        body = _canonical_body()
        for anchor in FIVE_FIELD_ANCHORS:
            with self.subTest(anchor=anchor):
                self.assertIn(
                    anchor,
                    body,
                    f"Five-field Sol-High gate: required field anchor '{anchor}' "
                    f"missing from compact TEAM_CHARTER body",
                )

    def test_defer_not_valid_opposing_verdict(self):
        """The compact body must not contain `PASS|FAIL|defer` — defer is not
        a valid Sol-High verdict and must be excluded from the template."""
        body = _canonical_body()
        self.assertIsNone(
            DEFER_VALID_VERDICT_PATTERN.search(body),
            "Compact TEAM_CHARTER body contains 'PASS|FAIL|defer' — "
            "`defer` must not be offered as a valid Sol-High verdict. "
            "Template must allow PASS|FAIL only.",
        )

    def test_defer_explicitly_excluded(self):
        """The compact body must positively state that defer is not a valid verdict."""
        body = _canonical_body()
        excluded = (
            "`defer` is never a valid opposing verdict" in body
            or "not defer" in body
        )
        self.assertTrue(
            excluded,
            "Compact TEAM_CHARTER body must explicitly exclude `defer` as a "
            "valid verdict (e.g. '`defer` is never a valid opposing verdict' "
            "or 'not defer' in gate description)",
        )

    def test_all_negative_conditions_explicitly_excluded(self):
        """Every non-conflict condition must appear in the compact gate."""
        body = _canonical_body().lower()
        for condition in (
            "single-fail",
            "deferral",
            "abstention",
            "silence",
            "missing",
            "incomplete",
            "different revision",
        ):
            with self.subTest(condition=condition):
                self.assertIn(
                    condition,
                    body,
                    f"Compact Sol-High gate must exclude {condition}",
                )

    def test_copilot_and_sol_high_are_separate(self):
        """The compact body must distinguish the Copilot audit lane from Sol-High."""
        body = _canonical_body()
        self.assertIn(
            "GitHub Copilot audit lane",
            body,
            "Compact body must name 'GitHub Copilot audit lane' explicitly",
        )
        self.assertIn(
            "Sol-High",
            body,
            "Compact body must name 'Sol-High' explicitly",
        )
        self.assertIn(
            "separate",
            body,
            "Compact body must state Sol-High is a separate resource from "
            "the Copilot audit lane",
        )

    def test_pr52_non_example_present(self):
        body = _canonical_body()
        self.assertIn(
            "PR #52",
            body,
            "Compact body must preserve the PR #52 non-example",
        )


class TeamCharterNoBannedContentTests(unittest.TestCase):
    def test_no_lifecycle_prose_in_compact_body(self):
        """Lifecycle prose, mermaid diagrams, and embedding worked-example
        content must not appear in the compact TEAM_CHARTER body."""
        body = _canonical_body()
        for banned in BANNED_IN_COMPACT:
            with self.subTest(banned=banned):
                self.assertNotIn(
                    banned,
                    body,
                    f"Compact TEAM_CHARTER body must not contain '{banned}' "
                    f"(lifecycle prose / mermaid / embedding worked example "
                    f"belongs in full charter only)",
                )


if __name__ == "__main__":
    unittest.main()
