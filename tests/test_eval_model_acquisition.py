"""Fixture-only model acquisition receipt tests; no Ollama pull occurs."""

from __future__ import annotations

import subprocess

import pytest

from eval_corpus.model_acquisition import (
    ModelAcquisitionError,
    run_authorized_model_pull,
)


class _Identity:
    def __init__(self, digest="sha256:test"):
        self.digest = digest

    def list_models(self):
        return [{"name": "fixture-model", "digest": self.digest}]

    def resolve_model(self, tag):
        return {"model_tag": tag, "model_digest": self.digest}


def _run(*args, **kwargs):
    return subprocess.CompletedProcess(
        args=args[0], returncode=0, stdout=b"pulled\n", stderr=b""
    )


def test_authorized_pull_receipt_proves_digest_and_store_change(tmp_path):
    store = tmp_path / "models"
    store.mkdir()
    binary = tmp_path / "ollama"
    binary.write_text("fixture", encoding="utf-8")
    report = run_authorized_model_pull(
        ollama_binary=binary,
        model_store_path=store,
        model_tag="fixture-model",
        expected_digest="sha256:test",
        ollama_host="http://127.0.0.1:11434",
        identity_client=_Identity(),
        authorized=True,
        run_fn=_run,
    )
    assert report["status"] == "OK"
    assert report["exit_code"] == 0
    assert report["stdout_sha256"]
    assert report["pre_store_inventory"]["inventory_sha256"] == report["post_store_inventory"]["inventory_sha256"]


def test_pull_requires_authorization(tmp_path):
    store = tmp_path / "models"
    store.mkdir()
    binary = tmp_path / "ollama"
    binary.write_text("fixture", encoding="utf-8")
    with pytest.raises(ModelAcquisitionError, match="authorization"):
        run_authorized_model_pull(
            ollama_binary=binary,
            model_store_path=store,
            model_tag="fixture-model",
            expected_digest="sha256:test",
            ollama_host="http://127.0.0.1:11434",
            identity_client=_Identity(),
            authorized=False,
            run_fn=_run,
        )
