"""The production write path passes the configured embedding model to the store.

Hermetic: stores live in ``tmp_path``; the production session runs with a
scratch config, lease lock and attestation directory, and ``load_config`` is
patched exactly as ``tests/test_shadow_writer_gate_c3.py`` does. The live Chroma
directory and the operator config are never opened.

The last section feeds what the real writer recorded to ``convmem doctor``'s
existing identity check, so the original symptom is covered end to end: a
collection created through the production path no longer draws the "legacy
collection metadata lacks convmem:embed_model" warning.
"""

# pylint: disable=protected-access

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from chromadb.errors import NotFoundError

import config as config_mod
from chroma_readonly import collection_config_metadata, collection_uuid
from chroma_store import EMBED_MODEL_KEY, SUMMARIES, UNITS
from chroma_write_store import (
    configured_embed_model,
    open_chroma_for_write,
    open_production_recovery_write_store,
    production_chroma_write_session,
)

MODEL = "nomic-embed-text:latest"
COSINE_ONLY = {"hnsw:space": "cosine"}
IDENTIFIED = {**COSINE_ONLY, EMBED_MODEL_KEY: MODEL}


def _cfg(chroma: Path, *, models: dict[str, Any] | None) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {"enabled": False},
    }
    if models is not None:
        cfg["models"] = models
    return cfg


def _write_config(path: Path, chroma: Path, embed_model_line: str) -> None:
    path.write_text(
        "[index]\n"
        f'chroma_dir = "{chroma}"\n'
        'collection = "knowledge_units"\n'
        "[models]\n"
        f"{embed_model_line}"
        'ollama_host = "http://127.0.0.1:11434"\n'
        "[shadow_ledger]\n"
        "enabled = false\n",
        encoding="utf-8",
    )


def _inner_store(session):  # type: ignore[no-untyped-def]
    """The raw store the factory built.

    ``ProductionWriteSession.store`` is annotated as a plain store but is the
    index-lock-guarded wrapper, which refuses raw collection access without the
    index write lock. The store that carries the model sits in its ``_inner``.
    """
    return session.store._inner  # pylint: disable=no-member


def _load_toml(cfg_path: Path):
    def load(path=None):  # type: ignore[no-untyped-def]
        return tomllib.loads(Path(path or cfg_path).read_text(encoding="utf-8"))

    return mock.patch.object(config_mod, "load_config", side_effect=load)


# --------------------------------------------------------------------------------------
# Reading the model out of config
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cfg", "expected"),
    [
        ({"models": {"embed_model": MODEL}}, MODEL),
        ({"models": {"embed_model": f"  {MODEL}\n"}}, MODEL),
        (None, None),
        ({}, None),
        ({"models": None}, None),
        ({"models": "nomic"}, None),
        ({"models": {}}, None),
        ({"models": {"embed_model": ""}}, None),
        ({"models": {"embed_model": "   "}}, None),
        ({"models": {"embed_model": 768}}, None),
    ],
)
def test_configured_embed_model_reads_only_a_real_name(cfg, expected) -> None:
    assert configured_embed_model(cfg) == expected


# --------------------------------------------------------------------------------------
# The production factory
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("purpose", ["production", "test"])
def test_factory_records_the_configured_model_on_both_collections(
    tmp_path: Path, purpose: str
) -> None:
    chroma = tmp_path / "chroma"
    store, _ = open_chroma_for_write(
        _cfg(chroma, models={"embed_model": MODEL}), chroma, purpose=purpose
    )
    try:
        store._collection(UNITS)
        store._collection(SUMMARIES)
    finally:
        store.close()

    assert collection_config_metadata(chroma, UNITS) == IDENTIFIED
    assert collection_config_metadata(chroma, SUMMARIES) == IDENTIFIED


@pytest.mark.parametrize(
    "models", [None, {}, {"embed_model": ""}, {"embed_model": 768}], ids=repr
)
def test_factory_without_a_configured_model_records_no_identity(
    tmp_path: Path, models: dict[str, Any] | None
) -> None:
    chroma = tmp_path / "chroma"
    store, _ = open_chroma_for_write(_cfg(chroma, models=models), chroma, purpose="test")
    try:
        store._collection(UNITS)
    finally:
        store.close()

    assert collection_config_metadata(chroma, UNITS) == COSINE_ONLY


