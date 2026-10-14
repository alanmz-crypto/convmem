"""Claude verify probes, round 9 (905e602): writers that take C1 inside an open store session.

Each probe opens the real production store session (no fake session), against a scratch
config. Scratch only.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json
import traceback

from tests.test_zz_codex_audit import _route_fixture


def _real_session_env(tmp_path, monkeypatch):
    import chroma_write_store
    import config
    import incremental_jsonl as inc

    source, cfg, _route = _route_fixture(tmp_path, monkeypatch)
    layout = inc.ProductionBoundary(cfg, str(source)).layout
    monkeypatch.setattr(
        chroma_write_store,
        "DEFAULT_WRITER_LOCK",
        layout["locks"] / "chroma_writer_gate.lock",
    )
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.toml")
    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    monkeypatch.setattr("brief.refresh_brief_after_change", lambda *a, **k: None, raising=False)
    return cfg


def _where(exc):
    return repr(exc)[:160], [
        f"{f.filename.split('/')[-1]}:{f.lineno}"
        for f in traceback.extract_tb(exc.__traceback__)
    ][-5:]


def test_real_session_counts_one_store_session(tmp_path, monkeypatch) -> None:
    """Control: the real session is what the lock-order check counts."""
    from chroma_write_store import (
        production_chroma_store_session_depth,
        production_chroma_write_session,
    )

    _real_session_env(tmp_path, monkeypatch)
    with production_chroma_write_session(entrypoint="claude_verify9") as session:
        assert session.store is not None
        assert production_chroma_store_session_depth() == 1
    assert production_chroma_store_session_depth() == 0


def test_refine_backfill_domain_pays_then_writes(tmp_path, monkeypatch) -> None:
    import llm
    import refine
    from chroma_store import ChromaStore

    cfg = _real_session_env(tmp_path, monkeypatch)
    seed = ChromaStore(cfg["index"]["chroma_dir"])
    seed.add_unit(
        "u-untagged",
        "notes about python packaging",
        [0.1, 0.2, 0.3],
        {"id": "u-untagged", "title": "Packaging", "source_path": "/scratch/a"},
    )
    seed.close()
    paid: list[int] = []
    monkeypatch.setattr(llm, "generate", lambda *a, **k: paid.append(1) or "coding.tooling")
    try:
        result, err = refine.run_job("backfill_domain", limit=1, verbose=False), None
    except Exception as exc:  # report how much was paid before the failure
        result, err = None, _where(exc)
    assert err is None, ("paid calls:", len(paid), err)
    assert result["updated"] == 1, result


def test_monitor_cli_ingests_through_real_session(tmp_path, monkeypatch) -> None:
    import convmem
    import llm
    import monitor
    from typer.testing import CliRunner

    _real_session_env(tmp_path, monkeypatch)
    embeds: list[int] = []
    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
    monkeypatch.setattr(
        monitor,
        "fetch_https_headers",
        lambda site, *, session=None, timeout=20.0: ({}, "offline"),
    )
    monkeypatch.setattr(
        monitor,
        "check_tls_redirect",
        lambda site, *, session=None, timeout=20.0: False,
    )
    monkeypatch.setattr(llm, "ollama_embed", lambda *a, **k: embeds.append(1) or [0.1, 0.2, 0.3])
    out = CliRunner().invoke(convmem.app, ["monitor", "--site", "example.test"])
    err = _where(out.exception) if out.exception and not isinstance(out.exception, SystemExit) else None
    assert out.exit_code == 0 and err is None, ("embeds:", len(embeds), err, out.output[-300:])
    stats, _end = json.JSONDecoder().raw_decode(out.output[out.output.index("{"):])
    assert stats["observations"] > 0, stats


def test_repository_knowledge_retirement_through_real_session(tmp_path, monkeypatch) -> None:
    import repository_knowledge_scope as rks
    from chroma_store import ChromaStore
    from repository_knowledge_sync import reconcile_manifest
    from tests.test_repository_knowledge_scope import _commit_all, _init_repo, _write_manifest

    cfg = _real_session_env(tmp_path, monkeypatch)
    rks.reset_configuration()
    root = tmp_path / "repo"
    root.mkdir()
    _init_repo(root)
    man = _write_manifest(root, {"docs/plan.md": ("# Plan\n", "markdown")})
    _commit_all(root)
    rk_cfg = {"index": dict(cfg["index"]), "watch": {"repository_knowledge_manifests": [str(man)]}}
    reconcile_manifest(str(man), rk_cfg, dispatch=lambda *_: None)
    prior_manifest = rks.sha256_file(man)
    prior_file = rks.sha256_file(root / "docs/plan.md")
    source = str((root / "docs/plan.md").resolve())
    seed = ChromaStore(cfg["index"]["chroma_dir"])
    seed.add_unit(
        "right-row",
        "right",
        [0.0, 0.1, 0.2],
        {
            "id": "right-row",
            "source_path": source,
            "source_type": "repository_knowledge_v1",
            "file_sha256": prior_file,
            "manifest_sha256": prior_manifest,
        },
    )
    seed.close()
    payload = json.loads(man.read_text(encoding="utf-8"))
    (root / "docs/plan.md").unlink()
    payload["entries"] = [e for e in payload["entries"] if e["path"] != "docs/plan.md"]
    payload["classifications"] = [
        r for r in payload["classifications"] if r["path"] != "docs/plan.md"
    ]
    payload["retire"] = [
        {
            "path": "docs/plan.md",
            "prior_file_sha256": prior_file,
            "prior_manifest_sha256": prior_manifest,
            "reason": "probe retire",
        }
    ]
    man.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _commit_all(root, "retire")
    try:
        result, err = reconcile_manifest(str(man), rk_cfg, dispatch=lambda *_: None), None
    except Exception as exc:
        result, err = None, _where(exc)
    assert err is None, err
    assert result["retired"]["superseded"] == 1, result
