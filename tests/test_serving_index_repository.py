"""Integration tests for the CG-2 serving repository boundary (T1)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chroma_store import ChromaStore, open_chroma_for_read
from serving_authority import (
    OwnerUnavailableError,
    ServingAuthorityError,
    ServingBackendTransient,
    publish_legacy_fence,
)
from serving_index_repository import (
    MediatedFallbackResult,
    open_serving_index_repository,
    runtime_serving_read_sites,
)


from tests.serving_test_helpers import assert_serving_open_raises, serving_test_cfg


def _cfg(tmp_path: Path, chroma: Path) -> dict:
    return serving_test_cfg(tmp_path, chroma)


def test_legacy_gateway_matches_direct_chroma_query_units(tmp_path: Path) -> None:
    """Legacy-global mode must preserve vector query results (T1 equivalence)."""

    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = _cfg(tmp_path, chroma)
    store = ChromaStore(str(chroma))
    embedding = [0.1] * 8
    store.add_unit(
        "unit-a",
        "alpha knowledge",
        embedding,
        {"id": "unit-a", "title": "alpha"},
    )
    store.close()

    direct = open_chroma_for_read(str(chroma))
    try:
        direct_rows = direct.query_units(embedding, 5)
    finally:
        direct.close()

    with open_serving_index_repository(cfg) as repo:
        gateway_rows = repo.query_units(embedding, 5)

    assert [row["id"] for row in gateway_rows] == [row["id"] for row in direct_rows]


def test_authority_failure_never_triggers_query_fallback(tmp_path: Path) -> None:
    """Fenced owners fail closed; query_units must not keyword-fallback."""

    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = _cfg(tmp_path, chroma)
    publish_legacy_fence(
        cfg["index"]["generation_root"],
        "source:/tmp/fenced.jsonl",
        "2026-08-15T00:00:00Z",
    )

    from query import query_units

    with patch("query.ollama_embed", return_value=[0.1] * 8), patch(
        "query._fallback_query_rows"
    ) as fallback, patch(
        "rerank.rerank",
        side_effect=lambda _q, rows, _m, k: rows[:k],
    ):
        with pytest.raises(OwnerUnavailableError):
            query_units("blocked query", top_k=3, cfg=cfg)
        fallback.assert_not_called()


def test_transient_backend_uses_mediated_fallback_only(tmp_path: Path) -> None:
    """Only ServingBackendTransient may reach mediated keyword fallback."""

    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = _cfg(tmp_path, chroma)

    fallback_rows = [
        {
            "id": "kw-1",
            "metadata": {"title": "keyword hit"},
            "document": "keyword hit",
            "score": 0.5,
        }
    ]

    with patch("query.ollama_embed", return_value=[0.1] * 8), patch(
        "query._fallback_query_rows", return_value=fallback_rows
    ), patch(
        "rerank.rerank",
        side_effect=lambda _q, rows, _m, k: rows[:k],
    ):
        from query import query_units

        with patch(
            "serving_index_repository.open_serving_index_repository"
        ) as mock_open:
            repo = MagicMock()
            repo.query_units.side_effect = ServingBackendTransient("locked")
            repo.mediated_keyword_fallback.return_value = MediatedFallbackResult(
                rows=fallback_rows,
                collection_name="knowledge_units",
            )
            repo.legacy_store.return_value = MagicMock()
            cm = MagicMock()
            cm.__enter__.return_value = repo
            cm.__exit__.return_value = False
            mock_open.return_value = cm

            results = query_units("hello", top_k=1, cfg=cfg)

    assert results[0]["id"] == "kw-1"
    repo.mediated_keyword_fallback.assert_called_once()  # pylint: disable=no-member
    mock_open.assert_called()


def test_serving_authority_error_is_not_transient(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = _cfg(tmp_path, chroma)

    assert_serving_open_raises(
        cfg,
        ServingAuthorityError,
        patch_target="serving_index_repository.resolve_frozen_authority_vector",
        patch_side_effect=ServingAuthorityError("quarantined"),
    )


def test_runtime_boundary_inventory_records_reads(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = _cfg(tmp_path, chroma)

    before = runtime_serving_read_sites()
    with open_serving_index_repository(cfg) as repo:
        repo.count_units()
        repo.units_metadata()
    after = runtime_serving_read_sites()

    assert after >= before
    assert ("serving_index_repository.py", "count_units", "ChromaStore") in after
    assert ("serving_index_repository.py", "units_metadata", "ChromaStore") in after
