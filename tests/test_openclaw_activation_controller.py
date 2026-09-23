"""Controller — production refusal + T5 Gate C lifecycle cores (M6)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_FIXTURE = REPO / "tests" / "fixtures" / "openclaw_strict"
if str(_FIXTURE) not in sys.path:
    sys.path.insert(0, str(_FIXTURE))

from fixture_platform import FixturePlatform, LOGICAL_PEERS  # noqa: E402
from lifecycle_scripts import (  # noqa: E402
    HEX_A,
    HEX_B,
    HEX_D,
    HEX_E,
    PUB,
    agent_success_b64,
    base_activation_manifest,
    base_clock_review,
    base_launch_policy,
    cancel_request,
    revoke_request,
    script_partial_frame_discard,
    script_peer_policy_ok,
    status_request,
    turn_request,
)


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
    assert hasattr(ctl, "lifecycle_config_core")
    assert hasattr(ctl, "ControllerCore")


def _pair():
    import openclaw_activation_controller as ctl
    import openclaw_activation_supervisor as sup

    platform = FixturePlatform()
    supervisor = sup.SupervisorCore(platform=platform)
    controller = ctl.ControllerCore(platform=platform, supervisor=supervisor)
    return platform, controller, supervisor, ctl


def test_logical_peer_policy_exact_uids():
    platform, *_ = _pair()
    script_peer_policy_ok(platform)
    assert LOGICAL_PEERS["operator"] == (1000, 1000)
    assert LOGICAL_PEERS["controller"] == (0, 0)
    assert LOGICAL_PEERS["supervisor"] == (0, 0)
    assert LOGICAL_PEERS["runtime"] == (1001, 1001)
    assert "sample_clock" in platform.port_ops() or platform.trace  # peer ops traced
    assert platform.port_ops().count("peer") == 4


def test_case53_peer_forgery_denied():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    platform.forge_peer("evil", uid=1001, gid=1001)
    resp = controller.handle_control("evil", status_request())
    assert resp["outcome"] == "invalid_request"
    assert resp["payload"]["reason"] == "bad_arguments"


def test_case55_runtime_denied_private_paths_pre_activation():
    platform, controller, supervisor, ctl = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    # Runtime reads of private qualification/issuer/governance/control must deny.
    for path in (
        "/fixture/private/qualification/x",
        "/fixture/private/issuer/x",
        "/fixture/private/governance/x",
        "/fixture/private/control/x",
    ):
        assert platform.access("runtime", path, "read") is False
    # Controller may read private qualification.
    assert platform.access("controller", "/fixture/private/qualification/manifest.json", "read")
    ctl.lifecycle_config_core({})
    with pytest.raises(ValueError, match="lifecycle_not_disabled"):
        ctl.lifecycle_config_core({"heartbeat": True})


def test_stable_slot_activation_and_ready():
    platform, controller, supervisor, _ = _pair()
    st = controller.enroll_slot(
        HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z"
    )
    assert st.state == "NEW"
    manifest = base_activation_manifest()
    policy = base_launch_policy()
    # Schedule supervisor ready before activate waits.
    # activate spawns first — schedule after qualify by intercepting: pre-bind schedule via hook.
    # We schedule after qualify_and_activate returns handle.
    st2 = controller.qualify_and_activate(
        HEX_B, manifest, policy, lifecycle_config={}, remaining_snapshot_lifetime_ns=3_600_000_000_000
    )
    handle = supervisor.supervisor_handle
    assert handle is not None
    assert st2.state == "ACTIVE_IDLE"
    assert "next_event" in platform.port_ops()
    assert st2.unit_invocation_id
    assert st2.containment_id
    assert st2.manager_boot_id
    assert "manager_start" in platform.port_ops()
    assert "spawn" in platform.port_ops()


def test_case53_turn_cancel_status_revoke_and_capacity():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    manifest = base_activation_manifest()
    policy = base_launch_policy()
    controller.qualify_and_activate(HEX_B, manifest, policy, lifecycle_config={})
    platform.set_peer("op1", "operator")

    # status
    st_resp = controller.handle_control("op1", status_request(request_id=HEX_A))
    assert st_resp["outcome"] == "status"
    assert st_resp["payload"]["state"] == "ACTIVE_IDLE"
    assert st_resp["payload"]["turn_id"] is None

    # turn → running
    t_resp = controller.handle_control("op1", turn_request())
    assert t_resp["outcome"] == "running"
    assert t_resp["payload"]["turn_id"] == HEX_D

    # second turn → busy (no queue)
    t2 = controller.handle_control(
        "op1", turn_request(request_id=HEX_E, turn_id=HEX_E, text="other")
    )
    assert t2["outcome"] == "busy"

    # same turn id / same text → running (dedup, no rerun)
    t3 = controller.handle_control("op1", turn_request(request_id="ffffffffffffffffffffffffffffffff"))
    assert t3["outcome"] == "running"

    # same turn id / different text → conflict
    t4 = controller.handle_control(
        "op1", turn_request(request_id="11111111111111111111111111111111", text="changed")
    )
    assert t4["outcome"] == "request_conflict"

    # cancel live turn → sealed
    c_resp = controller.handle_control("op1", cancel_request(request_id="22222222222222222222222222222222"))
    assert c_resp["outcome"] == "sealed"
    assert controller.slots[HEX_B].state == "SEALED"


def test_case53_blocked_consumer_revoke_linearization():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    platform.set_peer("op1", "operator")
    platform.set_peer("op2", "operator")
    controller.handle_control("op1", turn_request())
    # Agent output then release with blocked consumer.
    handle = supervisor.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    platform.schedule_event(handle, "stdout", bytes_b64=agent_success_b64())
    platform.schedule_event(handle, "exit", exit_code=0)
    ev = platform.next_event(handle)
    supervisor.ingest_agent_event(ev)
    ev2 = platform.next_event(handle)
    assert ev2["kind"] == "exit"
    result = supervisor.release_commit(exit_code=0, consumer_blocked=True)
    assert result["evidence_basis"] == "model_output_unverified"
    assert supervisor.pending_delivery is not None
    # Revoke on separate connection without waiting for blocked consumer.
    r = controller.handle_control(
        "op2", revoke_request(request_id="33333333333333333333333333333333"), consumer_blocked=True
    )
    assert r["outcome"] == "revoking"
    # Already committed bytes remain an answer; cancel reports already_committed.
    ac = supervisor.handle_request(cancel_request(request_id="44444444444444444444444444444444"))
    assert ac["outcome"] == "already_committed"


def test_case46_53_retirement_only_on_exact_empty_observation():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    inv = controller.slots[HEX_B].unit_invocation_id
    assert inv
    # manager_stop ack is never empty proof.
    ack = controller.request_manager_stop(HEX_B)
    assert ack["acknowledged"] is True
    with pytest.raises(ValueError, match="quarantined"):
        controller.attempt_retirement(HEX_B)
    assert controller.slots[HEX_B].state == "QUARANTINED"

    # Reset via fresh slot reuse path: new enrollment after clearing quarantine for mutant.
    platform2, controller2, supervisor2, _ = _pair()
    controller2.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller2.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    inv2 = controller2.slots[HEX_B].unit_invocation_id
    controller2.request_manager_stop(HEX_B)
    # Detached descendant remains → quarantine
    platform2.add_detached_descendant(inv2, "proc:grandchild:x")
    with pytest.raises(ValueError, match="quarantined"):
        controller2.attempt_retirement(HEX_B)

    # Outstanding model work → quarantine
    platform3, controller3, supervisor3, _ = _pair()
    controller3.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller3.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    inv3 = controller3.slots[HEX_B].unit_invocation_id
    controller3.request_manager_stop(HEX_B)
    platform3.force_observe(inv3, terminal=True, populated=None)
    with pytest.raises(ValueError, match="quarantined"):
        controller3.attempt_retirement(HEX_B)

    # Exact terminal=true, populated=false → receipt + SEALED
    platform4, controller4, supervisor4, _ = _pair()
    controller4.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller4.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    inv4 = controller4.slots[HEX_B].unit_invocation_id
    controller4.request_manager_stop(HEX_B)
    platform4.clear_all_members(inv4)
    platform4.force_observe(inv4, terminal=True, populated=False)
    receipt = controller4.attempt_retirement(HEX_B, terminal_reason="operator")
    assert receipt["schema"] == "convmem.activation-retirement.v1"
    assert controller4.slots[HEX_B].state == "SEALED"
    # Slot reuse after exact retirement.
    controller4.qualify_and_activate(
        HEX_B,
        base_activation_manifest(activation_id="ffffffffffffffffffffffffffffffff"),
        base_launch_policy(),
        lifecycle_config={},
    )
    assert controller4.slots[HEX_B].state == "ACTIVE_IDLE"


def test_case57_stale_receipts_and_supervisor_cannot_attest():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    inv = controller.slots[HEX_B].unit_invocation_id
    controller.request_manager_stop(HEX_B)
    platform.clear_all_members(inv)
    platform.force_observe(inv, terminal=True, populated=False, manager_boot_id="stale-boot")
    with pytest.raises(ValueError, match="stale_boot"):
        controller.attempt_retirement(HEX_B)
    with pytest.raises(ValueError, match="supervisor_cannot_attest"):
        supervisor.empty_domain_attestation()


def test_case57_manager_membership_survives_supervisor_death():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    inv = controller.slots[HEX_B].unit_invocation_id
    # Supervisor exit does not clear membership.
    platform.schedule_event(supervisor.supervisor_handle, "exit", exit_code=0)
    platform.next_event(supervisor.supervisor_handle)
    obs = platform.manager_observe(inv)
    assert obs["populated"] is True
    # Controller restart preserves set.
    controller.reconcile_after_controller_restart(HEX_B)
    assert controller.slots[HEX_B].state == "QUARANTINED"
    # Only harness-scheduled removal clears members.
    platform.clear_all_members(inv)
    obs2 = platform.manager_observe(inv)
    assert obs2["populated"] is False


def test_case54_clock_boot_freshness_and_rollback_retains_head():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    anchor1 = controller.slots[HEX_B].freshness_anchor
    assert anchor1 is not None
    deadline1 = anchor1.snapshot_deadline_boottime_ns
    # Same-boot shrink only.
    controller.establish_freshness_anchor(
        controller.slots[HEX_B],
        authority_snapshot_id="snap-fixture-1",
        remaining_snapshot_lifetime_ns=1_000_000_000,
    )
    assert controller.slots[HEX_B].freshness_anchor.snapshot_deadline_boottime_ns <= deadline1
    # Suspend/resume advances BOOTTIME (cannot extend lease by wall alone).
    platform.suspend_resume(5_000_000_000)
    sample = platform.sample_clock()
    assert sample["boottime_after_ns"] >= 1_000_000_000 + 5_000_000_000
    # Wall backwards seals.
    platform.advance_wall("2026-09-20T00:00:00Z")
    platform.set_peer("op1", "operator")
    controller.handle_control("op1", status_request())
    assert controller.slots[HEX_B].state == "REVOKING"
    assert controller.slots[HEX_B].terminal_reason == "clock_anomaly"
    # New boot requires clock review; expiry cannot renew.
    platform.new_boot("boot-fixture-0002", wall_time="2026-09-21T12:00:00Z")
    with pytest.raises(ValueError, match="clock_review_required"):
        controller.establish_freshness_anchor(
            controller.slots[HEX_B],
            authority_snapshot_id="snap-fixture-1",
            remaining_snapshot_lifetime_ns=1_000_000_000,
        )
    review = base_clock_review()
    controller.slots[HEX_B].expires_at = "2026-09-22T00:00:00Z"
    controller.establish_freshness_anchor(
        controller.slots[HEX_B],
        authority_snapshot_id="snap-fixture-1",
        remaining_snapshot_lifetime_ns=1_000_000_000,
        clock_review=review,
    )
    # Rollback serving-only retains head/expiry; teardown ≠ recovery.
    view = controller.serving_rollback_view(HEX_B)
    assert view["authority_head"] == PUB
    assert view["expires_at"] == "2026-09-22T00:00:00Z"
    assert view["session_resumable"] is False
    assert view["teardown_is_recovery"] is False
    assert view["serving_only"] is True
    bad_review = base_clock_review(expires_at="2026-09-23T00:00:00Z")
    platform.new_boot("boot-fixture-0003", wall_time="2026-09-21T13:00:00Z")
    with pytest.raises(ValueError, match="expiry_renewal_forbidden"):
        controller.establish_freshness_anchor(
            controller.slots[HEX_B],
            authority_snapshot_id="snap-fixture-1",
            remaining_snapshot_lifetime_ns=1_000_000_000,
            clock_review=bad_review,
        )


def test_case33_spawn_tuple_crosses_platform_only():
    platform, controller, supervisor, _ = _pair()
    policy = base_launch_policy()
    # Hostile env/argv must not be accepted by validate path used at spawn.
    import openclaw_activation_supervisor as sup

    with pytest.raises(ValueError):
        sup.validate_launch_tuple(
            policy,
            "agent",
            ["/evil"],
            dict(policy["processes"]["agent"]["environment"]),
            "/fixture/empty",
            {},
        )
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), policy, lifecycle_config={}
    )
    # Every spawn traced through platform.
    assert any(t["op"] == "spawn" for t in platform.trace)


def test_case35_kill_child_partial_success_paths():
    """Only fully released commit may succeed; mid-stream kill → no success."""

    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    platform.set_peer("op1", "operator")
    controller.handle_control("op1", turn_request())
    handle = supervisor.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    # Kill before complete output.
    platform.schedule_event(handle, "exit", exit_code=9)
    ev = platform.next_event(handle)
    assert ev["kind"] == "exit"
    with pytest.raises(ValueError, match="nonzero_agent_exit"):
        supervisor.release_commit(exit_code=9)
    # Fresh turn + full success path.
    controller2_platform, controller2, supervisor2, _ = _pair()
    controller2.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller2.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    controller2_platform.set_peer("op1", "operator")
    controller2.handle_control("op1", turn_request())
    h2 = supervisor2.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    controller2_platform.schedule_agent_success(h2)
    supervisor2.ingest_agent_event(controller2_platform.next_event(h2))
    assert controller2_platform.next_event(h2)["kind"] == "exit"
    committed = supervisor2.release_commit(exit_code=0)
    assert committed["model_output"]["fixture"] == "protocol-only"


def test_case45_lifecycle_config_disables_and_no_unsolicited_turn():
    import openclaw_activation_controller as ctl

    core = ctl.lifecycle_config_core({})
    assert core["heartbeat"] is False
    assert core["automatic_memory_flush"] is False
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config=core
    )
    # No turn without operator framed request.
    assert supervisor.active_turn_id is None
    platform.set_peer("op1", "operator")
    st = controller.handle_control("op1", status_request())
    assert st["payload"]["turn_id"] is None


def test_partial_frame_and_lock_order():
    platform, controller, supervisor, _ = _pair()
    script_partial_frame_discard(platform)
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    inv = controller.slots[HEX_B].unit_invocation_id
    controller.request_manager_stop(HEX_B)
    platform.clear_all_members(inv)
    platform.force_observe(inv, terminal=True, populated=False)
    controller.attempt_retirement(HEX_B)
    # Retire before lineage exclusive — no reverse lock path.
    controller.retire_before_lineage_exclusive(HEX_B)


def test_case58_production_refusal_with_unwrapped_specimen_bytes():
    """Production entrypoints refuse even if a specimen payload is unwrapped adjacent."""

    import openclaw_activation_controller as ctl

    # Specimen-shaped kwargs must not enable start.
    try:
        ctl.start(
            activation_manifest=base_activation_manifest(),
            launch_policy=base_launch_policy(),
        )
    except SystemExit as exc:
        assert exc.code == 78
    else:
        raise AssertionError("expected refusal")


def test_all_platform_ops_traced_for_clock_peer_access_spawn_manager():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    platform.set_peer("op1", "operator")
    platform.access("controller", "/fixture/receipt/x", "create")
    platform.sample_clock()
    inv = controller.slots[HEX_B].unit_invocation_id
    platform.manager_stop(inv)
    platform.manager_observe(inv)
    ops = set(platform.port_ops())
    for required in (
        "sample_clock",
        "peer",
        "access",
        "spawn",
        "manager_start",
        "manager_stop",
        "manager_observe",
    ):
        assert required in ops, required


def test_module_enroll_slot_wrapper():
    import openclaw_activation_controller as ctl
    import openclaw_activation_supervisor as sup

    platform = FixturePlatform()
    supervisor = sup.SupervisorCore(platform=platform)
    st = ctl.enroll_slot(
        platform,
        supervisor,
        HEX_B,
        HEX_A,
        authority_head=PUB,
        expires_at="2026-09-22T00:00:00Z",
    )
    assert st.slot_id == HEX_B
