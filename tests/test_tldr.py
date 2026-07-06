"""Tests for convmem tldr command."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from tldr import list_lanes, read_tldr, resolve_tldr_path


class TldrTests(unittest.TestCase):
    def test_list_lanes(self):
        names = list_lanes()
        self.assertIn("convmem", names)
        self.assertIn("willowyhollow-practice", names)

    def test_resolve_willowyhollow_from_cwd(self):
        practice = Path("/home/lauer/WordPress/willowyhollow-practice")
        with mock.patch.object(Path, "cwd", return_value=practice):
            path = resolve_tldr_path()
        self.assertTrue(path.name.endswith("WILLOWYHOLLOW-TLDR.md"))

    def test_resolve_explicit_lane(self):
        path = resolve_tldr_path(lane="convmem")
        self.assertTrue(path.name.endswith("CONVMEM-TLDR.md"))

    def test_read_tldr_nonempty(self):
        text = read_tldr(lane="convmem")
        self.assertIn("convmem doctor", text)


if __name__ == "__main__":
    unittest.main()
