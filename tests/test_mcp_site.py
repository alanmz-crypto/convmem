"""MCP site parameter wiring."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import mcp_server


class McpSiteTests(unittest.TestCase):
    @patch("query.query_units")
    def test_search_fast_blocked_until_brief_on_etc(self, mock_query):
        mcp_server._mcp_brief_called = False
        with patch.object(
            mcp_server, "_workspace_project_slug", return_value=("/etc", "etc")
        ):
            out = mcp_server.search_fast("pacman configuration")
        mock_query.assert_not_called()
        payload = __import__("json").loads(out)
        self.assertTrue(payload.get("blocked_until_brief"))

    @patch("query.query_units", return_value=[])
    def test_search_fast_passes_site(self, mock_query):
        mcp_server._mcp_brief_called = True
        mcp_server.search_fast("csp", site="staging2.willowyhollow.com")
        mock_query.assert_called_once_with(
            "csp", top_k=5, domain=None, site="staging2.willowyhollow.com"
        )

    @patch("query.query_units")
    def test_search_fast_blocks_off_topic_compose(self, mock_query):
        out = mcp_server.search_fast("Docker Compose plugin for VS Code")
        mock_query.assert_not_called()
        payload = __import__("json").loads(out)
        self.assertTrue(payload.get("blocked_off_topic"))
        self.assertEqual(payload.get("results"), [])

    @patch("brief.gather_brief_payload", return_value={"generated_at": "t", "projects": []})
    def test_brief_corrects_convmem_slug_from_cwd(self, mock_payload):
        with patch.object(mcp_server, "_workspace_project_slug", return_value=("/home/lauer/Projects/ComfyUIimprov", "comfyuiimprov")):
            out = mcp_server.brief(project="convmem")
        mock_payload.assert_called_once_with(with_tests=False, project="comfyuiimprov")
        payload = __import__("json").loads(out)
        self.assertEqual(payload["project_slug_corrected"]["to"], "comfyuiimprov")

    @patch("brief.gather_brief_payload", return_value={"generated_at": "t", "projects": []})
    def test_brief_skips_slug_inference_on_boot_entries(self, mock_payload):
        with patch.object(
            mcp_server,
            "_workspace_project_slug",
            return_value=("/boot/loader/entries", "entries"),
        ):
            out = mcp_server.brief(project="")
        mock_payload.assert_called_once_with(with_tests=False, project="")
        payload = __import__("json").loads(out)
        self.assertEqual(payload.get("brief_mode"), "system_runbook")
        self.assertEqual((payload.get("runbook_hint") or {}).get("subject"), "boot entries")

    @patch("brief.gather_brief_payload", return_value={"generated_at": "t", "projects": []})
    def test_brief_runbook_hint_pacman(self, mock_payload):
        with patch.object(
            mcp_server,
            "_workspace_project_slug",
            return_value=("/etc", "etc"),
        ):
            out = mcp_server.brief(project="")
        payload = __import__("json").loads(out)
        hint = payload.get("runbook_hint") or {}
        self.assertEqual(hint.get("subject"), "pacman configuration")
        self.assertIn("pacman", hint.get("suggested_search_fast", ""))

    @patch("brief.gather_brief_payload", return_value={"generated_at": "t", "projects": []})
    def test_brief_infers_slug_when_empty(self, mock_payload):
        with patch.object(
            mcp_server,
            "_workspace_project_slug",
            return_value=("/home/lauer/Projects/ComfyUIimprov", "comfyuiimprov"),
        ):
            mcp_server.brief(project="")
        mock_payload.assert_called_once_with(with_tests=False, project="comfyuiimprov")

    @patch(
        "brief.gather_brief_payload",
        return_value={
            "generated_at": "t",
            "projects": [
                {"slug": "convmem", "repo_path": "/home/lauer/Projects/convmem"},
                {"slug": "documents", "repo_path": "/home/lauer/Documents"},
            ],
            "recent_decisions": [{"id": "dec_prop_x"}],
        },
    )
    def test_brief_workspace_local_filters_unrelated_projects(self, mock_payload):
        with patch.object(
            mcp_server,
            "_workspace_project_slug",
            return_value=("/home/lauer/Documents", "documents"),
        ):
            out = mcp_server.brief(project="")
        mock_payload.assert_called_once_with(with_tests=False, project="")
        payload = __import__("json").loads(out)
        self.assertEqual(payload.get("brief_mode"), "workspace_local")
        self.assertEqual(len(payload.get("projects") or []), 1)
        self.assertEqual(payload["projects"][0]["slug"], "documents")
        self.assertEqual(payload.get("recent_decisions"), [])
        hint = payload.get("workspace_hint") or {}
        self.assertIn("documents", hint.get("suggested_search_fast", ""))
        self.assertIn("has_readme_md", hint)
        self.assertIn("mandatory_tool_order", hint)
        self.assertIn("Turn 1 MUST be MCP brief()", payload.get("answer_from", ""))

    @patch(
        "brief.gather_brief_payload",
        return_value={
            "generated_at": "t",
            "projects": [{"slug": "convmem", "repo_path": "/home/lauer/Projects/convmem"}],
            "recent_decisions": [{"id": "dec_prop_x"}],
        },
    )
    def test_brief_workspace_local_strips_global_noise_when_no_match(self, mock_payload):
        with patch.object(
            mcp_server,
            "_workspace_project_slug",
            return_value=("/home/lauer/Documents", "documents"),
        ):
            out = mcp_server.brief(project="")
        payload = __import__("json").loads(out)
        self.assertEqual(payload.get("projects"), [])
        self.assertEqual(payload.get("recent_decisions"), [])
        self.assertEqual(payload.get("brief_mode"), "workspace_local")

    @patch("query.query_units")
    def test_search_fast_blocked_until_brief_on_documents(self, mock_query):
        mcp_server._mcp_brief_called = False
        with patch.object(
            mcp_server,
            "_workspace_project_slug",
            return_value=("/home/lauer/Documents", "documents"),
        ):
            out = mcp_server.search_fast("documents crush catalog")
        mock_query.assert_not_called()
        payload = __import__("json").loads(out)
        self.assertTrue(payload.get("blocked_until_brief"))
        self.assertEqual(payload.get("brief_mode"), "workspace_local")

    @patch("brief.gather_brief_payload", return_value={"generated_at": "t", "projects": []})
    def test_folder_state_delegates_to_brief(self, mock_payload):
        out = mcp_server.folder_state(project="convem")
        mock_payload.assert_called_once_with(with_tests=False, project="convem")
        self.assertIn("generated_at", out)

    def test_mcp_instructions_workspace_local_cwd(self):
        import os

        with patch("os.getcwd", return_value="/home/linuxbrew"):
            text = mcp_server._build_mcp_instructions("BASE")
        self.assertIn("workspace_local", text)
        self.assertIn("folder_state()", text)
        self.assertIn("/home/linuxbrew", text)

    @patch("brief.gather_brief_payload", return_value={"generated_at": "t", "projects": []})
    def test_folder_state_ignores_project_slug_on_workspace_local(self, mock_payload):
        with patch.object(
            mcp_server,
            "_workspace_project_slug",
            return_value=("/home/linuxbrew", "linuxbrew"),
        ):
            out = mcp_server.folder_state(project="linuxbrew")
        mock_payload.assert_called_once_with(with_tests=False, project="")
        payload = __import__("json").loads(out)
        self.assertEqual(payload.get("brief_mode"), "workspace_local")
        self.assertIn("ignored", payload.get("project_slug_warning", ""))

    @patch("ask.ask", return_value={"answer": "ok", "citations": []})
    def test_ask_passes_site(self, mock_ask):
        mcp_server.ask("csp status", site="staging2.willowyhollow.com")
        mock_ask.assert_called_once_with(
            "csp status",
            top_k=5,
            domain=None,
            site="staging2.willowyhollow.com",
            raw=False,
            evidence=False,
        )

    @patch("brief.gather_brief_payload", return_value={"generated_at": "t", "projects": []})
    def test_brief_mcp_calls_payload(self, mock_payload):
        out = mcp_server.brief(project="willowyhollow-dev", with_tests=False)
        mock_payload.assert_called_once_with(with_tests=False, project="willowyhollow-dev")
        self.assertIn("generated_at", out)


if __name__ == "__main__":
    unittest.main()
