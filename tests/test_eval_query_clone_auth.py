"""Manifest binding tests for disposable query-clone materialization."""

from __future__ import annotations

import json
import shutil

import pytest

from eval_corpus.chroma_clone import (
    clone_chroma_root,
    materialize_authorized_chroma_clone,
)
from eval_corpus.run_manifest import (
    bind_query_clone,
    make_real_run_manifest_for_tests,
    write_approval_sidecar,
)


def _manifest_and_runtime(tmp_path, fingerprint="a" * 64):
    source = tmp_path / "authoritative"
    parent = tmp_path / "attempts"
    source.mkdir()
    parent.mkdir()
    (source / "chroma.sqlite3").write_bytes(b"source\n")
    probe = clone_chroma_root(
        source,
        parent / "fingerprint-probe",
        approved_source_root=tmp_path,
        approved_destination_parent=parent,
    )
    fingerprint = probe["source_content_fingerprint"]
    shutil.rmtree(parent / "fingerprint-probe")
    paths = {
        "source_chroma": str(source),
        "clone_root": str(parent / "clone-0"),
        "clone_parent": str(parent),
    }
    runtime = {**paths, "source_content_fingerprint": fingerprint}
    body = make_real_run_manifest_for_tests(
        paths=paths,
        operations=["query_clone"],
        source_content_fingerprint=fingerprint,
    )
    manifest = tmp_path / "query-clone.json"
    manifest.write_text(json.dumps(body), encoding="utf-8")
    write_approval_sidecar(manifest)
    return source, parent, manifest, runtime


def test_query_clone_binds_exact_paths_and_fingerprint(tmp_path):
    source, parent, manifest, runtime = _manifest_and_runtime(tmp_path)
    context = bind_query_clone(
        authorize_fixture=False,
        run_manifest_path=manifest,
        runtime=runtime,
    )
    assert context.operation == "query_clone"

    receipt = materialize_authorized_chroma_clone(
        source,
        parent / "clone-0",
        approved_source_root=tmp_path,
        approved_destination_parent=parent,
        authorize_fixture=False,
        run_manifest_path=manifest,
        runtime=runtime,
    )
    assert receipt["source_content_fingerprint"] == runtime["source_content_fingerprint"]


def test_query_clone_rejects_wrong_fingerprint_and_retargeted_path(tmp_path):
    _source, parent, manifest, runtime = _manifest_and_runtime(tmp_path)
    with pytest.raises(PermissionError, match="mismatch"):
        bind_query_clone(
            authorize_fixture=False,
            run_manifest_path=manifest,
            runtime={**runtime, "source_content_fingerprint": "b" * 64},
        )
    with pytest.raises(PermissionError, match="mismatch"):
        bind_query_clone(
            authorize_fixture=False,
            run_manifest_path=manifest,
            runtime={**runtime, "clone_root": parent / "other"},
        )
