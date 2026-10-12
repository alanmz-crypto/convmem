"""Hermetic tests for issue #308 inter-model provenance rejection sidecar."""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest

import ingest
from chroma_store import ChromaStore
from distill import make_unit_id
from inter_model_index import InterModelSupersessionRequired, index_inter_model_messages
from inter_model_rejections import (
    REJECTION_KIND_PROVENANCE_SUPERSESSION,
    clear_inter_model_rejection_for_path,
    inter_model_rejection_matches,
    load_inter_model_rejections,
    record_provenance_supersession_rejection,
    rejections_path,
)
from source_reconciler import discover_legacy_source_drift
from tests.purge_test_util import patch_live_config
from watch import flush_path


class _FakeProductionWrite:
    def __init__(self, store: ChromaStore, cfg: dict) -> None:
        self.store = store
        self.live_cfg = cfg


def _cfg(tmp_path: Path, source: Path) -> dict:
    return {
        "sources": {"paths": [str(source)]},
        "watch": {"paths": [str(source)]},
        "index": {
            "processed_log": str(tmp_path / "processed.json"),
            "units_export": str(tmp_path / "knowledge_units.jsonl"),
            "chroma_dir": str(tmp_path / "chroma"),
        },
        "ingest_dedup": {
            "semantic_similarity": 0.92,
            "candidate_k": 10,
            "max_semantic_candidates_per_unit": 3,
        },
    }


def _inter_model_path(tmp_path: Path, name: str = "HANDOFF-test.md") -> Path:
    path = tmp_path / "docs" / "inter-model" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("## Packet\n\nOriginal body.\n", encoding="utf-8")
    return path


def _seed_indexed_section(cfg: dict, path: Path, body: str = "## Packet\n\nOriginal body.\n") -> None:
    path.write_text(body, encoding="utf-8")
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        from adapters.inter_model_doc import parse

        messages = parse(str(path))
        unit_id = make_unit_id(
            str(path.resolve()), int(messages[0]["section_index"]), "Packet", 0
        )

        @contextmanager
        def fake_session(*, entrypoint=None):
            del entrypoint
            yield _FakeProductionWrite(store, cfg)

        with mock.patch(
            "inter_model_index.production_chroma_write_session", fake_session
        ), mock.patch("inter_model_index.ollama_embed", return_value=[0.1, 0.2, 0.3]):
            Path(cfg["index"]["processed_log"]).write_text("{}", encoding="utf-8")
            index_inter_model_messages(
                str(path),
                messages,
                path_key=str(path.resolve()),
                chroma_dir=cfg["index"]["chroma_dir"],
                embed_model="nomic-embed-text",
                ollama_host="http://localhost:11434",
                cfg=cfg,
                verbose=False,
            )
    finally:
        store.close()


def _run_index_one_supersession(cfg: dict, path: Path) -> tuple[str, ...]:
    from adapters.inter_model_doc import parse

    path.write_text("## Packet\n\nReplacement body.\n", encoding="utf-8")
    real_write_session = ingest.production_chroma_write_session
    root = Path(cfg["index"]["chroma_dir"]).parent

    def hermetic_write_session(*, entrypoint: str, **kwargs):
        return real_write_session(
            entrypoint=entrypoint,
            lock_path=root / "writer.lock",
            attest_dir=root / "attest",
            census_dir=root / "census",
            **kwargs,
        )

    with patch_live_config(cfg), mock.patch(
        "ingest.production_chroma_write_session", side_effect=hermetic_write_session
    ), mock.patch(
        "inter_model_index.production_chroma_write_session",
        side_effect=hermetic_write_session,
    ), mock.patch("inter_model_index.ollama_embed", return_value=[0.1, 0.2, 0.3]), mock.patch(
        "ingest.detect_format", return_value="inter_model_doc"
    ):
        return ingest._index_one_file(  # pylint: disable=protected-access
            cfg=cfg,
            idx=cfg["index"],
            path=str(path),
            parser=parse,
            processed=ingest.load_processed(cfg["index"]["processed_log"]),
            models={
                "summarize_model": "s",
                "distill_model": "d",
                "embed_model": "e",
                "ollama_host": "http://localhost:11434",
            },
            units_export=Path(cfg["index"]["units_export"]),
            chunk_size=60,
            overlap=0,
            min_confidence=0.1,
            force_file=str(path),
            force_reindex=False,
            supersede_on_reindex=False,
            verbose=False,
        )


