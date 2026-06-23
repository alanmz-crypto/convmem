"""Tests for per-project brief rollup."""

from __future__ import annotations

import unittest

from brief import gather_project_activity, resolve_project_from_path


class BriefProjectTests(unittest.TestCase):
    def test_cursor_project_path(self):
        path = (
            "/home/lauer/.cursor/projects/home-lauer-GitClones-willowyhollow-dev/"
            "agent-transcripts/x/x.jsonl"
        )
        slug, repo = resolve_project_from_path(path)
        self.assertEqual(slug, "willowyhollow-dev")
        self.assertTrue(repo.endswith("GitClones/willowyhollow-dev"))

    def test_projects_wp_sec_agent(self):
        path = (
            "/home/lauer/.cursor/projects/home-lauer-Projects-wp-sec-agent/"
            "agent-transcripts/y/y.jsonl"
        )
        slug, repo = resolve_project_from_path(path)
        self.assertEqual(slug, "wp-sec-agent")
        self.assertTrue(repo.endswith("Projects/wp-sec-agent"))

    def test_crush_db_under_repo(self):
        path = "/home/lauer/GitClones/willowyhollow-dev/.crush/crush.db"
        slug, repo = resolve_project_from_path(path)
        self.assertEqual(slug, "willowyhollow-dev")
        self.assertTrue(repo.endswith("GitClones/willowyhollow-dev"))

    def test_gather_project_filter(self):
        from unittest.mock import patch

        cfg = {
            "sources": {
                "inventory": "/tmp/inv.jsonl",
            }
        }

        class FakePath:
            def __init__(self, path):
                self._path = path

            def expanduser(self):
                return self

            def is_file(self):
                return False

        with patch("brief._load_inventory_records", return_value=[]):
            with patch(
                "brief.collection_metadata_rows",
                return_value=[
                    {
                        "source_path": (
                            "/home/lauer/.cursor/projects/"
                            "home-lauer-GitClones-willowyhollow-dev/"
                            "agent-transcripts/a/a.jsonl"
                        ),
                        "title": "Aider handoff",
                        "timestamp": "2026-06-01T00:00:00Z",
                    }
                ],
            ):
                rows = gather_project_activity(
                    cfg, "/tmp/chroma", project_filter="willowyhollow-dev"
                )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["slug"], "willowyhollow-dev")
        self.assertIn("handoff", rows[0]["entry_search"])


if __name__ == "__main__":
    unittest.main()
