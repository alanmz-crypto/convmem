"""Controller — production refusal + T5 Gate C lifecycle cores (M6)."""

from __future__ import annotations

import copy
import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_FIXTURE = REPO / "tests" / "fixtures" / "openclaw_strict"
if str(_FIXTURE) not in sys.path:
    sys.path.insert(0, str(_FIXTURE))

from fixture_platform import (  # noqa: E402
    CONTROL_IO_TIMEOUT_NS,
    MAX_CONTROL_CONNECTIONS,
    MAX_REQUEST_FRAME,
    FixturePlatform,
    LOGICAL_PEERS,
    encode_control_frame,
    try_decode_control_frame,
)
from lifecycle_scripts import (  # noqa: E402
    HEX_A,
    HEX_B,
    HEX_E,
    PUB,
    _enter_revoking_for_retirement,
    agent_argv_template,
    base_activation_manifest,
    base_clock_review,
    base_launch_policy,
    cancel_request,
    clock_review_inventory_bytes,
    independent_canonical,
    independent_content_hash,
    install_clock_review_inventory,
    open_operator_session,
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
    for path in (
        "/fixture/private/qualification/x",
        "/fixture/private/issuer/x",
        "/fixture/private/governance/x",
        "/fixture/private/control/x",
    ):
        assert platform.access("runtime", path, "read") is False
    assert platform.access("controller", "/fixture/private/qualification-evil", "read") is False
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
    st2 = controller.qualify_and_activate(
        HEX_B,
        base_activation_manifest(),
        base_launch_policy(),
        lifecycle_config={},
        remaining_snapshot_lifetime_ns=3_600_000_000_000,
    )
    assert supervisor.supervisor_handle is not None
    assert st2.state == "ACTIVE_IDLE"
    assert st2.unit_invocation_id
    assert st2.containment_id
    assert st2.manager_boot_id
    assert "manager_start" in platform.port_ops()
    assert "spawn" in platform.port_ops()


def test_framed_control_partials_caps_timeout_eight_connections():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    conns = []
    for i in range(MAX_CONTROL_CONNECTIONS):
        cid = f"op{i}"
        platform.open_control_connection(cid, "operator")
        controller.open_control_session(cid)
        conns.append(cid)
    with pytest.raises(ValueError, match="control_connection_capacity"):
        platform.open_control_connection("op-extra", "operator")
    with pytest.raises(ValueError, match="control_connection_capacity"):
        controller.open_control_session("op-extra2")

    cid = conns[0]
    full = encode_control_frame(status_request(request_id=HEX_E))
    partial = full[:5]
    assert controller.handle_framed_bytes(cid, partial) is None
    framed = controller.handle_framed_bytes(cid, full[5:])
    assert framed is not None
    assert len(framed) <= MAX_REQUEST_FRAME * 2
    # Response cap via bounded outbound queue write path.
    assert len(platform.control_outbound(cid).write_trace) >= 1
    obj, rem, err = try_decode_control_frame(framed)
    assert err is None and rem == b"" and obj is not None
    assert obj["outcome"] == "status"

    cid2 = conns[1]
    desync = encode_control_frame(status_request(request_id=HEX_A)) + b"\x00"
    assert controller.handle_framed_bytes(cid2, desync) is None

    cid3 = conns[2]
    controller.handle_framed_bytes(cid3, encode_control_frame(status_request())[:3])
    platform.advance_boottime(CONTROL_IO_TIMEOUT_NS + 1)
    assert controller.handle_framed_bytes(cid3, b"\x00") is None
    assert cid3 not in controller._open_sessions


def test_framed_closed_requests_and_request_id_conflict():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    platform.open_control_connection("op1", "operator")
    controller.open_control_session("op1")

    bad = turn_request()
    bad["extra"] = "nope"
    before = len(platform.control_outbound("op1").write_trace)
    framed = controller.handle_framed_bytes("op1", encode_control_frame(bad))
    assert framed is not None
    assert len(platform.control_outbound("op1").write_trace) == before + 1
    obj, _, _ = try_decode_control_frame(framed)
    assert obj["outcome"] == "invalid_request"

    bad2 = turn_request(request_id=HEX_E)
    bad2["text"] = 12345  # type: ignore[assignment]
    framed2 = controller.handle_framed_bytes("op1", encode_control_frame(bad2))
    obj2, _, _ = try_decode_control_frame(framed2)
    assert obj2["outcome"] == "invalid_request"
    assert len(platform.control_outbound("op1").write_trace) == before + 2

    opd = open_operator_session(controller, platform, "opd")
    r1 = controller.handle_control(opd, turn_request())
    assert r1["outcome"] == "running"
    conflict = turn_request(text="changed-bytes")
    r2 = controller.handle_control(opd, conflict)
    assert r2["outcome"] == "request_conflict"

    r3 = controller.handle_control(
        opd,
        turn_request(request_id="ffffffffffffffffffffffffffffffff"),
    )
    assert r3["outcome"] == "running"


def test_cancel_to_revoking_then_independent_retirement():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    op1 = open_operator_session(controller, platform, "op1")
    assert controller.handle_control(op1, turn_request())["outcome"] == "running"
    c_resp = controller.handle_control(
        op1, cancel_request(request_id="22222222222222222222222222222222")
    )
    assert c_resp["outcome"] == "cancelled"
    assert controller.slots[HEX_B].state == "REVOKING"
    assert controller.slots[HEX_B].state != "SEALED"

    inv = controller.slots[HEX_B].unit_invocation_id
    controller.request_manager_stop(HEX_B)
    platform.clear_all_members(inv)
    platform.force_observe(inv, terminal=True, populated=False)
    receipt = controller.attempt_retirement(HEX_B, terminal_reason="disconnect")
    assert receipt["schema"] == "convmem.activation-retirement.v1"
    assert controller.slots[HEX_B].state == "SEALED"
    assert receipt["activation_manifest_sha256"] == controller.slots[
        HEX_B
    ].verified_manifest_content_sha256


def test_sealed_immutability_and_fresh_activation_history():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    _enter_revoking_for_retirement(controller)
    inv = controller.slots[HEX_B].unit_invocation_id
    platform.clear_all_members(inv)
    platform.force_observe(inv, terminal=True, populated=False)
    first_receipt = controller.attempt_retirement(HEX_B, terminal_reason="operator")
    first_act = controller.slots[HEX_B].activation_id
    sealed_slot = controller.slots[HEX_B]
    assert sealed_slot.state == "SEALED"
    predecessor = sealed_slot.sealed_record
    assert predecessor is not None
    assert predecessor.state == "SEALED"
    pred_receipt = dict(predecessor.retirement_receipt)
    pred_id = predecessor.activation_id

    act2 = "ffffffffffffffffffffffffffffffff"
    policy2 = base_launch_policy(_activation_id=act2)
    controller.qualify_and_activate(
        HEX_B,
        base_activation_manifest(activation_id=act2, state_dir="/fixture/state/act-2"),
        policy2,
        lifecycle_config={},
    )
    live = controller.slots[HEX_B]
    assert live is not sealed_slot
    assert live.state == "ACTIVE_IDLE"
    assert live.activation_id == act2
    # Retained OLD SlotState stays SEALED with unchanged identity/receipt.
    assert sealed_slot.state == "SEALED"
    assert sealed_slot.activation_id == pred_id == first_act
    assert sealed_slot.retirement_receipt == first_receipt
    assert predecessor.state == "SEALED"
    assert predecessor.activation_id == pred_id == first_act
    assert predecessor.retirement_receipt == pred_receipt == first_receipt
    assert predecessor in live.sealed_history
    with pytest.raises(TypeError):
        predecessor.retirement_receipt["tampered"] = True  # type: ignore[index]
    with pytest.raises(TypeError):
        predecessor.state = "QUALIFYING"  # type: ignore[misc]
    # Live mutation must not alter the sealed predecessor / old slot.
    live.retirement_receipt = {"tampered": True}
    assert predecessor.retirement_receipt == first_receipt
    assert sealed_slot.retirement_receipt == first_receipt
    assert supervisor.accepted == {}
    assert supervisor.pending_delivery is None


def test_activation_failure_retains_domain_for_retire_quarantine():
    platform = FixturePlatform(auto_ready_on_supervisor_spawn=False)
    import openclaw_activation_controller as ctl
    import openclaw_activation_supervisor as sup

    supervisor = sup.SupervisorCore(platform=platform)
    controller = ctl.ControllerCore(platform=platform, supervisor=supervisor)
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    with pytest.raises(ValueError, match="supervisor_not_ready"):
        controller.qualify_and_activate(
            HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
        )
    st = controller.slots[HEX_B]
    assert st.state == "REVOKING"
    assert st.unit_invocation_id
    assert st.containment_id
    assert st.activation_id
    assert st.stop_requested is True
    platform.clear_all_members(st.unit_invocation_id)
    platform.force_observe(st.unit_invocation_id, terminal=True, populated=False)
    receipt = controller.attempt_retirement(HEX_B, terminal_reason="integrity_failure")
    assert receipt["unit_invocation_id"] == st.unit_invocation_id


def test_exact_null_observation_quarantines():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    _enter_revoking_for_retirement(controller)
    inv = controller.slots[HEX_B].unit_invocation_id
    platform.force_observe(inv, terminal=True, populated=None)
    with pytest.raises(ValueError, match="quarantined"):
        controller.attempt_retirement(HEX_B)
    assert controller.slots[HEX_B].state == "QUARANTINED"


def test_case46_53_retirement_only_on_exact_empty_observation():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    _enter_revoking_for_retirement(controller)
    with pytest.raises(ValueError, match="quarantined"):
        controller.attempt_retirement(HEX_B)
    assert controller.slots[HEX_B].state == "QUARANTINED"

    platform2, controller2, supervisor2, _ = _pair()
    controller2.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller2.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    inv2 = controller2.slots[HEX_B].unit_invocation_id
    _enter_revoking_for_retirement(controller2)
    platform2.add_detached_descendant(inv2, "proc:grandchild:x")
    with pytest.raises(ValueError, match="quarantined"):
        controller2.attempt_retirement(HEX_B)

    platform4, controller4, supervisor4, _ = _pair()
    controller4.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller4.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    inv4 = controller4.slots[HEX_B].unit_invocation_id
    _enter_revoking_for_retirement(controller4)
    platform4.clear_all_members(inv4)
    platform4.force_observe(inv4, terminal=True, populated=False)
    receipt = controller4.attempt_retirement(HEX_B, terminal_reason="operator")
    assert receipt["schema"] == "convmem.activation-retirement.v1"
    assert controller4.slots[HEX_B].state == "SEALED"


def test_case57_stale_receipts_and_supervisor_cannot_attest():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    inv = controller.slots[HEX_B].unit_invocation_id
    _enter_revoking_for_retirement(controller)
    platform.clear_all_members(inv)
    platform.force_observe(inv, terminal=True, populated=False, manager_boot_id="stale-boot")
    with pytest.raises(ValueError, match="stale_boot"):
        controller.attempt_retirement(HEX_B)
    with pytest.raises(ValueError, match="supervisor_cannot_attest"):
        supervisor.empty_domain_attestation()


def test_case57_manager_membership_survives_and_restart_persists_quarantine():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    inv = controller.slots[HEX_B].unit_invocation_id
    platform.schedule_event(supervisor.supervisor_handle, "exit", exit_code=0)
    platform.next_event(supervisor.supervisor_handle)
    obs = platform.manager_observe(inv)
    assert obs["populated"] is True
    controller.slots[HEX_B].persisted["state"] = "ACTIVE_IDLE"
    controller.reconcile_after_controller_restart(HEX_B)
    assert controller.slots[HEX_B].state == "QUARANTINED"
    assert controller.slots[HEX_B].persisted["state"] == "QUARANTINED"
    platform.clear_all_members(inv)
    assert platform.manager_observe(inv)["populated"] is False


def test_case54_clock_interval_review_inventory():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    anchor1 = controller.slots[HEX_B].freshness_anchor
    assert anchor1 is not None
    deadline1 = anchor1.snapshot_deadline_boottime_ns
    controller.establish_freshness_anchor(
        controller.slots[HEX_B],
        authority_snapshot_id="snap-fixture-1",
        remaining_snapshot_lifetime_ns=1_000_000_000,
    )
    assert controller.slots[HEX_B].freshness_anchor.snapshot_deadline_boottime_ns <= deadline1
    platform.suspend_resume(5_000_000_000)
    sample = platform.sample_clock()
    assert sample["boottime_after_ns"] >= 1_000_000_000 + 5_000_000_000
    platform.advance_wall("2026-09-20T00:00:00Z")
    op1 = open_operator_session(controller, platform, "op1")
    controller.handle_control(op1, status_request())
    assert controller.slots[HEX_B].state == "REVOKING"
    assert controller.slots[HEX_B].terminal_reason == "clock_anomaly"

    platform.new_boot("boot-fixture-0002", wall_time="2026-09-21T12:00:00Z")
    review = base_clock_review()
    controller.slots[HEX_B].expires_at = "2026-09-22T00:00:00Z"
    with pytest.raises(ValueError, match="clock_review_inventory_miss"):
        controller.establish_freshness_anchor(
            controller.slots[HEX_B],
            authority_snapshot_id="snap-fixture-1",
            remaining_snapshot_lifetime_ns=1_000_000_000,
            clock_review=review,
        )
    install_clock_review_inventory(platform, review)
    controller.establish_freshness_anchor(
        controller.slots[HEX_B],
        authority_snapshot_id="snap-fixture-1",
        remaining_snapshot_lifetime_ns=1_000_000_000,
        clock_review=review,
    )
    view = controller.serving_rollback_view(HEX_B)
    assert view["authority_head"] == PUB
    assert view["session_resumable"] is False
    bad_review = base_clock_review(
        boot_id="boot-fixture-0003",
        expires_at="2026-09-23T00:00:00Z",
        reviewed_wall_time="2026-09-21T13:00:00Z",
    )
    platform.new_boot("boot-fixture-0003", wall_time="2026-09-21T13:00:00Z")
    install_clock_review_inventory(platform, bad_review)
    with pytest.raises(ValueError, match="expiry_renewal_forbidden"):
        controller.establish_freshness_anchor(
            controller.slots[HEX_B],
            authority_snapshot_id="snap-fixture-1",
            remaining_snapshot_lifetime_ns=1_000_000_000,
            clock_review=bad_review,
        )
    assert clock_review_inventory_bytes(review)


def test_case33_spawn_tuple_exact_trace():
    platform, controller, supervisor, _ = _pair()
    policy = base_launch_policy()
    import openclaw_activation_supervisor as sup

    with pytest.raises(ValueError):
        sup.validate_launch_tuple(
            policy,
            "agent",
            ["/evil"],
            dict(policy["processes"]["agent"]["environment"]),
            "/fixture/empty",
            {"stdin": object(), "stdout": object(), "stderr": object()},
        )
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(HEX_B, base_activation_manifest(), policy, lifecycle_config={})
    spawn_recs = [t for t in platform.trace if t["op"] == "spawn" and t["role"] == "supervisor"]
    assert spawn_recs
    assert spawn_recs[0]["argv"] == list(policy["processes"]["supervisor"]["argv_template"])
    assert spawn_recs[0]["cwd"] == policy["processes"]["supervisor"]["cwd"]
    assert spawn_recs[0]["env"] == dict(policy["processes"]["supervisor"]["environment"])


def test_case35_kill_child_partial_success_paths():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    op1 = open_operator_session(controller, platform, "op1")
    controller.handle_control(op1, turn_request())
    handle = supervisor.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    platform.schedule_event(handle, "exit", exit_code=9)
    ev = platform.next_event(handle)
    supervisor.ingest_agent_event(ev)
    assert supervisor.state == "REVOKING"
    with pytest.raises(ValueError, match="no_active_turn|revoked_before_commit|nonzero_agent_exit"):
        supervisor.release_commit()

    controller2_platform, controller2, supervisor2, _ = _pair()
    controller2.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller2.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    op2 = open_operator_session(controller2, controller2_platform, "op1")
    controller2.handle_control(op2, turn_request())
    h2 = supervisor2.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    controller2_platform.schedule_agent_success(h2)
    supervisor2.ingest_agent_event(controller2_platform.next_event(h2))
    supervisor2.ingest_agent_event(controller2_platform.next_event(h2))
    committed = supervisor2.release_commit()
    assert committed["model_output"]["fixture"] == "protocol-only"


def test_case45_lifecycle_config_disables_and_no_unsolicited_turn():
    import openclaw_activation_controller as ctl

    core = ctl.lifecycle_config_core({})
    assert core["heartbeat"] is False
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config=core
    )
    assert supervisor.active_turn_id is None
    op1 = open_operator_session(controller, platform, "op1")
    st = controller.handle_control(op1, status_request())
    assert st["payload"]["turn_id"] is None


