"""Combined-effect test for the deploy-script interaction (register row: deploy-script-interaction).

Exercises deploy-builder-reference.sh without touching the real crush.json:

- Seeds a sandbox crush.json in a scrambled pre-Stage-4 state (digests listed
  individually, ritual mid-list).
- Asserts Stage 4 approach A final standing paths: ritual → rules/ → CRUSH.md,
  digests absent from global_context_paths, digests present under
  builder-reference/, pointer under rules/, and idempotence on a second run.
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
RULES = "~/.config/crush/rules/"
CRUSH_MD = "~/.config/crush/CRUSH.md"
EXPECTED = [RITUAL, RULES, CRUSH_MD]
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
        """Sandbox crush.json in scrambled pre-demotion order."""
        crush_dir = home / ".config" / "crush"
        rules = crush_dir / "rules"
        rules.mkdir(parents=True)
        digest = lambda name: str(rules / f"builder-reference-{name}.md")  # noqa: E731
        # Leave stale digest files under rules/ so deploy must migrate them.
        for name in DIGEST_NAMES:
            (rules / f"builder-reference-{name}.md").write_text(
                f"# stub {name}\n", encoding="utf-8"
            )
        scrambled = [
            digest("ddia"),
            digest("ousterhout"),
            CRUSH_MD,
            RITUAL,
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
        env["HOME"] = str(home)
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
            crush_dir = home / ".config" / "crush"

            first = self._run_deploy(home)
            self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
            paths = self._paths(config)
            self.assertEqual(paths, EXPECTED, paths)

            digest_dir = crush_dir / "builder-reference"
            rules = crush_dir / "rules"
            for name in DIGEST_NAMES:
                self.assertTrue(
                    (digest_dir / f"builder-reference-{name}.md").is_file(), name
                )
                self.assertFalse(
                    (rules / f"builder-reference-{name}.md").exists(), name
                )
            self.assertTrue((rules / "builder-reference-pointer.md").is_file())

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
        crush_dir = home / ".config" / "crush"
        crush_dir.mkdir(parents=True)
        partial = [
            str(crush_dir / "rules" / "builder-reference-ousterhout.md"),
            CRUSH_MD,
        ]
        config = crush_dir / "crush.json"
        config.write_text(
            json.dumps({"options": {"global_context_paths": partial}}, indent=2) + "\n",
            encoding="utf-8",
        )
        return config

    def test_restores_ritual_when_absent_from_paths(self):
        real_config = Path.home() / ".config" / "crush" / "crush.json"
        real_mtime = real_config.stat().st_mtime_ns if real_config.is_file() else None

        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            config = self._seed_sandbox_ritual_absent(home)

            first = self._run_deploy(home)
            self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
            paths = self._paths(config)
            self.assertEqual(paths, EXPECTED, paths)
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
