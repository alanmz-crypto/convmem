"""Tests for convmem doctor."""

import unittest
from unittest.mock import patch

from doctor import DoctorCheck, doctor_exit_code, run_doctor


class DoctorTests(unittest.TestCase):
    @patch("doctor._check_index_drift")
    @patch("doctor._check_restic_password_backup")
    @patch("doctor._check_restic_external")
    @patch("doctor._check_restic")
    @patch("doctor._check_verify_script")
    @patch("doctor._check_continue_mcp")
    @patch("doctor._check_mcp_wiring")
    @patch("doctor._check_mcp_import")
    @patch("doctor._check_chroma")
    @patch("doctor._check_ollama")
    @patch("doctor._check_deepseek_key")
    @patch("doctor._check_config")
    @patch("doctor.load_config")
    def test_run_doctor_all_pass(
        self,
        mock_load,
        mock_cfg,
        mock_key,
        mock_ollama,
        mock_chroma,
        mock_mcp,
        mock_wire,
        mock_cont,
        mock_verify,
        mock_restic,
        mock_restic_external,
        mock_restic_password_backup,
        mock_drift,
    ):
        mock_load.return_value = {"index": {"chroma_dir": "/tmp/c"}, "models": {}}
        ok = DoctorCheck("x", True, "ok")
        for mock in (
            mock_cfg,
            mock_key,
            mock_ollama,
            mock_chroma,
            mock_drift,
            mock_restic,
            mock_restic_external,
            mock_restic_password_backup,
            mock_mcp,
            mock_wire,
            mock_cont,
        ):
            mock.return_value = ok
        mock_verify.return_value = DoctorCheck("verify_continue", True, "skipped")

        checks = run_doctor(run_verify=False)
        self.assertTrue(all(c.ok for c in checks))
        self.assertEqual(doctor_exit_code(checks), 0)

    def test_doctor_exit_code_fail(self):
        checks = [
            DoctorCheck("a", True, "ok"),
            DoctorCheck("b", False, "bad"),
        ]
        self.assertEqual(doctor_exit_code(checks), 1)


if __name__ == "__main__":
    unittest.main()