def test_partial_frame_and_lock_order():
    platform, controller, supervisor, _ = _pair()
    script_partial_frame_discard(platform)
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    inv = controller.slots[HEX_B].unit_invocation_id
    _enter_revoking_for_retirement(controller)
    platform.clear_all_members(inv)
    platform.force_observe(inv, terminal=True, populated=False)
    controller.attempt_retirement(HEX_B)
    controller.retire_before_lineage_exclusive(HEX_B)


def test_case58_production_refusal_with_unwrapped_specimen_bytes():
    import openclaw_activation_controller as ctl

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
    platform.peer("op1")  # authenticated peer observation (set_peer alone is harness)
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


def test_duplicate_key_frame_rejected():
    from fixture_platform import decode_json_object

    with pytest.raises(ValueError, match="duplicate_key"):
        decode_json_object(b'{"a":1,"a":2}')


# --- Negative / independence regression (Codex parent-contract defects) ---


def test_negative_self_hash_and_capability_cannot_excuse():
    import openclaw_activation_controller as ctl

    manifest = base_activation_manifest()
    expected = independent_content_hash(manifest, "manifest_payload_sha256")
    assert manifest["manifest_payload_sha256"] == expected
    bad = dict(manifest)
    bad["manifest_payload_sha256"] = "sha256:" + ("0" * 64)
    assert bad["manifest_payload_sha256"] != expected
    with pytest.raises(ValueError, match="manifest_self_hash"):
        ctl.validate_activation_manifest(
            bad,
            slot_id=HEX_B,
            lineage_id=HEX_A,
            authority_head=PUB,
            expires_at="2026-09-22T00:00:00Z",
            capability_digests={"activation_manifest": expected},
        )

    policy = base_launch_policy()
    expected_p = independent_content_hash(policy, "policy_payload_sha256")
    bad_p = dict(policy)
    bad_p["policy_payload_sha256"] = "sha256:" + ("1" * 64)
    assert bad_p["policy_payload_sha256"] != expected_p
    with pytest.raises(ValueError, match="launch_policy_self_hash"):
        ctl.validate_launch_policy(
            bad_p, capability_digests={"launch_policy": expected_p}
        )


