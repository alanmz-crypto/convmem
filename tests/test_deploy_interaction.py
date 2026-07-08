"""Combined-effect test for the deploy-script interaction (register row: deploy-script-interaction).

Exercises the real interaction between deploy-agent-protocol.sh and
deploy-builder-reference.sh without repo side effects (Variant B):

- deploy-agent-protocol.sh's crush stanza only prepends CONVMEM-RITUAL.md when
  missing, then chains deploy-builder-reference.sh as the designated last
  writer. Running the full protocol script here would regenerate repo
  artifacts (generate-agent-protocol.sh), so instead the test seeds a sandbox
  crush.json in the worst state the protocol stanza plus historical drift can
  produce (digests first, ritual mid-list, CRUSH.md not last) and runs
  deploy-builder-reference.sh against it.
- Asserts the canonical final order (ritual first, CRUSH.md last, no
  duplicates) and idempotence on a second run — the exact regression class
  behind the 2026-07-07 merge-order incident (insert-at-front + presence-only
  idempotence check).

Path-matching fidelity: the re-sort in deploy-builder-reference.sh matches
digest entries by absolute expanded path but the ritual/CRUSH.md markers as
literal "~/..." strings. The seed mirrors that, matching real-config state.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "deploy-builder-reference.sh"

RITUAL = "~/.config/crush/CONVMEM-RITUAL.md"
CRUSH_MD = "~/.config/crush/CRUSH.md"
DIGEST_NAMES = (
    "ousterhout",
    "manning",
    "zeller",
    "hard-parts",
    "ddia",
    "arch-patterns-python",
    "evolutionary-architectures",
)


@unittest.skipUnless(shutil.which("bash") and shutil.which("python3"), "needs bash + python3")
class DeployInteractionTests(unittest.TestCase):
    def _seed_sandbox(self, home: Path) -> Path:
        """Sandbox crush.json in scrambled order: digests first, ritual mid, CRUSH.md not last."""
        crush_dir = home / ".config" / "crush"
        crush_dir.mkdir(parents=True)
        # Digest entries as absolute sandbox paths — how the deploy script writes them.
        digest = lambda name: str(crush_dir / "rules" / f"builder-reference-{name}.md")  # noqa: E731
        scrambled = [
            digest("ddia"),
            digest("ousterhout"),
            CRUSH_MD,
            RITUAL,
            "~/.config/crush/rules/convmem.md",  # non-digest context entry, must survive in middle
            digest("manning"),
        ]
        config = crush_dir / "crush.json"
        config.write_text(
            json.dumps({"options": {"global_context_paths": scrambled}}, indent=2) + "\n",
            encoding="utf-8",
        )
        return config

    def _run_deploy(self, home: Path) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["HOME"] = str(home)  # set, never unset — the scripts default to /home/lauer
        return subprocess.run(
            ["bash", str(DEPLOY_SCRIPT)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    @staticmethod
    def _paths(config: Path) -> list:
        return json.loads(config.read_text(encoding="utf-8"))["options"]["global_context_paths"]

    def test_combined_effect_order_and_idempotence(self):
        real_config = Path.home() / ".config" / "crush" / "crush.json"
        real_mtime = real_config.stat().st_mtime_ns if real_config.is_file() else None

        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            config = self._seed_sandbox(home)

            first = self._run_deploy(home)
            self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
            paths = self._paths(config)

            basenames = [Path(str(p)).name for p in paths]
            self.assertEqual(basenames[0], "CONVMEM-RITUAL.md", paths)
            self.assertEqual(basenames[-1], "CRUSH.md", paths)
            self.assertEqual(len(paths), len(set(paths)), f"duplicate entries: {paths}")
            self.assertIn("~/.config/crush/rules/convmem.md", paths)  # middle entries survive
            for name in DIGEST_NAMES:  # all 7 digests present, between middle and CRUSH.md
                self.assertIn(f"builder-reference-{name}.md", basenames)
            digest_idx = [i for i, b in enumerate(basenames) if b.startswith("builder-reference-")]
            self.assertEqual(digest_idx, list(range(digest_idx[0], digest_idx[0] + 7)))
            self.assertLess(basenames.index("convmem.md"), digest_idx[0])

            second = self._run_deploy(home)
            self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
            self.assertEqual(
                self._paths(config), paths, "second deploy changed order — not idempotent"
            )

        if real_mtime is not None:
            self.assertEqual(
                real_config.stat().st_mtime_ns, real_mtime, "test touched the real crush.json"
            )

    def _seed_sandbox_ritual_absent(self, home: Path) -> Path:
        """Digests + CRUSH.md present; ritual marker missing (partial migration)."""
        crush_dir = home / ".config" / "crush"
        crush_dir.mkdir(parents=True)
        digest = lambda name: str(crush_dir / "rules" / f"builder-reference-{name}.md")  # noqa: E731
        partial = [
            digest("ousterhout"),
            digest("manning"),
            "~/.config/crush/rules/convmem.md",
            CRUSH_MD,
        ]
        config = crush_dir / "crush.json"
        config.write_text(
            json.dumps({"options": {"global_context_paths": partial}}, indent=2) + "\n",
            encoding="utf-8",
        )
        return config

    def test_restores_ritual_when_absent_from_paths(self):
        """Codex finding: last-writer must prepend ritual when marker is missing."""
        real_config = Path.home() / ".config" / "crush" / "crush.json"
        real_mtime = real_config.stat().st_mtime_ns if real_config.is_file() else None

        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            config = self._seed_sandbox_ritual_absent(home)

            first = self._run_deploy(home)
            self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
            paths = self._paths(config)
            basenames = [Path(str(p)).name for p in paths]
            self.assertEqual(basenames[0], "CONVMEM-RITUAL.md", paths)
            self.assertEqual(basenames[-1], "CRUSH.md", paths)
            self.assertEqual(paths.count(RITUAL), 1)

            second = self._run_deploy(home)
            self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
            self.assertEqual(
                self._paths(config), paths, "second deploy changed order — not idempotent"
            )

        if real_mtime is not None:
            self.assertEqual(
                real_config.stat().st_mtime_ns, real_mtime, "test touched the real crush.json"
            )


if __name__ == "__main__":
    unittest.main()
