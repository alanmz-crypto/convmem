"""Ingest pipeline.

For each source file:
  - skip if its content hash is already in processed.json (idempotent)
  - parse -> canonical messages
  - chunk (size/overlap from config)
  - per chunk:
      summarize -> embed -> conversation_summaries  (fallback / --raw)
      distill   -> embed -> knowledge_units       (primary search, Step 5+)
"""

import hashlib
import json
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
            continue  # unsupported / deferred format

        if limit_files is not None and seen_files >= limit_files:
            break
        seen_files += 1

        try:
            file_hash = sha256_file(path)
        except OSError as e:
            if verbose:
                print(f"  [skip] cannot read {path}: {e}")
            continue

        # Excluded files are always skipped, even with force_file
        if file_hash in processed and processed[file_hash].get("excluded"):
            stats["files_skipped"] += 1
            if verbose:
                print(f"  [skip] excluded {Path(path).name}")
            continue

        if force_reindex and force_file:
            path_str = str(Path(path).expanduser().resolve())
            for key, entry in list(processed.items()):
                if isinstance(entry, dict) and entry.get("path") == path_str:
                    del processed[key]

        path_key = str(Path(path).expanduser().resolve())

        # Growing append-only transcripts: drop stale processed entry when hash changes.
        if force_file and not force_reindex:
            stale = _stored_hash_for_path(path_key, processed)
            if stale and stale != file_hash:
                del processed[stale]

        if not force_reindex:
            if file_hash in processed:
                stats["files_skipped"] += 1
                if verbose:
                    print(f"  [skip] unchanged {Path(path).name}")
                continue

        fmt = detect_format(path)
        tool = TOOL_BY_FORMAT.get(fmt, fmt or "unknown")

        chroma_dir = idx["chroma_dir"]

        if force_file:
            with ChromaStore(chroma_dir) as store:
                n_units_del = 0
                n_sum_del = 0
                tombstone_tag = f"{path_key}#{file_hash[:12]}"
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

        try:
            messages = parser(path)
        except Exception as e:
            if verbose:
                print(f"  [skip] parse failed {path}: {e}")
            continue

        if fmt == "inter_model_doc":
            chroma_dir = idx["chroma_dir"]
            if force_file:
                with ChromaStore(chroma_dir) as store:
                    tombstone_tag = f"{path_key}#{file_hash[:12]}"
                    if supersede_on_reindex:
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
                from inter_model_index import index_inter_model_messages

                n_units = index_inter_model_messages(
                    path,
                    messages,
                    path_key=path_key,
                    chroma_dir=chroma_dir,
                    embed_model=models["embed_model"],
                    ollama_host=models["ollama_host"],
                    verbose=verbose,
                    units_export=units_export if units_export else None,
                )
            except Exception as e:
                if verbose:
                    print(f"  [skip] inter-model index failed {path}: {e}")
                continue

            processed[file_hash] = {
                "path": path_key,
                "chunks": 0,
                "units": n_units,
            }
            save_processed(idx["processed_log"], processed)
            stats["files_processed"] += 1
            stats["units_indexed"] += n_units
            continue

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
            with ChromaStore(chroma_dir) as store:
                store.add_summary(doc_id, summary, summary_embedding, metadata)
                n_indexed += 1
                for unit, doc, unit_embedding, unit_meta in units_to_add:
                    store.add_unit(unit["id"], doc, unit_embedding, unit_meta)
                    if units_export:
                        units_export.parent.mkdir(parents=True, exist_ok=True)
                        with open(units_export, "a", encoding="utf-8") as uf:
                            uf.write(json.dumps(unit) + "\n")
                    n_units += 1

        processed[file_hash] = {
            "path": path_key,
            "chunks": n_indexed,
            "units": n_units,
        }
        save_processed(idx["processed_log"], processed)
        stats["files_processed"] += 1
        stats["chunks_indexed"] += n_indexed
        stats["units_indexed"] += n_units

    if stats["files_processed"] > 0:
        try:
            from brief import refresh_brief_after_change

            refresh_brief_after_change(cfg)
        except Exception:
            pass

    return stats
