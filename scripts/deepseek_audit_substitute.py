#!/usr/bin/env python3
"""CLI for DeepSeek V4-Pro Copilot audit-lane substitute.

Default is dry-run (build packet + digests + validate fixtures). Live API/post
requires --live and Ryan-facing confirmation flags.

Canonical: docs/plans/ARCHITECTURE-deepseek-v4pro-audit-substitute.md
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval_corpus.deepseek_audit_substitute import (  # pylint: disable=wrong-import-position
    AUDIT_PROTOCOL_VERSION,
    LOCKED_REQUEST_CONFIG,
    MODEL_ID,
    STATIC_REVIEW_FRAMING,
    Terminal,
    audit_run_key,
    audit_spec_digest,
    build_evidence_packet_text,
    build_user_message,
    compose_system_prompt_with_example,
    egress_scan_outbound_body,
    evidence_packet_sha256,
    load_audit_spec,
    make_boundary_nonce,
    marker_html,
    producer_identity_digest,
    request_envelope_sha256,
    resolve_producer_identity,
    system_prompt_sha256,
    validate_model_response,
)


def _run(cmd: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True)


def _git_show(repo: Path, rev_path: str) -> tuple[str, str]:
    oid = _run(["git", "rev-parse", rev_path], cwd=repo).strip()
    body = _run(["git", "show", rev_path], cwd=repo)
    return oid, body


def build_packet_from_git(
    repo: Path,
    tip: str,
    base: str,
    *,
    required_dependencies: list[str],
    spec_digest: str,
) -> bytes:
    name_status = _run(
        ["git", "diff", "--name-status", f"{base}..{tip}"], cwd=repo
    ).splitlines()
    sections: list[tuple[str, str, str]] = []
    for line in name_status:
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            path = parts[2]
            oid, body = _git_show(repo, f"{tip}:{path}")
            sections.append((path, oid, body))
            old = parts[1]
            try:
                oid_b, body_b = _git_show(repo, f"{base}:{old}")
                sections.append((f"{old} (base before rename)", oid_b, body_b))
            except subprocess.CalledProcessError:
                pass
        elif status.startswith("D") and len(parts) >= 2:
            path = parts[1]
            oid, body = _git_show(repo, f"{base}:{path}")
            sections.append((path, oid, body))
        elif status.startswith(("A", "M")) and len(parts) >= 2:
            path = parts[1]
            oid, body = _git_show(repo, f"{tip}:{path}")
            sections.append((path, oid, body))
            if status.startswith("M"):
                oid_b, body_b = _git_show(repo, f"{base}:{path}")
                sections.append((f"{path} (base)", oid_b, body_b))
        else:
            continue

    dependency_sections: list[tuple[str, str, str]] = []
    missing: list[str] = []
    for dep in required_dependencies:
        try:
            oid, body = _git_show(repo, f"{tip}:{dep}")
            dependency_sections.append((dep, oid, body))
        except subprocess.CalledProcessError:
            missing.append(dep)
    if missing:
        raise FileNotFoundError(
            "missing_required_dependencies:" + ",".join(sorted(missing))
        )

    return build_evidence_packet_text(
        tip=tip,
        base=base,
        spec_digest=spec_digest,
        name_status_lines=name_status,
        file_sections=sections,
        dependency_sections=dependency_sections,
    )


def main(argv: list[str] | None = None) -> int:  # pylint: disable=too-many-locals
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=ROOT, help="Audited repository checkout")
    p.add_argument("--audit-spec", type=Path, required=True, help="Slice 3A audit spec JSON")
    p.add_argument("--tip", required=True, help="40-char tip SHA")
    p.add_argument("--base", required=True, help="40-char base SHA")
    p.add_argument("--pr", type=int, help="PR number (required for --live post)")
    p.add_argument("--out-dir", type=Path, default=Path("/tmp/deepseek-audit-out"))
    p.add_argument(
        "--live",
        action="store_true",
        help="Call DeepSeek API (requires DEEPSEEK_API_KEY and --i-authorize-live)",
    )
    p.add_argument(
        "--i-authorize-live",
        action="store_true",
        help="Ryan-facing confirmation that live substitute audit is authorized",
    )
    p.add_argument(
        "--post-comment",
        action="store_true",
        help="Post VALID_PASS/VALID_FAIL comment via gh (requires --live success)",
    )
    args = p.parse_args(argv)

    tip, base = args.tip.lower(), args.base.lower()
    if len(tip) != 40 or len(base) != 40:
        print("tip/base must be full 40-char SHAs", file=sys.stderr)
        return 2

    audited_repo = args.repo.resolve()
    producer_repo = ROOT
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    try:
        spec = load_audit_spec(args.audit_spec)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(json.dumps({"terminal": Terminal.INVALID_EXECUTION.value, "reason": str(exc)}))
        return 2

    producer = resolve_producer_identity(producer_repo)
    if producer.dirty_paths:
        print(
            json.dumps(
                {
                    "terminal": Terminal.INVALID_EXECUTION.value,
                    "reason": "producer_dirty",
                    "paths": list(producer.dirty_paths),
                }
            )
        )
        return 2

    spec_digest = audit_spec_digest(spec)
    prod_digest = producer_identity_digest(producer)

    try:
        evidence = build_packet_from_git(
            audited_repo,
            tip,
            base,
            required_dependencies=list(spec.required_dependencies),
            spec_digest=spec_digest,
        )
    except FileNotFoundError as exc:
        print(json.dumps({"terminal": Terminal.INVALID_EXECUTION.value, "reason": str(exc)}))
        return 2

    evidence_digest = evidence_packet_sha256(evidence)
    nonce = make_boundary_nonce()
    system = compose_system_prompt_with_example(
        tip, base, evidence_digest, spec.criteria
    )
    sys_digest = system_prompt_sha256(system)
    user_msg = build_user_message(
        evidence_bytes=evidence, evidence_digest=evidence_digest, boundary_nonce=nonce
    )
    envelope = request_envelope_sha256(system_prompt=system, user_message=user_msg)
    run_key = audit_run_key(
        tip=tip,
        base=base,
        evidence_digest=evidence_digest,
        system_digest=sys_digest,
        spec_digest=spec_digest,
        producer_identity_digest_value=prod_digest,
    )

    outbound = canonical_request_body(system, user_msg.decode("utf-8", errors="replace"))
    hits = egress_scan_outbound_body(outbound)
    digests = {
        "audit_protocol_version": AUDIT_PROTOCOL_VERSION,
        "tip": tip,
        "base": base,
        "spec_digest": spec_digest,
        "producer_identity_digest": prod_digest,
        "producer_head_sha": producer.head_sha,
        "evidence_packet_sha256": evidence_digest,
        "system_prompt_sha256": sys_digest,
        "request_envelope_sha256": envelope,
        "AUDIT_RUN_KEY": run_key,
        "BOUNDARY_NONCE": nonce,
        "egress_hits": hits,
        "locked_request_config": LOCKED_REQUEST_CONFIG,
        "static_review_framing": STATIC_REVIEW_FRAMING,
        "marker": marker_html(run_key),
    }
    (out / "digests.json").write_text(json.dumps(digests, indent=2) + "\n")
    (out / "evidence_packet.bin").write_bytes(evidence)
    (out / "user_message.bin").write_bytes(user_msg)
    (out / "system_prompt.txt").write_text(system)

    if hits:
        print(json.dumps({"terminal": Terminal.INVALID_EXECUTION.value, "reason": "egress", "hits": hits}))
        return 3

    print(json.dumps({k: digests[k] for k in (
        "evidence_packet_sha256", "request_envelope_sha256", "AUDIT_RUN_KEY", "egress_hits"
    )}, indent=2))

    if not args.live:
        print("dry-run complete (no API call). Use --live --i-authorize-live to call DeepSeek.")
        return 0

    if not args.i_authorize_live:
        print("--live requires --i-authorize-live", file=sys.stderr)
        return 2

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("DEEPSEEK_API_KEY not set", file=sys.stderr)
        return 2

    try:
        import requests
    except ImportError:
        print("requests required for --live", file=sys.stderr)
        return 2

    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg.decode("utf-8")},
        ],
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
        "response_format": {"type": "json_object"},
        "max_tokens": 8192,
        "stream": False,
    }
    last_err = None
    response_obj: dict | None = None
    for _attempt in range(1, 3):
        assert request_envelope_sha256(system_prompt=system, user_message=user_msg) == envelope
        try:
            r = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=600,
            )
            r.raise_for_status()
            response_obj = r.json()
            content = (
                ((response_obj.get("choices") or [{}])[0].get("message") or {}).get("content")
            )
            if content and str(content).strip():
                break
            last_err = "empty_content"
            response_obj = None
        except Exception as exc:  # pylint: disable=broad-exception-caught
            last_err = f"transport:{exc}"
            response_obj = None
    if response_obj is None:
        print(json.dumps({"terminal": Terminal.INVALID_EXECUTION.value, "reason": last_err}))
        return 4

    if not isinstance(response_obj, dict):
        print(json.dumps({"terminal": Terminal.INVALID_EXECUTION.value, "reason": "response_type"}))
        return 4
    api_response: dict = response_obj
    safe = {k: v for k, v in api_response.items() if k != "reasoning_content"}
    choices = safe.get("choices")
    if isinstance(choices, list):
        safe_choices = []
        for ch in choices:
            if not isinstance(ch, dict):
                continue
            ch2 = dict(ch)
            msg = dict(ch2.get("message") or {})
            msg.pop("reasoning_content", None)
            ch2["message"] = msg
            safe_choices.append(ch2)
        safe["choices"] = safe_choices
    (out / "response_redacted.json").write_text(json.dumps(safe, indent=2) + "\n")

    result = validate_model_response(
        response=api_response,
        tip=tip,
        base=base,
        evidence_digest=evidence_digest,
        expected_ids=spec.checklist_ids,
    )
    print(json.dumps({"terminal": result.terminal.value, "reason": result.reason}))
    if result.terminal == Terminal.INVALID_EXECUTION:
        return 4
    if args.post_comment:
        if not args.pr:
            print("--post-comment requires --pr", file=sys.stderr)
            return 2
        body = render_comment(result, digests, tip, base)
        subprocess.check_call(
            ["gh", "pr", "comment", str(args.pr), "--body", body], cwd=audited_repo
        )
    return 0 if result.terminal == Terminal.VALID_PASS else 5


def canonical_request_body(system: str, user_text: str) -> bytes:
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
        "response_format": {"type": "json_object"},
        "max_tokens": 8192,
        "stream": False,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def render_comment(result, digests, tip, base) -> str:
    label = "PASS" if result.terminal == Terminal.VALID_PASS else "FAIL"
    summary = ""
    if result.parsed:
        summary = str(result.parsed.get("summary") or "")
    lines = [
        "## External evidence — DeepSeek V4-Pro substitute audit (not a ledger record)",
        "",
        digests["marker"],
        "",
        STATIC_REVIEW_FRAMING,
        "",
        "```text",
        f"Substitute audit-lane verdict (DeepSeek V4-Pro): {label} — {summary}",
        f"Terminal: {result.terminal.value}",
        f"Tip: {tip}",
        f"Base: {base}",
        f"Evidence-Packet-SHA256: {digests['evidence_packet_sha256']}",
        f"Request-Envelope-SHA256: {digests['request_envelope_sha256']}",
        f"AUDIT_RUN_KEY: {digests['AUDIT_RUN_KEY']}",
        "Model: deepseek-v4-pro (thinking=enabled, reasoning_effort=high, max_tokens=8192, stream=false)",
    ]
    if result.parsed:
        for item in result.parsed.get("checklist", []):
            lines.append(f"{item['id']}: {item['status']} — {item['evidence']}")
    lines.extend(["```", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
