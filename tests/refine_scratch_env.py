"""Scratch config + writer paths for refine tests that open production sessions."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from tests.purge_test_util import purge_cfg


@contextmanager
def patch_refine_scratch_env(root: Path, cfg: dict):
    """Bind config and writer defaults to one temp tree for refine job tests."""
    import chroma_write_store
    import config

    chroma_root = Path(cfg["index"]["chroma_dir"]).expanduser().resolve().parent
    locks = chroma_root / "locks"
    patches = [
        mock.patch.object(config, "CONFIG_PATH", root / "config.toml"),
        mock.patch.object(config, "load_config", lambda *a, **k: cfg),
        mock.patch.object(
            chroma_write_store,
            "DEFAULT_WRITER_LOCK",
            locks / "chroma_writer_gate.lock",
        ),
        mock.patch.object(
            chroma_write_store,
            "DEFAULT_ATTEST_DIR",
            chroma_root / "writer_attestations",
        ),
    ]
    started = [p.start() for p in patches]  # pylint: disable=unused-variable
    try:
        yield
    finally:
        for p in reversed(patches):
            p.stop()


def scratch_cfg(root: Path) -> dict:
    return purge_cfg(root)
