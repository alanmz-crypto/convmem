"""Tests for config path resolution."""

import importlib
import os
import tempfile
import unittest
from pathlib import Path


class ConfigPathTests(unittest.TestCase):
    def test_convmem_config_env_overrides_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "lab.toml"
            cfg_path.write_text(
                "[index]\n"
                'chroma_dir = "/tmp/lab-chroma"\n'
                'processed_log = "/tmp/lab-processed.json"\n',
                encoding="utf-8",
            )
            old = os.environ.get("CONVMEM_CONFIG")
            try:
                os.environ["CONVMEM_CONFIG"] = str(cfg_path)
                import config

                importlib.reload(config)
                self.assertEqual(config.CONFIG_PATH, cfg_path)
                loaded = config.load_config()
                self.assertEqual(loaded["index"]["chroma_dir"], "/tmp/lab-chroma")
            finally:
                if old is None:
                    os.environ.pop("CONVMEM_CONFIG", None)
                else:
                    os.environ["CONVMEM_CONFIG"] = old
                import config

                importlib.reload(config)

    def test_load_config_explicit_path(self):
        from config import load_config

        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "explicit.toml"
            cfg_path.write_text(
                "[index]\nchroma_dir = '/tmp/x'\nprocessed_log = '/tmp/p.json'\n",
                encoding="utf-8",
            )
            loaded = load_config(cfg_path)
            self.assertEqual(loaded["index"]["chroma_dir"], "/tmp/x")


if __name__ == "__main__":
    unittest.main()
