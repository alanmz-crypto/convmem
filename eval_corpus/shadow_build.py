"""Embed-only shadow builder: provenance, write-once manifest, row-safe resume."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from eval_corpus.adjudicate import verify_corpus_acceptance_hashes
from eval_corpus.fingerprint import corpus_fingerprint_hex, package_sha256_hex
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


def chroma_safe_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """Chroma accepts only scalar metadata values."""
    out: dict[str, Any] = {}
    for k, v in meta.items():
        if isinstance(v, list):
            out[k] = " ".join(str(x) for x in v)
        elif isinstance(v, (str, int, float, bool)) or v is None:
            if v is None:
                continue
            out[k] = v
        else:
            out[k] = str(v)
    return out


def write_build_manifest(path: Path | str, manifest: dict[str, Any]) -> str:
    """Write-once build-manifest. Divergent overwrite refused."""
    path = Path(path)
    banned = {"build_manifest_sha256", "sha256", "self_sha256"}
    if banned & set(manifest):
        raise ValueError("build-manifest must not contain its own hash fields")
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        if existing != payload:
            raise RuntimeError(
                f"build-manifest write-once violation: {path} already exists with different content"
            )
        return sha256_file(path)
    atomic_write_json(path, manifest, indent=2, sort_keys=True)
    return sha256_file(path)


def write_build_result(path: Path | str, result: dict[str, Any]) -> None:
    if "build_result_sha256" in result or "self_sha256" in result:
        raise ValueError("build-result must not contain its own sha field")
    atomic_write_json(path, result, indent=2, sort_keys=True)


def collection_metadata_from_manifest(
    manifest: dict[str, Any],
    *,
    manifest_sha256: str,
    package_sha256: str | None = None,
) -> dict[str, Any]:
    pkg = str(
        package_sha256
        if package_sha256 is not None
        else (manifest.get("package_sha256") or "")
    )
    return {
        "hnsw:space": "cosine",
        "convmem:schema_version": str(manifest.get("schema_version") or "1"),
        "convmem:embed_provider": str(manifest.get("embed_provider") or "ollama"),
        "convmem:embed_model": str(manifest["embed_model"]),
        "convmem:embed_model_digest": str(manifest.get("embed_model_digest") or ""),
        "convmem:embed_dimensions": int(manifest["embed_dimensions"]),
        "convmem:unit_corpus_fingerprint": str(manifest["unit_corpus_fingerprint"]),
        "convmem:package_sha256": pkg,
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
    package_sha256: str,
    batch_size: int,
) -> list[str]:
    errors: list[str] = []
    checks = {
        "convmem:embed_model": str(embed_model),
        "convmem:unit_corpus_fingerprint": str(unit_corpus_fingerprint),
        "convmem:build_manifest_sha256": str(build_manifest_sha256),
        "convmem:package_sha256": str(package_sha256),
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
    try:
        if int(stored.get("convmem:batch_size")) != int(batch_size):
            errors.append(
                "convmem:batch_size: got "
                f"{stored.get('convmem:batch_size')!r} expected {batch_size!r}"
            )
    except (TypeError, ValueError):
        errors.append(f"convmem:batch_size: invalid {stored.get('convmem:batch_size')!r}")
    return errors


def row_content_hash(document: str, metadata: dict[str, Any]) -> str:
    payload = {"document": document, "metadata": metadata}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def expected_row_from_package_unit(unit: dict) -> tuple[str, dict[str, Any], str]:
    doc = str(unit["document"])
    meta = chroma_safe_metadata(normalized_shadow_metadata(unit))
    return doc, meta, row_content_hash(doc, meta)


def plan_resume_adds(
    package_by_id: dict[str, dict],
    existing_rows: dict[str, dict],
) -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    skip: list[str] = []

    for eid, row in existing_rows.items():
        if eid not in package_by_id:
            errors.append(f"reject foreign id absent from package: {eid}")
            continue
        exp_doc, exp_meta, exp_hash = expected_row_from_package_unit(package_by_id[eid])
        got_doc = str(row.get("document") or "")
        got_meta = chroma_safe_metadata(dict(row.get("metadata") or {}))
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
    out: dict[str, dict] = {}
    for u in units:
        uid = str(u.get("id") or "").strip()
        if not uid:
            raise ValueError("package unit missing id")
        if uid in out:
            raise ValueError(f"duplicate package id: {uid}")
        out[uid] = u
    return out


def verify_package_against_manifest(units: list[dict], manifest: dict[str, Any]) -> str:
    """Recompute package SHA + fingerprint; compare to manifest. Return package SHA."""
    package = package_units_by_id(units)
    if int(manifest.get("unit_count") or 0) != len(package):
        raise ValueError(
            f"manifest unit_count {manifest.get('unit_count')!r} != package {len(package)}"
        )
    fp = corpus_fingerprint_hex(list(package.values()))
    pkg_sha = package_sha256_hex(list(package.values()))
    if str(manifest.get("unit_corpus_fingerprint") or "") != fp:
        raise ValueError("unit_corpus_fingerprint mismatch vs recomputed package")
    if str(manifest.get("package_sha256") or "") and str(manifest.get("package_sha256")) != pkg_sha:
        raise ValueError("package_sha256 mismatch vs recomputed package")
    return pkg_sha


def collection_reuse_allowed(stored: dict[str, Any], *, expected: dict[str, Any]) -> list[str]:
    """Collection resume identities only (not comparison reuse)."""
    return verify_collection_metadata_for_resume(
        stored,
        embed_model=str(expected["embed_model"]),
        unit_corpus_fingerprint=str(expected["unit_corpus_fingerprint"]),
        embed_dimensions=int(expected["embed_dimensions"]),
        build_manifest_sha256=str(expected["build_manifest_sha256"]),
        package_sha256=str(expected["package_sha256"]),
        batch_size=int(expected["batch_size"]),
    )


def comparison_reuse_allowed(
    *,
    prior: dict[str, Any],
    current: dict[str, Any],
    run_manifest_permits: bool,
) -> list[str]:
    """Comparison reuse requires full identity match + run-manifest permission."""
    if not run_manifest_permits:
        return ["run-manifest does not permit comparison_reuse"]
    keys = (
        "unit_corpus_fingerprint",
        "package_sha256",
        "embed_model",
        "embed_model_digest",
        "embed_dimensions",
        "query_set_sha256",
        "enrichment_sha256",
        "config_identity_sha256",
    )
    errors: list[str] = []
    for k in keys:
        if str(prior.get(k) or "") != str(current.get(k) or ""):
            errors.append(f"comparison reuse mismatch at {k}")
    return errors


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
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        import os

        os.fsync(f.fileno())


def run_shadow_build(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    units: list[dict],
    chroma_dir: Path | str,
    manifest: dict[str, Any],
    embed_fn: EmbedFn,
    batch_size: int | None = None,
    resume: bool = False,
    collection_name: str = UNITS_COLLECTION,
    manifest_path: Path | str | None = None,
    result_path: Path | str | None = None,
    journal_path: Path | str | None = None,
    capture_dir: Path | str | None = None,
    require_corpus_acceptance: bool = False,
) -> dict[str, Any]:
    """Embed-only shadow build with injectable ``embed_fn``."""
    import chromadb

    if require_corpus_acceptance:
        if capture_dir is None:
            raise ValueError("capture_dir required when require_corpus_acceptance")
        errs = verify_corpus_acceptance_hashes(Path(capture_dir))
        if errs:
            raise RuntimeError("corpus acceptance revalidation failed: " + "; ".join(errs))

    package_sha = verify_package_against_manifest(units, manifest)
    package = package_units_by_id(units)

    recorded_batch = int(manifest.get("batch_size") or 1)
    runtime_batch = recorded_batch if batch_size is None else int(batch_size)
    if runtime_batch != recorded_batch:
        raise ValueError(
            f"runtime batch_size {runtime_batch} != manifest batch_size {recorded_batch}"
        )

    chroma_dir = Path(chroma_dir).expanduser()
    chroma_dir.mkdir(parents=True, exist_ok=True)
    paths = BuildPaths(
        chroma_dir=chroma_dir,
        manifest_path=Path(manifest_path or (chroma_dir.parent / "build-manifest.json")),
        result_path=Path(result_path or (chroma_dir.parent / "build-result.json")),
        journal_path=Path(journal_path or (chroma_dir.parent / "build-journal.jsonl")),
    )

    t0 = time.perf_counter()
    manifest_sha = write_build_manifest(paths.manifest_path, manifest)
    col_meta = collection_metadata_from_manifest(
        manifest, manifest_sha256=manifest_sha, package_sha256=package_sha
    )

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
            package_sha256=package_sha,
            batch_size=recorded_batch,
        )
        if errs:
            raise RuntimeError("collection metadata resume guard failed: " + "; ".join(errs))
        if not resume:
            raise RuntimeError(
                f"collection {collection_name!r} already exists; pass resume=True to continue"
            )
    else:
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
    for i in range(0, len(add), max(1, runtime_batch)):
        batch_ids = add[i : i + max(1, runtime_batch)]
        docs: list[str] = []
        metas: list[dict] = []
        embeddings: list[list[float]] = []
        for uid in batch_ids:
            unit = package[uid]
            doc = str(unit["document"])
            meta = chroma_safe_metadata(normalized_shadow_metadata(unit))
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
            {"ts": _now(), "event": "batch_add", "ids": batch_ids, "added_total": added},
        )

    final_ids = set(_read_existing_rows(col))
    assert_complete_id_set(set(package), final_ids)

    elapsed = max(time.perf_counter() - t0, 1e-9)
    units_per_sec = len(package) / elapsed
    result = {
        "status": "OK",
        "build_manifest_sha256": manifest_sha,
        "unit_corpus_fingerprint": str(manifest["unit_corpus_fingerprint"]),
        "package_sha256": package_sha,
        "embed_model": str(manifest["embed_model"]),
        "embed_dimensions": dims,
        "batch_size": recorded_batch,
        "unit_count": len(package),
        "skipped_count": len(skip),
        "added_count": added,
        "collection_name": collection_name,
        "chroma_dir": str(chroma_dir),
        "elapsed_sec": round(elapsed, 6),
        "units_per_sec": round(units_per_sec, 6),
        "finished_at": _now(),
    }
    write_build_result(paths.result_path, result)
    return result
