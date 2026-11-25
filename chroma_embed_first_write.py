"""Refuse a collection's first vector when a different model made it than the collection records.

``llm.ollama_embed`` tags every vector with the model that made it, but a collection's
stamp comes from the configuration read when the writer opened, possibly after the
embedding. Writers also read before they write (dedupe queries, ``get_unit``), and a read
creates the collection already stamped. So a vector is compared with what the collection
records, or with what the store would stamp if it does not exist yet.

Only a collection's first vector is refused: once it holds vectors, a mismatch is left to
``convmem doctor`` (refusing it would stall indexing after any config model change).
Untagged vectors and collections that record nothing are not judged. This applies to every
store, not only ones configured with a model.

Nothing about what a collection *holds* is ever remembered. Whether it is empty is read at
the moment a vector conflicts with the recorded model, so another session emptying the
collection, or a write that failed after committing, cannot leave a stale answer behind. The
only thing cached per store is a collection's recorded model, which never changes. A second
process can still fill or empty the collection between this check and the write; production
sessions hold the index write lock, which is what serialises writers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from chromadb.errors import NotFoundError

from chroma_store import (
    EMBED_MODEL_KEY,
    EmbedIdentityError,
    normalize_embed_model,
    same_embed_model,
)

if TYPE_CHECKING:
    from chroma_store import ChromaStore


def _recorded_model(store: "ChromaStore", name: str) -> tuple[str | None, bool]:
    """(the model ``name`` records or would be stamped with, whether it exists)."""
    if name in store.recorded_stamps:
        return store.recorded_stamps[name], True
    try:
        collection = store.client.get_collection(name=name)
    except NotFoundError:
        return store.embed_model, False  # what the write about to happen would stamp
    stamp = normalize_embed_model((collection.metadata or {}).get(EMBED_MODEL_KEY))
    store.recorded_stamps[name] = stamp
    return stamp, True


def require_first_vector_matches(store: "ChromaStore", name: str, embeddings: Any) -> None:
    """Raise ``EmbedIdentityError`` when the first vector contradicts what ``name`` records."""
    if embeddings is None or len(embeddings) == 0:
        return
    made_by = {normalize_embed_model(getattr(v, "embed_model", None)) for v in embeddings} - {None}
    if not made_by:
        return
    stamped, exists = _recorded_model(store, name)
    if stamped is None or all(same_embed_model(model, stamped) for model in made_by):
        return  # nothing recorded, or nothing conflicts: no need to look at what it holds
    if exists and store.client.get_collection(name=name).count() > 0:
        return  # not a first write
    raise EmbedIdentityError(
        f"refusing to store a vector made by {sorted(made_by)} as the first vector of "
        f"{name!r}, which records {stamped!r}: the configured model changed after it "
        "was embedded, so re-run the write"
    )
