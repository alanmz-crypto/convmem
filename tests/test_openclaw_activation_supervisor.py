"""Supervisor — production refusal + T5 turn/release/revoke cores (M6)."""

from __future__ import annotations

import base64
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
        argv = list(proc["argv_template"])
        got = sup.validate_launch_tuple(
            policy,
            role,
            argv,
            dict(proc["environment"]),
            str(proc["cwd"]),
            fd if role == "supervisor" else {},
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


def test_one_turn_no_queue_and_accepted_cap_via_preload():
    """Capacity seal via independent fixture preload — no direct clear of turn state."""

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

    # Complete the live turn legitimately, then preload 255 committed histories.
    handle = core.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    platform.schedule_agent_success(handle)
    core.ingest_agent_event(platform.next_event(handle))
    core.ingest_agent_event(platform.next_event(handle))
    core.release_commit()
    assert core.state == "ACTIVE_IDLE"

    records = platform.preload_accepted_turn_history(count=255, turn_state="committed")
    # Drop the one already accepted (HEX_D) overlap by using preload ids 1..255.
    core.preload_completed_history(records)
    # accepted already has HEX_D + 255 preload = 256 → next seals.
    assert len(core.accepted) == 256
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
    core.ingest_agent_event({"kind": "exit", "bytes_b64": None, "exit_code": 0})
    core.revoke("operator")
    with pytest.raises(ValueError, match="revoked_before_commit"):
        core.release_commit()


def test_release_linearization_uses_final_clock_and_actual_exit():
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
    # Spawn argv must equal validated substituted TURN_TEXT form.
    spawn_rec = [t for t in platform.trace if t["op"] == "spawn" and t["role"] == "agent"][-1]
    assert spawn_rec["argv"] == ["/fixture/bin/agent", "--message", "fixture turn"]
    platform.schedule_agent_success(handle)
    core.ingest_agent_event(platform.next_event(handle))
    core.ingest_agent_event(platform.next_event(handle))
    platform.advance_boottime(12345)
    result = core.release_commit()
    assert result["committed_boottime_ns"] == core._last_valid_clock["boottime_after_ns"]
    assert result["model_output"]["text"] == "synthetic answer"
    assert len(AGENT_SUCCESS_BYTES) > 0
    # Caller-forged exit code argument removed — observed exit only.
    with pytest.raises(TypeError):
        core.release_commit(exit_code=0)  # type: ignore[call-arg]


def test_stderr_separation_and_malformed_nonfinite_duplicate_output():
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
    # stderr must not become model_output.
    err_b64 = base64.b64encode(b'{"evil":true}').decode("ascii")
    platform.schedule_event(handle, "stderr", bytes_b64=err_b64)
    platform.schedule_event(handle, "stdout", bytes_b64=base64.b64encode(AGENT_SUCCESS_BYTES).decode("ascii"))
    platform.schedule_event(handle, "exit", exit_code=0)
    core.ingest_agent_event(platform.next_event(handle))
    core.ingest_agent_event(platform.next_event(handle))
    core.ingest_agent_event(platform.next_event(handle))
    result = core.release_commit()
    assert result["model_output"]["fixture"] == "protocol-only"
    assert "evil" not in result["model_output"]

    # Malformed / nonfinite / duplicate / trailing.
    for bad in (
        b'{"a":1}{"b":2}',
        b'{"a":NaN}',
        b'{"a":1,"a":2}',
        b"[1,2,3]",
    ):
        core2 = sup.SupervisorCore(platform=FixturePlatform())
        core2.bind_activation(
            activation_manifest=base_activation_manifest(),
            publication_sha256=PUB,
            lease_deadline_boottime_ns=10_000_000_000_000,
            slot_id=HEX_B,
            supervisor_handle="1" * 32,
        )
        core2.handle_request(turn_request())
        h = core2.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
        plat = core2.platform
        plat.schedule_event(h, "stdout", bytes_b64=base64.b64encode(bad).decode("ascii"))
        plat.schedule_event(h, "exit", exit_code=0)
        core2.ingest_agent_event(plat.next_event(h))
        core2.ingest_agent_event(plat.next_event(h))
        with pytest.raises(ValueError):
            core2.release_commit()


def test_publication_activation_drift_at_release():
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
    core.ingest_agent_event(platform.next_event(handle))
    core.publication_sha256 = "sha256:" + ("b" * 64)
    with pytest.raises(ValueError, match="publication_drift"):
        core.release_commit()


def test_watchdog_cadence_and_release_revoke_schedules():
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
    samples_at_start = len(core._watchdog_samples)
    assert samples_at_start >= 1
    core.script_work_intervals(3)
    assert len(core._watchdog_samples) >= samples_at_start + 3
    # Intervals advanced by WATCHDOG_INTERVAL_NS on platform clock — no real wait.
    assert any(t["op"] == "harness_advance_boottime" for t in platform.trace)

    core.handle_request(turn_request())
    handle = core.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    platform.schedule_agent_success(handle)
    core.ingest_agent_event(platform.next_event(handle))
    core.ingest_agent_event(platform.next_event(handle))
    before = len(core._watchdog_samples)
    core.release_commit()
    assert len(core._watchdog_samples) >= before + 1

    # Lease expiry via watchdog.
    core2 = sup.SupervisorCore(platform=FixturePlatform())
    core2.bind_activation(
        activation_manifest=base_activation_manifest(),
        publication_sha256=PUB,
        lease_deadline_boottime_ns=1_000_000_000,
        slot_id=HEX_B,
        supervisor_handle="1" * 32,
    )
    core2.platform.advance_boottime(5_000_000_000)
    core2.tick_watchdog()
    assert core2._revoked is True
    assert core2._revoke_reason == "expiry"


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


def test_non_string_text_not_coerced():
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
    req = turn_request()
    req["text"] = 42  # type: ignore[assignment]
    assert core.handle_request(req)["outcome"] == "invalid_request"