def test_negative_nested_launch_shape_env_fd_mount_endpoint():
    import openclaw_activation_controller as ctl

    policy = base_launch_policy()
    # Env key mutation.
    bad_env = copy.deepcopy(policy)
    bad_env["processes"]["agent"]["environment"]["EVIL"] = "1"
    bad_env["policy_payload_sha256"] = independent_content_hash(
        bad_env, "policy_payload_sha256"
    )
    with pytest.raises(ValueError, match="env_keys"):
        ctl.validate_launch_policy(bad_env)

    # FD inheritance mutation.
    bad_fd = copy.deepcopy(policy)
    bad_fd["processes"]["agent"]["inherited_fd_roles"] = ["control"]
    bad_fd["policy_payload_sha256"] = independent_content_hash(
        bad_fd, "policy_payload_sha256"
    )
    with pytest.raises(ValueError, match="fd_roles_fixed:agent|runtime_fd_forbidden|bad_fd"):
        ctl.validate_launch_policy(bad_fd)

    # Mount source role mutation.
    bad_mount = copy.deepcopy(policy)
    bad_mount["writable_mounts"][0]["source_role"] = "host_home"
    bad_mount["policy_payload_sha256"] = independent_content_hash(
        bad_mount, "policy_payload_sha256"
    )
    with pytest.raises(ValueError, match="mount_source_role|writable_mount"):
        ctl.validate_launch_policy(bad_mount)

    # Endpoint ports not distinct.
    bad_ep = copy.deepcopy(policy)
    bad_ep["endpoints"]["model_port"] = bad_ep["endpoints"]["gateway_port"]
    bad_ep["policy_payload_sha256"] = independent_content_hash(
        bad_ep, "policy_payload_sha256"
    )
    with pytest.raises(ValueError, match="endpoint_ports_not_distinct"):
        ctl.validate_launch_policy(bad_ep)


