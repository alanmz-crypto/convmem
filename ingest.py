"""Ingest pipeline.

For each source file:
  - skip if its content hash is already in processed.json (idempotent)
  - parse -> canonical messages
  - chunk (size/overlap from config)
  - per chunk:
      summarize -> embed -> conversation_summaries  (fallback / --raw)
      distill   -> embed -> knowledge_units       (primary search, Step 5+)
"""

import fcntl
import hashlib
import json
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

from adapters.detect import detect_format, get_parser, TOOL_BY_FORMAT
from chroma_store import ChromaStore
from config import load_config
from distill import distill, normalize_unit
from llm import ollama_embed, summarize


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def load_processed(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"processed.json corrupt at {p}: {e}") from e


def save_processed(path: str, data: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(p)


def processed_lock_path(processed_path: str) -> Path:
    """Stable sidecar lock path (not processed.json — atomic replace changes inode)."""
    p = Path(processed_path)
    return p.with_name(p.name + ".lock")


@contextmanager
def _processed_lock(processed_path: str):
    """Exclusive advisory lock on the processed-state sidecar."""
    lock = processed_lock_path(processed_path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def mutate_processed(processed_path: str, mutator: Callable[[dict], None]) -> dict:
    """Lock, reload on-disk state, mutate, atomic-save, unlock.

    Hold only for read+mutate+write. Never across parse/LLM/embed/Chroma work.
    Always releases the lock on exception paths (via `_processed_lock`).
    """
    with _processed_lock(processed_path):
        data = load_processed(processed_path)
        mutator(data)
        save_processed(processed_path, data)
        return data


def chunk_messages(messages: list[dict], size: int, overlap: int) -> list[dict]:
    """Sliding-window chunks over a message list.

    Returns dicts with the message slice plus its start/end offsets.
    """
    if size <= 0:
        size = 60
    step = max(1, size - overlap)
    chunks = []
    i = 0
    n = len(messages)
    while i < n:
        window = messages[i : i + size]
        chunks.append(
            {
                "messages": window,
                "start_offset": i,
                "end_offset": i + len(window) - 1,
            }
        )
        if i + size >= n:
            break
        i += step
    return chunks


def render_chunk(messages: list[dict], total_budget: int = 10000) -> str:
    """Render a chunk for summarization within a bounded character budget.

    A per-message share of the budget is computed so the summarizer sees
    breadth across all turns in the chunk rather than a single huge
    head-truncated message.
    """
    if not messages:
        return ""
    per_msg = max(150, total_budget // len(messages))
    lines = []
    for m in messages:
        content = m["content"].strip()
        if len(content) > per_msg:
            content = content[:per_msg] + " […]"
        lines.append(f"{m['role']}: {content}")
    return "\n".join(lines)


def _chunk_date(messages: list[dict]) -> str:
    for m in messages:
        ts = m.get("timestamp")
        if ts:
            return str(ts)[:10]
    return ""


def _chunk_session_meta(messages: list[dict], path: str) -> dict:
    from open_source import _session_id_from_path

    conv_id = next(
        (m.get("conversation_id") for m in messages if m.get("conversation_id")), ""
    )
    session_id = next(
        (m.get("session_id") for m in messages if m.get("session_id")), ""
    ) or _session_id_from_path(path) or ""
    workspace = next(
        (m.get("workspace_directory") for m in messages if m.get("workspace_directory")),
        "",
    )
    source_type = next(
        (m.get("source_type") for m in messages if m.get("source_type")), ""
    )
    meta = {
        "conversation_id": conv_id or "",
        "session_id": session_id or "",
        "workspace_directory": workspace or "",
    }
    if source_type:
        meta["source_type"] = source_type
    return meta


def _files_from_inventory(inventory_path: str) -> list[dict]:
    records = []
    with open(inventory_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _processed_path_str(entry_path: str) -> str:
    return str(Path(entry_path).expanduser().resolve())


def _stored_hash_for_path(path_str: str, processed: dict) -> str | None:
    """Return processed.json key (content hash) for a resolved path, if any."""
    for key, entry in processed.items():
        if not isinstance(entry, dict) or entry.get("excluded"):
            continue
        ep = entry.get("path")
        if ep and _processed_path_str(ep) == path_str:
            return key
    return None


def _path_is_excluded(processed: dict, path_key: str) -> bool:
    for entry in processed.values():
        if not isinstance(entry, dict) or not entry.get("excluded"):
            continue
        ep = entry.get("path")
        if ep and _processed_path_str(ep) == path_key:
            return True
    return False


def _purge_stale_same_path(
    processed: dict,
    path_key: str,
    keep_hash: str,
    *,
    preserve_exclusions: bool = True,
) -> int:
    """Remove other same-path keys. Exclusions survive when preserve_exclusions=True."""
    removed = 0
    for key, entry in list(processed.items()):
        if key == keep_hash or not isinstance(entry, dict):
            continue
        ep = entry.get("path")
        if not ep or _processed_path_str(ep) != path_key:
            continue
        if preserve_exclusions and entry.get("excluded"):
            continue
        del processed[key]
        removed += 1
    return removed


def commit_processed_index_entry(
    processed_path: str,
    *,
    file_hash: str,
    path_key: str,
    chunks: int,
    units: int,
) -> bool:
    """Merge one file's index metadata under the processed-state lock.

    Reloads latest disk state; never writes a whole stale pre-index snapshot.
    Returns False when a path-based exclusion blocks the commit (exclusion kept).
    """
    result = {"committed": False}

    def mutator(data: dict) -> None:
        if _path_is_excluded(data, path_key):
            return
        existing = data.get(file_hash)
        if isinstance(existing, dict) and existing.get("excluded"):
            return
        data[file_hash] = {
            "path": path_key,
            "chunks": chunks,
            "units": units,
        }
        _purge_stale_same_path(data, path_key, file_hash, preserve_exclusions=True)
        result["committed"] = True

    mutate_processed(processed_path, mutator)
    return result["committed"]


def exclude_processed_path(
    processed_path: str,
    target: str,
    file_hash: str,
    reason: str = "",
    *,
    purged_at: str | None = None,
) -> None:
    """Mark a resolved path excluded under the processed-state lock.

    Canonicalizes path exclusion across content hashes: clears other active
    same-path exclusion markers, keeps one marker on ``file_hash``, and
    preserves the latest explicit reason (or carries forward a prior reason
    when re-excluding without a new reason). Optional ``purged_at`` stamps the
    surviving marker in the same transaction (purge path).
    """
    path_key = _processed_path_str(target)

    def mutator(data: dict) -> None:
        carried_reason = reason
        if not carried_reason:
            for entry in data.values():
                if not isinstance(entry, dict) or not entry.get("excluded"):
                    continue
                ep = entry.get("path")
                if ep and _processed_path_str(ep) == path_key:
                    prior = entry.get("exclude_reason") or ""
                    if prior:
                        carried_reason = prior

        for entry in data.values():
            if not isinstance(entry, dict) or not entry.get("excluded"):
                continue
            ep = entry.get("path")
            if ep and _processed_path_str(ep) == path_key:
                entry.pop("excluded", None)
                entry.pop("exclude_reason", None)
                entry.pop("purged_at", None)

        entry = data.get(file_hash, {})
        if not isinstance(entry, dict):
            entry = {}
        entry["path"] = path_key
        entry["excluded"] = True
        if carried_reason:
            entry["exclude_reason"] = carried_reason
        else:
            entry.pop("exclude_reason", None)
        if purged_at:
            entry["purged_at"] = purged_at
        else:
            entry.pop("purged_at", None)
        data[file_hash] = entry

    mutate_processed(processed_path, mutator)


def undo_exclude_processed_path(processed_path: str, target: str) -> bool:
    """Clear every active exclusion for one resolved path in one transaction.

    Returns True if at least one active marker was cleared. Other paths untouched.
    """
    path_key = _processed_path_str(target)
    found = {"ok": False}

    def mutator(data: dict) -> None:
        for entry in data.values():
            if not isinstance(entry, dict) or not entry.get("excluded"):
                continue
            ep = entry.get("path")
            if ep and _processed_path_str(ep) == path_key:
                entry.pop("excluded", None)
                entry.pop("exclude_reason", None)
                found["ok"] = True

    mutate_processed(processed_path, mutator)
    return found["ok"]


def watch_skip_reason(
    path: str | Path,
    *,
    processed: dict | None = None,
    file_hash: str | None = None,
) -> str | None:
    """Why watch should skip this file without opening Chroma. None = may ingest."""
    p = Path(path).expanduser().resolve()
    if processed is None:
        cfg = load_config()
        processed = load_processed(cfg["index"]["processed_log"])
    path_str = str(p)

    for entry in processed.values():
        if not isinstance(entry, dict) or not entry.get("excluded"):
            continue
        ep = entry.get("path")
        if ep and _processed_path_str(ep) == path_str:
            return "excluded"

    path_known_hash = _stored_hash_for_path(path_str, processed)
    if path_known_hash is not None:
        if file_hash is None:
            try:
                file_hash = sha256_file(str(p))
            except OSError:
                return "unreadable"
        if file_hash == path_known_hash:
            return "unchanged"
        return None

    if file_hash is None:
        try:
            file_hash = sha256_file(str(p))
        except OSError:
            return "unreadable"

    if file_hash in processed and processed[file_hash].get("excluded"):
        return "excluded"
    if file_hash in processed:
        return "unchanged"
    return None


def _deduplicate_units_export(export_path: Path) -> int:
    """Rewrite knowledge_units.jsonl keeping only the last occurrence of each unit ID.

    This prevents unbounded growth from repeated re-indexing. Returns lines removed.
    Holds the export flock for the full rewrite.
    """
    from purge_locks import export_flock_path

    if not export_path.is_file():
        return 0
    with export_flock_path(export_path):
        seen: dict[str, str] = {}  # unit_id -> json_line
        n_before = 0
        for line in export_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            n_before += 1
            try:
                rec = json.loads(stripped)
                uid = rec.get("id", "")
                if uid:
                    seen[uid] = stripped
            except json.JSONDecodeError:
                pass  # preserve unparseable lines
        if n_before == 0:
            return 0
        n_after = len(seen)
        if n_after >= n_before:
            return 0  # nothing to compact
        tmp = export_path.with_suffix(export_path.suffix + ".compact.tmp")
        tmp.write_text("\n".join(seen.values()) + "\n", encoding="utf-8")
        tmp.replace(export_path)
        return n_before - n_after


def _echo_neutralize_preview(
    preview: list, display_name: str, tombstone_tag: str, verbose: bool
) -> None:
    """Unconditional provenance echo before a supersede (neutralize) run.

    Guardrail for the neutralize-provenance-confirm standing check: a supersede
    cannot execute without the affected source, unit count, timestamp range,
    and tombstone tag being printed first. One line per logical file —
    --supersede runs at every handoff sync, so this must stay compact.
    """
    if not preview:
        return
    stamps = sorted(
        t[:10]
        for unit in preview
        for t in (unit.get("created_at"), unit.get("updated_at"))
        if t
    )
    span = f" ({stamps[0]}..{stamps[-1]})" if stamps else ""
    print(
        f"  [neutralize] {len(preview)} active units for {display_name}{span}"
        f" -> tombstone as {tombstone_tag}"
    )
    if verbose:
        sample = ", ".join(
            f"{u['id']} \"{u['title']}\"" if u.get("title") else str(u["id"])
            for u in preview[:5]
        )
        more = f" (+{len(preview) - 5} more)" if len(preview) > 5 else ""
        print(f"  [neutralize]   {sample}{more}")



def _commit_chunk_to_stores(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    cfg: dict,
    idx: dict,
    path_key: str,
    path: str,
    file_hash: str,
    chroma_dir: str,
    units_export: Path | None,
    doc_id: str,
    summary: str,
    summary_embedding: list,
    metadata: dict,
    units_to_add: list,
    verbose: bool,
) -> tuple[bool, int, int]:
    """Source/export-locked batch write. Returns (ok, n_indexed_delta, n_units_delta)."""
    from purge_locks import export_flock, source_flock

    with source_flock(cfg, path_key):
        processed = load_processed(idx["processed_log"])
        if _path_is_excluded(processed, path_key) or (
            file_hash in processed and processed[file_hash].get("excluded")
        ):
            if verbose:
                print(f"  [skip] excluded during batch-write {Path(path).name}")
            return False, 0, 0
        n_units = 0
        with ChromaStore(chroma_dir) as store:
            store.add_summary(doc_id, summary, summary_embedding, metadata)
            for unit, doc, unit_embedding, unit_meta in units_to_add:
                store.add_unit(unit["id"], doc, unit_embedding, unit_meta)
                if units_export:
                    units_export.parent.mkdir(parents=True, exist_ok=True)
                    with export_flock(cfg):
                        with open(units_export, "a", encoding="utf-8") as uf:
                            uf.write(json.dumps(unit) + "\n")
                n_units += 1
        return True, 1, n_units


def _index_inter_model_file(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    cfg: dict,
    idx: dict,
    path: str,
    path_key: str,
    file_hash: str,
    messages: list,
    models: dict,
    units_export: Path | None,
    force_file: str | None,
    supersede_on_reindex: bool,
    verbose: bool,
) -> tuple[bool, int]:
    """Index one inter-model doc. Returns (committed, n_units)."""
    from inter_model_index import index_inter_model_messages

    chroma_dir = idx["chroma_dir"]
    if force_file:
        with ChromaStore(chroma_dir) as store:
            tombstone_tag = f"{path_key}#{file_hash[:12]}"
            if supersede_on_reindex:
                _echo_neutralize_preview(
                    store.preview_supersede_for_source(path_key),
                    Path(path).name,
                    tombstone_tag,
                    verbose,
                )
                n_del = store.supersede_units_for_source(
                    path_key, superseded_by=tombstone_tag
                )
                if verbose and n_del:
                    print(
                        f"  [reindex] superseded {n_del} units for {Path(path).name}",
                    )
            else:
                n_del = store.delete_units_for_source(path_key)
                if verbose and n_del:
                    print(f"  [reindex] cleared {n_del} units for {Path(path).name}")
    try:
        n_units = index_inter_model_messages(
            path,
            messages,
            path_key=path_key,
            chroma_dir=chroma_dir,
            embed_model=models["embed_model"],
            ollama_host=models["ollama_host"],
            cfg=cfg,
            verbose=verbose,
            units_export=units_export if units_export else None,
        )
    except Exception as e:
        if verbose:
            print(f"  [skip] inter-model index failed {path}: {e}")
        return False, 0

    committed = commit_processed_index_entry(
        idx["processed_log"],
        file_hash=file_hash,
        path_key=path_key,
        chunks=0,
        units=n_units,
    )
    return committed, n_units


def _process_file_chunks(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    cfg: dict,
    idx: dict,
    path: str,
    path_key: str,
    file_hash: str,
    messages: list,
    models: dict,
    tool: str,
    chroma_dir: str,
    units_export: Path | None,
    chunk_size: int,
    overlap: int,
    min_confidence: float,
    verbose: bool,
) -> tuple[bool, int, int]:
    """Summarize/distill/embed unlocked, then locked batch writes.

    Returns (completed_without_exclusion_abort, chunks_indexed, units_indexed).
    """
    chunks = chunk_messages(messages, chunk_size, overlap)
    if verbose:
        print(f"  [index] {Path(path).name}  ({len(messages)} msgs, {len(chunks)} chunks)")

    n_indexed = 0
    n_units = 0
    chunk_date = ""
    for ch in chunks:
        text = render_chunk(ch["messages"])
        if not text.strip():
            continue
        chunk_date = _chunk_date(ch["messages"]) or chunk_date
        try:
            summary = summarize(
                text,
                model=models["summarize_model"],
                ollama_host=models["ollama_host"],
                deepseek_base_url=models.get(
                    "deepseek_base_url", "https://api.deepseek.com"
                ),
            )
            summary_embedding = ollama_embed(
                summary,
                model=models["embed_model"],
                host=models["ollama_host"],
            )
        except Exception as e:
            if verbose:
                print(f"    [warn] chunk {ch['start_offset']} summarize failed: {e}")
            continue

        try:
            raw_units = distill(
                text,
                model=models["distill_model"],
                ollama_host=models["ollama_host"],
                deepseek_base_url=models.get(
                    "deepseek_base_url", "https://api.deepseek.com"
                ),
            )
        except Exception as e:
            if verbose:
                print(f"    [warn] chunk {ch['start_offset']} distill failed: {e}")
            raw_units = []

        session_meta = _chunk_session_meta(ch["messages"], path)
        units_to_add: list[tuple] = []
        for unit_idx, raw in enumerate(raw_units):
            unit = normalize_unit(
                raw,
                source_path=path_key,
                tool=tool,
                date=chunk_date,
                min_confidence=min_confidence,
                author_model=models["distill_model"],
                start_offset=ch["start_offset"],
                unit_index=unit_idx,
            )
            if unit is None:
                continue
            doc = unit["summary"] + " " + " ".join(unit["keywords"])
            try:
                unit_embedding = ollama_embed(
                    doc,
                    model=models["embed_model"],
                    host=models["ollama_host"],
                )
            except Exception as e:
                if verbose:
                    print(f"    [warn] unit embed failed: {e}")
                continue
            unit_meta = {
                "id": unit["id"],
                "type": unit["type"],
                "title": unit["title"],
                "source_path": unit["source_path"],
                "confidence": unit["confidence"],
                "timestamp": unit["timestamp"] or "",
                "tool": unit["tool"],
                "start_offset": ch["start_offset"],
                "domain": unit["domain"],
                "author_model": unit["author_model"],
                "verifier_model": unit["verifier_model"] or "",
                **session_meta,
            }
            units_to_add.append((unit, doc, unit_embedding, unit_meta))

        doc_id = hashlib.sha256(
            f"{path_key}:{ch['start_offset']}".encode()
        ).hexdigest()
        metadata = {
            "source_path": path_key,
            "tool": tool,
            "date": _chunk_date(ch["messages"]),
            "message_count": len(ch["messages"]),
            "start_offset": ch["start_offset"],
            "end_offset": ch["end_offset"],
            **session_meta,
        }
        # Batch write only — parse/LLM/embed above hold no source/export locks (N17).
        ok, d_idx, d_units = _commit_chunk_to_stores(
            cfg=cfg,
            idx=idx,
            path_key=path_key,
            path=path,
            file_hash=file_hash,
            chroma_dir=chroma_dir,
            units_export=units_export if units_export else None,
            doc_id=doc_id,
            summary=summary,
            summary_embedding=summary_embedding,
            metadata=metadata,
            units_to_add=units_to_add,
            verbose=verbose,
        )
        if not ok:
            return False, n_indexed, n_units
        n_indexed += d_idx
        n_units += d_units
    return True, n_indexed, n_units


def _reindex_clear_existing(
    *,
    chroma_dir: str,
    path: str,
    path_key: str,
    file_hash: str,
    supersede_on_reindex: bool,
    verbose: bool,
) -> None:
    """Clear or supersede derived rows before force re-index of one file."""
    with ChromaStore(chroma_dir) as store:
        n_units_del = 0
        n_sum_del = 0
        tombstone_tag = f"{path_key}#{file_hash[:12]}"
        if supersede_on_reindex:
            # One echo per logical file: merge previews across the
            # path/path_key variants, deduped by unit id.
            merged: dict[str, dict] = {}
            for sp in dict.fromkeys([path, path_key]):
                for unit in store.preview_supersede_for_source(sp):
                    merged.setdefault(unit["id"], unit)
            _echo_neutralize_preview(
                list(merged.values()), Path(path).name, tombstone_tag, verbose
            )
        for sp in dict.fromkeys([path, path_key]):
            if supersede_on_reindex:
                n_units_del += store.supersede_units_for_source(
                    sp, superseded_by=tombstone_tag
                )
                # Summaries have no tombstone metadata yet — still hard-delete.
                n_sum_del += store.delete_summaries_for_source(sp)
            else:
                n_units_del += store.delete_units_for_source(sp)
                n_sum_del += store.delete_summaries_for_source(sp)
        if verbose and (n_units_del or n_sum_del):
            verb = "superseded" if supersede_on_reindex else "cleared"
            print(
                f"  [reindex] {verb} {n_units_del} units, "
                f"{n_sum_del} summaries for {Path(path).name}",
            )




def _index_one_file(  # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
    *,
    cfg: dict,
    idx: dict,
    path: str,
    parser,
    processed: dict,
    models: dict,
    units_export: Path | None,
    chunk_size: int,
    overlap: int,
    min_confidence: float,
    force_file: str | None,
    force_reindex: bool,
    supersede_on_reindex: bool,
    verbose: bool,
) -> tuple[str, int, int]:
    """Index one already-resolved source file. Returns (status, chunks, units).

    status:
      - ``ignored`` — unreadable or parse-failed (does not increment files_skipped)
      - ``skipped`` — excluded / unchanged / inter-model or commit exclusion
      - ``processed`` — durable commit succeeded
    """
    try:
        file_hash = sha256_file(path)
    except OSError as e:
        if verbose:
            print(f"  [skip] cannot read {path}: {e}")
        return "ignored", 0, 0

    path_key = str(Path(path).expanduser().resolve())

    if _path_is_excluded(processed, path_key) or (
        file_hash in processed and processed[file_hash].get("excluded")
    ):
        if verbose:
            print(f"  [skip] excluded {Path(path).name}")
        return "skipped", 0, 0

    if force_reindex and force_file:
        for key, entry in list(processed.items()):
            if (
                isinstance(entry, dict)
                and entry.get("path") == path_key
                and not entry.get("excluded")
            ):
                del processed[key]

    if force_file and not force_reindex:
        stale = _stored_hash_for_path(path_key, processed)
        if stale and stale != file_hash:
            del processed[stale]

    if not force_reindex:
        if file_hash in processed:
            if verbose:
                print(f"  [skip] unchanged {Path(path).name}")
            return "skipped", 0, 0

    fmt = detect_format(path)
    tool = TOOL_BY_FORMAT.get(fmt, fmt or "unknown")
    chroma_dir = idx["chroma_dir"]

    if force_file:
        _reindex_clear_existing(
            chroma_dir=chroma_dir,
            path=path,
            path_key=path_key,
            file_hash=file_hash,
            supersede_on_reindex=supersede_on_reindex,
            verbose=verbose,
        )

    try:
        messages = parser(path)
    except Exception as e:
        if verbose:
            print(f"  [skip] parse failed {path}: {e}")
        return "ignored", 0, 0

    if fmt == "inter_model_doc":
        committed, n_units = _index_inter_model_file(
            cfg=cfg,
            idx=idx,
            path=path,
            path_key=path_key,
            file_hash=file_hash,
            messages=messages,
            models=models,
            units_export=units_export,
            force_file=force_file,
            supersede_on_reindex=supersede_on_reindex,
            verbose=verbose,
        )
        if not committed:
            if verbose and n_units == 0:
                print(f"  [skip] inter-model index failed or excluded {Path(path).name}")
            elif verbose:
                print(f"  [skip] excluded during index {Path(path).name}")
            return "skipped", 0, 0
        return "processed", 0, n_units

    completed, n_indexed, n_units = _process_file_chunks(
        cfg=cfg,
        idx=idx,
        path=path,
        path_key=path_key,
        file_hash=file_hash,
        messages=messages,
        models=models,
        tool=tool,
        chroma_dir=chroma_dir,
        units_export=units_export,
        chunk_size=chunk_size,
        overlap=overlap,
        min_confidence=min_confidence,
        verbose=verbose,
    )
    if not completed:
        return "skipped", n_indexed, n_units

    committed = commit_processed_index_entry(
        idx["processed_log"],
        file_hash=file_hash,
        path_key=path_key,
        chunks=n_indexed,
        units=n_units,
    )
    if not committed:
        if verbose:
            print(f"  [skip] excluded during index {Path(path).name}")
        return "skipped", n_indexed, n_units
    return "processed", n_indexed, n_units


def index(
    force_file: str | None = None,
    limit_files: int | None = None,
    verbose: bool = True,
    force_reindex: bool = False,
    supersede_on_reindex: bool = False,
) -> dict:
    """Run the summary ingest. Returns a stats dict."""
    cfg = load_config()
    idx = cfg["index"]
    models = cfg["models"]
    distill_cfg = cfg.get("distill", {})
    min_confidence = float(distill_cfg.get("min_confidence", 0.6))
    units_export = Path(idx.get("units_export", "")).expanduser()
    processed = load_processed(idx["processed_log"])
    chunk_size = idx.get("chunk_size", 60)
    overlap = idx.get("chunk_overlap", 10)

    if force_file:
        targets = [{"path": str(Path(force_file).expanduser())}]
    else:
        targets = _files_from_inventory(cfg["sources"]["inventory"])

    stats = {
        "files_processed": 0,
        "files_skipped": 0,
        "chunks_indexed": 0,
        "units_indexed": 0,
    }
    seen_files = 0

    for rec in targets:
        path = rec["path"]
        parser = get_parser(path)
        if parser is None:
            continue  # unsupported / deferred — ignore, do not consume limit_files

        if limit_files is not None and seen_files >= limit_files:
            break
        seen_files += 1
        status, n_chunks, n_units = _index_one_file(
            cfg=cfg,
            idx=idx,
            path=path,
            parser=parser,
            processed=processed,
            models=models,
            units_export=units_export,
            chunk_size=chunk_size,
            overlap=overlap,
            min_confidence=min_confidence,
            force_file=force_file,
            force_reindex=force_reindex,
            supersede_on_reindex=supersede_on_reindex,
            verbose=verbose,
        )
        processed = load_processed(idx["processed_log"])
        if status == "processed":
            stats["files_processed"] += 1
            stats["chunks_indexed"] += n_chunks
            stats["units_indexed"] += n_units
        elif status == "skipped":
            stats["files_skipped"] += 1
        # status == "ignored": unreadable / parse-failed — prior behavior: no files_skipped

    if stats["files_processed"] > 0:
        try:
            from brief import refresh_brief_after_change

            refresh_brief_after_change(cfg)
        except Exception:
            pass

    # Compact the JSONL export to remove duplicate unit IDs from re-indexing.
    if units_export and units_export.is_file():
        removed = _deduplicate_units_export(units_export)
        if removed:
            stats["export_duplicates_removed"] = removed

    return stats