def test_factory_with_no_cfg_at_all_still_opens_and_records_nothing(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    store, _ = open_chroma_for_write(None, chroma, purpose="test")
    try:
        store._collection(UNITS)
    finally:
        store.close()

    assert collection_config_metadata(chroma, UNITS) == COSINE_ONLY


def test_factory_with_creation_off_creates_nothing_even_with_a_model(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    store, _ = open_chroma_for_write(
        _cfg(chroma, models={"embed_model": MODEL}),
        chroma,
        purpose="test",
        create_collections=False,
    )
    try:
        with pytest.raises(NotFoundError):
            store._collection(UNITS)
    finally:
        store.close()

    assert collection_uuid(chroma, UNITS) is None
    assert collection_uuid(chroma, SUMMARIES) is None


# --------------------------------------------------------------------------------------
# The real production session (lease, live-config load, guarded store)
# --------------------------------------------------------------------------------------


def test_production_session_records_the_model_from_live_config(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg_path = tmp_path / "config.toml"
    _write_config(cfg_path, chroma, f'embed_model = "{MODEL}"\n')

    with _load_toml(cfg_path):
        with production_chroma_write_session(
            cfg_path,
            lock_path=tmp_path / "gate.lock",
            attest_dir=tmp_path / "attest",
            entrypoint="test.embed-identity",
        ) as session:
            inner = _inner_store(session)
            inner._collection(UNITS)
            inner._collection(SUMMARIES)
            assert inner.embed_model == MODEL

    assert collection_config_metadata(chroma, UNITS) == IDENTIFIED
    assert collection_config_metadata(chroma, SUMMARIES) == IDENTIFIED


def test_production_session_with_no_model_in_config_records_no_identity(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg_path = tmp_path / "config.toml"
    _write_config(cfg_path, chroma, "")  # [models] present, embed_model absent

    with _load_toml(cfg_path):
        with production_chroma_write_session(
            cfg_path,
            lock_path=tmp_path / "gate.lock",
            attest_dir=tmp_path / "attest",
            entrypoint="test.embed-identity",
        ) as session:
            _inner_store(session)._collection(UNITS)

    assert collection_config_metadata(chroma, UNITS) == COSINE_ONLY


def test_recovery_session_never_creates_collections(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg_path = tmp_path / "config.toml"
    _write_config(cfg_path, chroma, f'embed_model = "{MODEL}"\n')

    with _load_toml(cfg_path):
        session = open_production_recovery_write_store(
            cfg_path,
            lock_path=tmp_path / "gate.lock",
            attest_dir=tmp_path / "attest",
            entrypoint="test.embed-identity-recovery",
        )
        try:
            with pytest.raises(NotFoundError):
                _inner_store(session)._collection(UNITS)
        finally:
            session.store.close()

    assert collection_uuid(chroma, UNITS) is None
    assert collection_uuid(chroma, SUMMARIES) is None


# --------------------------------------------------------------------------------------
# What `convmem doctor` makes of a store the production writer created
# --------------------------------------------------------------------------------------


def _doctor_check(chroma: Path, configured: str):
    from doctor import _check_embed_collection_identity

    return _check_embed_collection_identity(
        {"index": {"chroma_dir": str(chroma)}, "models": {"embed_model": configured}}
    )


def _create_through_factory(chroma: Path, models: dict[str, Any] | None) -> None:
    store, _ = open_chroma_for_write(_cfg(chroma, models=models), chroma, purpose="test")
    try:
        store._collection(UNITS)
        store._collection(SUMMARIES)
    finally:
        store.close()


def test_doctor_passes_for_a_collection_the_writer_created_with_the_same_model(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    _create_through_factory(chroma, {"embed_model": MODEL})

    check = _doctor_check(chroma, MODEL)

    assert check.effective_status() == "pass", check.detail
    assert MODEL in check.detail


def test_doctor_fails_when_the_configured_model_changed_after_creation(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _create_through_factory(chroma, {"embed_model": "model-a"})

    check = _doctor_check(chroma, "model-b")

    assert check.effective_status() == "fail"
    assert "embed model mismatch" in check.detail
    assert "model-a" in check.detail and "model-b" in check.detail


def test_doctor_still_warns_for_a_collection_created_without_identity(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _create_through_factory(chroma, None)

    check = _doctor_check(chroma, MODEL)

    assert check.effective_status() == "warn"
    assert "lacks convmem:embed_model" in check.detail
