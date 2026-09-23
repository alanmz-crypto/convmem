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
    base_activation_manifest,
    base_clock_review,
    base_launch_policy,
    cancel_request,
    clock_review_inventory_bytes,
    install_clock_review_inventory,
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
    # Path-component boundary: prefix /fixture/private/qualification must not
    # match /fixture/private/qualification-evil.
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
    # Eight authenticated concurrent connections via FixturePlatform queues.
    conns = []
    for i in range(MAX_CONTROL_CONNECTIONS):
        cid = f"op{i}"
        platform.open_control_connection(cid, "operator")
        controller.open_control_session(cid)
        conns.append(cid)
    with pytest.raises(ValueError, match="control_connection_capacity"):
        platform.open_control_connection("op-extra", "operator")

    # Partial frame remains partial — no success.
    cid = conns[0]
    full = encode_control_frame(status_request(request_id=HEX_E))
    partial = full[:5]
    assert controller.handle_framed_bytes(cid, partial) is None
    # Complete frame yields encoded closed response under 2MiB.
    framed = controller.handle_framed_bytes(cid, full[5:])
    assert framed is not None
    assert len(framed) <= MAX_REQUEST_FRAME * 2
    obj, rem, err = try_decode_control_frame(framed)
    assert err is None and rem == b"" and obj is not None
    assert obj["outcome"] == "status"
    assert set(obj.keys()) == {
        "schema",
        "request_id",
        "slot_id",
        "activation_id",
        "outcome",
        "payload",
    }

    # Trailing-frame desync closes with no partial success.
    cid2 = conns[1]
    desync = encode_control_frame(status_request(request_id=HEX_A)) + b"\x00"
    assert controller.handle_framed_bytes(cid2, desync) is None

    # Scripted 10s timeout closes idle connection.
    cid3 = conns[2]
    controller.handle_framed_bytes(cid3, encode_control_frame(status_request())[:3])
    platform.advance_boottime(CONTROL_IO_TIMEOUT_NS + 1)
    assert controller.handle_framed_bytes(cid3, b"\x00") is None


def test_framed_closed_requests_and_request_id_conflict():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    platform.open_control_connection("op1", "operator")
    controller.open_control_session("op1")

    # Extra field rejected.
    bad = turn_request()
    bad["extra"] = "nope"
    framed = controller.handle_framed_bytes("op1", encode_control_frame(bad))
    assert framed is not None
    obj, _, _ = try_decode_control_frame(framed)
    assert obj["outcome"] == "invalid_request"

    # Non-string text not coerced.
    bad2 = turn_request(request_id=HEX_E)
    bad2["text"] = 12345  # type: ignore[assignment]
    framed2 = controller.handle_framed_bytes("op1", encode_control_frame(bad2))
    obj2, _, _ = try_decode_control_frame(framed2)
    assert obj2["outcome"] == "invalid_request"

    # Accept turn, then same request_id with changed bytes → conflict.
    platform.set_peer("opd", "operator")
    r1 = controller.handle_control("opd", turn_request())
    assert r1["outcome"] == "running"
    conflict = turn_request(text="changed-bytes")
    r2 = controller.handle_control("opd", conflict)
    assert r2["outcome"] == "request_conflict"

    # New request_id, same turn identity → existing state (running).
    r3 = controller.handle_control(
        "opd",
        turn_request(request_id="ffffffffffffffffffffffffffffffff"),
    )
    assert r3["outcome"] == "running"


def test_cancel_to_revoking_then_independent_retirement():
    platform, controller, supervisor, _ = _pair()
    controller.enroll_slot(HEX_B, HEX_A, authority_head=PUB, expires_at="2026-09-22T00:00:00Z")
    controller.qualify_and_activate(
        HEX_B, base_activation_manifest(), base_launch_policy(), lifecycle_config={}
    )
    platform.set_peer("op1", "operator")
    assert controller.handle_control("op1", turn_request())["outcome"] == "running"
    c_resp = controller.handle_control(
        "op1", cancel_request(request_id="22222222222222222222222222222222")
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
    # Content hash on receipt (verified), not a re-hash including self-hash field alone.
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
    assert controller.slots[HEX_B].state == "SEALED"

    # SEALED has no outgoing transition on the sealed record — reuse archives it.
    controller.qualify_and_activate(
        HEX_B,
        base_activation_manifest(
            activation_id="ffffffffffffffffffffffffffffffff",
            state_dir="/fixture/state/act-2",
        ),
        base_launch_policy(),
        lifecycle_config={},
    )
    st = controller.slots[HEX_B]
    assert st.state == "ACTIVE_IDLE"
    assert st.activation_id == "ffffffffffffffffffffffffffffffff"
    assert len(st.sealed_history) == 1
    assert st.sealed_history[0].activation_id == first_act
    assert st.sealed_history[0].retirement_receipt == first_receipt
    # No old session resume.
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
    # Still retire/quarantine capable.
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
    # Explicit populated=null (unknown) — distinct from no override.
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
    # Restart must persist quarantine — not restore stale ACTIVE bytes.
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
    # Wall backwards seals via observed decrease.
    platform.advance_wall("2026-09-20T00:00:00Z")
    platform.set_peer("op1", "operator")
    controller.handle_control("op1", status_request())
    assert controller.slots[HEX_B].state == "REVOKING"
    assert controller.slots[HEX_B].terminal_reason == "clock_anomaly"

    # New boot: copied reviewer UID alone fails without inventory membership.
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
    bad_review = base_clock_review(expires_at="2026-09-23T00:00:00Z")
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
            {},
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
    platform.set_peer("op1", "operator")
    controller.handle_control("op1", turn_request())
    handle = supervisor.spawn_agent_for_active_turn(base_launch_policy(), "fixture turn")
    platform.schedule_event(handle, "exit", exit_code=9)
    ev = platform.next_event(handle)
    supervisor.ingest_agent_event(ev)
    with pytest.raises(ValueError, match="nonzero_agent_exit"):
        supervisor.release_commit()

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
    # object_pairs_hook path — not vacuous len(dict) check.
    from fixture_platform import decode_json_object

    with pytest.raises(ValueError, match="duplicate_key"):
        decode_json_object(b'{"a":1,"a":2}')
