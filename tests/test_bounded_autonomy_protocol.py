"""Fitness checks for the Stage 3 convmem-default BOUNDED_AUTONOMY protocol slice.

Protects against standing-token bloat (word ceiling), surface drift (exact body
once on execution surfaces), accidental inheritance outside convmem routine work,
and ChatGPT strategy-pack omission.
"""

from __future__ import annotations

import unittest

from tests.protocol_slice_helpers import (
    assert_absent_from_chatgpt_pack,
    assert_exact_body_once_on_surfaces,
    canonical_slice_body,
)

OPT_IN_PHRASE = "Mode: bounded autonomy"
REVIEW_REQUIRED_PHRASE = "Mode: review required"
WORD_CEILING = 130
_SECTION = "BOUNDED_AUTONOMY"


def _canonical_body() -> str:
    return canonical_slice_body(_SECTION)


class BoundedAutonomyProtocolTests(unittest.TestCase):
    def test_canonical_body_word_ceiling(self):
        body = _canonical_body()
        words = body.split()
        self.assertLessEqual(
            len(words),
            WORD_CEILING,
            f"BOUNDED_AUTONOMY body is {len(words)} words (ceiling {WORD_CEILING})",
        )

    def test_convmem_only_default_for_routine_reversible(self):
        body = _canonical_body()
        self.assertIn("Default for Routine-reversible work only in convmem", body)
        self.assertNotIn("never default", body)

    def test_review_required_override(self):
        body = _canonical_body()
        self.assertIn(f"`{REVIEW_REQUIRED_PHRASE}`", body)
        self.assertIn("disables it", body)

    def test_opt_in_phrase_preserved(self):
        body = _canonical_body()
        self.assertIn(f"`{OPT_IN_PHRASE}`", body)
        self.assertIn("opts in where higher rules permit", body)

    def test_wordpress_probation_not_inherited(self):
        body = _canonical_body()
        self.assertIn("WordPress stays review-required pending separate probation", body)

    def test_excluded_domains_never_inherit(self):
        body = _canonical_body()
        self.assertIn(
            "Other repos, architecture, security, and external-configuration work never inherit it",
            body,
        )

    def test_exact_body_once_on_execution_surfaces(self):
        assert_exact_body_once_on_surfaces(
            self,
            _canonical_body(),
            label="BOUNDED_AUTONOMY",
            extra_once_phrases=(OPT_IN_PHRASE, REVIEW_REQUIRED_PHRASE),
        )

    def test_absent_from_chatgpt_strategy_pack(self):
        assert_absent_from_chatgpt_pack(
            self,
            _canonical_body(),
            forbidden_phrases=(OPT_IN_PHRASE, REVIEW_REQUIRED_PHRASE),
        )


if __name__ == "__main__":
    unittest.main()
