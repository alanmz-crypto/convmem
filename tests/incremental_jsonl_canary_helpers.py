"""Shared helpers for hermetic JSONL production-canary tests."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from incremental_jsonl_canary import (
    Gate0ProbeHooks,
    P2_CAPABILITY_MODE,
    CALL_CEILINGS_APPEND,
    CALL_CEILINGS_INITIAL,
    CALL_CEILINGS_WHOLE,
    CANARY_SCHEMA_VERSION,
    CanaryGrant,
    decode_grant,
    ProductionCanaryBoundary,
    ProviderGrant,
    ResourceRole,
    RollbackGrant,
    SourceGrant,
    AppendEnvelope,
)
from incremental_jsonl_isolation import create_fresh_root
from tests.incremental_jsonl_helpers import kiro_record

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).with_name("incremental_jsonl_canary_worker.py")


def write_kiro_source(root: Path, count: int, *, name: str = "sess_canary") -> tuple[Path, Path]:
    source = root / "sources" / "hash" / name / "messages.jsonl"
    source.parent.mkdir(parents=True, exist_ok=True)
    data = b"".join(kiro_record(i) for i in range(count))
    source.write_bytes(data)
    meta = source.parent / "session.json"
    meta.write_text(
        json.dumps({"id": name, "workspacePaths": [str(root / "workspace")], "title": "canary"}),
        encoding="utf-8",
    )
    stat_result = source.stat()
    complete_boundary = data.rfind(b"\n") + 1
    prefix_sha = hashlib.sha256(data[:complete_boundary]).hexdigest()
    meta_sha = hashlib.sha256(meta.read_bytes()).hexdigest()
    return source, SourceGrant(
        path=str(source.resolve()),
        metadata_path=str(meta.resolve()),
        device=stat_result.st_dev,
        inode=stat_result.st_ino,
        size=stat_result.st_size,
        complete_boundary=complete_boundary,
        prefix_sha256=prefix_sha,
        metadata_sha256=meta_sha,
    )


def build_resource_layout(root: Path, source_path: str) -> dict[str, Path]:
    home = root / "home"
    share = home / ".local/share/convmem"
    processed = share / "processed.json"
    export = share / "knowledge_units.jsonl"
    source_digest = hashlib.sha256(source_path.encode()).hexdigest()
    for path in (share, share / "locks", share / "writer_attestations", share / "writer_census"):
        path.mkdir(parents=True, exist_ok=True)
        os.chmod(path, 0o700)
    return {
        "chroma": share / "chroma",
        "incremental_state": share / "incremental-jsonl",
        "export": export,
        "dedupe": share,
        "processed": processed,
        "writer_lock": share / "locks/chroma_writer_gate.lock",
        "source_lock": share / f"locks/source/{source_digest}.lock",
        "export_lock": export.with_suffix(export.suffix + ".lock"),
        "processed_lock": processed.with_name(processed.name + ".lock"),
        "attestations": share / "writer_attestations",
        "census": share / "writer_census",
    }


def build_grant(
    root: Path,
    source_grant: SourceGrant,
    *,
    nonce: str | None = None,
    code_revision: str = "test-revision",
    expires_at: str = "2099-12-31T23:59:59Z",
) -> tuple[CanaryGrant, str]:
    layout = build_resource_layout(root, source_grant.path)
    for path in layout.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    overlay = root / "overlay.toml"
    layout = build_resource_layout(root, source_grant.path)
    overlay.parent.mkdir(parents=True, exist_ok=True)
    for key in ("chroma", "incremental_state", "export", "dedupe", "processed"):
        layout[key].parent.mkdir(parents=True, exist_ok=True)
    overlay.write_text(
        "[index]\n"
        f'chroma_dir = {json.dumps(str(layout["chroma"]))}\n'
        f'processed_log = {json.dumps(str(layout["processed"]))}\n'
        f'units_export = {json.dumps(str(layout["export"]))}\n'
        "chunk_size = 60\n"
        "chunk_overlap = 10\n"
        "\n"
        "[index.incremental_jsonl]\n"
        "enabled = true\n"
        f'state_dir = {json.dumps(str(layout["incremental_state"]))}\n'
        "allow_full_rebuild = false\n"
        "\n"
        "[models]\n"
        'embed_model = "nomic-embed-text"\n'
        'summarize_model = "llama3.1:8b"\n'
        'distill_model = "llama3.1:8b"\n'
        'ollama_host = "127.0.0.1:11434"\n'
        "\n"
        "[distill]\n"
        "min_confidence = 0.6\n",
        encoding="utf-8",
    )
    os.chmod(overlay, 0o600)
    overlay_digest = hashlib.sha256(overlay.read_bytes()).hexdigest()
    resources = tuple(
        ResourceRole(path=str(layout[key].resolve()), role=key)
        for key in (
            "chroma",
            "incremental_state",
            "export",
            "dedupe",
            "processed",
            "writer_lock",
            "source_lock",
            "export_lock",
            "processed_lock",
            "attestations",
            "census",
        )
    )
    grant = CanaryGrant(
        schema_version=CANARY_SCHEMA_VERSION,
        code_revision=code_revision,
        expires_at=expires_at,
        nonce=nonce or os.urandom(16).hex(),
        run_once=True,
        source=source_grant,
        append_envelope=AppendEnvelope(
            max_byte_boundary=source_grant.size + 4096,
            max_accepted_records=110,
            max_append_epochs=6,
            immutable_prefix=True,
        ),
        resources=resources,
        config_overlay=str(overlay.resolve()),
        config_overlay_digest=overlay_digest,
        provider=ProviderGrant(
            loopback_host="127.0.0.1:11434",
            summarize_model="llama3.1:8b",
            summarize_digest="46e0c10c039e",
            embed_model="nomic-embed-text",
            embed_canonical_tag="nomic-embed-text:latest",
            embed_digest="0a109f422b47",
            distill_model="llama3.1:8b",
            distill_digest="46e0c10c039e",
        ),
        call_ceilings={
            "initial": CALL_CEILINGS_INITIAL,
            "append": CALL_CEILINGS_APPEND,
            "whole_run": CALL_CEILINGS_WHOLE,
        },
        faults=tuple(
            (
                "summary_upsert",
                "unit_upsert",
                "units_prune",
                "checkpoint_publish",
                "dedupe_reconcile",
            )
        ),
        rollback=RollbackGrant(
            capsule_path=str((root / "capsule.json").resolve()),
            expected_digest="0" * 64,
        ),
        evidence_dir=str((root / "evidence").resolve()),
        expected_pre_state={"checkpoint": None, "generation": None},
    )
    digest = hashlib.sha256(grant.digest_payload()).hexdigest()
    return grant, digest


def write_grant_file(root: Path, grant: CanaryGrant) -> Path:
    path = root / "grant.json"
    path.write_text(json.dumps(grant.to_payload(), indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def hermetic_root(tmp_path: Path) -> Path:
    root, _token = create_fresh_root(tmp_path)
    return root


def worker_run(
    env: dict[str, str],
    *,
    command: str,
    args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    import site

    full_env = dict(env)
    full_env["CONVMEM_INCREMENTAL_SITE"] = site.getusersitepackages()
    cmd = [sys.executable, "-I", str(WORKER), command, *(args or [])]
    return subprocess.run(
        cmd,
        env=full_env,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture()
def canary_fixture(tmp_path: Path):
    root = hermetic_root(tmp_path)
    source, source_grant = write_kiro_source(root, 61)
    grant, digest = build_grant(root, source_grant)
    grant_path = write_grant_file(root, grant)
    boundary = ProductionCanaryBoundary.from_grant(grant, root=root)
    return {
        "root": root,
        "source": source,
        "grant": grant,
        "digest": digest,
        "grant_path": grant_path,
        "boundary": boundary,
    }


def build_p2_grant(
    root: Path,
    source_grant: SourceGrant,
    *,
    nonce: str | None = None,
    code_revision: str = "8741774273e968824e4c09f1a7d6bb57729c0d43",
    expires_at: str = "2099-12-31T23:59:59Z",
) -> tuple[CanaryGrant, str]:
    grant, digest = build_grant(
        root,
        source_grant,
        nonce=nonce,
        code_revision=code_revision,
        expires_at=expires_at,
    )
    payload = grant.to_payload()
    payload["capability_mode"] = "p2-exact-resource-v1"
    path = root / "p2-grant.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    loaded = decode_grant(path)
    digest = hashlib.sha256(loaded.digest_payload()).hexdigest()
    return loaded, digest


def append_kiro_source(source: Path, start_index: int, count: int) -> SourceGrant:
    data = source.read_bytes()
    appended = b"".join(kiro_record(i) for i in range(start_index, start_index + count))
    source.write_bytes(data + appended)
    meta = source.parent / "session.json"
    stat_result = source.stat()
    complete_boundary = (data + appended).rfind(b"\n") + 1
    prefix_sha = hashlib.sha256((data + appended)[:complete_boundary]).hexdigest()
    meta_sha = hashlib.sha256(meta.read_bytes()).hexdigest()
    return SourceGrant(
        path=str(source.resolve()),
        metadata_path=str(meta.resolve()),
        device=stat_result.st_dev,
        inode=stat_result.st_ino,
        size=stat_result.st_size,
        complete_boundary=complete_boundary,
        prefix_sha256=prefix_sha,
        metadata_sha256=meta_sha,
    )


def p2_gate0_hooks_pass() -> "Gate0ProbeHooks":
    from incremental_jsonl_canary import Gate0ProbeHooks

    return Gate0ProbeHooks(
        watcher_probe=lambda: {"pass": "true", "method": "stub"},
        process_census=lambda: {"pass": "true", "matches": "0"},
        service_launcher_denied=lambda: {"pass": "true", "detail": "denied"},
        writer_census=lambda _boundary: {"pass": "true"},
        model_manifest=lambda _grant: {"pass": "true"},
        network_self_test=lambda: {"pass": "true", "detail": "blocked"},
        restic_identifier=lambda: {"pass": "true", "backup_id": "hermetic-stub"},
        zero_adoption=lambda _boundary, _grant: {"pass": "true"},
    )
