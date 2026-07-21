"""Hermetic tests for DeepSeek V4-Pro audit substitute core."""

from __future__ import annotations

import json

from eval_corpus.deepseek_audit_substitute import (
    MODEL_ID,
    Terminal,
    audit_run_key,
    build_evidence_packet_text,
    build_user_message,
    compose_system_prompt_with_example,
    egress_scan_outbound_body,
    evidence_packet_sha256,
    find_authorized_marker,
    length_prefixed_sha256,
    make_boundary_nonce,
    marker_html,
    parse_strict_json,
    request_envelope_sha256,
    system_prompt_sha256,
    validate_model_response,
)


TIP = "a" * 40
BASE = "b" * 40


def _ok_response(content_obj: dict) -> dict:
    return {
        "id": "resp_test",
        "model": MODEL_ID,
        "system_fingerprint": "fp_test",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": json.dumps(content_obj)},
            }
        ],
    }


def test_length_prefixed_order_matters():
    a = length_prefixed_sha256([b"ab", b"c"])
    b = length_prefixed_sha256([b"a", b"bc"])
    assert a != b


def test_nonce_not_in_evidence_digest():
    evidence = build_evidence_packet_text(
        tip=TIP,
        base=BASE,
        name_status_lines=["M\tfoo.md"],
        file_sections=[("foo.md", "oid1", "hello")],
    )
    d1 = evidence_packet_sha256(evidence)
    nonce = make_boundary_nonce()
    _ = build_user_message(
        evidence_bytes=evidence, evidence_digest=d1, boundary_nonce=nonce
    )
    assert evidence_packet_sha256(evidence) == d1
    assert nonce not in evidence.decode()


def test_envelope_changes_with_nonce_but_run_key_stable_for_same_evidence():
    evidence = build_evidence_packet_text(
        tip=TIP,
        base=BASE,
        name_status_lines=["A\tx.md"],
        file_sections=[("x.md", "oid", "body")],
    )
    digest = evidence_packet_sha256(evidence)
    system = compose_system_prompt_with_example(TIP, BASE, digest)
    sys_d = system_prompt_sha256(system)
    u1 = build_user_message(evidence_bytes=evidence, evidence_digest=digest, boundary_nonce="aa" * 16)
    u2 = build_user_message(evidence_bytes=evidence, evidence_digest=digest, boundary_nonce="bb" * 16)
    assert request_envelope_sha256(system_prompt=system, user_message=u1) != request_envelope_sha256(
        system_prompt=system, user_message=u2
    )
    k1 = audit_run_key(
        tip=TIP, base=BASE, evidence_digest=digest, system_digest=sys_d, runner_git_sha="c" * 40
    )
    k2 = audit_run_key(
        tip=TIP, base=BASE, evidence_digest=digest, system_digest=sys_d, runner_git_sha="c" * 40
    )
    assert k1 == k2


def test_duplicate_json_keys_rejected():
    try:
        parse_strict_json('{"a":1,"a":2}')
        assert False, "expected error"
    except ValueError as exc:
        assert "duplicate" in str(exc)


def test_validate_pass_and_fail_and_invalid():
    evidence = build_evidence_packet_text(
        tip=TIP,
        base=BASE,
        name_status_lines=[],
        file_sections=[],
    )
    digest = evidence_packet_sha256(evidence)
    checklist = [
        {"id": i, "status": "PASS", "evidence": "ok"}
        for i in ("C1", "C2a", "C2b", "C3", "C4a", "C4b", "C5", "C6", "C7")
    ]
    good = {
        "verdict": "PASS",
        "summary": "fine",
        "tip": TIP,
        "base": BASE,
        "packet_sha256": digest,
        "checklist": checklist,
    }
    r = validate_model_response(
        response=_ok_response(good), tip=TIP, base=BASE, evidence_digest=digest
    )
    assert r.terminal == Terminal.VALID_PASS

    checklist_fail = list(checklist)
    checklist_fail[0] = {"id": "C1", "status": "FAIL", "evidence": "nope"}
    bad = dict(good)
    bad["checklist"] = checklist_fail
    bad["verdict"] = "FAIL"
    r2 = validate_model_response(
        response=_ok_response(bad), tip=TIP, base=BASE, evidence_digest=digest
    )
    assert r2.terminal == Terminal.VALID_FAIL

    empty = _ok_response(good)
    empty["choices"][0]["message"]["content"] = "   "
    r3 = validate_model_response(
        response=empty, tip=TIP, base=BASE, evidence_digest=digest
    )
    assert r3.terminal == Terminal.INVALID_EXECUTION
    assert r3.reason == "empty_content"

    tools = _ok_response(good)
    tools["choices"][0]["message"]["tool_calls"] = [{"id": "x"}]
    r4 = validate_model_response(
        response=tools, tip=TIP, base=BASE, evidence_digest=digest
    )
    assert r4.terminal == Terminal.INVALID_EXECUTION
    assert r4.reason == "tool_calls"


def test_marker_authorized_only_exact():
    key = "d" * 64
    body = f"hello\n{marker_html(key)}\n"
    assert find_authorized_marker(body, key)
    assert not find_authorized_marker("Tip: x\nPacket-SHA256: y\n", key)


def test_egress_flags_secret():
    hits = egress_scan_outbound_body(
        b'{"Authorization":"Bearer sk-abcdefghijklmnopqrstuvwxyz1234"}',
        allow_path_substrings=["Projects/convmem"],
    )
    assert hits
