# pylint: disable=wrong-import-position,protected-access,too-many-locals
"""Subprocess worker for §9.7 ingest.index end-to-end measurement."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

HARNES_ROOT = Path(__file__).resolve().parents[1]
if str(HARNES_ROOT) not in sys.path:
    sys.path.insert(0, str(HARNES_ROOT))

from tests.linux_proc import peak_rss_bytes as _peak_rss_bytes
from tests.linux_proc import proc_fd_targets as _proc_fd_targets
from tests.linux_proc import rss_bytes as _rss_bytes
from tests.watch_oom_hermetic_isolation import DENIED
from tests.watch_oom_memory_worker_shared import (
    denied_exit_code,
    emit_worker_json,
    prepare_worker,
)
from tests.watch_oom_exposure_index_e2e_support import EMBED_VECTOR


def _purge_target_modules() -> None:
    for name in list(sys.modules):
        if name in {
            "ingest",
            "brief",
            "doctor",
            "config",
            "chroma_readonly",
            "chroma_store",
            "chroma_write_store",
        } or name.startswith(("ingest.", "brief.", "doctor.", "config.")):
            sys.modules.pop(name, None)


def _configure_target_imports(target_root: Path) -> None:
    target = str(target_root.resolve())
    sys.path[:] = [p for p in sys.path if p != target]
    sys.path.insert(0, target)


def _assert_target_paths(target_root: Path, modules: dict[str, object]) -> dict[str, str]:
    root = target_root.resolve()
    paths: dict[str, str] = {}
    for name, mod in modules.items():
        file_path = Path(getattr(mod, "__file__", "") or "").resolve()
        if not str(file_path).startswith(str(root)):
            raise RuntimeError(f"{name} resolved outside target tree: {file_path}")
        paths[name] = str(file_path)
    return paths


def _distill_stub(*_args, **_kwargs):
    units = [
        {
            "type": "explanation",
            "title": "E2E measurement unit",
            "summary": (
                "Deterministic distill output for §9.7 ingest.index probe "
                f"{hashlib.sha256(str(_args).encode()).hexdigest()[:12]}."
            ),
            "keywords": ["e2e", "measurement", "unique"],
            "confidence": 0.95,
            "domain": "coding.storage",
        }
    ]
    return units, json.dumps(units, ensure_ascii=False, sort_keys=True)


def _log(step: str) -> None:
    print(f"[e2e-worker] {step}", file=sys.stderr, flush=True)


def _dispatch(args: argparse.Namespace) -> int:
    target_root = Path(args.target_root).resolve()
    config_path = Path(args.config_path).resolve()
    writer_root = Path(args.writer_root).resolve()
    brief_path = Path(args.brief_path).resolve()
    register_path = Path(args.register_path).resolve()
    transcript = Path(args.transcript).resolve()
    chroma_dir = Path(args.chroma_dir).resolve()

    os.environ["CONVMEM_CONFIG"] = str(config_path)
    _log("config set")
    _purge_target_modules()
    _configure_target_imports(target_root)

    import config as config_mod
    import ingest
    import brief
    import doctor
    import chroma_readonly
    _log("target imports ready")

    target_paths = _assert_target_paths(
        target_root,
        {
            "ingest": ingest,
            "brief": brief,
            "doctor": doctor,
            "config": config_mod,
            "chroma_readonly": chroma_readonly,
        },
    )

    import_baseline = _rss_bytes()
    started = time.monotonic()

    real_write_session = ingest.production_chroma_write_session
    real_writer_boundary = ingest.production_writer_boundary

    def hermetic_write_session(*, entrypoint: str, **kwargs):
        kwargs.setdefault("config_path", config_path)
        kwargs["lock_path"] = writer_root / "writer.lock"
        kwargs["attest_dir"] = writer_root / "attest"
        kwargs["census_dir"] = writer_root / "census"
        return real_write_session(entrypoint=entrypoint, **kwargs)

    def hermetic_writer_boundary(*, entrypoint: str, **kwargs):
        kwargs["lock_path"] = writer_root / "writer.lock"
        kwargs["attest_dir"] = writer_root / "attest"
        kwargs["census_dir"] = writer_root / "census"
        return real_writer_boundary(entrypoint=entrypoint, **kwargs)

    units_before = chroma_readonly.collection_count(str(chroma_dir), "knowledge_units")

    with ExitStack() as stack:
        stack.enter_context(patch.object(brief, "DEFAULT_BRIEF_PATH", brief_path))
        stack.enter_context(patch.object(doctor, "_standing_register_path", return_value=register_path))
        stack.enter_context(patch("ingest.summarize", return_value="e2e summary"))
        stack.enter_context(patch("ingest._distill_with_provenance", side_effect=_distill_stub))
        stack.enter_context(patch("ingest.ollama_embed", return_value=EMBED_VECTOR))
        stack.enter_context(patch("llm.summarize", return_value="e2e summary"))
        stack.enter_context(patch("llm.ollama_embed", return_value=EMBED_VECTOR))
        stack.enter_context(patch("distill.distill_with_response", side_effect=_distill_stub))
        stack.enter_context(patch("ingest.time.sleep"))
        stack.enter_context(patch("ingest.production_chroma_write_session", side_effect=hermetic_write_session))
        stack.enter_context(patch("ingest.production_writer_boundary", side_effect=hermetic_writer_boundary))
        stack.enter_context(
            patch(
                "brief._systemd_state",
                return_value="enabled/active",
            )
        )
        stack.enter_context(
            patch(
                "brief._mcp_registration",
                return_value={"cursor": "registered", "crush": "registered"},
            )
        )
        stack.enter_context(patch("brief._watch_process_memory", return_value=None))
        stack.enter_context(patch("brief._pending_decision_ingest", return_value=[]))
        _log("starting ingest.index")
        stats = ingest.index(
            force_file=str(transcript),
            verbose=False,
            force_reindex=True,
        )
        _log(f"ingest.index done: {stats}")

    elapsed = time.monotonic() - started
    units_after = chroma_readonly.collection_count(str(chroma_dir), "knowledge_units")

    if stats.get("files_processed", 0) < 1:
        raise RuntimeError(f"ingest.index did not process transcript: {stats}")
    if units_after <= units_before:
        raise RuntimeError(
            f"expected new units in temporary Chroma: before={units_before} after={units_after}"
        )
    if not brief_path.is_file() or brief_path.stat().st_size < 1:
        raise RuntimeError("brief refresh did not publish output")

    cfg = config_mod.load_config(config_path)
    due, detail = doctor._exposure_window_probe(
        {"id": "exposure-window-tracking", "status": "open", "last_verified": "2026-07-01"},
        cfg,
    )
    probe_digest = hashlib.sha256(f"{due}|{detail}".encode()).hexdigest()

    for path in (
        writer_root / "writer.lock",
        writer_root / "attest",
        writer_root / "census",
    ):
        resolved = str(path.expanduser().resolve())
        prod_share = str((Path.home() / ".local/share/convmem").resolve())
        if resolved.startswith(prod_share):
            raise RuntimeError(f"writer path resolves into production: {resolved}")

    emit_worker_json(
        {
            "target_sha": args.target_sha,
            "harness_hash": args.harness_hash,
            "import_baseline_rss_bytes": import_baseline,
            "peak_rss_bytes": _peak_rss_bytes(),
            "elapsed_seconds": round(elapsed, 3),
            "index_stats": stats,
            "units_before": units_before,
            "units_after": units_after,
            "probe_due": due,
            "probe_detail": detail,
            "probe_digest": probe_digest,
            "brief_digest": hashlib.sha256(brief_path.read_bytes()).hexdigest(),
            "brief_bytes": brief_path.stat().st_size,
            "target_module_paths": target_paths,
            "opened_paths": sorted(set(_proc_fd_targets())),
            "denied_paths": DENIED,
            "transcript_sha256": hashlib.sha256(transcript.read_bytes()).hexdigest(),
        }
    )
    return denied_exit_code()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--target-sha", required=True)
    parser.add_argument("--harness-hash", required=True)
    parser.add_argument("--config-path", required=True)
    parser.add_argument("--chroma-dir", required=True)
    parser.add_argument("--writer-root", required=True)
    parser.add_argument("--brief-path", required=True)
    parser.add_argument("--register-path", required=True)
    parser.add_argument("--transcript", required=True)
    args = parser.parse_args()
    prepare_worker()
    return _dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())
