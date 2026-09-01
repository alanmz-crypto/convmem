"""Tests for the narrow, non-leaking provider-pattern scanner."""

from __future__ import annotations

import unittest
from pathlib import Path

from extract_procedures import DEFAULT_OUTPUT
from scripts.secret_scan import find_secret_types


class SecretPatternTests(unittest.TestCase):
    def test_obvious_placeholders_are_not_provider_credentials(self):
        for text in (
            "DEEPSEEK_API_KEY=REPLACE_ME",
            "DEEPSEEK_API_KEY=your-key-here",
            '"DEEPSEEK_API_KEY": "REPLACE_ME_OR_OMIT_IF_IN_env.local"',
            "GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }}",
        ):
            self.assertEqual(find_secret_types(text), ())

    def test_shell_option_is_not_a_deepseek_key(self):
        self.assertEqual(find_secret_types("--disk-cache-dir=/tmp/cache"), ())

    def test_labels_do_not_include_matched_text(self):
        labels = find_secret_types("DEEPSEEK_API_KEY=REPLACE_ME")
        self.assertTrue(all("REPLACE_ME" not in label for label in labels))

    def test_procedure_export_defaults_outside_repository(self):
        self.assertEqual(DEFAULT_OUTPUT.name, "procedures.jsonl")
        self.assertNotEqual(DEFAULT_OUTPUT.parent, Path.cwd())


if __name__ == "__main__":
    unittest.main()
