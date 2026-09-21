"""Controller — T0a production refusal green; T5 core red."""

from __future__ import annotations

import subprocess
import sys


def test_production_start_refuses_runtime_not_qualified():
    proc = subprocess.run(
        [sys.executable, "-I", "openclaw_activation_controller.py"],
        capture_output=True,
        text=True,
        check=False,
        close_fds=True,
    )
    assert proc.returncode == 78
    assert proc.stdout == ""
    assert proc.stderr == "runtime_not_qualified\n"


def test_start_function_refuses_before_os_effects():
    import openclaw_activation_controller as ctl

    try:
        ctl.start()
    except SystemExit as exc:
        assert exc.code == 78
    else:
        raise AssertionError("expected SystemExit 78")


def test_t5_controller_core_capability_absent():
    import openclaw_activation_controller as ctl

    assert hasattr(ctl, "enroll_slot"), "[T5] controller enroll_slot capability absent"
