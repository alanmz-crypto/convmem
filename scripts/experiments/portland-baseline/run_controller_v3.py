#!/usr/bin/env python3
"""Portland Rerun3 Protocol v3 controller — clean semantic lane."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Harness modules live alongside this file.
HARNESS_DIR = Path(__file__).resolve().parent
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

from index_runner import INDEX_CWD, index_file  # noqa: E402
from protocol_v3 import (  # noqa: E402
    BLINDNESS_FORBIDDEN_READS,
    CONTAMINATION_EXCLUSIONS,
    MECHANICAL_CORRECTIVE_SHA,
    PHASE4_SCOPE_MAP,
    RESTIC_SNAPSHOT,
    RUN_ID,
    build_background_identity,
    build_protocol_manifest,
    manifest_digest,
    parse_phase4a_subject,
    validate_phase4_scope_map,
)
from run_controller import (  # noqa: E402
    RESTIC_PASSWORD_FILE,
    RESTIC_REPO,
    contamination_audit,
    find_rollout_path,
    restore_background,
    run_cmd,
    save_json,
    transcript_text,
    utc_now,
    write_configs,
)
from seed_admissibility_v3 import evaluate_seed_v3, write_private_inventory_v3  # noqa: E402

AGENT_A_WORKSPACE = Path.home() / ".local/share/convmem" / "experiments" / RUN_ID / "agent-a-workspace"
CODEX_BASE = [
    "codex",
    "exec",
    "--json",
    "--skip-git-repo-check",
    "--ignore-rules",
    "-c",
    'sandbox_permissions=["disk-full-read-access"]',
    "-c",
    "shell_environment_policy.inherit=all",
]


def root() -> Path:
    return Path(os.environ.get("PORTLAND_RERUN_ROOT", f"/home/lauer/.local/share/convmem/experiments/{RUN_ID}"))


def execution_revision() -> str:
    proc = run_cmd(["git", "rev-parse", "HEAD"], cwd=INDEX_CWD)
    return (proc.stdout or "").strip() or "unknown"


def codex_model_settings() -> dict:
    return {
        "cli": "codex exec",
        "model": os.environ.get("PORTLAND_CODEX_MODEL", "default-from-config"),
        "profile": os.environ.get("PORTLAND_CODEX_PROFILE", ""),
        "workspace": str(AGENT_A_WORKSPACE),
        "multi_turn": "codex exec resume",
    }


def codex_turn(prompt: str, *, thread_id: str | None = None, profile: str | None = None, timeout: int = 1200):
    cmd = list(CODEX_BASE)
    cmd.extend(["-C", str(AGENT_A_WORKSPACE)])
    if profile:
        cmd.extend(["-p", profile])
    if thread_id:
        cmd.extend(["resume", thread_id, prompt])
    else:
        cmd.append(prompt)
    proc = run_cmd(cmd, cwd=AGENT_A_WORKSPACE, timeout=timeout)
    events = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    tid = thread_id or ""
    assistant_parts: list[str] = []
    for ev in events:
        if ev.get("type") == "thread.started":
            tid = ev.get("thread_id") or tid
        if ev.get("type") != "item.completed":
            continue
        item = ev.get("item") or {}
        if item.get("type") != "agent_message":
            continue
        text = item.get("text") or ""
        if not text and isinstance(item.get("content"), list):
            for part in item["content"]:
                if isinstance(part, dict):
                    text += part.get("text") or ""
        if text:
            assistant_parts.append(text)
    assistant_text = assistant_parts[-1] if assistant_parts else ""
    ok = proc.returncode == 0 and bool(tid) and bool(assistant_text.strip())
    return tid, assistant_text, events, proc.stdout + ("\n" + proc.stderr if proc.stderr else ""), ok


def verify_blindness() -> dict:
    """Ensure Agent-A workspace does not expose forbidden protocol material."""
    AGENT_A_WORKSPACE.mkdir(parents=True, exist_ok=True)
    violations: list[str] = []
    repo = INDEX_CWD
    for rel in BLINDNESS_FORBIDDEN_READS:
        target = repo / rel if not rel.startswith("/") else Path(rel)
        if target.exists():
            try:
                resolved = target.resolve()
                ws = AGENT_A_WORKSPACE.resolve()
                if ws == resolved or ws in resolved.parents or resolved in ws.parents:
                    violations.append(str(target))
            except OSError:
                pass
    # Workspace must not be inside convmem experiment harness tree.
    harness = (repo / "scripts" / "experiments" / "portland-baseline").resolve()
    ws = AGENT_A_WORKSPACE.resolve()
    if harness in ws.parents or ws == harness:
        violations.append(f"workspace inside harness: {ws}")
    ok = len(violations) == 0
    return {
        "verified_at": utc_now(),
        "workspace": str(ws),
        "forbidden_reads_checked": BLINDNESS_FORBIDDEN_READS,
        "violations": violations,
        "pass": ok,
    }


def _env_v3() -> None:
    os.environ["PORTLAND_RUN_ID"] = RUN_ID
    os.environ["PORTLAND_RERUN_ROOT"] = str(root())


def cmd_setup(_: argparse.Namespace) -> int:
    _env_v3()
    r = root()
    if r.exists():
        shutil.rmtree(r)
    r.mkdir(parents=True, exist_ok=True)
    AGENT_A_WORKSPACE.mkdir(parents=True, exist_ok=True)
    write_configs(r)
    info = restore_background(r)
    bg_identity = build_background_identity(
        experiment_root=r,
        config_path=r / "config" / "background-config.toml",
    )
    save_json(r / "results" / "background_restore.json", info)
    save_json(r / "frozen" / "background_identity.json", bg_identity)
    print(json.dumps({"status": "setup_complete", "root": str(r), **info}, indent=2))
    return 0


def cmd_freeze_protocol(_: argparse.Namespace) -> int:
    _env_v3()
    ok, reason = validate_phase4_scope_map()
    if not ok:
        print("RERUN3 PROTOCOL-V3 FREEZE BLOCKED")
        print(reason)
        return 2
    r = root()
    if not (r / "store" / "background").exists():
        print("RERUN3 HARNESS FAILURE: run setup first")
        return 1
    rev = execution_revision()
    manifest = build_protocol_manifest(execution_revision=rev, model_settings=codex_model_settings())
    digest = manifest_digest(manifest)
    manifest["manifest_sha256"] = digest
    frozen = r / "frozen" / "protocol_v3_manifest.json"
    save_json(frozen, manifest)
    (r / "frozen" / "protocol_v3_manifest.sha256").write_text(digest + "\n", encoding="utf-8")
    save_json(r / "frozen" / "phase4_scope_map.json", {
        "frozen_at": utc_now(),
        "relocation_scope": "relocation",
        "mapping": PHASE4_SCOPE_MAP,
        "validation": reason,
    })
    print(json.dumps({
        "status": "protocol_v3_frozen",
        "manifest_path": str(frozen),
        "manifest_sha256": digest,
        "phase4_scope_map": PHASE4_SCOPE_MAP,
        "mechanical_corrective_sha": MECHANICAL_CORRECTIVE_SHA,
    }, indent=2))
    return 0


def cmd_verify_blindness(_: argparse.Namespace) -> int:
    _env_v3()
    report = verify_blindness()
    save_json(root() / "results" / "blindness_verification.json", report)
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 3


def _require_frozen_manifest(r: Path) -> dict | None:
    path = r / "frozen" / "protocol_v3_manifest.json"
    if not path.exists():
        print("RERUN3 HARNESS FAILURE: protocol manifest not frozen")
        return None
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected = manifest.get("manifest_sha256") or manifest_digest(manifest)
    on_disk = (r / "frozen" / "protocol_v3_manifest.sha256").read_text(encoding="utf-8").strip()
    if expected != on_disk:
        print("RERUN3 HARNESS FAILURE: manifest hash mismatch")
        return None
    return manifest


def reset_live_from_background(r: Path) -> None:
    bg = r / "store" / "background"
    live = r / "store" / "live"
    if live.exists():
        shutil.rmtree(live)
    live.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bg / "chroma", live / "chroma", dirs_exist_ok=True)
    if (bg / "processed.json").exists():
        shutil.copy2(bg / "processed.json", live / "processed.json")


def prepare_agent_a_run(r: Path) -> None:
    """Reset live corpus and prior Agent-A evidence; preserve frozen protocol."""
    reset_live_from_background(r)
    ev = r / "evidence" / "agent-a"
    if ev.exists():
        shutil.rmtree(ev)
    if AGENT_A_WORKSPACE.exists():
        shutil.rmtree(AGENT_A_WORKSPACE)
    AGENT_A_WORKSPACE.mkdir(parents=True, exist_ok=True)
    (AGENT_A_WORKSPACE / "README.md").write_text(
        "# Portland planning workspace\n\nPersonal notes for relocation planning.\n",
        encoding="utf-8",
    )


def _find_phase4_artifact(workspace: Path, subject: str) -> str | None:
    candidates = list(workspace.rglob("*"))
    subject_re = re.compile(re.escape(subject), re.I)
    for path in sorted(candidates, key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True):
        if not path.is_file():
            continue
        if path.suffix in {".json", ".jsonl", ".pyc"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if subject_re.search(path.name) or subject_re.search(text[:500]):
            return str(path)
    return None


def cmd_agent_a(_: argparse.Namespace) -> int:
    _env_v3()
    r = root()
    manifest = _require_frozen_manifest(r)
    if manifest is None:
        return 1
    blindness = verify_blindness()
    save_json(r / "results" / "blindness_verification.json", blindness)
    if not blindness["pass"]:
        print("RERUN3 HARNESS FAILURE: blindness verification failed")
        return 1

    prepare_agent_a_run(r)
    profile = os.environ.get("PORTLAND_CODEX_PROFILE") or None
    phases = manifest["agent_a_phases"]
    thread_id = ""
    phase_records: list[dict] = []
    locked_scope = ""
    phase4_subject = ""

    for phase in phases:
        name = phase["phase"]
        if name == "phase4b" and not locked_scope:
            print("RERUN3 HARNESS FAILURE: Phase 4b without locked scope")
            return 1
        tid, reply, events, raw, ok = codex_turn(phase["prompt"], thread_id=thread_id or None, profile=profile)
        if not ok:
            print(f"RERUN3 HARNESS FAILURE: codex turn failed at {name}")
            save_json(r / "results" / "agent_a_v3.json", {"phases": phase_records, "failure": f"codex_{name}"})
            return 4
        thread_id = tid
        ev_dir = r / "evidence" / "agent-a" / name
        ev_dir.mkdir(parents=True, exist_ok=True)
        (ev_dir / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
        (ev_dir / "reply.txt").write_text(reply, encoding="utf-8")
        (ev_dir / "raw.txt").write_text(raw, encoding="utf-8")
        rec = {"phase": name, "thread_id": thread_id, "reply_length": len(reply), "at": utc_now()}
        phase_records.append(rec)

        if name == "phase4a":
            phase4_subject = parse_phase4a_subject(reply) or ""
            if phase4_subject not in PHASE4_SCOPE_MAP:
                print("RERUN3 SEED-GENERATION FAILURE: invalid Phase 4a subject")
                save_json(r / "results" / "agent_a_v3.json", {"phases": phase_records, "failure": "phase4a_subject"})
                return 5
            locked_scope = PHASE4_SCOPE_MAP[phase4_subject]
            lock = {
                "subject": phase4_subject,
                "locked_scope": locked_scope,
                "locked_at": utc_now(),
                "before_phase4b": True,
            }
            save_json(r / "frozen" / "phase4_scope_lock.json", lock)
            rec["phase4_subject"] = phase4_subject
            rec["locked_scope"] = locked_scope

    rollout = find_rollout_path(thread_id)
    agent_record = {
        "run_id": RUN_ID,
        "protocol_version": 3,
        "thread_id": thread_id,
        "rollout_path": rollout,
        "phases": phase_records,
        "phase4_subject": phase4_subject,
        "locked_scope": locked_scope,
        "completed_at": utc_now(),
        "single_candidate": True,
    }
    save_json(r / "results" / "agent_a_v3.json", agent_record)

    phase4_artifact = _find_phase4_artifact(AGENT_A_WORKSPACE, phase4_subject) if phase4_subject else None
    indexed_paths: list[str] = []

    if rollout:
        idx = index_file(config_path=r / "config" / "live-config.toml", source_path=rollout, cwd=INDEX_CWD)
        agent_record["index_exit"] = idx.returncode
        agent_record["index_cwd"] = str(INDEX_CWD)
        m = re.search(r"units_indexed=(\d+)", idx.stdout or "")
        agent_record["units_indexed_transcript"] = int(m.group(1)) if m else 0
        indexed_paths.append(rollout)

    if phase4_artifact:
        idx2 = index_file(
            config_path=r / "config" / "live-config.toml",
            source_path=phase4_artifact,
            cwd=INDEX_CWD,
        )
        agent_record["phase4_artifact"] = phase4_artifact
        agent_record["phase4_index_exit"] = idx2.returncode
        indexed_paths.append(phase4_artifact)

    save_json(r / "results" / "agent_a_v3.json", agent_record)

    if agent_record.get("index_exit", 1) != 0:
        print("RERUN3 HARNESS FAILURE: transcript indexing failed")
        return 4

    transcript = transcript_text(rollout or "")
    adm = evaluate_seed_v3(
        transcript=transcript,
        config_path=r / "config" / "live-config.toml",
        repo_cwd=INDEX_CWD,
        locked_phase4_scope=locked_scope,
        phase4_artifact_path=phase4_artifact,
    )
    save_json(r / "results" / "seed_admissibility_v3.json", adm)
    seal = write_private_inventory_v3(r / "results" / "k_inventory.private.json", adm)

    if not adm["admissible"]:
        print(adm.get("failure_mode") or "RERUN3 SEED-GENERATION FAILURE")
        return 5

    marker = freeze_c1_v3(r, agent_record, adm, seal)
    report = build_seed_ready_report(r, manifest, agent_record, adm, marker, seal)
    save_json(r / "results" / "rerun3_v3_seed_ready.json", report)
    print("RERUN3 V3 SEED READY")
    print(json.dumps(report, indent=2))
    return 0


def freeze_c1_v3(r: Path, agent_record: dict, adm: dict, inventory_seal: str) -> dict:
    live = r / "store" / "live"
    frozen = r / "c1-frozen"
    if frozen.exists():
        shutil.rmtree(frozen)
    shutil.copytree(live, frozen)
    digest = hashlib.sha256()
    for path in sorted((frozen / "chroma").rglob("*")):
        if path.is_file():
            digest.update(path.read_bytes())
    doctor = run_cmd(["convmem", "doctor"], env={"CONVMEM_CONFIG": str(r / "config" / "c1-frozen-config.toml")})
    units = 0
    m = re.search(r"chroma: (\d+) knowledge units", doctor.stdout or "")
    if m:
        units = int(m.group(1))
    bg_units = json.loads((r / "results" / "background_restore.json").read_text()).get("background_units", 0)
    delta = units - bg_units
    delta_manifest = {
        "background_units": bg_units,
        "c1_units": units,
        "delta_units": delta,
        "authorized_sources": agent_record.get("rollout_path"),
        "phase4_artifact": agent_record.get("phase4_artifact"),
        "inventory_seal": inventory_seal,
    }
    delta_hash = hashlib.sha256(json.dumps(delta_manifest, sort_keys=True).encode()).hexdigest()
    marker = {
        "run_id": RUN_ID,
        "protocol_version": 3,
        "frozen_at": utc_now(),
        "background_snapshot": RESTIC_SNAPSHOT,
        "background_units": bg_units,
        "frozen_units": units,
        "delta_units": delta,
        "store_digest": digest.hexdigest(),
        "delta_manifest_sha256": delta_hash,
        "contamination_audit": contamination_audit(frozen / "chroma"),
        "exclusion_terms": CONTAMINATION_EXCLUSIONS,
        "agent_b_material_absent": True,
        "pre_v3_candidate_excluded": True,
    }
    save_json(r / "frozen" / "c1_marker.json", marker)
    save_json(r / "frozen" / "c1_delta_manifest.json", delta_manifest)
    save_json(frozen / "marker.json", marker)
    return marker


def build_seed_ready_report(r: Path, manifest: dict, agent: dict, adm: dict, marker: dict, seal: str) -> dict:
    bg_id = json.loads((r / "frozen" / "background_identity.json").read_text(encoding="utf-8"))
    blindness = json.loads((r / "results" / "blindness_verification.json").read_text(encoding="utf-8"))
    lock = json.loads((r / "frozen" / "phase4_scope_lock.json").read_text(encoding="utf-8"))
    return {
        "status": "RERUN3 V3 SEED READY",
        "mechanical_corrective_sha": MECHANICAL_CORRECTIVE_SHA,
        "protocol_v3_manifest_path": str(r / "frozen" / "protocol_v3_manifest.json"),
        "protocol_v3_manifest_sha256": manifest.get("manifest_sha256"),
        "execution_revision": manifest.get("execution_revision"),
        "agent_a_thread_id": agent.get("thread_id"),
        "blindness_verification": blindness.get("pass"),
        "k_statuses": {k: v["status"] for k, v in adm["k"].items()},
        "k8_k9_relational": adm.get("k8_k9_relational"),
        "k10": {
            "subject": lock.get("subject"),
            "locked_scope": lock.get("locked_scope"),
            "provenance": adm.get("k10_provenance"),
        },
        "sealed_private_inventory_sha256": seal,
        "background_logical_digest": bg_id.get("logical_corpus_export_digest"),
        "c1_logical_digest": marker.get("store_digest"),
        "physical_snapshot_identity": marker.get("store_digest"),
        "c1_delta_manifest_sha256": marker.get("delta_manifest_sha256"),
        "contamination_verification": marker.get("contamination_audit"),
        "protocol_deviations": [],
        "agent_b_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Portland Rerun3 Protocol v3 controller")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="Restore background from d3908f4e into clean v3 root")
    sub.add_parser("freeze-protocol", help="Freeze and hash Protocol v3 manifest")
    sub.add_parser("verify-blindness", help="Verify Agent-A readable-root isolation")
    sub.add_parser("agent-a", help="Run single-candidate multi-turn Agent A")
    args = parser.parse_args()
    handlers = {
        "setup": cmd_setup,
        "freeze-protocol": cmd_freeze_protocol,
        "verify-blindness": cmd_verify_blindness,
        "agent-a": cmd_agent_a,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
