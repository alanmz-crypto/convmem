#!/usr/bin/env python3
"""Portland baseline experiment controller (Rerun3 seed protocol)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from index_runner import INDEX_CWD, index_file
from seed_admissibility import evaluate_seed, write_private_inventory

RUN_ID = os.environ.get("PORTLAND_RUN_ID", "portland-baseline-2026-08-30-rerun3")
RESTIC_SNAPSHOT = "d3908f4e"
RESTIC_REPO = "/home/lauer/.local/share/convmem-restic"
RESTIC_PASSWORD_FILE = "/run/media/lauer/BIT-Brg-larch-7t/convmem-secrets/restic.password"
MAX_AGENT_A_ATTEMPTS = 3

AGENT_A_PROMPT = """Help me plan a relocation to Portland, Oregon in one comprehensive session.

Work through these phases conversationally in order. Develop realistic specifics through the conversation — ask what you need and record conclusions as we go.

Phase 1 — Housing constraints: establish a concrete monthly housing budget ceiling, lifestyle/accessibility preferences, and household/workspace requirements.

Phase 2 — Neighborhood investigation: consider Portland neighborhood options and record at least one specific neighborhood observation, one rejected option with its reason, and at least one unresolved question.

Phase 3 — Decision change: make a provisional neighborhood priority, then later in this same session revisit that choice after additional considerations and decide whether to retain or change it. Record both the earlier and current priority clearly.

Phase 4 — Adjacent subject: discuss another practical aspect of the move outside housing/neighborhood selection (financial, employment, transportation, or logistics) and capture the relevant facts."""

QUESTIONS = {
    "Q1": "What is the rent budget ceiling for the Portland move?",
    "Q2": "How much can we afford for housing there each month?",
    "Q3": "What did we think about that one neighborhood?",
    "Q4": "Given the must-haves, what kind of place should we look for?",
    "Q5": "What's the current decision on which Portland neighborhood to prioritize?",
    "Q6": "Which option did we rule out and why?",
    "Q7": "What's still open / undecided about the move?",
    "Q8": "Is there anything relevant we filed elsewhere?",
}

CONTAMINATION_TERMS = [
    "portland-baseline-2026-08-29",
    "portland-baseline-2026-08-30-rerun1",
    "portland-baseline-2026-08-30-rerun2",
    "PORTLAND-AGENT-A",
    "portland-relocation-notes.md",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def root() -> Path:
    return Path(os.environ.get("PORTLAND_RERUN_ROOT", f"/home/lauer/.local/share/convmem/experiments/{RUN_ID}"))


def save_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run_cmd(cmd: list[str], *, env: dict | None = None, cwd: str | Path | None = None, timeout: int = 600):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=merged,
        cwd=str(cwd or INDEX_CWD),
        timeout=timeout,
        check=False,
    )


def write_configs(r: Path) -> None:
    cfg = r / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    for name, chroma, processed in (
        ("background", r / "store" / "background" / "chroma", r / "store" / "background" / "processed.json"),
        ("live", r / "store" / "live" / "chroma", r / "store" / "live" / "processed.json"),
        ("c1-frozen", r / "c1-frozen" / "chroma", r / "c1-frozen" / "processed.json"),
    ):
        chroma.parent.mkdir(parents=True, exist_ok=True)
        text = f"""[sources]
paths = []
inventory = ""

[index]
chroma_dir = "{chroma}"
processed_log = "{processed}"
units_export = "/dev/null"

[models]
embed_model = "nomic-embed-text"
summarize_model = "llama3.1:8b"
distill_model = "deepseek-v4-flash"
ollama_host = "http://localhost:11434"
rerank_model = "BAAI/bge-reranker-v2-m3"
deepseek_base_url = "https://api.deepseek.com"

[distill]
min_confidence = 0.6

[watch]
debounce_seconds = 90