def test_provenance_guard_rejection_records_path_hash_and_skips_unchanged_stores(
    tmp_path: Path,
) -> None:
    """Handoff test 1: provenance guard records rejection; stores unchanged."""
    path = _inter_model_path(tmp_path)
    cfg = _cfg(tmp_path, path)
    Path(cfg["index"]["chroma_dir"]).mkdir(parents=True)
    Path(cfg["index"]["processed_log"]).write_text("{}", encoding="utf-8")
    _seed_indexed_section(cfg, path)
    processed_before = Path(cfg["index"]["processed_log"]).read_text(encoding="utf-8")
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        before_ids = set(store.ids_for_source("knowledge_units", str(path.resolve())))
    finally:
        store.close()

    status = _run_index_one_supersession(cfg, path)
    assert status[0] == "skipped"
    file_hash = ingest.sha256_file(str(path))
    side = load_inter_model_rejections(cfg["index"]["processed_log"])
    assert side[str(path.resolve())]["file_hash"] == file_hash
    assert side[str(path.resolve())]["kind"] == REJECTION_KIND_PROVENANCE_SUPERSESSION
    assert Path(cfg["index"]["processed_log"]).read_text(encoding="utf-8") == processed_before
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        after_ids = set(store.ids_for_source("knowledge_units", str(path.resolve())))
    finally:
        store.close()
    assert after_ids == before_ids


def test_watch_skip_reason_inter_model_rejected_until_content_changes(tmp_path: Path) -> None:
    """Handoff test 2: watch_skip_reason skips rejected hash; allows after change."""
    path = _inter_model_path(tmp_path)
    cfg = _cfg(tmp_path, path)
    file_hash = ingest.sha256_file(str(path))
    record_provenance_supersession_rejection(
        cfg["index"]["processed_log"],
        path_key=str(path.resolve()),
        file_hash=file_hash,
        section_id="0",
    )
    processed = {}
    assert (
        ingest.watch_skip_reason(
            path,
            processed=processed,
            processed_log=cfg["index"]["processed_log"],
        )
        == "inter_model_rejected"
    )
    path.write_text("## Packet\n\nNew bytes.\n", encoding="utf-8")
    assert (
        ingest.watch_skip_reason(
            path,
            processed=processed,
            processed_log=cfg["index"]["processed_log"],
        )
        is None
    )


def test_reconciliation_ignores_rejected_hash_until_content_changes(tmp_path: Path) -> None:
    """Handoff test 3: reconciler skips rejected path/hash; reports after change."""
    path = _inter_model_path(tmp_path)
    cfg = _cfg(tmp_path, path)
    observed = ingest.sha256_file(str(path))
    record_provenance_supersession_rejection(
        cfg["index"]["processed_log"],
        path_key=str(path.resolve()),
        file_hash=observed,
        section_id="0",
    )
    assert discover_legacy_source_drift(cfg) == []
    path.write_text("## Packet\n\nChanged for reconciliation.\n", encoding="utf-8")
    findings = discover_legacy_source_drift(cfg)
    assert len(findings) == 1
    assert findings[0].reason == "new_eligible_source"


def test_repeated_watch_events_do_not_respawn_index(tmp_path: Path) -> None:
    """Handoff test 4: unchanged bytes after rejection produce no index attempts."""
    path = _inter_model_path(tmp_path)
    cfg = _cfg(tmp_path, path)
    file_hash = ingest.sha256_file(str(path))
    record_provenance_supersession_rejection(
        cfg["index"]["processed_log"],
        path_key=str(path.resolve()),
        file_hash=file_hash,
        section_id="0",
    )
    mock_index = mock.Mock()
    processed = {}
    with patch_live_config(cfg), mock.patch(
        "ingest.load_config", return_value=cfg
    ), mock.patch("ingest.load_processed", return_value=processed):
        for _ in range(3):
            assert flush_path(str(path), index_fn=mock_index, verbose=False) is None
    mock_index.assert_not_called()


