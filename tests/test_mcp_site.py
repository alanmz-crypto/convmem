"""MCP site parameter wiring."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import mcp_server


class McpSiteTests(unittest.TestCase):
    @patch("query.query_units", return_value=[])
    def test_search_fast_passes_site(self, mock_query):
        mcp_server.search_fast("csp", site="staging2.willowyhollow.com")
        mock_query.assert_called_once_with(
            "csp", top_k=5, domain=None, site="staging2.willowyhollow.com"
        )

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


if __name__ == "__main__":
    unittest.main()