def test_negative_noncanonical_frame_and_connection_accounting():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    # Unopened connection must not be serviced.
    assert controller.handle_framed_bytes("never-opened", b"\x00\x00\x00\x01{") is None

    platform.open_control_connection("op1", "operator")
    controller.open_control_session("op1")
    with pytest.raises(ValueError, match="duplicate_control_open"):
        controller.open_control_session("op1")
    assert controller._active_control_connections == 1

    # Non-canonical JSON (space after colon) rejected even if parseable; closes op1.
    obj = status_request()
    ugly = json.dumps(obj, separators=(", ", ": ")).encode("utf-8")
    frame = struct.pack(">I", len(ugly)) + ugly
    assert controller.handle_framed_bytes("op1", frame) is None
    assert controller._active_control_connections == 0

    # Unknown close must not decrement — exercise on a newly opened live connection.
    platform.open_control_connection("op-live", "operator")
    controller.open_control_session("op-live")
    before = controller._active_control_connections
    assert before == 1
    controller.close_control_session("unknown-id")
    assert controller._active_control_connections == before
    controller.close_control_session("op-live")
    assert controller._active_control_connections == before - 1
    controller.close_control_session("op-live")  # already closed
    assert controller._active_control_connections == before - 1
    controller.close_control_session("op1")  # already closed by malformed frame
    assert controller._active_control_connections == before - 1


