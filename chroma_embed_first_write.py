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

Nothing is remembered between calls: neither what a collection holds nor what it records.
Another session can empty a collection, drop and recreate it with another model, or change
its metadata in place, so both are read from the collection at the moment of the write (and
again inside the write guard, after it may have reloaded the client). A second process can
still change the collection between that read and the write; production sessions hold the
index write lock, which is what serialises writers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from chromadb.errors import NotFoundError

from chroma_embed_model_names import same_embed_model
from chroma_store import EMBED_MODEL_KEY, EmbedIdentityError, normalize_embed_model

if TYPE_CHECKING:
    from chroma_store import ChromaStore


def require_first_vector_matches(store: "ChromaStore", name: str, embeddings: Any) -> None:
    """Raise ``EmbedIdentityError`` when the first vector contradicts what ``name`` records."""
    if embeddings is None or len(embeddings) == 0:
        return
    made_by = {normalize_embed_model(getattr(v, "embed_model", None)) for v in embeddings} - {None}
    if not made_by:
        return
    try:
        collection = store.client.get_collection(name=name)
    except NotFoundError:
        collection, stamped = None, store.embed_model  # what the write about to happen would stamp
    else:
        stamped = normalize_embed_model((collection.metadata or {}).get(EMBED_MODEL_KEY))
    if stamped is None or all(same_embed_model(model, stamped) for model in made_by):
        return  # nothing recorded, or nothing conflicts: no need to look at what it holds
    if collection is not None and collection.count() > 0:
        return  # not a first write
    raise EmbedIdentityError(
        f"refusing to store a vector made by {sorted(made_by)} as the first vector of "
        f"{name!r}, which records {stamped!r}: the configured model changed after it "
        "was embedded, so re-run the write"
    )
