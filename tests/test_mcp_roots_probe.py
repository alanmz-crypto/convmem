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


if __name__ == "__main__":
    unittest.main()