def test_negative_clock_review_wrong_hash_and_wall_binding():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    platform.new_boot("boot-fixture-0002", wall_time="2026-09-21T12:00:00Z")
    review = base_clock_review()
    # Plant body-without-hash only — insufficient.
    body_wo = {k: review[k] for k in sorted(review) if k != "review_payload_sha256"}
    platform.install_operator_inventory_bytes(independent_canonical(body_wo))
    with pytest.raises(ValueError, match="clock_review_inventory_miss"):
        controller.establish_freshness_anchor(
            controller.slots[HEX_B],
            authority_snapshot_id="snap-fixture-1",
            remaining_snapshot_lifetime_ns=1_000_000_000,
            clock_review=review,
        )
    # Wrong embedded hash with full-object plant of correct bytes still fails self-hash.
    good_bytes = clock_review_inventory_bytes(review)
    platform.install_operator_inventory_bytes(good_bytes)
    wrong = dict(review)
    wrong["review_payload_sha256"] = "sha256:" + ("d" * 64)
    assert wrong["review_payload_sha256"] != independent_content_hash(
        wrong, "review_payload_sha256"
    )
    with pytest.raises(ValueError, match="clock_review_self_hash"):
        controller.establish_freshness_anchor(
            controller.slots[HEX_B],
            authority_snapshot_id="snap-fixture-1",
            remaining_snapshot_lifetime_ns=1_000_000_000,
            clock_review=wrong,
        )
    # Unrelated wall must not authorize.
    wall_bad = base_clock_review(reviewed_wall_time="2026-09-21T11:00:00Z")
    install_clock_review_inventory(platform, wall_bad)
    with pytest.raises(ValueError, match="clock_review_wall_mismatch"):
        controller.establish_freshness_anchor(
            controller.slots[HEX_B],
            authority_snapshot_id="snap-fixture-1",
            remaining_snapshot_lifetime_ns=1_000_000_000,
            clock_review=wall_bad,
        )


