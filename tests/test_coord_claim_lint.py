"""Tests for inter-model coordination claim lint."""

from __future__ import annotations

import unittest

from coord_claim_lint import lint_inter_model_text


class CoordClaimLintTests(unittest.TestCase):
    def test_allows_narrative_tests_passed(self):
        text = "## What happened\n\nThe tests passed after the fix.\n"
        self.assertEqual(lint_inter_model_text(text), [])

    def test_flags_soak_passed_on_bullet_line(self):
        text = "## State\n\n- soak passed on this PID\n"
        self.assertEqual(len(lint_inter_model_text(text)), 1)

    def test_flags_soak_passed_on_next_line_after_blank(self):
        text = "## State\n\nsoak passed\n"
        self.assertEqual(len(lint_inter_model_text(text)), 1)

    def test_no_paragraph_bypass(self):
        text = "## Decision\n\ndec_prop_20260623_004023_44a1 is unrelated\n\n- soak passed\n"
        self.assertEqual(len(lint_inter_model_text(text)), 1)

    def test_allows_soak_passed_with_dec_on_same_line(self):
        text = "## State\n\n- soak passed per dec_prop_20260623_004023_44a1\n"
        self.assertEqual(lint_inter_model_text(text), [])

    def test_flags_signed_off_in_decision(self):
        text = "## Decision\n\nWatch stability: signed off.\n"
        self.assertEqual(len(lint_inter_model_text(text)), 1)

    def test_flags_table_cell_line(self):
        text = "## Verdict\n\n| check | status |\n| soak | passed |\n"
        self.assertEqual(len(lint_inter_model_text(text)), 1)


if __name__ == "__main__":
    unittest.main()