def test_non_guard_embedding_failure_writes_no_rejection(tmp_path: Path) -> None:
    """Handoff test 5: embedding errors stay retryable with no sidecar write."""
    path = _inter_model_path(tmp_path)
    cfg = _cfg(tmp_path, path)
    Path(cfg["index"]["chroma_dir"]).mkdir(parents=True)
    Path(cfg["index"]["processed_log"]).write_text("{}", encoding="utf-8")
    _seed_indexed_section(cfg, path)
    path.write_text("## Packet\n\nReplacement body.\n", encoding="utf-8")
    from adapters.inter_model_doc import parse

    real_write_session = ingest.production_chroma_write_session
    root = Path(cfg["index"]["chroma_dir"]).parent

    def hermetic_write_session(*, entrypoint: str, **kwargs):
        return real_write_session(
            entrypoint=entrypoint,
            lock_path=root / "writer.lock",
            attest_dir=root / "attest",
            census_dir=root / "census",
            **kwargs,
        )

    with patch_live_config(cfg), mock.patch(
        "inter_model_index.ollama_embed", side_effect=RuntimeError("embed")
    ), mock.patch(
        "ingest.production_chroma_write_session", side_effect=hermetic_write_session
    ), mock.patch(
        "inter_model_index.production_chroma_write_session",
        side_effect=hermetic_write_session,
    ), mock.patch("ingest.detect_format", return_value="inter_model_doc"):
        status = ingest._index_one_file(  # pylint: disable=protected-access
            cfg=cfg,
            idx=cfg["index"],
            path=str(path),
            parser=parse,
            processed=ingest.load_processed(cfg["index"]["processed_log"]),
            models={
                "summarize_model": "s",
                "distill_model": "d",
                "embed_model": "e",
                "ollama_host": "http://localhost:11434",
            },
            units_export=Path(cfg["index"]["units_export"]),
            chunk_size=60,
            overlap=0,
            min_confidence=0.1,
            force_file=str(path),
            force_reindex=False,
            supersede_on_reindex=False,
            verbose=False,
        )
    assert status[0] == "skipped"
    assert not rejections_path(cfg["index"]["processed_log"]).exists()


def test_rejection_is_path_specific_not_content_global(tmp_path: Path) -> None:
    """Handoff test 6: same bytes at another path are not suppressed."""
    path_a = _inter_model_path(tmp_path, "a.md")
    path_b = _inter_model_path(tmp_path, "b.md")
    path_b.write_text(path_a.read_text(encoding="utf-8"), encoding="utf-8")
    cfg = _cfg(tmp_path, path_a)
    file_hash = ingest.sha256_file(str(path_a))
    record_provenance_supersession_rejection(
        cfg["index"]["processed_log"],
        path_key=str(path_a.resolve()),
        file_hash=file_hash,
        section_id="0",
    )
    assert (
        ingest.watch_skip_reason(
            path_a,
            processed={},
            processed_log=cfg["index"]["processed_log"],
        )
        == "inter_model_rejected"
    )
    assert (
        ingest.watch_skip_reason(
            path_b,
            processed={},
            processed_log=cfg["index"]["processed_log"],
        )
        is None
    )


def test_corrupt_sidecar_fails_open_and_concurrent_writes_preserve_records(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Handoff test 7: corrupt sidecar fails open; concurrent writes keep records."""
    cfg = _cfg(tmp_path, tmp_path / "docs" / "inter-model" / "x.md")
    side = rejections_path(cfg["index"]["processed_log"])
    side.parent.mkdir(parents=True, exist_ok=True)
    side.write_text("{not json", encoding="utf-8")
    assert not inter_model_rejection_matches(
        cfg["index"]["processed_log"], "/any/path.md", "deadbeef"
    )
    err = capsys.readouterr().err
    assert "failing open" in err

    paths = [tmp_path / f"docs/inter-model/p{i}.md" for i in range(4)]
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"## Packet\n\nBody {p.name}.\n", encoding="utf-8")

    def writer(p: Path) -> None:
        record_provenance_supersession_rejection(
            cfg["index"]["processed_log"],
            path_key=str(p.resolve()),
            file_hash=ingest.sha256_file(str(p)),
            section_id="0",
        )

    threads = [threading.Thread(target=writer, args=(p,)) for p in paths]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    data = load_inter_model_rejections(cfg["index"]["processed_log"])
    assert len(data) == len(paths)
    assert clear_inter_model_rejection_for_path(cfg["index"]["processed_log"], paths[0])