def test_negative_empty_fd_roles_not_unconstrained():
    import openclaw_activation_supervisor as sup

    policy = base_launch_policy()
    # Policy lists supervisor fds; empty spawn map must fail.
    with pytest.raises(ValueError, match="fd_roles_mismatch"):
        sup.validate_launch_tuple(
            policy,
            "supervisor",
            list(policy["processes"]["supervisor"]["argv_template"]),
            dict(policy["processes"]["supervisor"]["environment"]),
            "/fixture/empty",
            {},
        )


def test_capacity_drives_manager_stop_and_capacity_receipt():
    """cap → REVOKING+stop → uncertain/nonempty refuse → exact empty permits capacity."""

    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    # Fill accepted history to 256 via one live commit + 255 preload.
    op = open_operator_session(controller, platform, "cap-op")
    assert controller.handle_control(op, turn_request())["outcome"] == "running"
    handle = supervisor.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    platform.schedule_agent_success(handle)
    supervisor.ingest_agent_event(platform.next_event(handle))
    supervisor.ingest_agent_event(platform.next_event(handle))
    supervisor.release_commit()
    controller.slots[HEX_B].state = "ACTIVE_IDLE"
    records = platform.preload_accepted_turn_history(count=255, turn_state="committed")
    supervisor.preload_completed_history(records)
    assert len(supervisor.accepted) == 256

    capped = controller.handle_control(
        op,
        turn_request(
            request_id="99999999999999999999999999999999",
            turn_id="88888888888888888888888888888888",
            text="cap",
        ),
    )
    assert capped["outcome"] == "unavailable"
    assert capped["payload"]["reason"] == "capacity"
    st = controller.slots[HEX_B]
    assert st.state == "REVOKING"
    assert st.terminal_reason == "capacity"
    assert st.stop_requested is True
    assert st.persisted.get("stop_requested") is True
    assert "manager_stop" in platform.port_ops()

    inv = st.unit_invocation_id
    platform.force_observe(inv, terminal=True, populated=None)
    with pytest.raises(ValueError, match="quarantined"):
        controller.attempt_retirement(HEX_B)
    assert controller.slots[HEX_B].state == "QUARANTINED"

    # Fresh activation path for nonempty refuse (re-enroll via new controller pair).
    platform2, controller2, supervisor2, _ = _pair()
    controller2.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller2.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    op2 = open_operator_session(controller2, platform2, "cap-op2")
    assert controller2.handle_control(op2, turn_request())["outcome"] == "running"
    h2 = supervisor2.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    platform2.schedule_agent_success(h2)
    supervisor2.ingest_agent_event(platform2.next_event(h2))
    supervisor2.ingest_agent_event(platform2.next_event(h2))
    supervisor2.release_commit()
    controller2.slots[HEX_B].state = "ACTIVE_IDLE"
    supervisor2.preload_completed_history(
        platform2.preload_accepted_turn_history(count=255, turn_state="committed")
    )
    controller2.handle_control(
        op2,
        turn_request(
            request_id="99999999999999999999999999999999",
            turn_id="88888888888888888888888888888888",
            text="cap",
        ),
    )
    inv2 = controller2.slots[HEX_B].unit_invocation_id
    platform2.force_observe(inv2, terminal=True, populated=True)
    with pytest.raises(ValueError, match="quarantined"):
        controller2.attempt_retirement(HEX_B)

    platform3, controller3, supervisor3, _ = _pair()
    controller3.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller3.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    op3 = open_operator_session(controller3, platform3, "cap-op3")
    assert controller3.handle_control(op3, turn_request())["outcome"] == "running"
    h3 = supervisor3.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    platform3.schedule_agent_success(h3)
    supervisor3.ingest_agent_event(platform3.next_event(h3))
    supervisor3.ingest_agent_event(platform3.next_event(h3))
    supervisor3.release_commit()
    controller3.slots[HEX_B].state = "ACTIVE_IDLE"
    supervisor3.preload_completed_history(
        platform3.preload_accepted_turn_history(count=255, turn_state="committed")
    )
    controller3.handle_control(
        op3,
        turn_request(
            request_id="99999999999999999999999999999999",
            turn_id="88888888888888888888888888888888",
            text="cap",
        ),
    )
    st3 = controller3.slots[HEX_B]
    assert st3.state == "REVOKING"
    assert st3.terminal_reason == "capacity"
    inv3 = st3.unit_invocation_id
    platform3.clear_all_members(inv3)
    platform3.force_observe(inv3, terminal=True, populated=False)
    receipt = controller3.attempt_retirement(HEX_B)
    assert receipt["terminal_reason"] == "capacity"
    assert st3.state == "SEALED"
    sealed = controller3.handle_control(op3, status_request(request_id=HEX_E))
    assert sealed["outcome"] == "sealed"
    assert sealed["payload"]["retirement_ref"] == receipt["receipt_payload_sha256"]
    assert sealed["payload"]["retirement_ref"] is not None


