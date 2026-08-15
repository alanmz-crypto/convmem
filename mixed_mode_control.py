"""Authority-clean Chroma control collections for mixed-mode proof."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from chroma_store import ChromaStore, UNITS
from file_generation_store import FileGenerationStore
from mixed_mode_retrieval import assert_pinned_chroma_version


def build_authority_clean_control(
    source_chroma_dir: str | Path,
    control_chroma_dir: str | Path,
    *,
    active_generations: Callable[[], Mapping[str, str]],
    previous_generations: Callable[[], Mapping[str, str]] | None = None,
    collection_name: str = UNITS,
) -> dict[str, Any]:
    """Materialize a temporary collection containing only serving-authorized rows.

    The control uses the same cosine HNSW metadata and row embeddings as the
    mixed source so ANN divergence isolates filtering from approximation.
    """

    assert_pinned_chroma_version()
    source_path = Path(source_chroma_dir).expanduser()
    control_path = Path(control_chroma_dir).expanduser()
    control_path.mkdir(parents=True, exist_ok=True)
    previous = previous_generations or dict
    with FileGenerationStore(
        source_path,
        active_generations=active_generations,
        previous_generations=previous,
    ) as source_store:
        rows = source_store._get_rows(  # pylint: disable=protected-access
            collection_name, include_embeddings=True
        )
        source_col = source_store._store._collection(collection_name)  # pylint: disable=protected-access
        source_metadata = dict(source_col.metadata or {"hnsw:space": "cosine"})

    with ChromaStore(str(control_path), create_collections=True) as control_store:
        control_col = control_store.client.get_or_create_collection(
            name=collection_name,
            metadata=source_metadata,
        )
        if rows:
            ids = [str(row["id"]) for row in rows]
            documents = [str(row["document"]) for row in rows]
            embeddings = []
            metadatas = []
            for row in rows:
                embedding = row.get("embedding")
                if embedding is not None and hasattr(embedding, "tolist"):
                    embedding = embedding.tolist()
                embeddings.append(list(embedding))
                metadatas.append(dict(row["metadata"]))
            control_col.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )

    return {
        "schema": "convmem/authority-clean-control-v1",
        "source_chroma_dir": str(source_path),
        "control_chroma_dir": str(control_path),
        "collection_name": collection_name,
        "authorized_row_count": len(rows),
        "collection_metadata": source_metadata,
    }
