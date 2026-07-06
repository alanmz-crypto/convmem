"""Tests for next-step hint footers."""

from __future__ import annotations

import os
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

import typer

from next_steps import (
    after_doctor,
    after_search,
    emit_next_steps,
    script_hints,
    workspace_context,
)


class NextStepsTests(unittest.TestCase):
    def test_emit_disabled_by_env(self):
        buf = StringIO()
        with mock.patch.dict(os.environ, {"CONVMEM_NO_NEXT_STEPS": "1"}):
            with mock.patch.object(typer, "echo", side_effect=lambda s, **k: buf.write(str(s) + "\n")):
                emit_next_steps(["should not print"])
        self.assertEqual(buf.getvalue(), "")

    def test_emit_prints_header(self):
        buf = StringIO()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CONVMEM_NO_NEXT_STEPS", None)
            with mock.patch.object(typer, "echo", side_effect=lambda s, **k: buf.write(str(s) + "\n")):
                emit_next_steps(["line one"])
        self.assertIn("Next steps", buf.getvalue())
        self.assertIn("line one", buf.getvalue())

    def test_workspace_willowyhollow_practice(self):
        practice = Path("/home/lauer/WordPress/willowyhollow-practice")
        with mock.patch.object(Path, "cwd", return_value=practice):
            ctx = workspace_context()
        self.assertEqual(ctx["lane"], "willowyhollow-practice")
        self.assertEqual(ctx["staging_site"], "staging2.willowyhollow.com")

    def test_after_doctor_pass_includes_brief(self):
        buf = StringIO()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CONVMEM_NO_NEXT_STEPS", None)
            with mock.patch("next_steps.workspace_context", return_value={"lane": "general"}):
                with mock.patch.object(typer, "echo", side_effect=lambda s, **k: buf.write(str(s) + "\n")):
                    after_doctor(passed=True)
        self.assertIn("brief", buf.getvalue())

    def test_after_search_zero_hits_suggests_ask(self):
        buf = StringIO()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CONVMEM_NO_NEXT_STEPS", None)
            with mock.patch(
                "next_steps.workspace_context",
                return_value={"lane": "willowyhollow-practice"},
            ):
                with mock.patch.object(typer, "echo", side_effect=lambda s, **k: buf.write(str(s) + "\n")):
                    after_search(query="deploy", site=None, n_results=0)
        self.assertIn("ask", buf.getvalue())
        self.assertIn("Deploy Workflow", buf.getvalue())

    def test_script_hints_digest(self):
        buf = StringIO()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CONVMEM_NO_NEXT_STEPS", None)
            with mock.patch.object(typer, "echo", side_effect=lambda s, **k: buf.write(str(s) + "\n")):
                script_hints("cross-project-digest", skip_ask=True)
        self.assertIn("smoke-cross-project-digest", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
