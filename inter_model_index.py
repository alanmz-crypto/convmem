"""Direct section indexing for docs/inter-model/*.md (no LLM summarize/distill)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from chroma_store import ChromaStore
from distill import make_unit_id
from llm import ollama_embed

_TOOL = "inter-model"
_DOMAIN = "coding.tooling"
_MAX_EMBED_CHARS = 8000


def _keywords_from(path: Path, title: str) -> list[str]:
    stem_parts = re.split(r"[-_]", path.stem)
    title_parts = re.findall(r"[a-zA-Z0-9]+", title.lower())
    seen: set[str] = set()
    out: list[str] = []
    for word in stem_parts + title_parts:
        w = word.lower().strip()
        if len(w) >= 3 and w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) >= 8:
            break
    for pad in ("convmem", "coordination", "inter-model"):
        if len(out) >= 3:
            break
        if pad not in seen:
            out.append(pad)
    return out[:8]


def index_inter_model_messages(
    path: str,
    messages: list[dict],
    *,
    path_key: str,
    chroma_dir: str,
    embed_model: str,
    ollama_host: str,
    verbose: bool = True,
    units_export: Path | None = None,
    cfg: dict | None = None,
) -> int:
    """Embed each section message as a knowledge unit. Returns units indexed."""
    src = Path(path)
    n_units = 0
    units_batch: list[tuple] = []

    for msg in messages:
        section_index = int(msg.get("section_index", 0))
        title = str(msg.get("section_title") or src.stem).strip()
        content = str(msg.get("content") or "").strip()
        if not content:
            continue

        summary = content
        if len(summary) > 500:
            summary = summary[:497] + "…"
        keywords = _keywords_from(src, title)
        doc = f"{title} {summary} {' '.join(keywords)}"
        if len(doc) > _MAX_EMBED_CHARS:
            doc = doc[: _MAX_EMBED_CHARS - 1] + "…"

        try:
            embedding = ollama_embed(doc, model=embed_model, host=ollama_host)
        except Exception as e:
            if verbose:
                print(f"    [warn] section {section_index} embed failed: {e}")
            continue

        unit_id = make_unit_id(path_key, section_index, title, 0)
        unit = {
            "id": unit_id,
            "type": "explanation",
            "title": title,
            "summary": summary,
            "keywords": keywords,
            "source_path": path_key,
            "confidence": 1.0,
            "timestamp": msg.get("timestamp"),
            "tool": _TOOL,
            "domain": _DOMAIN,
            "author_model": "inter-model-index",
            "verifier_model": None,
        }
        meta = {
            "id": unit_id,
            "type": unit["type"],
            "title": title,
            "source_path": path_key,
            "confidence": 1.0,
            "timestamp": unit["timestamp"] or "",
            "tool": _TOOL,
            "start_offset": section_index,
            "domain": _DOMAIN,
            "author_model": unit["author_model"],
            "verifier_model": "",
            "source_type": "inter_model_doc",
            "conversation_id": "",
            "session_id": "",
            "workspace_directory": "",
        }
        units_batch.append((unit, doc, embedding, meta))
        n_units += 1

    if not units_batch:
        return 0

    # Embeds above run unlocked; source/export locks only wrap the batch write.
    from source_purge import export_flock_path, source_flock

    lock_cfg = cfg
    if lock_cfg is None:
        # Derive data-root locks from chroma/export siblings when caller omits cfg.
        data_root = Path(chroma_dir).expanduser().resolve().parent
        lock_cfg = {
            "index": {
                "processed_log": str(data_root / "processed.json"),
                "units_export": str(units_export)
                if units_export
                else str(data_root / "knowledge_units.jsonl"),
            }
        }

    with source_flock(lock_cfg, path_key):
        from ingest import _path_is_excluded, load_processed

        processed = load_processed(lock_cfg["index"]["processed_log"])
        if _path_is_excluded(processed, path_key):
            if verbose:
                print(f"  [skip] excluded during inter-model write {Path(path).name}")
            return 0
        with ChromaStore(chroma_dir) as store:
            for unit, doc, embedding, meta in units_batch:
                store.add_unit(unit["id"], doc, embedding, meta)
                if units_export:
                    units_export.parent.mkdir(parents=True, exist_ok=True)
                    with export_flock_path(units_export):
                        with open(units_export, "a", encoding="utf-8") as uf:
                            uf.write(json.dumps(unit) + "\n")

    if verbose:
        print(f"  [inter-model] {src.name}: {n_units} section units")
    return n_units
