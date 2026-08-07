"""Hermetic deterministic enrichment materialization tests."""

from __future__ import annotations

import pytest

from eval_corpus.enrichment_materialize import materialize_enrichment


def test_materialization_reports_same_source_and_destination_identity(tmp_path):
    root = tmp_path / "eval"
    source_dir = root / "inputs"
    destination_dir = root / "arm"
    source_dir.mkdir(parents=True)
    destination_dir.mkdir()
    source = source_dir / "decisions-approved.jsonl"
    destination = destination_dir / "decisions-approved.jsonl"
    source.write_bytes(b'{"id":"dec_prop_1","summary":"one"}\r\n')

    report = materialize_enrichment(source, destination, approved_root=root)

    assert report["source_sha256"] == report["destination_sha256"]
    assert report["row_count"] == 1
    assert report["destination"]["link_count"] == 1
    assert destination.read_bytes() == source.read_bytes()


def test_materialization_rejects_existing_destination(tmp_path):
    root = tmp_path / "eval"
    source_dir = root / "inputs"
    destination_dir = root / "arm"
    source_dir.mkdir(parents=True)
    destination_dir.mkdir()
    source = source_dir / "decisions-approved.jsonl"
    destination = destination_dir / "decisions-approved.jsonl"
    source.write_text('{"id":"dec_prop_1"}\n', encoding="utf-8")
    destination.write_text("existing\n", encoding="utf-8")

    with pytest.raises(PermissionError):
        materialize_enrichment(source, destination, approved_root=root)


def test_materialization_rejects_symlinked_source(tmp_path):
    root = tmp_path / "eval"
    source_dir = root / "inputs"
    destination_dir = root / "arm"
    outside = tmp_path / "outside.jsonl"
    source_dir.mkdir(parents=True)
    destination_dir.mkdir()
    outside.write_text('{"id":"outside"}\n', encoding="utf-8")
    source = source_dir / "decisions-approved.jsonl"
    source.symlink_to(outside)

    with pytest.raises(PermissionError, match="symlink"):
        materialize_enrichment(
            source,
            destination_dir / "decisions-approved.jsonl",
            approved_root=root,
        )
