"""Tests for Portland baseline harness index cwd pinning."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_DIR = REPO_ROOT / "scripts" / "experiments" / "portland-baseline"
PROBE_TOKEN = "HARNESS_CWD_PROBE_TOKEN_r3f9a2"


def _load_index_runner():
    path = HARNESS_DIR / "index_runner.py"
    spec = importlib.util.spec_from_file_location("portland_index_runner", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["portland_index_runner"] = module
    spec.loader.exec_module(module)
    return module


class PortlandBaselineIndexCwdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="portland-harness-cwd-"))
        self.chroma_dir = self.tmp / "chroma"
        self.processed = self.tmp / "processed.json"
        self.cfg = self.tmp / "config.toml"
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.processed.write_text("{}", encoding="utf-8")
        self.cfg.write_text(
            f"""[sources]
paths = []
inventory = ""

[index]
chroma_dir = "{self.chroma_dir}"
processed_log = "{self.processed}"
units_export = "/dev/null"

[models]
embed_model = "nomic-embed-text"
ollama_host = "http://localhost:11434"

[watch]
debounce_seconds = 90

[refine]
enabled = false
""",
            encoding="utf-8",
        )
        sessions = Path.home() / ".codex" / "sessions" / "2099" / "01" / "01"
        sessions.mkdir(parents=True, exist_ok=True)
        self.fixture = sessions / "rollout-harness-cwd-probe.jsonl"
        rows = [
            {
                "timestamp": "2099-01-01T00:00:00.000Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": f"Discuss widget calibration. {PROBE_TOKEN}"}],
                },
            },
            {
                "timestamp": "2099-01-01T00:00:01.000Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": f"Recorded calibration note {PROBE_TOKEN}."}],
                },
            },
        ]
        self.fixture.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        if self.fixture.exists():
            self.fixture.unlink()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_index_subprocess_always_receives_pinned_cwd(self) -> None:
        index_runner = _load_index_runner()
        with patch("portland_index_runner.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            index_runner.index_file(config_path=self.cfg, source_path=self.fixture)
            mock_run.assert_called_once()
            self.assertEqual(
                mock_run.call_args.kwargs["cwd"],
                str(index_runner.INDEX_CWD.resolve()),
            )

    def test_index_from_arbitrary_launch_cwd_populates_isolated_corpus(self) -> None:
        index_runner = _load_index_runner()
        launch_dir = self.tmp / "arbitrary-launch-cwd"
        launch_dir.mkdir()
        script = f"""
import sys
sys.path.insert(0, {json.dumps(str(HARNESS_DIR))})
from index_runner import index_file, INDEX_CWD
proc = index_file(
    config_path={json.dumps(str(self.cfg))},
    source_path={json.dumps(str(self.fixture))},
    cwd=INDEX_CWD,
)
raise SystemExit(proc.returncode)
"""
        outer = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=str(launch_dir),
            check=False,
        )
        self.assertEqual(outer.returncode, 0, msg=outer.stderr or outer.stdout)

        search = subprocess.run(
            ["convmem", "search", PROBE_TOKEN, "--top", "3"],
            capture_output=True,
            text=True,
            env={**os.environ, "CONVMEM_CONFIG": str(self.cfg)},
            cwd=str(REPO_ROOT),
            check=False,
        )
        self.assertEqual(search.returncode, 0, msg=search.stderr)
        self.assertIn(PROBE_TOKEN, search.stdout, msg=search.stdout)

        prod_stats = subprocess.run(
            ["convmem", "stats"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            check=False,
        )
        self.assertEqual(prod_stats.returncode, 0, msg=prod_stats.stderr)
        self.assertNotIn(str(self.chroma_dir), prod_stats.stdout)


if __name__ == "__main__":
    unittest.main()
