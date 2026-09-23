"""Supervisor — production refusal + T5 turn/release/revoke cores (M6)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_FIXTURE = REPO / "tests" / "fixtures" / "openclaw_strict"
if str(_FIXTURE) not in sys.path:
    sys.path.insert(0, str(_FIXTURE))

from fixture_platform import AGENT_SUCCESS_BYTES, FixturePlatform  # noqa: E402
from lifecycle_scripts import (  # noqa: E402
    HEX_B,
    HEX_D,
    PUB,
    base_activation_manifest,
    base_launch_policy,
    status_request,
    turn_request,
)


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

    assert hasattr(
        sup, "validate_launch_tuple"
    ), "[T5] supervisor validate_launch_tuple capability absent"
    assert hasattr(sup, "SupervisorCore")


def test_validate_launch_tuple_exact_roles():
    import openclaw_activation_supervisor as sup

    policy = base_launch_policy()
    for role in ("supervisor", "gateway", "agent", "strict_server", "model_worker"):
        proc = policy["processes"][role]
        fd: dict = {}
        if role == "supervisor":
            fd = {"notify": object(), "lease": object()}
        got = sup.validate_launch_tuple(
            policy,
            role,
            list(proc["argv_template"]),
            dict(proc["environment"]),
            str(proc["cwd"]),
            fd,
        )
        assert got["role"] == role
    with pytest.raises(ValueError, match="runtime_fd_forbidden"):
        sup.validate_launch_tuple(
            policy,
            "agent",
            list(policy["processes"]["agent"]["argv_template"]),
            dict(policy["processes"]["agent"]["environment"]),
            "/fixture/empty",
            {"control": object()},
        )
    with pytest.raises(ValueError, match="argv_mismatch"):
        sup.validate_launch_tuple(
            policy,
            "model_worker",
            ["/evil"],
            dict(policy["processes"]["model_worker"]["environment"]),
            "/fixture/empty",
            {},
        )


def test_one_turn_no_queue_and_accepted_cap_seals():
    import openclaw_activation_supervisor as sup

    platform = FixturePlatform()
    core = sup.SupervisorCore(platform=platform)
    core.bind_activation(
        activation_manifest=base_activation_manifest(),
        publication_sha256=PUB,
        lease_deadline_boottime_ns=10_000_000_000_000,
        slot_id=HEX_B,
        supervisor_handle="1" * 32,
    )
    r1 = core.handle_request(turn_request())
    assert r1["outcome"] == "running"
    r2 = core.handle_request(
        turn_request(turn_id="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", text="x")
    )
    assert r2["outcome"] == "busy"
    core.active_turn_id = None
    core.state = "ACTIVE_IDLE"
    for i in range(1, 256):
        tid = f"{i:032x}"
        core.active_turn_id = None
        core.state = "ACTIVE_IDLE"
        resp = core.handle_request(
            turn_request(request_id=f"{(i + 10):032x}", turn_id=tid, text=f"t{i}")
        )
        assert resp["outcome"] == "running", (i, resp)
    core.active_turn_id = None
    core.state = "ACTIVE_IDLE"
    sealed = core.handle_request(
        turn_request(
            request_id="99999999999999999999999999999999",
            turn_id="88888888888888888888888888888888",
            text="cap",
        )
    )
    assert sealed["outcome"] == "sealed"
    assert sealed["payload"]["reason"] == "capacity"


def test_release_revoke_race_revoke_wins():
    import openclaw_activation_supervisor as sup

    platform = FixturePlatform()
    core = sup.SupervisorCore(platform=platform)
    core.bind_activation(
        activation_manifest=base_activation_manifest(),
        publication_sha256=PUB,
        lease_deadline_boottime_ns=10_000_000_000_000,
        slot_id=HEX_B,
        supervisor_handle="1" * 32,
    )
    core.handle_request(turn_request())
    handle = core.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    platform.schedule_agent_success(handle)
    core.ingest_agent_event(platform.next_event(handle))
    platform.next_event(handle)
    core.revoke("operator")
    with pytest.raises(ValueError, match="revoked_before_commit"):
        core.release_commit(exit_code=0)


def test_release_linearization_uses_final_clock_sample():
    import openclaw_activation_supervisor as sup

    platform = FixturePlatform()
    core = sup.SupervisorCore(platform=platform)
    core.bind_activation(
        activation_manifest=base_activation_manifest(),
        publication_sha256=PUB,
        lease_deadline_boottime_ns=10_000_000_000_000,
        slot_id=HEX_B,
        supervisor_handle="1" * 32,
    )
    core.handle_request(turn_request())
    handle = core.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    platform.schedule_agent_success(handle)
    core.ingest_agent_event(platform.next_event(handle))
    platform.next_event(handle)
    platform.advance_boottime(12345)
    result = core.release_commit(exit_code=0)
    assert result["committed_boottime_ns"] == core._last_valid_clock["boottime_after_ns"]
    assert result["model_output"]["text"] == "synthetic answer"
    assert len(AGENT_SUCCESS_BYTES) > 0


def test_uncertain_crash_no_rerun():
    import openclaw_activation_supervisor as sup

    platform = FixturePlatform()
    core = sup.SupervisorCore(platform=platform)
    core.bind_activation(
        activation_manifest=base_activation_manifest(),
        publication_sha256=PUB,
        lease_deadline_boottime_ns=10_000_000_000_000,
        slot_id=HEX_B,
        supervisor_handle="1" * 32,
    )
    core.handle_request(turn_request())
    out = core.observe_uncertain_after_crash(status_request())
    assert out["outcome"] == "unavailable"
    assert out["payload"]["reason"] == "disconnect"


def test_watchdog_lease_expiry():
    import openclaw_activation_supervisor as sup

    platform = FixturePlatform()
    core = sup.SupervisorCore(platform=platform)
    core.bind_activation(
        activation_manifest=base_activation_manifest(),
        publication_sha256=PUB,
        lease_deadline_boottime_ns=1_000_000_000,
        slot_id=HEX_B,
        supervisor_handle="1" * 32,
    )
    platform.advance_boottime(5_000_000_000)
    core.tick_watchdog()
    assert core._revoked is True
    assert core._revoke_reason == "expiry"


def test_status_busy_invalid_not_stored_as_turn_identities():
    import openclaw_activation_supervisor as sup

    platform = FixturePlatform()
    core = sup.SupervisorCore(platform=platform)
    core.bind_activation(
        activation_manifest=base_activation_manifest(),
        publication_sha256=PUB,
        lease_deadline_boottime_ns=10_000_000_000_000,
        slot_id=HEX_B,
        supervisor_handle="1" * 32,
    )
    core.handle_request(status_request())
    assert core.accepted == {}
    core.handle_request(turn_request(publication="sha256:" + ("c" * 64)))
    assert HEX_D not in core.accepted


def test_mutant_supervisor_emptiness_attestation_fails():
    import openclaw_activation_supervisor as sup

    platform = FixturePlatform()
    core = sup.SupervisorCore(platform=platform)
    with pytest.raises(ValueError, match="supervisor_cannot_attest"):
        core.empty_domain_attestation()
