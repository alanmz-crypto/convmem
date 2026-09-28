"""Hermetic tests for DeepSeek V4-Pro audit substitute core."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from eval_corpus.deepseek_audit_substitute import (
    AUDIT_SPEC_VERSION,
    AUTHORIZED_PRODUCER_PATHS,
    MODEL_ID,
    STATIC_REVIEW_FRAMING,
    Terminal,
    AuditSpecError,
    audit_run_key,
    audit_run_key_v1,
    audit_spec_digest,
    build_evidence_packet_text,
    build_user_message,
    compose_system_prompt_with_example,
    detect_unsupported_execution_claims,
    egress_scan_decoded_content,
    egress_scan_outbound_body,
    evidence_packet_sha256,
    find_authorized_marker,
    length_prefixed_sha256,
    load_audit_spec,
    make_boundary_nonce,
    marker_html,
    parse_audit_spec,
    parse_strict_json,
    producer_identity_digest,
    request_envelope_sha256,
    resolve_producer_identity,
    system_prompt_sha256,
    validate_locked_envelope_structure,
    validate_model_response,
)
from eval_corpus.deepseek_audit_substitute import ProducerIdentity

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "deepseek_audit_substitute.py"

TIP = "a" * 40
BASE = "b" * 40


def _independent_locked_envelope(system_text: str, user_text: str) -> dict:
    """Test-owned locked wire envelope oracle (structurally distinct from production)."""
    messages = []
    for role, content in (("system", system_text), ("user", user_text)):
        messages.append({"role": role, "content": content})
    envelope: dict = {"model": MODEL_ID, "messages": messages}
    for key, value in (
        ("thinking", {"type": "enabled"}),
        ("reasoning_effort", "high"),
        ("response_format", {"type": "json_object"}),
        ("max_tokens", 8192),
        ("stream", False),
    ):
        envelope[key] = value
    return envelope


def _valid_spec_dict(**overrides) -> dict:
    base = {
        "audit_spec_version": AUDIT_SPEC_VERSION,
        "mode": "pre_pr_static_git_evidence",
        "criteria": [
            {"id": "C1", "meaning": "Seven authorized files only."},
            {"id": "C2a", "meaning": "Destination contract."},
            {"id": "C2b", "meaning": "Engine identity."},
            {"id": "C3", "meaning": "Permissions."},
            {"id": "C4a", "meaning": "Theme transfer."},
            {"id": "C4b", "meaning": "Present/absent."},
            {"id": "C5", "meaning": "Removed chowns."},
            {"id": "C6", "meaning": "Test mapping."},
            {"id": "C7", "meaning": "Documentation gaps."},
        ],
        "required_dependencies": [
            "docker-compose.yml",
            ".gitignore",
            "scripts/practice-theme-preflight.sh",
            "tests/practice-theme-preflight.sh",
        ],
    }
    base.update(overrides)
    return base


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


def _init_repo(path: Path) -> None:
    subprocess.check_call(["git", "init", "-q"], cwd=path)
    subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=path)
    subprocess.check_call(["git", "config", "user.name", "Test"], cwd=path)


def _commit_all(path: Path, message: str = "commit") -> str:
    subprocess.check_call(["git", "add", "-A"], cwd=path)
    subprocess.check_call(["git", "commit", "-q", "-m", message], cwd=path)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()


def _disposable_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _init_repo(repo)
    return repo

def _disposable_producer_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "producer"
    repo.mkdir(parents=True, exist_ok=True)
    _init_repo(repo)
    for rel in AUTHORIZED_PRODUCER_PATHS:
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"producer {rel}\n", encoding="utf-8")
    _commit_all(repo, "producer baseline")
    return repo


def _disposable_audited_repo(tmp_path: Path) -> tuple[Path, str, str]:
    audited = _disposable_repo(tmp_path / "audited")
    for dep in [
        "docker-compose.yml",
        ".gitignore",
        "scripts/practice-theme-preflight.sh",
        "tests/practice-theme-preflight.sh",
    ]:
        dep_path = audited / dep
        dep_path.parent.mkdir(parents=True, exist_ok=True)
        dep_path.write_text("*.pyc\n" if dep == ".gitignore" else f"{dep}\n", encoding="utf-8")
    (audited / "changed.txt").write_text("v1\n", encoding="utf-8")
    base = _commit_all(audited)
    (audited / "changed.txt").write_text("v2\n", encoding="utf-8")
    tip = _commit_all(audited, "tip")
    return audited, base, tip


def _block_external_calls(monkeypatch) -> None:
    def _fail_if_called(*_a, **_k):
        raise AssertionError("live external call attempted")

    monkeypatch.setattr("requests.post", _fail_if_called)

    real_check_call = subprocess.check_call

    def _guarded_check_call(cmd, *args, **kwargs):
        if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "gh":
            raise AssertionError("gh posting attempted")
        return real_check_call(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "check_call", _guarded_check_call)


def _parse_main_json(stdout: str) -> dict:
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("{") and "terminal" in line:
            return json.loads(line)
    raise AssertionError(f"no JSON terminal payload in stdout: {stdout!r}")


def _run_main(
    *,
    audited: Path,
    producer: Path,
    spec_path: Path,
    tip: str,
    base: str,
    out_dir: Path,
    monkeypatch,
) -> tuple[int, str, str]:
    from scripts import deepseek_audit_substitute as cli

    monkeypatch.setattr(cli, "ROOT", producer)
    _block_external_calls(monkeypatch)
    rc = cli.main(
        [
            "--repo",
            str(audited),
            "--audit-spec",
            str(spec_path),
            "--tip",
            tip,
            "--base",
            base,
            "--out-dir",
            str(out_dir),
        ]
    )
    return rc, "", ""  # caller uses capsys


def test_length_prefixed_order_matters():
    a = length_prefixed_sha256([b"ab", b"c"])
    b = length_prefixed_sha256([b"a", b"bc"])
    assert a != b


def test_nonce_not_in_evidence_digest():
    evidence = build_evidence_packet_text(
        tip=TIP,
        base=BASE,
        spec_digest="s" * 64,
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
    spec = parse_audit_spec(_valid_spec_dict())
    spec_d = audit_spec_digest(spec)
    prod_d = "p" * 64
    evidence = build_evidence_packet_text(
        tip=TIP,
        base=BASE,
        spec_digest=spec_d,
        name_status_lines=["A\tx.md"],
        file_sections=[("x.md", "oid", "body")],
    )
    digest = evidence_packet_sha256(evidence)
    system = compose_system_prompt_with_example(TIP, BASE, digest, spec.criteria)
    sys_d = system_prompt_sha256(system)
    u1 = build_user_message(evidence_bytes=evidence, evidence_digest=digest, boundary_nonce="aa" * 16)
    u2 = build_user_message(evidence_bytes=evidence, evidence_digest=digest, boundary_nonce="bb" * 16)
    assert request_envelope_sha256(system_prompt=system, user_message=u1) != request_envelope_sha256(
        system_prompt=system, user_message=u2
    )
    k1 = audit_run_key(
        tip=TIP,
        base=BASE,
        evidence_digest=digest,
        system_digest=sys_d,
        spec_digest=spec_d,
        producer_identity_digest_value=prod_d,
    )
    k2 = audit_run_key(
        tip=TIP,
        base=BASE,
        evidence_digest=digest,
        system_digest=sys_d,
        spec_digest=spec_d,
        producer_identity_digest_value=prod_d,
    )
    assert k1 == k2


def test_duplicate_json_keys_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        parse_strict_json('{"a":1,"a":2}')


def test_validate_pass_and_fail_and_invalid():
    evidence = build_evidence_packet_text(
        tip=TIP,
        base=BASE,
        spec_digest="d" * 64,
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


def test_valid_max_tokens_envelope_passes_structure_validation():
    payload = _independent_locked_envelope("x", "y")
    assert not validate_locked_envelope_structure(payload)
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    assert not egress_scan_outbound_body(body)


def test_egress_flags_credential_without_exposing_value():
    secret = "sk-abcdefghijklmnopqrstuvwxyz1234567890"
    hits = egress_scan_decoded_content(f"Authorization Bearer {secret}")
    assert hits
    assert secret not in hits[0]
    body = json.dumps(
        _independent_locked_envelope("safe", f"token={secret}"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    outbound_hits = egress_scan_outbound_body(body)
    assert outbound_hits
    assert secret not in " ".join(outbound_hits)


def test_bare_token_word_does_not_trigger_egress():
    body = json.dumps(
        _independent_locked_envelope("safe", "discuss oauth token field semantics only"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    assert not egress_scan_outbound_body(body)


def test_malformed_spec_rejected(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(AuditSpecError):
        load_audit_spec(bad)


def test_missing_criteria_rejected():
    with pytest.raises(AuditSpecError, match="missing_criteria"):
        parse_audit_spec(_valid_spec_dict(criteria=[]))


def test_wrong_criteria_id_set_rejected():
    spec = _valid_spec_dict()
    spec["criteria"] = [{"id": "C1", "meaning": "only one"}]
    with pytest.raises(AuditSpecError, match="criteria_id_set"):
        parse_audit_spec(spec)


def test_missing_dependency_block_in_evidence(tmp_path: Path):
    repo = _disposable_repo(tmp_path)
    (repo / "changed.txt").write_text("v1\n", encoding="utf-8")
    base = _commit_all(repo)
    (repo / "changed.txt").write_text("v2\n", encoding="utf-8")
    tip = _commit_all(repo, "tip")

    spec = parse_audit_spec(_valid_spec_dict())
    spec_d = audit_spec_digest(spec)

    from scripts.deepseek_audit_substitute import build_packet_from_git

    with pytest.raises(FileNotFoundError, match="missing_required_dependencies"):
        build_packet_from_git(
            repo,
            tip,
            base,
            required_dependencies=list(spec.required_dependencies),
            spec_digest=spec_d,
        )


def test_dependency_bytes_and_oids_match_pinned_revision(tmp_path: Path):
    repo = _disposable_repo(tmp_path)
    (repo / "docker-compose.yml").write_text("version: '3'\n", encoding="utf-8")
    (repo / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    base = _commit_all(repo)
    (repo / "changed.txt").write_text("x\n", encoding="utf-8")
    tip = _commit_all(repo, "tip")

    spec = parse_audit_spec(
        _valid_spec_dict(required_dependencies=["docker-compose.yml", ".gitignore"])
    )
    spec_d = audit_spec_digest(spec)

    from scripts.deepseek_audit_substitute import build_packet_from_git

    packet = build_packet_from_git(
        repo,
        tip,
        base,
        required_dependencies=list(spec.required_dependencies),
        spec_digest=spec_d,
    )
    text = packet.decode()
    expected_oid = subprocess.check_output(
        ["git", "rev-parse", f"{tip}:docker-compose.yml"], cwd=repo, text=True
    ).strip()
    assert f"dependency=docker-compose.yml blob={expected_oid}" in text
    assert "version: '3'" in text
    assert f"spec_digest: {spec_d}" in text


def test_producer_identity_from_producer_checkout(tmp_path: Path):
    repo = _disposable_repo(tmp_path)
    for rel in AUTHORIZED_PRODUCER_PATHS:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"content for {rel}\n", encoding="utf-8")
    head = _commit_all(repo)

    identity = resolve_producer_identity(repo)
    assert identity.head_sha == head
    assert set(identity.path_blobs) == set(AUTHORIZED_PRODUCER_PATHS)
    assert not identity.dirty_paths


def test_each_dirty_producer_path_blocks(tmp_path: Path):
    repo = _disposable_repo(tmp_path)
    for rel in AUTHORIZED_PRODUCER_PATHS:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"content for {rel}\n", encoding="utf-8")
    _commit_all(repo)

    for rel in AUTHORIZED_PRODUCER_PATHS:
        (repo / rel).write_text("dirty\n", encoding="utf-8")
        identity = resolve_producer_identity(repo)
        assert rel in identity.dirty_paths
        (repo / rel).write_text(f"content for {rel}\n", encoding="utf-8")


def test_unrelated_dirt_does_not_block_producer(tmp_path: Path):
    repo = _disposable_repo(tmp_path)
    for rel in AUTHORIZED_PRODUCER_PATHS:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"content for {rel}\n", encoding="utf-8")
    _commit_all(repo)
    (repo / "unrelated.txt").write_text("noise\n", encoding="utf-8")

    identity = resolve_producer_identity(repo)
    assert not identity.dirty_paths


def test_identity_changes_affect_digests_and_run_key():
    spec_d = "s" * 64
    evidence = build_evidence_packet_text(
        tip=TIP,
        base=BASE,
        spec_digest=spec_d,
        name_status_lines=[],
        file_sections=[],
    )
    digest = evidence_packet_sha256(evidence)
    system = compose_system_prompt_with_example(
        TIP,
        BASE,
        digest,
        parse_audit_spec(_valid_spec_dict()).criteria,
    )
    sys_d = system_prompt_sha256(system)

    id1 = ProducerIdentity(head_sha="1" * 40, path_blobs={"a": "o1"}, dirty_paths=())
    id2 = ProducerIdentity(head_sha="2" * 40, path_blobs={"a": "o2"}, dirty_paths=())
    d1 = producer_identity_digest(id1)
    d2 = producer_identity_digest(id2)
    assert d1 != d2

    k1 = audit_run_key(
        tip=TIP,
        base=BASE,
        evidence_digest=digest,
        system_digest=sys_d,
        spec_digest=spec_d,
        producer_identity_digest_value=d1,
    )
    k2 = audit_run_key(
        tip=TIP,
        base=BASE,
        evidence_digest=digest,
        system_digest=sys_d,
        spec_digest=spec_d,
        producer_identity_digest_value=d2,
    )
    assert k1 != k2


def test_unrelated_audited_head_movement_leaves_pinned_identity_unchanged(
    tmp_path: Path, monkeypatch, capsys
):
    producer = _disposable_producer_repo(tmp_path / "producer")
    audited, base, tip = _disposable_audited_repo(tmp_path)
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(_valid_spec_dict()), encoding="utf-8")

    from scripts import deepseek_audit_substitute as cli

    monkeypatch.setattr(cli, "ROOT", producer)
    _block_external_calls(monkeypatch)

    out1 = tmp_path / "out1"
    rc1 = cli.main(
        [
            "--repo",
            str(audited),
            "--audit-spec",
            str(spec_path),
            "--tip",
            tip,
            "--base",
            base,
            "--out-dir",
            str(out1),
        ]
    )
    captured1 = capsys.readouterr()
    assert rc1 == 0, captured1.err + captured1.out
    digests1 = json.loads((out1 / "digests.json").read_text(encoding="utf-8"))

    (audited / "unrelated-after-tip.txt").write_text("noise\n", encoding="utf-8")
    advanced_head = _commit_all(audited, "after tip")
    assert advanced_head != tip

    out2 = tmp_path / "out2"
    rc2 = cli.main(
        [
            "--repo",
            str(audited),
            "--audit-spec",
            str(spec_path),
            "--tip",
            tip,
            "--base",
            base,
            "--out-dir",
            str(out2),
        ]
    )
    captured2 = capsys.readouterr()
    assert rc2 == 0, captured2.err + captured2.out
    digests2 = json.loads((out2 / "digests.json").read_text(encoding="utf-8"))

    stable_keys = (
        "evidence_packet_sha256",
        "spec_digest",
        "producer_identity_digest",
        "AUDIT_RUN_KEY",
        "tip",
        "base",
        "producer_head_sha",
    )
    for key in stable_keys:
        assert digests1[key] == digests2[key]

    assert digests1["request_envelope_sha256"]
    assert digests2["request_envelope_sha256"]

    v1_a = audit_run_key_v1(
        tip=TIP,
        base=BASE,
        evidence_digest=digests1["evidence_packet_sha256"],
        system_digest=digests1["system_prompt_sha256"],
        runner_git_sha="old_head",
    )
    v1_b = audit_run_key_v1(
        tip=TIP,
        base=BASE,
        evidence_digest=digests1["evidence_packet_sha256"],
        system_digest=digests1["system_prompt_sha256"],
        runner_git_sha="new_head",
    )
    assert v1_a != v1_b




@pytest.mark.parametrize("dirty_mode", ["unstaged", "staged"])
def test_dirty_producer_blocks_main_preparation(
    tmp_path: Path, monkeypatch, capsys, dirty_mode: str
):
    producer = _disposable_producer_repo(tmp_path / "producer")
    audited, base, tip = _disposable_audited_repo(tmp_path)
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(_valid_spec_dict()), encoding="utf-8")
    out_dir = tmp_path / "out"

    from scripts import deepseek_audit_substitute as cli

    monkeypatch.setattr(cli, "ROOT", producer)
    _block_external_calls(monkeypatch)

    target = AUTHORIZED_PRODUCER_PATHS[0]
    (producer / target).write_text("dirty producer content\n", encoding="utf-8")
    if dirty_mode == "staged":
        subprocess.check_call(["git", "add", "--", target], cwd=producer)

    rc = cli.main(
        [
            "--repo",
            str(audited),
            "--audit-spec",
            str(spec_path),
            "--tip",
            tip,
            "--base",
            base,
            "--out-dir",
            str(out_dir),
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2, captured.err + captured.out
    payload = _parse_main_json(captured.out)
    assert payload["terminal"] == Terminal.INVALID_EXECUTION.value
    assert payload["reason"] == "producer_dirty"
    assert target in payload["paths"]
    assert not (out_dir / "digests.json").exists()
    assert not (out_dir / "evidence_packet.bin").exists()
    assert not (out_dir / "user_message.bin").exists()
    assert not (out_dir / "system_prompt.txt").exists()

def test_static_review_framing_in_system_prompt_and_comment():
    spec = parse_audit_spec(_valid_spec_dict())
    evidence = build_evidence_packet_text(
        tip=TIP,
        base=BASE,
        spec_digest=audit_spec_digest(spec),
        name_status_lines=[],
        file_sections=[],
    )
    digest = evidence_packet_sha256(evidence)
    system = compose_system_prompt_with_example(TIP, BASE, digest, spec.criteria)
    assert STATIC_REVIEW_FRAMING in system
    assert "C6:" in system

    from scripts.deepseek_audit_substitute import render_comment

    digests = {
        "marker": marker_html("k" * 64),
        "evidence_packet_sha256": digest,
        "request_envelope_sha256": "e" * 64,
        "AUDIT_RUN_KEY": "k" * 64,
    }
    result = validate_model_response(
        response=_ok_response(
            {
                "verdict": "PASS",
                "summary": "ok",
                "tip": TIP,
                "base": BASE,
                "packet_sha256": digest,
                "checklist": [
                    {"id": i, "status": "PASS", "evidence": "x"}
                    for i in (
                        "C1",
                        "C2a",
                        "C2b",
                        "C3",
                        "C4a",
                        "C4b",
                        "C5",
                        "C6",
                        "C7",
                    )
                ],
            }
        ),
        tip=TIP,
        base=BASE,
        evidence_digest=digest,
    )
    comment = render_comment(result, digests, TIP, BASE)
    assert STATIC_REVIEW_FRAMING in comment


def test_execution_claims_rejected():
    evidence = build_evidence_packet_text(
        tip=TIP,
        base=BASE,
        spec_digest="d" * 64,
        name_status_lines=[],
        file_sections=[],
    )
    digest = evidence_packet_sha256(evidence)
    checklist = [
        {"id": i, "status": "PASS", "evidence": "ok"}
        for i in ("C1", "C2a", "C2b", "C3", "C4a", "C4b", "C5", "C6", "C7")
    ]
    payload = {
        "verdict": "PASS",
        "summary": "I executed pytest and it passed",
        "tip": TIP,
        "base": BASE,
        "packet_sha256": digest,
        "checklist": checklist,
    }
    assert detect_unsupported_execution_claims(payload["summary"])
    result = validate_model_response(
        response=_ok_response(payload), tip=TIP, base=BASE, evidence_digest=digest
    )
    assert result.terminal == Terminal.INVALID_EXECUTION
    assert result.reason.startswith("execution_claim:")


def test_disposable_dry_run_succeeds_without_api_or_gh(tmp_path: Path, monkeypatch, capsys):
    producer = _disposable_producer_repo(tmp_path / "producer")
    audited, base, tip = _disposable_audited_repo(tmp_path)
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(_valid_spec_dict()), encoding="utf-8")
    out_dir = tmp_path / "out"

    from scripts import deepseek_audit_substitute as cli

    monkeypatch.setattr(cli, "ROOT", producer)
    _block_external_calls(monkeypatch)

    rc = cli.main(
        [
            "--repo",
            str(audited),
            "--audit-spec",
            str(spec_path),
            "--tip",
            tip,
            "--base",
            base,
            "--out-dir",
            str(out_dir),
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0, captured.err + captured.out
    assert (out_dir / "digests.json").exists()
    assert "dry-run complete" in captured.out
