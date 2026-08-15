"""Helpers for patching the CG-2 serving repository in unit tests."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from serving_authority import ServingBackendTransient
from serving_index_repository import MediatedFallbackResult


def _serving_repo_from_store(store: MagicMock) -> MagicMock:
    repo = MagicMock()
    repo.query_units = store.query_units
    repo.query_summaries = store.query_summaries
    repo.legacy_store.return_value = store
    repo.count_units = store.count_units
    repo.count_summaries = store.count_summaries
    repo.units_metadata = store.units_metadata
    repo.close = MagicMock(side_effect=store.close)

    def mediated_keyword_fallback(
        collection_name: str,
        text: str,
        top_k: int,
        **_kwargs: object,
    ) -> MediatedFallbackResult:
        rows = store.query_units(text, top_k) if collection_name == "knowledge_units" else []
        return MediatedFallbackResult(rows=rows, collection_name=collection_name)

    repo.mediated_keyword_fallback = mediated_keyword_fallback
    return repo


@contextmanager
def serving_repo_context(store: MagicMock):
    repo = _serving_repo_from_store(store)
    try:
        yield repo
    finally:
        repo.close()


def patch_open_serving_index_repository(store: MagicMock):
    def _open(*_args, **_kwargs):
        return serving_repo_context(store)

    return patch(
        "serving_index_repository.open_serving_index_repository",
        _open,
    )


def patch_query_serving(store: MagicMock):
    return patch_open_serving_index_repository(store)


def patch_query_serving_transient_fallback(store: MagicMock, fallback_rows: list[dict]):
    repo = _serving_repo_from_store(store)
    repo.query_units.side_effect = ServingBackendTransient("contention")
    repo.query_summaries.side_effect = ServingBackendTransient("contention")

    def mediated_keyword_fallback(
        collection_name: str,
        _text: str,
        _top_k: int,
        **_kwargs: object,
    ) -> MediatedFallbackResult:
        return MediatedFallbackResult(rows=fallback_rows, collection_name=collection_name)

    repo.mediated_keyword_fallback = mediated_keyword_fallback

    @contextmanager
    def _cm(*_args, **_kwargs):
        yield repo

    return patch(
        "serving_index_repository.open_serving_index_repository",
        side_effect=_cm,
    )


def patch_ask_serving(store: MagicMock):
    return patch_open_serving_index_repository(store)