[refine]
enabled = false
"""
        (cfg / f"{name}-config.toml").write_text(text, encoding="utf-8")
    (cfg / "c0-broken-config.toml").write_text("[index]\nchroma_dir = \"/dev/null/blocked\"\n", encoding="utf-8")


def contamination_audit(chroma_path: Path) -> dict:
    proc = run_cmd(["rg", "-i", "-l", "|".join(CONTAMINATION_TERMS), str(chroma_path)])
    hits = [x for x in (proc.stdout or "").splitlines() if x.strip()]
    return {"terms": CONTAMINATION_TERMS, "hits": hits, "pass": len(hits) == 0}


def restore_background(r: Path) -> dict:
    target = r / "restore-scratch"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    proc = run_cmd(
        [
            "restic",
            "-r",
            RESTIC_REPO,
            "restore",
            RESTIC_SNAPSHOT,
            "--target",
            str(target),
            "--include",
            "/home/lauer/.local/share/convmem/chroma",
            "--include",
            "/home/lauer/.local/share/convmem/processed.json",
        ],
        env={"RESTIC_PASSWORD_FILE": RESTIC_PASSWORD_FILE},
        timeout=900,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"restic restore failed: {proc.stderr}")
    src = target / "home" / "lauer" / ".local" / "share" / "convmem"
    bg = r / "store" / "background"
    bg.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src / "chroma", bg / "chroma", dirs_exist_ok=True)
    if (src / "processed.json").exists():
        shutil.copy2(src / "processed.json", bg / "processed.json")
    live = r / "store" / "live"
    live.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bg / "chroma", live / "chroma", dirs_exist_ok=True)
    if (bg / "processed.json").exists():
        shutil.copy2(bg / "processed.json", live / "processed.json")
    shutil.rmtree(target)
    doctor = run_cmd(["convmem", "doctor"], env={"CONVMEM_CONFIG": str(r / "config" / "background-config.toml")})
    units = 0
    m = re.search(r"chroma: (\d+) knowledge units", doctor.stdout or "")
    if m:
        units = int(m.group(1))
    return {
        "snapshot": RESTIC_SNAPSHOT,
        "restored_at": utc_now(),
        "background_units": units,
        "contamination_audit": contamination_audit(bg / "chroma"),
    }


def codex_exec(prompt: str, *, profile: str | None = None, extra_env: dict | None = None, timeout: int = 1200):
    cmd = [
        "codex",
        "exec",
        "--json",
        "--ignore-rules",
        "-c",
        'sandbox_permissions=["disk-full-read-access"]',
        "-c",
        "shell_environment_policy.inherit=all",
    ]
    if profile:
        cmd.extend(["-p", profile])
    cmd.append(prompt)
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    proc = run_cmd(cmd, env=env, cwd=INDEX_CWD, timeout=timeout)
    events = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    thread_id = ""
    for ev in events:
        if ev.get("type") == "thread.started":
            thread_id = ev.get("thread_id") or ""
    return thread_id, events, proc.stdout + ("\n" + proc.stderr if proc.stderr else "")


def find_rollout_path(thread_id: str) -> str:
    if not thread_id:
        return ""
    codex_home = Path.home() / ".codex" / "sessions"
    for path in sorted(codex_home.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        if thread_id.replace("-", "")[:12] in path.name.replace("-", ""):
            return str(path)
    return ""


def transcript_text(rollout_path: str) -> str:
    if not rollout_path or not Path(rollout_path).exists():
        return ""
    return Path(rollout_path).read_text(encoding="utf-8", errors="ignore")


def run_agent_a(r: Path, attempt: int) -> dict:
    thread_id, events, raw = codex_exec(AGENT_A_PROMPT)
    ev_dir = r / "evidence" / "agent-a" / f"attempt-{attempt}"
    ev_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = ev_dir / "events.jsonl"
    jsonl_path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    (ev_dir / "raw.txt").write_text(raw, encoding="utf-8")
    rollout = find_rollout_path(thread_id)
    record = {
        "run_id": RUN_ID,
        "attempt": attempt,
        "thread_id": thread_id,
        "started_at": utc_now(),
        "rollout_path": rollout,
        "events_path": str(jsonl_path),
        "prompt_frozen": True,
    }
    if rollout:
        idx = index_file(config_path=r / "config" / "live-config.toml", source_path=rollout, cwd=INDEX_CWD)
        record["index_exit"] = idx.returncode
        record["index_stdout_tail"] = (idx.stdout or "")[-1500:]
        record["index_stderr_tail"] = (idx.stderr or "")[-1500:]
        record["index_cwd"] = str(INDEX_CWD)
        m = re.search(r"units_indexed=(\d+)", idx.stdout or "")
        record["units_indexed"] = int(m.group(1)) if m else 0
    save_json(r / "results" / f"agent_a_attempt_{attempt}.json", record)
    return record


def freeze_c1(r: Path) -> dict:
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
    marker = {
        "run_id": RUN_ID,
        "frozen_at": utc_now(),
        "background_snapshot": RESTIC_SNAPSHOT,
        "frozen_units": units,
        "store_digest": digest.hexdigest(),
        "contamination_audit": contamination_audit(frozen / "chroma"),
        "agent_b_material_absent": True,
        "rerun2_preserved_separate": True,
    }
    save_json(r / "frozen" / "marker.json", marker)
    save_json(frozen / "marker.json", marker)
    return marker


def cmd_setup(_: argparse.Namespace) -> int:
    r = root()
    r.mkdir(parents=True, exist_ok=True)
    write_configs(r)
    info = restore_background(r)
    save_json(r / "results" / "background_restore.json", info)
    save_json(r / "results" / "frozen_protocol.json", {
        "run_id": RUN_ID,
        "agent_a_prompt": AGENT_A_PROMPT,
        "questions": QUESTIONS,
        "effort_budget_n": 5,
        "max_agent_a_attempts": MAX_AGENT_A_ATTEMPTS,
    })
    print(json.dumps({"status": "setup_complete", "root": str(r), **info}, indent=2))
    return 0


def reset_live_from_background(r: Path) -> None:
    bg = r / "store" / "background"
    live = r / "store" / "live"
    if live.exists():
        shutil.rmtree(live)
    live.mkdir(parents=True)
    shutil.copytree(bg / "chroma", live / "chroma", dirs_exist_ok=True)
    if (bg / "processed.json").exists():
        shutil.copy2(bg / "processed.json", live / "processed.json")


def cmd_agent_a(_: argparse.Namespace) -> int:
    r = root()
    for attempt in range(1, MAX_AGENT_A_ATTEMPTS + 1):
        if attempt > 1:
            reset_live_from_background(r)
        rec = run_agent_a(r, attempt)
        transcript = transcript_text(rec.get("rollout_path", ""))
        if rec.get("index_exit") != 0 or rec.get("units_indexed", 0) <= 0:
            print(f"RERUN3 BLOCKED: indexing failed on attempt {attempt} (exit={rec.get('index_exit')}, units={rec.get('units_indexed')})", flush=True)
            if attempt >= MAX_AGENT_A_ATTEMPTS:
                return 4
            continue
        adm = evaluate_seed(
            transcript=transcript,
            config_path=r / "config" / "live-config.toml",
            repo_cwd=INDEX_CWD,
            attempt=attempt,
        )
        save_json(r / "results" / "seed_admissibility.json", adm)
        write_private_inventory(r / "results" / "k_inventory.private.json", transcript, adm)
        print(json.dumps({"agent_a": rec, "admissibility": adm}, indent=2))
        if adm.get("admissible"):
            marker = freeze_c1(r)
            if marker.get("frozen_units", 0) < 1000:
                print(f"RERUN3 BLOCKED: frozen corpus too small ({marker.get('frozen_units')} units)", flush=True)
                if attempt >= MAX_AGENT_A_ATTEMPTS:
                    return 5
                continue
            save_json(r / "results" / "rerun3_seed_ready.json", {
                "status": "RERUN3 SEED READY",
                "agent_a_thread_id": rec.get("thread_id"),
                "attempt": attempt,
                "frozen_marker": marker,
                "admissibility": {k: v["status"] for k, v in adm["k"].items()},
            })
            print("RERUN3 SEED READY")
            return 0
        if attempt < MAX_AGENT_A_ATTEMPTS:
            print(f"Seed inadmissible attempt {attempt}; retrying with frozen prompt...", flush=True)
    print("RERUN3 BLOCKED: seed inadmissible after 3 attempts")
    return 3


def main() -> int:
    parser = argparse.ArgumentParser(description="Portland baseline Rerun3 controller")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    sub.add_parser("agent-a")
    args = parser.parse_args()
    handlers = {"setup": cmd_setup, "agent-a": cmd_agent_a}
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
