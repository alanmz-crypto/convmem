#!/usr/bin/env python3
"""Smoke test for scripts/eval-judgebench.py dry-run."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "eval-judgebench.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("eval_judgebench_script", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EvalJudgebenchScriptTests(unittest.TestCase):
    @patch("eval_judgebench.runner.ollama_version", return_value="0.5.0")
    @patch("eval_model_identity.model_digest_and_quant", return_value=("remote", ""))
    def test_dry_run_exits_zero(self, _mock_digest, _mock_ver):
        module = _load_script()
        argv = [
            "eval-judgebench.py",
            "--judge-model",
            "deepseek-v4-pro",
            "--under-test-model",
            "llama3.1:8b",
            "--no-invoke",
        ]
        with patch.object(sys, "argv", argv):
            with patch("config.load_config", return_value={"models": {}}):
                code = module.main()
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
