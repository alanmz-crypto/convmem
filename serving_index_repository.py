"""CG-2 serving repository — single authority boundary for production reads.

Every CLI, MCP, and query-layer serving operation opens this repository instead
of constructing :class:`chroma_store.ChromaStore` directly.  The request-frozen
authority vector is resolved once per operation; only
:class:`serving_authority.ServingBackendTransient` may trigger a mediated
readonly fallback that preserves the same authority classification.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from chroma_readonly import collection_metadata_rows
from chroma_store import (
    SUMMARIES,
    UNITS,
    ChromaStore,
    is_chroma_contention_error,
    is_superseded,
    open_chroma_for_read,
)
from config import load_config
from file_generation_store import FileGenerationStore
from serving_authority import (
    FrozenAuthorityVector,
    OwnerAuthorityMode,
    OwnerUnavailableError,
    ServingAuthorityError,
    ServingBackendIntegrityError,
    ServingBackendTransient,
    resolve_frozen_authority_vector,
)

_log = logging.getLogger("convmem.serving_index_repository")

# Serving-adjacent read sites registered at runtime for boundary inventory.
_RUNTIME_SERVING_READ_SITES: set[tuple[str, str, str]] = set()


def register_serving_read_site(relative_path: str, function: str, operation: str) -> None:
    _RUNTIME_SERVING_READ_SITES.add((relative_path, function, operation))


def runtime_serving_read_sites() -> frozenset[tuple[str, str, str]]:
    return frozenset(_RUNTIME_SERVING_READ_SITES)


@dataclass(frozen=True)
class MediatedFallbackResult:
    """Keyword fallback rows produced under the frozen authority vector."""

    rows: list[dict]
    collection_name: str


class ServingIndexRepository:
    """Request-scoped serving facade with a frozen authority vector."""

    def __init__(
        self,
        vector: FrozenAuthorityVector,
        store: ChromaStore | FileGenerationStore,
        *,
        cfg: Mapping[str, Any],
        mediated_fallback: Callable[..., list[dict]] | None = None,
    ) -> None:
        self._vector = vector
        self._cfg = dict(cfg)
        self._mediated_fallback = mediated_fallback
        self._legacy_store: ChromaStore | None = None
        self._generation_store: FileGenerationStore | None = None
        if isinstance(store, FileGenerationStore):
            self._generation_store = store
            self._legacy_store = store.raw_store
        else:
            self._legacy_store = store

    @property
    def authority_vector(self) -> FrozenAuthorityVector:
        return self._vector

    @property
    def chroma_dir(self) -> str:
        return self._vector.chroma_dir

    def legacy_store(self) -> ChromaStore:
        """Underlying Chroma store for ledger/evidence helpers not yet mediated."""

        return self._require_legacy_store()

    def close(self) -> None:
        if self._generation_store is not None:
            self._generation_store.close()
        elif self._legacy_store is not None:
            self._legacy_store.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _require_legacy_store(self) -> ChromaStore:
        if self._legacy_store is None:
            raise ServingBackendIntegrityError("serving repository has no Chroma store")
        return self._legacy_store

    def _active_store(self) -> ChromaStore | FileGenerationStore:
        if self._generation_store is not None and self._vector.active_generations():
            return self._generation_store
        return self._require_legacy_store()

    def query_units(self, embedding: list[float], n_results: int, **kwargs: Any) -> list[dict]:
        register_serving_read_site("serving_index_repository.py", "query_units", "raw.query")
        store = self._active_store()
        try:
            if isinstance(store, FileGenerationStore):
                return store.query_units(embedding, n_results, **kwargs)
            return store.query_units(embedding, n_results, **kwargs)
        except Exception as exc:
            if is_chroma_contention_error(exc):
                raise ServingBackendTransient(str(exc)) from exc
            raise

    def query_summaries(self, embedding: list[float], n_results: int, **kwargs: Any) -> list[dict]:
        register_serving_read_site(
            "serving_index_repository.py", "query_summaries", "raw.query"
        )
        store = self._active_store()
        try:
            if isinstance(store, FileGenerationStore):
                return store.query_summaries(embedding, n_results, **kwargs)
            return store.query_summaries(embedding, n_results, **kwargs)
        except Exception as exc:
            if is_chroma_contention_error(exc):
                raise ServingBackendTransient(str(exc)) from exc
            raise

    def count_units(self, *, include_superseded: bool = False) -> int:
        register_serving_read_site("serving_index_repository.py", "count_units", "ChromaStore")
        store = self._active_store()
        if isinstance(store, FileGenerationStore):
            return store.count_units(include_superseded=include_superseded)
        return self._require_legacy_store().count_units(
            include_superseded=include_superseded
        )

    def physical_count_units(self) -> int:
        """All persisted unit rows, including inactive generations and tombstones."""

        return self._require_legacy_store()._collection(UNITS).count()  # pylint: disable=protected-access

    def serving_count_units(self) -> int:
        """Rows authorized under the frozen authority vector."""

        return self.count_units(include_superseded=False)

    def count_summaries(self) -> int:
        register_serving_read_site("serving_index_repository.py", "count_summaries", "ChromaStore")
        store = self._active_store()
        if isinstance(store, FileGenerationStore):
            return store.count_summaries()
        return self._require_legacy_store().count_summaries()

    def physical_count_summaries(self) -> int:
        return self._require_legacy_store()._collection(SUMMARIES).count()  # pylint: disable=protected-access

    def serving_count_summaries(self) -> int:
        return self.count_summaries()

    def units_metadata(self, *, include_superseded: bool = False) -> list[dict]:
        register_serving_read_site("serving_index_repository.py", "units_metadata", "ChromaStore")
        store = self._active_store()
        if isinstance(store, FileGenerationStore):
            return store.units_metadata(include_superseded=include_superseded)
        return self._require_legacy_store().units_metadata(
            include_superseded=include_superseded
        )

    def mediated_keyword_fallback(
        self,
        collection_name: str,
        text: str,
        top_k: int,
        *,
        domain: str | None = None,
        site: str | None = None,
    ) -> MediatedFallbackResult:
        """Readonly sqlite keyword fallback under the frozen authority vector."""

        register_serving_read_site(
            "serving_index_repository.py",
            "mediated_keyword_fallback",
            "sqlite3.connect[chroma]",
        )
        if self._mediated_fallback is not None:
            rows = self._mediated_fallback(
                collection_name,
                text,
                top_k,
                domain=domain,
                site=site,
                cfg=self._cfg,
            )
            return MediatedFallbackResult(rows=rows, collection_name=collection_name)

        from domains import domain_matches, normalize_domain
        from query import _keyword_score, _unit_domain
        from site_filter import filter_results_by_site, normalize_site

        chroma_dir = self.chroma_dir
        domain_norm = normalize_domain(domain) if domain else None
        site_norm = normalize_site(site) if site else None
        rows = collection_metadata_rows(chroma_dir, collection_name)
        results: list[dict] = []
        for meta in rows:
            if collection_name == UNITS and is_superseded(meta):
                continue
            if site_norm and not filter_results_by_site([{"metadata": meta}], site_norm):
                continue
            if domain_norm:
                unit_domain = _unit_domain(meta)
                if unit_domain is None or not domain_matches(unit_domain, domain_norm):
                    continue
            score = _keyword_score(text, meta)
            if score <= 0:
                continue
            results.append(
                {
                    "id": meta.get("id", ""),
                    "metadata": meta,
                    "document": meta.get("document") or meta.get("title") or "",
                    "score": round(min(score / 6.0, 0.99), 4),
                }
            )
        results.sort(
            key=lambda r: (
                r.get("score", 0.0),
                len(str(r.get("metadata", {}).get("title", ""))),
            ),
            reverse=True,
        )
        return MediatedFallbackResult(rows=results[:top_k], collection_name=collection_name)


def _open_backing_store(vector: FrozenAuthorityVector) -> ChromaStore | FileGenerationStore:
    active = vector.active_generations()
    if active and not vector.legacy_global:
        return FileGenerationStore(
            vector.chroma_dir,
            active_generations=vector.active_generations,
            previous_generations=vector.previous_generations,
        )
    return open_chroma_for_read(vector.chroma_dir)


@contextmanager
def open_serving_index_repository(
    cfg: Mapping[str, Any] | None = None,
    *,
    mediated_fallback: Callable[..., list[dict]] | None = None,
) -> Iterator[ServingIndexRepository]:
    """Open the CG-2 serving boundary for one operation."""

    live_cfg = dict(cfg or load_config())
    vector = resolve_frozen_authority_vector(live_cfg)
    for state in vector.by_owner.values():
        if state.mode == OwnerAuthorityMode.FENCED_NO_POINTER:
            raise OwnerUnavailableError(
                f"owner {state.owner_digest} is fenced without a qualified pointer"
            )
        if state.mode == OwnerAuthorityMode.QUARANTINED:
            raise ServingAuthorityError(
                f"owner {state.owner_digest} is quarantined"
            )

    store: ChromaStore | FileGenerationStore | None = None
    try:
        store = _open_backing_store(vector)
        repo = ServingIndexRepository(
            vector,
            store,
            cfg=live_cfg,
            mediated_fallback=mediated_fallback,
        )
        yield repo
    finally:
        if store is not None:
            if isinstance(store, FileGenerationStore):
                store.close()
            else:
                store.close()


def query_units_with_authority(
    embedding: list[float],
    n_results: int,
    *,
    cfg: Mapping[str, Any] | None = None,
    domain: str | None = None,
    site: str | None = None,
    text: str | None = None,
    mediated_fallback: Callable[..., list[dict]] | None = None,
    **kwargs: Any,
) -> list[dict]:
    """Vector query through the serving boundary with mediated transient fallback."""

    live_cfg = dict(cfg or load_config())
    try:
        with open_serving_index_repository(
            live_cfg, mediated_fallback=mediated_fallback
        ) as repo:
            return repo.query_units(embedding, n_results, **kwargs)
    except ServingBackendTransient:
        if text is None:
            raise
        with open_serving_index_repository(
            live_cfg, mediated_fallback=mediated_fallback
        ) as repo:
            return repo.mediated_keyword_fallback(
                UNITS, text, n_results, domain=domain, site=site
            ).rows
