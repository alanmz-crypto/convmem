# pylint: disable=protected-access
"""full_ci Restic provisioning contract (fail closed on GitHub, optional locally)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[1]
_BACKEND_PATH = _REPO / "tests" / "_safe_harbor_t3_backend_worker.py"


def _load_backend():
    import importlib.util

    spec = importlib.util.spec_from_file_location("safe_harbor_backend_restic_ci", _BACKEND_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SafeHarborT4ResticCiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = _load_backend()

    def _patch_node(self, tmp_path: Path) -> Path:
        node = tmp_path / "node-bin" / "node"
        node.parent.mkdir(parents=True)
        node.write_text("#!/bin/sh\n", encoding="utf-8")
        node.chmod(0o755)
        patcher = mock.patch.object(self.backend, "_select_node_executable", return_value=node.resolve())
        self.addCleanup(patcher.stop)
        patcher.start()
        return node.resolve()

    def test_full_ci_github_refuses_missing_restic_executable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._patch_node(tmp)
            fixture = tmp / "fixture"
            evidence = tmp / "evidence"
            env_patch = mock.patch.dict(
                os.environ,
                {"GITHUB_ACTIONS": "true"},
                clear=False,
            )
            self.addCleanup(env_patch.stop)
            env_patch.start()
            os.environ.pop("SAFE_HARBOR_CI_RESTIC_EXECUTABLE", None)
            with self.assertRaises(RuntimeError) as ctx:
                self.backend.build_allowlisted_env(fixture, evidence, expected_uid=os.getuid(), profile="full_ci")
            self.assertIn("SAFE_HARBOR_CI_RESTIC_EXECUTABLE", str(ctx.exception))

    def test_proof_profile_does_not_require_ci_restic_executable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fixture = tmp / "fixture"
            evidence = tmp / "evidence"
            patcher = mock.patch.dict(os.environ, {}, clear=False)
            self.addCleanup(patcher.stop)
            patcher.start()
            os.environ.pop("SAFE_HARBOR_CI_RESTIC_EXECUTABLE", None)
            env = self.backend.build_allowlisted_env(fixture, evidence, expected_uid=os.getuid(), profile="proof")
            self.assertEqual(env["SAFE_HARBOR_T3_FIXTURE_ROOT"], str(fixture.resolve()))

    def test_nofakegreen_verify_restic_binary_rejects_wrong_digest(self) -> None:
        from tests._safe_harbor_restic_ci import RESTIC_BINARY_SHA256, verify_restic_binary

        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "restic"
            bad.write_bytes(b"not-restic")
            with self.assertRaises(RuntimeError) as ctx:
                verify_restic_binary(bad)
            self.assertIn(RESTIC_BINARY_SHA256, str(ctx.exception))


def test_required_restic_cannot_be_reported_as_optional_skip(monkeypatch):
    from tests import test_safe_harbor_t2 as t2

    monkeypatch.setenv("SAFE_HARBOR_REQUIRE_RESTIC", "1")
    with mock.patch.object(t2.restic_snapshot, "check_restic_available", side_effect=t2.ResolverError("missing", 23)):
        with unittest.TestCase().assertRaisesRegex(RuntimeError, "refusing skipped coverage"):
            t2._restic_ok()
        monkeypatch.delenv("SAFE_HARBOR_REQUIRE_RESTIC")
        assert t2._restic_ok() is False
