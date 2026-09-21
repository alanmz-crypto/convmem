"""Documentary indexing for repository_knowledge_v1 (no LLM summarize/distill)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from chroma_write_store import production_chroma_write_session
from llm import ollama_embed
from provenance import sha256_hex
from provenance_binding import (
    PROVENANCE_ASSERTION_ID_KEY,
    PROVENANCE_COMMITMENT_KEY,
    PROVENANCE_ENVELOPE_KEY,
    PROVENANCE_INTEGRITY_KEY,
    PROVENANCE_STATUS_KEY,
    attach_unit_provenance,
    build_ingest_envelope,
    envelope_from_unit,
    projection_metadata,
)
from repository_knowledge_scope import ADAPTER_CONTRACT_VERSION, SOURCE_TYPE, decide_path

_TOOL = "repository-knowledge"
_DOMAIN = "coding.tooling"
_AUTHOR = "repository-file"
_MAX_EMBED_CHARS = 8000
_RECIPE_ID = "repository-knowledge-packaging-v1"


class RepositoryKnowledgeIndexError(RuntimeError):
    """A repository-knowledge index could not complete safely."""


def make_repository_unit_id(
    *,
    relpath: str,
    locator: str,
    chunk_sha256: str,
    adapter_version: str,
) -> str:
    key = f"{relpath}\0{locator}\0{chunk_sha256}\0{adapter_version}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _existing_unchanged(existing: dict, existing_meta: dict, doc: str) -> bool:
    from ingest_dedupe import canonical_unit_text, unit_content_hash

    existing_hash = existing_meta.get("content_hash")
    if existing_hash:
        return existing_hash == unit_content_hash(doc)
    existing_doc = str(existing.get("document") or "")
    return canonical_unit_text(existing_doc) == canonical_unit_text(doc)


def _replay_unchanged(store, unit: dict, doc: str, embedding: list[float], meta: dict):
    from ingest_dedupe import unit_content_hash

    existing = store.get_unit(unit["id"])
    if not isinstance(existing, dict) or not existing.get("id"):
        return unit, doc, embedding, meta
    existing_meta = existing.get("metadata") or {}
    if not _existing_unchanged(existing, existing_meta, doc):
        return unit, doc, embedding, meta
    if not existing_meta.get(PROVENANCE_COMMITMENT_KEY):
        return unit, doc, embedding, meta
    envelope = envelope_from_unit(
        {PROVENANCE_ENVELOPE_KEY: existing_meta.get(PROVENANCE_ENVELOPE_KEY)}
    )
    if envelope is None:
        return unit, doc, embedding, meta
    replayed = dict(unit)
    new_hash = unit_content_hash(doc)
    replayed[PROVENANCE_ENVELOPE_KEY] = envelope
    replayed[PROVENANCE_COMMITMENT_KEY] = existing_meta[PROVENANCE_COMMITMENT_KEY]
    replayed[PROVENANCE_ASSERTION_ID_KEY] = existing_meta[PROVENANCE_ASSERTION_ID_KEY]
    replayed[PROVENANCE_STATUS_KEY] = existing_meta.get(
        PROVENANCE_STATUS_KEY, "self-consistent"
    )
    replayed[PROVENANCE_INTEGRITY_KEY] = existing_meta.get(
        PROVENANCE_INTEGRITY_KEY, "untrusted"
    )
    replayed["content_hash"] = new_hash
    replayed_meta = dict(meta)
    replayed_meta["content_hash"] = new_hash
    replayed_meta.update(projection_metadata(replayed))
    return replayed, doc, embedding, replayed_meta


def index_repository_knowledge_messages(  # pylint: disable=too-many-locals,too-many-arguments
    path: str,
    messages: list[dict],
    *,
    path_key: str,
    chroma_dir: str,
    embed_model: str,
    ollama_host: str,
    cfg: dict,
    verbose: bool = True,
    units_export: Path | None = None,
    unit_ids_out: set[str] | None = None,
) -> int:
    """Embed each repository chunk as a documentary knowledge unit."""
    decision = decide_path(path)
    if decision.state != "eligible" or decision.entry is None or decision.manifest is None:
        raise RepositoryKnowledgeIndexError(f"{decision.code}: {decision.detail}")
    src = Path(path)
    units_batch: list[tuple] = []
    for msg in messages:
        content = str(msg.get("content") or "").strip()
        if not content:
            continue
        locator = str(msg.get("locator") or "")
        label = str(msg.get("chunk_label") or src.name)
        relpath = str(msg.get("repo_relpath") or decision.relpath or src.name)
        chunk_sha = sha256_hex(content)
        unit_id = make_repository_unit_id(
            relpath=relpath,
            locator=locator,
            chunk_sha256=chunk_sha,
            adapter_version=ADAPTER_CONTRACT_VERSION,
        )
        summary = content if len(content) <= 500 else content[:497] + "…"
        doc = f"{relpath} {label} {locator}\n\n{content}"
        if len(doc) > _MAX_EMBED_CHARS:
            doc = doc[: _MAX_EMBED_CHARS - 1] + "…"
        try:
            embedding = ollama_embed(doc, model=embed_model, host=ollama_host)
        except Exception as exc:
            raise RepositoryKnowledgeIndexError(f"embedding failed for {locator}") from exc
        unit = {
            "id": unit_id,
            "type": "explanation",
            "title": label,
            "summary": summary,
            "keywords": [relpath, label[:40]],
            "source_path": path_key,
            "confidence": 1.0,
            "timestamp": None,
            "tool": _TOOL,
            "domain": _DOMAIN,
            "author_model": _AUTHOR,
            "verifier_model": None,
            "source_type": SOURCE_TYPE,
        }
        provider_payload = {
            "kind": "repository-knowledge-packaging",
            "content": str(msg.get("original_source_text") or content),
            "repo_relpath": relpath,
            "locator": locator,
            "file_sha256": msg.get("file_sha256") or decision.file_sha256,
            "manifest_sha256": msg.get("manifest_sha256") or decision.manifest.identity,
            "git_commit": msg.get("git_commit") or decision.git_commit,
            "adapter_version": ADAPTER_CONTRACT_VERSION,
            "content_class": msg.get("content_class") or decision.entry.content_class,
        }
        envelope = build_ingest_envelope(
            records=[msg],
            consumed_views=[content],
            source_identity=str(msg.get("source_identity") or path_key),
            locator_prefix=locator,
            source_type=SOURCE_TYPE,
            transformer_class="packaging",
            transformer_identity="repository_knowledge_index",
            transformer_version=ADAPTER_CONTRACT_VERSION,
            derivation_kind="packaging",
            producer_class="external",
            producer_assurance="claimed",
            selection_parameters={
                "locator": locator,
                "content_sha256": chunk_sha,
                "file_sha256": provider_payload["file_sha256"],
                "manifest_sha256": provider_payload["manifest_sha256"],
                "git_commit": provider_payload["git_commit"],
                "adapter_version": ADAPTER_CONTRACT_VERSION,
            },
            provider_payload=provider_payload,
            recipe_id=_RECIPE_ID,
            recipe_spec={
                "kind": _RECIPE_ID,
                "document_projection": "path-label-locator-content",
                "max_embedding_chars": _MAX_EMBED_CHARS,
            },
            output_locator=f"{path_key}#{locator}",
            output_value=unit,
        )
        unit = attach_unit_provenance(unit, envelope)
        meta = {
            "id": unit_id,
            "type": unit["type"],
            "title": label,
            "source_path": path_key,
            "confidence": 1.0,
            "timestamp": "",
            "tool": _TOOL,
            "start_offset": int(msg.get("start_line") or 0),
            "domain": _DOMAIN,
            "author_model": _AUTHOR,
            "verifier_model": "",
            "source_type": SOURCE_TYPE,
            "repo_relpath": relpath,
            "locator": locator,
            "file_sha256": provider_payload["file_sha256"] or "",
            "manifest_sha256": provider_payload["manifest_sha256"] or "",
            "git_commit": provider_payload["git_commit"] or "",
            "adapter_version": ADAPTER_CONTRACT_VERSION,
            "content_class": provider_payload["content_class"] or "",
            **projection_metadata(unit),
            "conversation_id": "",
            "session_id": "",
            "workspace_directory": "",
        }
        units_batch.append((unit, doc, embedding, meta))

    if not units_batch:
        return 0

    from purge_locks import export_flock_path, source_flock

    processed_log = cfg["index"]["processed_log"]
    export_path = (
        Path(units_export)
        if units_export is not None
        else Path(cfg["index"]["units_export"]).expanduser()
    )

    def _load_processed(log_path: str) -> dict:
        pp = Path(log_path)
        if not pp.is_file():
            return {}
        return json.loads(pp.read_text(encoding="utf-8") or "{}")

    def _path_excluded(processed: dict, key: str) -> bool:
        for entry in processed.values():
            if not isinstance(entry, dict) or not entry.get("excluded"):
                continue
            ep = entry.get("path")
            if ep and str(Path(ep).expanduser().resolve()) == key:
                return True
        return False

    later = decide_path(path)
    if (
        later.file_sha256 != decision.file_sha256
        or later.git_commit != decision.git_commit
        or later.manifest is None
        or later.manifest.identity != decision.manifest.identity
    ):
        raise RepositoryKnowledgeIndexError("identity changed before publication")

    with source_flock(cfg, path_key):
        processed = _load_processed(processed_log)
        if _path_excluded(processed, path_key):
            raise RepositoryKnowledgeIndexError("source excluded during repository-knowledge write")
        with production_chroma_write_session(entrypoint="repository_knowledge_index") as session:
            store = session.store
            cfg = session.live_cfg
            from ingest_dedupe import evaluate_ingest_batch, persist_ingest_dedupe

            replayed_batch = [_replay_unchanged(store, *row) for row in units_batch]
            dedupe = evaluate_ingest_batch(store, cfg, replayed_batch)
            for unit, doc, embedding, meta in dedupe.accepted:
                store.add_unit(unit["id"], doc, embedding, meta)
                export_path.parent.mkdir(parents=True, exist_ok=True)
                with export_flock_path(export_path):
                    with open(export_path, "a", encoding="utf-8") as handle:
                        handle.write(json.dumps(unit, ensure_ascii=False) + "\n")
            if unit_ids_out is not None:
                unit_ids_out.update(row[0]["id"] for row in dedupe.accepted)
            persist_ingest_dedupe(cfg, dedupe)

    if verbose:
        print(
            f"  [repository-knowledge] {src.name}: {len(dedupe.accepted)} chunk units "
            f"({len(dedupe.exact_suppressions)} exact suppressed, "
            f"{len(dedupe.semantic_candidates)} semantic candidates)"
        )
    return len(dedupe.accepted)
