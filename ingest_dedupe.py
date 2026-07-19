"""Ingestion-time exact suppression and semantic duplicate candidate detection."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_unit_text(document: str) -> str:
    """Normalize formatting only; preserve case and punctuation for exactness."""
    return " ".join(str(document or "").split())


def unit_content_hash(document: str) -> str:
    return hashlib.sha256(canonical_unit_text(document).encode("utf-8")).hexdigest()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@dataclass
class IngestDedupeResult:
    accepted: list[tuple] = field(default_factory=list)
    exact_suppressions: list[dict] = field(default_factory=list)
    semantic_candidates: list[dict] = field(default_factory=list)


def _semantic_record(
    *,
    existing_id: str,
    new_id: str,
    similarity: float,
    existing_meta: dict,
    new_meta: dict,
) -> dict:
    return {
        "id_a": existing_id,
        "id_b": new_id,
        "similarity": round(similarity, 4),
        "title_a": existing_meta.get("title"),
        "title_b": new_meta.get("title"),
        "domain": new_meta.get("domain") or existing_meta.get("domain") or "general",
        "queued_at": _now_iso(),
        "status": "pending",
        "source": "ingest",
    }


def evaluate_ingest_batch(  # pylint: disable=too-many-locals
    store, cfg: dict, units_batch: list[tuple]
) -> IngestDedupeResult:
    """Filter exact duplicates and collect review-only semantic candidates."""
    dedupe_cfg = cfg.get("ingest_dedup") or {}
    threshold = float(dedupe_cfg.get("semantic_similarity", 0.92))
    candidate_k = max(1, int(dedupe_cfg.get("candidate_k", 10)))
    max_semantic = max(1, int(dedupe_cfg.get("max_semantic_candidates_per_unit", 3)))
    result = IngestDedupeResult()
    accepted_rows: list[tuple] = []

    for unit, document, embedding, metadata in units_batch:
        content_hash = unit_content_hash(document)
        unit = dict(unit)
        metadata = dict(metadata)
        unit["content_hash"] = content_hash
        metadata["content_hash"] = content_hash

        existing = store.query_units(embedding, candidate_k)
        exact_match = None
        semantic: list[tuple[float, str, dict]] = []
        canonical = canonical_unit_text(document)

        for candidate in existing:
            candidate_id = str(candidate.get("id") or "")
            if not candidate_id or candidate_id == unit["id"]:
                continue
            candidate_meta = candidate.get("metadata") or {}
            same_hash = candidate_meta.get("content_hash") == content_hash
            same_text = canonical_unit_text(candidate.get("document") or "") == canonical
            if same_hash or same_text:
                exact_match = candidate_id
                break
            distance = candidate.get("distance")
            if distance is None:
                continue
            similarity = 1.0 - float(distance)
            if similarity >= threshold:
                semantic.append((similarity, candidate_id, candidate_meta))

        if exact_match is None:
            for accepted_unit, _accepted_doc, accepted_embedding, accepted_meta in accepted_rows:
                if accepted_meta.get("content_hash") == content_hash:
                    exact_match = accepted_unit["id"]
                    break
                similarity = _cosine(embedding, accepted_embedding)
                if similarity >= threshold:
                    semantic.append(
                        (similarity, accepted_unit["id"], accepted_meta)
                    )

        if exact_match is not None:
            result.exact_suppressions.append(
                {
                    "suppressed_id": unit["id"],
                    "matched_id": exact_match,
                    "content_hash": content_hash,
                    "source_path": metadata.get("source_path") or "",
                    "suppressed_at": _now_iso(),
                }
            )
            continue

        accepted = (unit, document, embedding, metadata)
        accepted_rows.append(accepted)
        result.accepted.append(accepted)
        seen_ids: set[str] = set()
        for similarity, candidate_id, candidate_meta in sorted(
            semantic, key=lambda item: item[0], reverse=True
        ):
            if candidate_id in seen_ids:
                continue
            seen_ids.add(candidate_id)
            result.semantic_candidates.append(
                _semantic_record(
                    existing_id=candidate_id,
                    new_id=unit["id"],
                    similarity=similarity,
                    existing_meta=candidate_meta,
                    new_meta=metadata,
                )
            )
            if len(seen_ids) >= max_semantic:
                break

    return result


def _append_jsonl(path: Path, rows: list[dict], *, unique_pairs: bool = False) -> int:
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        existing_pairs: set[tuple[str, str]] = set()
        if unique_pairs and path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pair = tuple(sorted((str(row.get("id_a") or ""), str(row.get("id_b") or ""))))
                if all(pair):
                    existing_pairs.add(pair)
        written = 0
        with path.open("a", encoding="utf-8") as handle:
            for row in rows:
                if unique_pairs:
                    pair = tuple(
                        sorted((str(row.get("id_a") or ""), str(row.get("id_b") or "")))
                    )
                    if not all(pair) or pair in existing_pairs:
                        continue
                    existing_pairs.add(pair)
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
                written += 1
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return written


def persist_ingest_dedupe(cfg: dict, result: IngestDedupeResult) -> dict:
    data_dir = Path(cfg["index"]["chroma_dir"]).expanduser().parent
    exact_written = _append_jsonl(
        data_dir / "ingest_duplicate_suppressions.jsonl",
        result.exact_suppressions,
    )
    semantic_written = _append_jsonl(
        data_dir / "dedupe_queue.jsonl",
        result.semantic_candidates,
        unique_pairs=True,
    )
    return {
        "exact_suppressed": exact_written,
        "semantic_candidates_queued": semantic_written,
    }
