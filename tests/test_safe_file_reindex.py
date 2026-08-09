"""Regression coverage for non-destructive one-file reindexing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest import mock

import pytest

import ingest
from chroma_store import ChromaStore
from distill import DistillParseError, safe_json_parse
from tests.purge_test_util import patch_live_config


def _cfg(root: Path) -> dict:
    chroma = root / "chroma"
    chroma.mkdir()
    processed = root / "processed.json"
    processed.write_text("{}", encoding="utf-8")
    return {
        "index": {
            "chroma_dir": str(chroma),
            "processed_log": str(processed),
            "units_export": str(root / "knowledge_units.jsonl"),
        },
        "ingest_dedup": {
            "semantic_similarity": 0.92,
            "candidate_k": 10,
            "max_semantic_candidates_per_unit": 3,
        },
    }


def _models() -> dict:
    return {
        "summarize_model": "summary-model",
        "distill_model": "distill-model",
        "embed_model": "embed-model",
        "ollama_host": "http://localhost:11434",
    }


def _messages(count: int = 1) -> list[dict]:
    return [
        {"role": "user", "content": f"message {i}", "timestamp": "2026-08-09"}
        for i in range(count)
    ]


def _unit(title: str = "Replacement") -> dict:
    return {
        "type": "explanation",
        "title": title,
        "summary": f"{title} summary",
        "keywords": ["safe", "reindex", "coverage"],
        "confidence": 0.9,
        "domain": "coding.storage",
    }


def _seed_old(cfg: dict, src: Path) -> str:
    path_key = str(src.resolve())
    old_hash = ingest.sha256_file(str(src))
    Path(cfg["index"]["processed_log"]).write_text(
        json.dumps({old_hash: {"path": path_key, "chunks": 1, "units": 1}}),
        encoding="utf-8",
    )
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        store.add_unit(
            "old-unit",
            "old coverage",
            [1.0, 0.0],
            {"id": "old-unit", "title": "Old", "source_path": path_key},
        )
        store.add_summary(
            "old-summary",
            "old summary coverage",
            [1.0, 0.0],
            {"id": "old-summary", "source_path": path_key, "distill_status": "done"},
        )
    finally:
        store.close()
    return old_hash


def _run_one(
    cfg: dict,
    src: Path,
    *,
    parser=None,
    messages=None,
    distill_result=None,
    distill_side_effect=None,
    summarize_side_effect=None,
    embed_side_effect=None,
    force_reindex: bool = False,
    supersede: bool = False,
    chunk_size: int = 60,
    fmt: str = "cursor_jsonl",
):
    parser = parser or (lambda _path: messages if messages is not None else _messages())
    distill_result = [_unit()] if distill_result is None else distill_result
    embed = (
        embed_side_effect
        if embed_side_effect is not None
        else lambda *_args, **_kwargs: [0.1, 0.2]
    )
    real_write_session = ingest.production_chroma_write_session

    def hermetic_write_session(*, entrypoint: str, **kwargs):
        root = Path(cfg["index"]["chroma_dir"]).parent
        return real_write_session(
            entrypoint=entrypoint,
            lock_path=root / "writer.lock",
            attest_dir=root / "attest",
            census_dir=root / "census",
            **kwargs,
        )

    with patch_live_config(cfg), mock.patch(
        "ingest.detect_format", return_value=fmt
    ), mock.patch(
        "ingest.summarize",
        return_value="summary",
        side_effect=summarize_side_effect,
    ), mock.patch(
        "ingest.distill", return_value=distill_result, side_effect=distill_side_effect
    ) as distill_mock, mock.patch(
        "ingest.ollama_embed", side_effect=embed
    ), mock.patch(
        "ingest.time.sleep"
    ), mock.patch(
        "ingest._log_chunk_failure"
    ), mock.patch(
        "ingest.production_chroma_write_session", side_effect=hermetic_write_session
    ), mock.patch(
        "inter_model_index.production_chroma_write_session",
        side_effect=hermetic_write_session,
    ):
        result = ingest._index_one_file(
            cfg=cfg,
            idx=cfg["index"],
            path=str(src),
            parser=parser,
            processed=ingest.load_processed(cfg["index"]["processed_log"]),
            models=_models(),
            units_export=Path(cfg["index"]["units_export"]),
            chunk_size=chunk_size,
            overlap=0,
            min_confidence=0.1,
            force_file=str(src),
            force_reindex=force_reindex,
            supersede_on_reindex=supersede,
            verbose=False,
        )
    return result, distill_mock


def _source_ids(cfg: dict, src: Path) -> tuple[set[str], set[str]]:
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        path_key = str(src.resolve())
        return (
            store.ids_for_source("knowledge_units", path_key),
            store.ids_for_source("conversation_summaries", path_key),
        )
    finally:
        store.close()


def test_safe_json_parse_distinguishes_empty_from_invalid() -> None:
    assert safe_json_parse("[]") == []
    assert safe_json_parse("```json\n[]\n```") == []
    assert safe_json_parse('prefix [{"ok": true}] suffix') == [{"ok": True}]
    with pytest.raises(DistillParseError):
        safe_json_parse('{"not": "an array"}')
    with pytest.raises(DistillParseError):
        safe_json_parse("not json")


def test_valid_empty_is_committed_and_does_not_loop(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    src = tmp_path / "chat.jsonl"
    src.write_text("new empty extraction", encoding="utf-8")

    first, _ = _run_one(cfg, src, distill_result=[])
    second, _ = _run_one(cfg, src, distill_result=[])

    assert first[0] == "processed"
    assert second[0] == "skipped"
    processed = ingest.load_processed(cfg["index"]["processed_log"])
    assert ingest.sha256_file(str(src)) in processed
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        rows = [
            row
            for row in store.summaries_metadata()
            if row.get("source_path") == str(src.resolve())
        ]
    finally:
        store.close()
    assert [row["distill_status"] for row in rows] == ["empty"]


@pytest.mark.parametrize(
    "failure", [DistillParseError("bad array"), TimeoutError("late")]
)
def test_distill_failure_preserves_old_coverage_and_hash(
    tmp_path: Path, failure: Exception
) -> None:
    cfg = _cfg(tmp_path)
    src = tmp_path / "chat.jsonl"
    src.write_text("old", encoding="utf-8")
    old_hash = _seed_old(cfg, src)
    src.write_text("changed", encoding="utf-8")

    result, distill_mock = _run_one(cfg, src, distill_side_effect=failure)

    assert result[0] == "skipped"
    assert distill_mock.call_count == 3
    degraded_summary = hashlib.sha256(f"{src.resolve()}:0".encode()).hexdigest()
    assert _source_ids(cfg, src) == (
        {"old-unit"},
        {"old-summary", degraded_summary},
    )
    processed = ingest.load_processed(cfg["index"]["processed_log"])
    assert old_hash in processed
    assert ingest.sha256_file(str(src)) not in processed


def test_parse_failure_preserves_old_projection(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    src = tmp_path / "chat.jsonl"
    src.write_text("old", encoding="utf-8")
    old_hash = _seed_old(cfg, src)
    src.write_text("malformed", encoding="utf-8")

    result, _ = _run_one(
        cfg,
        src,
        parser=mock.Mock(side_effect=ValueError("parse failed")),
    )

    assert result[0] == "ignored"
    assert _source_ids(cfg, src) == ({"old-unit"}, {"old-summary"})
    assert old_hash in ingest.load_processed(cfg["index"]["processed_log"])


def test_unit_embedding_failure_preserves_old_projection(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    src = tmp_path / "chat.jsonl"
    src.write_text("old", encoding="utf-8")
    old_hash = _seed_old(cfg, src)
    src.write_text("changed", encoding="utf-8")

    result, _ = _run_one(
        cfg,
        src,
        embed_side_effect=[[0.1, 0.2], RuntimeError("unit embed failed")],
    )

    assert result[0] == "skipped"
    assert "old-unit" in _source_ids(cfg, src)[0]
    assert old_hash in ingest.load_processed(cfg["index"]["processed_log"])


def test_mid_write_failure_preserves_old_projection(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    src = tmp_path / "chat.jsonl"
    src.write_text("old", encoding="utf-8")
    old_hash = _seed_old(cfg, src)
    src.write_text("changed", encoding="utf-8")

    with mock.patch(
        "chroma_store.ChromaStore.add_unit", side_effect=RuntimeError("write")
    ):
        result, _ = _run_one(cfg, src)

    assert result[0] == "skipped"
    assert "old-unit" in _source_ids(cfg, src)[0]
    assert old_hash in ingest.load_processed(cfg["index"]["processed_log"])


def test_exclusion_during_build_preserves_old_projection(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    src = tmp_path / "chat.jsonl"
    src.write_text("old", encoding="utf-8")
    _seed_old(cfg, src)
    src.write_text("changed", encoding="utf-8")

    def exclude_during_summary(*_args, **_kwargs):
        ingest.exclude_processed_path(
            cfg["index"]["processed_log"],
            str(src.resolve()),
            ingest.sha256_file(str(src)),
            reason="race",
        )
        return "summary"

    result, _ = _run_one(cfg, src, summarize_side_effect=exclude_during_summary)

    assert result[0] == "skipped"
    assert "old-unit" in _source_ids(cfg, src)[0]
    assert any(
        isinstance(row, dict) and row.get("excluded")
        for row in ingest.load_processed(cfg["index"]["processed_log"]).values()
    )


def test_success_prunes_only_stale_snapshot_rows(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    src = tmp_path / "chat.jsonl"
    src.write_text("old", encoding="utf-8")
    _seed_old(cfg, src)
    src.write_text("changed", encoding="utf-8")

    result, _ = _run_one(cfg, src)

    unit_ids, summary_ids = _source_ids(cfg, src)
    assert result[0] == "processed"
    assert "old-unit" not in unit_ids
    assert "old-summary" not in summary_ids
    assert len(unit_ids) == 1
    assert len(summary_ids) == 1
    assert ingest.sha256_file(str(src)) in ingest.load_processed(
        cfg["index"]["processed_log"]
    )


def test_successful_retry_converges_after_failed_generation(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    src = tmp_path / "chat.jsonl"
    src.write_text("old", encoding="utf-8")
    old_hash = _seed_old(cfg, src)
    src.write_text("changed", encoding="utf-8")

    failed, _ = _run_one(cfg, src, distill_side_effect=TimeoutError("late"))
    assert failed[0] == "skipped"
    assert "old-unit" in _source_ids(cfg, src)[0]
    assert old_hash in ingest.load_processed(cfg["index"]["processed_log"])

    succeeded, _ = _run_one(cfg, src)
    assert succeeded[0] == "processed"
    assert "old-unit" not in _source_ids(cfg, src)[0]
    processed = ingest.load_processed(cfg["index"]["processed_log"])
    assert old_hash not in processed
    assert ingest.sha256_file(str(src)) in processed


def test_file_shrink_prunes_trailing_generation_only_after_success(
    tmp_path: Path,
) -> None:
    cfg = _cfg(tmp_path)
    src = tmp_path / "chat.jsonl"
    src.write_text("two chunks", encoding="utf-8")

    def per_chunk(text, **_kwargs):
        return [_unit(text)]

    first, _ = _run_one(
        cfg,
        src,
        messages=_messages(2),
        distill_side_effect=per_chunk,
        chunk_size=1,
    )
    assert first[0] == "processed"
    assert len(_source_ids(cfg, src)[0]) == 2

    src.write_text("one chunk", encoding="utf-8")
    second, _ = _run_one(
        cfg,
        src,
        messages=_messages(1),
        distill_side_effect=per_chunk,
        chunk_size=1,
    )

    assert second[0] == "processed"
    assert len(_source_ids(cfg, src)[0]) == 1
    assert len(_source_ids(cfg, src)[1]) == 1


def test_source_change_during_build_blocks_prune_and_hash(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    src = tmp_path / "chat.jsonl"
    src.write_text("old", encoding="utf-8")
    old_hash = _seed_old(cfg, src)
    src.write_text("generation one", encoding="utf-8")

    def change_source(*_args, **_kwargs):
        src.write_text("generation two", encoding="utf-8")
        return [_unit()]

    result, _ = _run_one(cfg, src, distill_side_effect=change_source)

    assert result[0] == "skipped"
    assert "old-unit" in _source_ids(cfg, src)[0]
    processed = ingest.load_processed(cfg["index"]["processed_log"])
    assert old_hash in processed
    assert ingest.sha256_file(str(src)) not in processed


def test_supersede_marks_only_stale_units_and_deletes_stale_summaries(
    tmp_path: Path,
) -> None:
    cfg = _cfg(tmp_path)
    src = tmp_path / "chat.jsonl"
    src.write_text("old", encoding="utf-8")
    _seed_old(cfg, src)
    src.write_text("changed", encoding="utf-8")

    result, _ = _run_one(cfg, src, supersede=True)

    assert result[0] == "processed"
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        old = store.get_unit("old-unit")
        active = store.ids_for_source("knowledge_units", str(src.resolve()))
        summaries = store.ids_for_source("conversation_summaries", str(src.resolve()))
    finally:
        store.close()
    assert old is not None and old["metadata"]["superseded"] is True
    assert len(active) == 2  # one active replacement plus retained tombstone
    assert "old-summary" not in summaries


def test_inter_model_embedding_failure_preserves_old_projection(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    src = tmp_path / "docs" / "inter-model" / "HANDOFF.md"
    src.parent.mkdir(parents=True)
    src.write_text("old", encoding="utf-8")
    old_hash = _seed_old(cfg, src)
    src.write_text("changed", encoding="utf-8")
    messages = [
        {
            "section_index": 0,
            "section_title": "Packet",
            "content": "replacement content",
        }
    ]

    with mock.patch(
        "inter_model_index.ollama_embed", side_effect=RuntimeError("embed")
    ):
        result, _ = _run_one(
            cfg,
            src,
            messages=messages,
            fmt="inter_model_doc",
        )

    assert result[0] == "skipped"
    assert "old-unit" in _source_ids(cfg, src)[0]
    assert old_hash in ingest.load_processed(cfg["index"]["processed_log"])