def test_launch_policy_fixed_fd_roles_and_executable_constraints():
    import openclaw_activation_controller as ctl

    policy = base_launch_policy()
    # Remove required supervisor descriptor role.
    bad_sup = copy.deepcopy(policy)
    bad_sup["processes"]["supervisor"]["inherited_fd_roles"] = [
        "supervisor_control",
        "notify",
    ]
    bad_sup["policy_payload_sha256"] = independent_content_hash(
        bad_sup, "policy_payload_sha256"
    )
    with pytest.raises(ValueError, match="fd_roles_fixed:supervisor"):
        ctl.validate_launch_policy(bad_sup)

    # Remove required agent stdin role.
    bad_ag = copy.deepcopy(policy)
    bad_ag["processes"]["agent"]["inherited_fd_roles"] = ["stdout", "stderr"]
    bad_ag["policy_payload_sha256"] = independent_content_hash(
        bad_ag, "policy_payload_sha256"
    )
    with pytest.raises(ValueError, match="fd_roles_fixed:agent"):
        ctl.validate_launch_policy(bad_ag)

    # Swap executable while re-self-hashing — argv[0] must equal executable.
    bad_exe = copy.deepcopy(policy)
    bad_exe["processes"]["gateway"]["executable"] = "/fixture/bin/evil-node"
    bad_exe["policy_payload_sha256"] = independent_content_hash(
        bad_exe, "policy_payload_sha256"
    )
    with pytest.raises(ValueError, match="executable_mismatch:gateway"):
        ctl.validate_launch_policy(bad_exe)

    bad_agent_exe = copy.deepcopy(policy)
    bad_agent_exe["processes"]["agent"]["executable"] = "/fixture/bin/evil-node"
    bad_agent_exe["policy_payload_sha256"] = independent_content_hash(
        bad_agent_exe, "policy_payload_sha256"
    )
    with pytest.raises(ValueError, match="executable_mismatch:agent"):
        ctl.validate_launch_policy(bad_agent_exe)

    # strict_server setpriv structure / executable relationship.
    bad_ss = copy.deepcopy(policy)
    bad_ss["processes"]["strict_server"]["argv_template"][7] = "/fixture/bin/other"
    bad_ss["policy_payload_sha256"] = independent_content_hash(
        bad_ss, "policy_payload_sha256"
    )
    with pytest.raises(ValueError, match="strict_server_executable_mismatch"):
        ctl.validate_launch_policy(bad_ss)


