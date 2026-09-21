"""Supervisor — T0a production refusal green; T5 core red."""

from __future__ import annotations

import subprocess
import sys


def test_production_entrypoint_refuses_runtime_not_qualified():
    proc = subprocess.run(
        [sys.executable, "-I", "openclaw_activation_supervisor.py"],
        capture_output=True,
        text=True,
        check=False,
        close_fds=True,
    )
    assert proc.returncode == 78
    assert proc.stdout == ""
    assert proc.stderr == "runtime_not_qualified\n"


def test_run_function_refuses_before_os_effects():
    import openclaw_activation_supervisor as sup

    try:
        sup.run()
    except SystemExit as exc:
        assert exc.code == 78
    else:
        raise AssertionError("expected SystemExit 78")


def test_t5_supervisor_core_capability_absent():
    import openclaw_activation_supervisor as sup

    assert hasattr(sup, "validate_launch_tuple"), "[T5] supervisor validate_launch_tuple capability absent"
