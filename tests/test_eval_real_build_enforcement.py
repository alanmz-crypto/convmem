"""Real-build enforcement must fail before an adapter or Chroma can run."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_corpus.run_manifest import (
    bind_baseline_build,
    make_real_run_manifest_for_tests,
    write_approval_sidecar,
)
from eval_corpus.shadow_build import run_shadow_build


def _build_runtime(root: Path, *, embed_mode: str = "ollama", resume: bool = False) -> dict:
    paths = {
        "package": root / "package.jsonl",
        "manifest": root / "build-manifest.json",
        "chroma_dir": root / "chroma",
        "result": root / "build-result.json",
        "journal": root / "build-journal.jsonl",
        "capture_dir": root / "capture",
        "attempt_root": root,
    }
    return {
        **paths,
        "model_tag": "installed-test-model",
        "model_digest": "sha256:" + ("a" * 64),
        "embed_dimensions": 768,
        "embed_host": "http://127.0.0.1:11434",
        "corpus_package_sha256": "b" * 64,
        "unit_corpus_fingerprint": "c" * 64,
        "config_identity_sha256": "f" * 64,
        "enrichment_sha256": "e" * 64,
        "build_identity": "test-build",
        "embed_mode": embed_mode,
        "resume": resume,
    }


@pytest.mark.parametrize("embed_mode", ["fake", "http-fake"])
def test_real_manifest_refuses_fake_adapters(tmp_path, embed_mode):
    runtime = _build_runtime(tmp_path, embed_mode=embed_mode)
    body = make_real_run_manifest_for_tests(
        paths={key: str(value) for key, value in runtime.items() if key in {
            "package", "manifest", "chroma_dir", "result", "journal", "capture_dir", "attempt_root"
        }},
        operations=["baseline_build"],
        model_tag=runtime["model_tag"],
        embed_host=runtime["embed_host"],
        baseline_model_digest=runtime["model_digest"],
        baseline_embed_dimensions=runtime["embed_dimensions"],
        embed_mode=embed_mode,
        resume=False,
    )
    manifest = tmp_path / "run.json"
    manifest.write_text(json.dumps(body), encoding="utf-8")
    write_approval_sidecar(manifest)
    with pytest.raises(PermissionError, match="embed_mode=ollama"):
        bind_baseline_build(
            authorize_fixture=False,
            run_manifest_path=manifest,
            runtime=runtime,
        )


def test_real_manifest_refuses_resume(tmp_path):
    runtime = _build_runtime(tmp_path, resume=True)
    body = make_real_run_manifest_for_tests(
        paths={key: str(value) for key, value in runtime.items() if key in {
            "package", "manifest", "chroma_dir", "result", "journal", "capture_dir", "attempt_root"
        }},
        operations=["baseline_build"],
        model_tag=runtime["model_tag"],
        embed_host=runtime["embed_host"],
        baseline_model_digest=runtime["model_digest"],
        baseline_embed_dimensions=runtime["embed_dimensions"],
        embed_mode="ollama",
        resume=True,
    )
    manifest = tmp_path / "run.json"
    manifest.write_text(json.dumps(body), encoding="utf-8")
    write_approval_sidecar(manifest)
    with pytest.raises(PermissionError, match="resume=false"):
        bind_baseline_build(
            authorize_fixture=False,
            run_manifest_path=manifest,
            runtime=runtime,
        )


def test_model_execution_binds_digest_and_dimension(tmp_path):
    from eval_corpus.run_manifest import bind_model_execution

    chroma = tmp_path / "chroma"
    chroma.mkdir()
    digest = "sha256:" + ("a" * 64)
    body = make_real_run_manifest_for_tests(
        paths={
            "chroma_dir": str(chroma),
            "embed_host": "http://127.0.0.1:11434",
        },
        operations=["model_execution"],
        model_tag="installed-test-model",
        model_digest=digest,
        embed_dimensions=768,
    )
    manifest = tmp_path / "run.json"
    manifest.write_text(json.dumps(body), encoding="utf-8")
    write_approval_sidecar(manifest)

    context = bind_model_execution(
        authorize_fixture=False,
        run_manifest_path=manifest,
        runtime={
            "model_tag": "installed-test-model",
            "model_digest": digest,
            "embed_dimensions": 768,
            "embed_host": "http://127.0.0.1:11434",
            "chroma_dir": chroma,
        },
    )
    assert context.execution_mode == "real"


def test_real_builder_refuses_existing_output_without_opening_chroma(tmp_path):
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    manifest = {"embed_mode": "ollama"}
    with pytest.raises(RuntimeError, match="absent chroma_dir"):
        run_shadow_build(
            units=[],
            chroma_dir=chroma,
            manifest=manifest,
            embed_fn=lambda _: [],
            execution_mode="real",
        )


def test_real_builder_refuses_resume_without_opening_chroma(tmp_path):
    with pytest.raises(RuntimeError, match="forbids resume"):
        run_shadow_build(
            units=[],
            chroma_dir=tmp_path / "chroma",
            manifest={"embed_mode": "ollama"},
            embed_fn=lambda _: [],
            resume=True,
            execution_mode="real",
        )
