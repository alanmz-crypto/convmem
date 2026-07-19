"""Embed-only shadow builder: manifest/result split, metadata lifecycle, row-safe resume."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from eval_corpus.io_atomic import atomic_write_json, sha256_file
from eval_corpus.reconstruct import normalized_shadow_metadata

EmbedFn = Callable[[str], list[float]]

UNITS_COLLECTION = "knowledge_units"


@dataclass
class BuildPaths:
    chroma_dir: Path
    manifest_path: Path
    result_path: Path
    journal_path: Path


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_build_manifest(path: Path | str, manifest: dict[str, Any]) -> str:
    """Write immutable pre-build manifest (must not contain its own sha). Return sha256."""
    banned = {"build_manifest_sha256", "sha256", "self_sha256"}
    if banned & set(manifest):
        raise ValueError("build-manifest must not contain its own hash fields")
    atomic_write_json(path, manifest, indent=2, sort_keys=True)
    return sha256_file(path)


def write_build_result(path: Path | str, result: dict[str, Any]) -> None:
    """Post-build result; may reference build_manifest_sha256; must not self-hash."""
    if "build_result_sha256" in result or "self_sha256" in result:
        raise ValueError("build-result must not contain its own sha field")
    atomic_write_json(path, result, indent=2, sort_keys=True)


def collection_metadata_from_manifest(
    manifest: dict[str, Any],
    *,
    manifest_sha256: str,
) -> dict[str, Any]:
    """Scalar-only collection metadata bound at create-once time."""
    return {
        "hnsw:space": "cosine",
        "convmem:schema_version": str(manifest.get("schema_version") or "1"),
        "convmem:embed_provider": str(manifest.get("embed_provider") or "ollama"),
        "convmem:embed_model": str(manifest["embed_model"]),
        "convmem:embed_model_digest": str(manifest.get("embed_model_digest") or ""),
        "convmem:embed_dimensions": int(manifest["embed_dimensions"]),
        "convmem:unit_corpus_fingerprint": str(manifest["unit_corpus_fingerprint"]),
        "convmem:unit_count": int(manifest["unit_count"]),
        "convmem:source_capture_fingerprint": str(
            manifest.get("source_capture_fingerprint") or ""
        ),
        "convmem:build_manifest_sha256": manifest_sha256,
        "convmem:batch_size": int(manifest.get("batch_size") or 1),
        "convmem:repo_commit": str(manifest.get("repo_commit") or ""),
        "convmem:build_timestamp": str(manifest.get("build_timestamp") or ""),
    }


def verify_collection_metadata_for_resume(
    stored: dict[str, Any],
    *,
    embed_model: str,
    unit_corpus_fingerprint: str,
    embed_dimensions: int,
    build_manifest_sha256: str,
) -> list[str]:
    """Return list of mismatch reasons (empty = ok)."""
    errors: list[str] = []
    checks = {
        "convmem:embed_model": str(embed_model),
        "convmem:unit_corpus_fingerprint": str(unit_corpus_fingerprint),
        "convmem:build_manifest_sha256": str(build_manifest_sha256),
    }
    for key, expected in checks.items():
        got = str(stored.get(key) or "")
        if got != expected:
            errors.append(f"{key}: got {got!r} expected {expected!r}")
    try:
        if int(stored.get("convmem:embed_dimensions")) != int(embed_dimensions):
            errors.append(
                "convmem:embed_dimensions: got "
                f"{stored.get('convmem:embed_dimensions')!r} expected {embed_dimensions!r}"
            )
    except (TypeError, ValueError):
        errors.append(
            f"convmem:embed_dimensions: invalid {stored.get('convmem:embed_dimensions')!r}"
        )
    return errors


def row_content_hash(document: str, metadata: dict[str, Any]) -> str:
    payload = {"document": document, "metadata": metadata}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def expected_row_from_package_unit(unit: dict) -> tuple[str, dict[str, Any], str]:
    doc = str(unit["document"])
    meta = normalized_shadow_metadata(unit)
    return doc, meta, row_content_hash(doc, meta)


def plan_resume_adds(
    package_by_id: dict[str, dict],
    existing_rows: dict[str, dict],
) -> tuple[list[str], list[str], list[str]]:
    """Return (skip_ids, add_ids, error_messages).

    existing_rows: id -> {document, metadata}
    """
    errors: list[str] = []
    skip: list[str] = []

    for eid, row in existing_rows.items():
        if eid not in package_by_id:
            errors.append(f"reject foreign id absent from package: {eid}")
            continue
        exp_doc, exp_meta, exp_hash = expected_row_from_package_unit(package_by_id[eid])
        got_doc = str(row.get("document") or "")
        got_meta = dict(row.get("metadata") or {})
        got_hash = row_content_hash(got_doc, got_meta)
        if got_doc != exp_doc or got_hash != exp_hash or got_meta != exp_meta:
            errors.append(f"document/metadata mismatch for id {eid}")
            continue
        skip.append(eid)

    if errors:
        return skip, [], errors

    add = [uid for uid in package_by_id if uid not in existing_rows]
    return skip, add, []


def assert_complete_id_set(package_ids: set[str], store_ids: set[str]) -> None:
    if package_ids != store_ids:
        missing = sorted(package_ids - store_ids)
        extra = sorted(store_ids - package_ids)
        raise RuntimeError(
            f"ID-set inequality: missing={missing[:5]} extra={extra[:5]} "
            f"(missing_n={len(missing)} extra_n={len(extra)})"
        )


def package_units_by_id(units: list[dict]) -> dict[str, dict]:
    return {str(u["id"]): u for u in units}


def _read_existing_rows(collection) -> dict[str, dict]:
    res = collection.get(include=["documents", "metadatas"])
    ids = res.get("ids") or []
    docs = res.get("documents") or []
    metas = res.get("metadatas") or []
    out: dict[str, dict] = {}
    for uid, doc, meta in zip(ids, docs, metas):
        out[str(uid)] = {"document": doc or "", "metadata": dict(meta or {})}
    return out


def _append_journal(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    # Append-only with fsync of the file after write (crash-safe enough for resume hints).
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        import os

        os.fsync(f.fileno())


def run_shadow_build(
    *,
    units: list[dict],
    chroma_dir: Path | str,
    manifest: dict[str, Any],
    embed_fn: EmbedFn,
    batch_size: int = 8,
    resume: bool = False,
    collection_name: str = UNITS_COLLECTION,
    manifest_path: Path | str | None = None,
    result_path: Path | str | None = None,
    journal_path: Path | str | None = None,
) -> dict[str, Any]:
    """Embed-only shadow build with injectable ``embed_fn`` (no live model required).

    Creates the collection once with full ``collection_metadata_from_manifest`` on
    first build; resume verifies collection metadata + row-safe skip/add planning.
    """
    import chromadb

    chroma_dir = Path(chroma_dir).expanduser()
    chroma_dir.mkdir(parents=True, exist_ok=True)
    paths = BuildPaths(
        chroma_dir=chroma_dir,
        manifest_path=Path(manifest_path or (chroma_dir.parent / "build-manifest.json")),
        result_path=Path(result_path or (chroma_dir.parent / "build-result.json")),
        journal_path=Path(journal_path or (chroma_dir.parent / "build-journal.jsonl")),
    )

    package = package_units_by_id(units)
    if int(manifest.get("unit_count") or 0) != len(package):
        raise ValueError(
            f"manifest unit_count {manifest.get('unit_count')!r} != package {len(package)}"
        )

    manifest_sha = write_build_manifest(paths.manifest_path, manifest)
    col_meta = collection_metadata_from_manifest(manifest, manifest_sha256=manifest_sha)

    client = chromadb.PersistentClient(path=str(chroma_dir))
    existing_names = {c.name for c in client.list_collections()}
    if collection_name in existing_names:
        col = client.get_collection(collection_name)
        stored = dict(col.metadata or {})
        errs = verify_collection_metadata_for_resume(
            stored,
            embed_model=str(manifest["embed_model"]),
            unit_corpus_fingerprint=str(manifest["unit_corpus_fingerprint"]),
            embed_dimensions=int(manifest["embed_dimensions"]),
            build_manifest_sha256=manifest_sha,
        )
        if errs:
            raise RuntimeError("collection metadata resume guard failed: " + "; ".join(errs))
        if not resume:
            raise RuntimeError(
                f"collection {collection_name!r} already exists; pass resume=True to continue"
            )
    else:
        # Chroma requires str/int/float/bool metadata values.
        create_meta = {
            k: (v if isinstance(v, (str, int, float, bool)) else str(v))
            for k, v in col_meta.items()
        }
        col = client.get_or_create_collection(name=collection_name, metadata=create_meta)

    existing_rows = _read_existing_rows(col)
    skip, add, errors = plan_resume_adds(package, existing_rows)
    if errors:
        raise RuntimeError("row-safe resume rejected: " + "; ".join(errors))

    dims = int(manifest["embed_dimensions"])
    added = 0
    for i in range(0, len(add), max(1, batch_size)):
        batch_ids = add[i : i + max(1, batch_size)]
        docs: list[str] = []
        metas: list[dict] = []
        embeddings: list[list[float]] = []
        for uid in batch_ids:
            unit = package[uid]
            doc = str(unit["document"])
            meta = normalized_shadow_metadata(unit)
            emb = embed_fn(doc)
            if len(emb) != dims:
                raise ValueError(
                    f"embed_fn returned dim {len(emb)} for id {uid}; expected {dims}"
                )
            docs.append(doc)
            metas.append(meta)
            embeddings.append(emb)
        col.add(ids=batch_ids, documents=docs, metadatas=metas, embeddings=embeddings)
        added += len(batch_ids)
        _append_journal(
            paths.journal_path,
            {
                "ts": _now(),
                "event": "batch_add",
                "ids": batch_ids,
                "added_total": added,
            },
        )

    final_ids = set(_read_existing_rows(col))
    assert_complete_id_set(set(package), final_ids)

    result = {
        "status": "OK",
        "build_manifest_sha256": manifest_sha,
        "unit_corpus_fingerprint": str(manifest["unit_corpus_fingerprint"]),
        "embed_model": str(manifest["embed_model"]),
        "embed_dimensions": dims,
        "unit_count": len(package),
        "skipped_count": len(skip),
        "added_count": added,
        "collection_name": collection_name,
        "chroma_dir": str(chroma_dir),
        "finished_at": _now(),
    }
    write_build_result(paths.result_path, result)
    return result
