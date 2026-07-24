"""Fitness: MCP Roots URI normalization and project detection."""

from __future__ import annotations

import unittest

from pydantic import TypeAdapter, ValidationError
from mcp import types as mcp_types

import mcp_server


class McpRootsHelpers(unittest.TestCase):
    # Intentionally exercise module helpers under test.
    # pylint: disable=protected-access

    def test_normalize_bare_path_to_file_uri(self):
        uri = mcp_server._normalize_root_uri("/home/lauer/Projects/convmem")
        self.assertTrue(uri.startswith("file://"))
        self.assertIn("/home/lauer/Projects/convmem", uri)

    def test_normalize_passes_through_file_uri(self):
        raw = "file:///home/lauer/Projects/convmem"
        self.assertEqual(mcp_server._normalize_root_uri(raw), raw)

    def test_recover_uris_from_cursor_bare_path_validation_error(self):
        uris: list[str] = []
        try:
            TypeAdapter(mcp_types.ListRootsResult).validate_python(
                {"roots": [{"uri": "/home/lauer/Projects/convmem"}]}
            )
            self.fail("expected ValidationError")
        except ValidationError as exc:
            uris = mcp_server._uris_from_list_roots_validation_error(exc)
        self.assertEqual(len(uris), 1)
        self.assertIn("/home/lauer/Projects/convmem", uris[0])

    def test_root_uris_indicate_project_for_convmem(self):
        uris = ["file:///home/lauer/Projects/convmem"]
        self.assertTrue(mcp_server._root_uris_indicate_project(uris))

    def test_root_uris_reject_home_and_tmp(self):
        self.assertFalse(
            mcp_server._root_uris_indicate_project(["file:///home/lauer"])
        )
        self.assertFalse(
            mcp_server._root_uris_indicate_project(["file:///tmp/p13-crush-soak"])
        )

    def test_all_shell_tools_invoke_roots_boundary(self):
        """Bugbot: search/related must probe Roots on first call, not only gated tools."""
        import inspect

        for name in (
            "brief",
            "search_fast",
            "search",
            "ask",
            "unresolved",
            "related",
            "stats",
        ):
            src = inspect.getsource(getattr(mcp_server, name))
            self.assertIn(
                "_apply_shell_roots_brief_boundary_sync()",
                src,
                msg=f"{name} must call Roots boundary sync",
            )

    def test_non_project_roots_restore_brief_after_cwd_omit(self):
        """Bugbot: import cwd omit must not permanently drop brief under alien Roots."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        mcp_server._SHELL_ROOTS.project = None
        mcp_server._SHELL_ROOTS.boundary_applied = False

        # Simulate import-time omit
        from mcp.server.fastmcp.exceptions import ToolError

        for name in ("brief", "folder_state"):
            try:
                mcp_server.mcp.remove_tool(name)
            except ToolError:
                pass

        session = MagicMock()
        session.check_client_capability = MagicMock(return_value=True)
        session.list_roots = AsyncMock(
            return_value=MagicMock(
                roots=[MagicMock(uri="file:///tmp/alien-workspace")]
            )
        )
        session.send_tool_list_changed = AsyncMock()

        with patch.object(mcp_server, "_mcp_profile", return_value="shell"):
            asyncio.run(
                mcp_server._apply_shell_roots_brief_boundary_if_needed(session)
            )

        # pylint: disable-next=protected-access
        names = {t.name for t in mcp_server.mcp._tool_manager.list_tools()}
        self.assertIn("brief", names)
        self.assertIn("folder_state", names)
        self.assertFalse(mcp_server._SHELL_ROOTS.project)
        session.send_tool_list_changed.assert_awaited()

        # Leave tools registered for sibling tests in this process.

    def test_sync_boundary_on_running_loop_uses_cwd_not_nested_asyncio(self):
        """Crush hang class: sync tools must not nested-await list_roots."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        mcp_server._SHELL_ROOTS.project = None
        mcp_server._SHELL_ROOTS.boundary_applied = False

        session = MagicMock()
        session.check_client_capability = MagicMock(return_value=True)
        session.list_roots = AsyncMock(
            side_effect=AssertionError("list_roots must not run on live loop sync path")
        )

        async def _on_loop():
            with patch.object(mcp_server, "_mcp_profile", return_value="shell"), patch.object(
                mcp_server, "_mcp_request_session", return_value=session
            ), patch.object(
                mcp_server, "_cwd_is_project_root", return_value=True
            ):
                mcp_server._apply_shell_roots_brief_boundary_sync()
            self.assertTrue(mcp_server._SHELL_ROOTS.boundary_applied)
            self.assertTrue(mcp_server._SHELL_ROOTS.project)
            session.list_roots.assert_not_called()

        asyncio.run(_on_loop())


if __name__ == "__main__":
    unittest.main()
