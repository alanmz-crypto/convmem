"""Codex finding: crush-hook search_seen must inherit from base session like ritual.

_ritual_complete() checks progress-$base_session when CRUSH_SESSION_ID is
parent$$child, but _seen_search() only checked the child progress file — so
children that inherit ritual still got denied for survey tools.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "scripts" / "crush-hook-convmem-allow.sh"


@unittest.skipUnless(shutil.which("bash") and HOOK.is_file(), "needs bash + hook script")
class CrushHookSearchInheritanceTests(unittest.TestCase):
    def _run_hook(
        self,
        *,
        cache: Path,
        session: str,
        tool: str = "ls",
        command: str | None = None,
    ) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["XDG_CACHE_HOME"] = str(cache)
        env["CRUSH_SESSION_ID"] = session
        env["CRUSH_TOOL_NAME"] = tool
        if command is None:
            env.pop("CRUSH_TOOL_INPUT_COMMAND", None)
        else:
            env["CRUSH_TOOL_INPUT_COMMAND"] = command
        return subprocess.run(
            ["bash", str(HOOK)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_child_inherits_parent_search_seen(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d)
            ritual_dir = cache / "convmem-crush-ritual"
            ritual_dir.mkdir(parents=True)
            parent = "parent-sess"
            child = f"{parent}$$child-sess"
            # Parent completed full ritual + search; child has no local markers.
            for suffix in ("doctor", "brief", "unresolved", "search_seen"):
                (ritual_dir / f"progress-{parent}.{suffix}").touch()

            out = self._run_hook(cache=cache, session=child, tool="ls")
            self.assertEqual(
                out.returncode,
                0,
                f"child survey should allow when parent searched;\n"
                f"stdout={out.stdout!r}\nstderr={out.stderr!r}",
            )
            self.assertNotIn("corpus has the answers", out.stderr)

    def _touch_ritual(self, ritual_dir: Path, session: str) -> None:
        for suffix in ("doctor", "brief", "unresolved"):
            (ritual_dir / f"progress-{session}.{suffix}").touch()

    def test_index_denied_after_ritual_complete(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d)
            ritual_dir = cache / "convmem-crush-ritual"
            ritual_dir.mkdir(parents=True)
            session = "sess-index-deny"
            self._touch_ritual(ritual_dir, session)
            (ritual_dir / f"progress-{session}.search_seen").touch()

            out = self._run_hook(
                cache=cache,
                session=session,
                tool="bash",
                command="convmem index --file /tmp/foo.db",
            )
            self.assertEqual(out.returncode, 2, out.stderr)
            self.assertIn("index/add/verify denied", out.stderr)

    def test_doctor_still_allowed_after_ritual_complete(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d)
            ritual_dir = cache / "convmem-crush-ritual"
            ritual_dir.mkdir(parents=True)
            session = "sess-doctor-ok"
            self._touch_ritual(ritual_dir, session)

            out = self._run_hook(
                cache=cache,
                session=session,
                tool="bash",
                command="convmem doctor",
            )
            self.assertEqual(out.returncode, 0, out.stderr)


if __name__ == "__main__":
    unittest.main()