def test_lifetime_authority_negative_and_caller_max_cannot_enlarge():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    with pytest.raises(ValueError, match="negative_snapshot_lifetime"):
        controller.qualify_and_activate(
            HEX_B,
            base_activation_manifest(),
            base_launch_policy(),
            lifecycle_config={},
            remaining_snapshot_lifetime_ns=-1,
        )
    assert controller.slots[HEX_B].state in ("NEW", "REVOKING")
    assert controller.slots[HEX_B].freshness_anchor is None

    platform2, controller2, supervisor2, _ = _pair()
    controller2.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    manifest = base_activation_manifest()
    manifest_max = manifest["max_monotonic_lifetime_seconds"]
    assert manifest_max == 3600
    st = controller2.qualify_and_activate(
        HEX_B,
        manifest,
        base_launch_policy(),
        lifecycle_config={},
        max_activation_lifetime_s=86_400,  # larger than manifest — must not enlarge
    )
    # Lease bound uses min(manifest_max, remaining_wall) — not the enlarged caller max.
    sample = platform2.sample_clock()
    # Effective max stays manifest_max (3600), not 86400.
    expected_lease_cap = int(sample["boottime_after_ns"]) + 1_000_000_000 * manifest_max
    assert st.lease_deadline_boottime_ns is not None
    assert st.lease_deadline_boottime_ns <= expected_lease_cap
    assert st.lease_deadline_boottime_ns < int(sample["boottime_after_ns"]) + 1_000_000_000 * 86_400


def test_closed_scalar_path_and_timestamp_validation():
    import openclaw_activation_controller as ctl

    with pytest.raises(ValueError, match="bad_wall_time"):
        ctl._parse_wall("2026-09-21 00:00:00Z")
    with pytest.raises(ValueError, match="bad_wall_time"):
        ctl._parse_wall("2026/09/21T00:00:00Z")
    with pytest.raises(ValueError, match="bad_wall_time"):
        ctl._parse_wall("2026-02-30T00:00:00Z")
    with pytest.raises(ValueError, match="bad_wall_time"):
        ctl._parse_wall("2026-09-21T24:00:00Z")
    with pytest.raises(ValueError, match="bad_wall_time"):
        ctl._parse_wall("2026-09-21T00:60:00Z")
    assert ctl._parse_wall("2026-09-21T00:00:00Z") > 0

    for bad_dir in (
        "/fixture/state/",
        "/fixture/state//act",
        "/fixture/state/./act",
        "/fixture/state/../etc",
        "/fixture/state/act/../x",
        "/fixture/state",
        "/other/state/act-1",
    ):
        with pytest.raises(ValueError, match="bad_state_dir"):
            ctl._validate_state_dir(bad_dir)
    assert ctl._validate_state_dir("/fixture/state/act-1") == "/fixture/state/act-1"

    manifest = base_activation_manifest()
    bad_port = dict(manifest)
    bad_port["gateway_port"] = True  # bool must not pass as int
    bad_port["manifest_payload_sha256"] = independent_content_hash(
        bad_port, "manifest_payload_sha256"
    )
    with pytest.raises(ValueError, match="bad_gateway_port"):
        ctl.validate_activation_manifest(
            bad_port,
            slot_id=HEX_B,
            lineage_id=HEX_A,
            authority_head=PUB,
            expires_at="2026-09-22T00:00:00Z",
        )

    policy = base_launch_policy()
    bad_uid = copy.deepcopy(policy)
    bad_uid["operator_uid"] = True
    bad_uid["policy_payload_sha256"] = independent_content_hash(
        bad_uid, "policy_payload_sha256"
    )
    with pytest.raises(ValueError, match="bad_operator_uid"):
        ctl.validate_launch_policy(bad_uid)


def test_framed_send_timeout_closes_without_partial_success():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    platform.open_control_connection("opsend", "operator")
    controller.open_control_session("opsend")
    outbound = platform.control_outbound("opsend")
    outbound.blocked = True
    frame = encode_control_frame(status_request(request_id=HEX_E))
    # First attempt: blocked send — no partial success; pending SEND armed.
    assert controller.handle_framed_bytes("opsend", frame) is None
    assert len(outbound.write_trace) == 0
    assert "opsend" in controller._open_sessions
    assert "opsend" in controller._pending_outbound
    # Scripted 10s SEND timeout via pending flush (fixture boottime — not host time).
    platform.advance_boottime(CONTROL_IO_TIMEOUT_NS + 1)
    assert controller.handle_framed_bytes("opsend", b"") is None
    assert "opsend" not in controller._open_sessions
    assert len(outbound.write_trace) == 0
    assert "opsend" not in controller._pending_outbound
