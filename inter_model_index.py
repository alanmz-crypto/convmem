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


def index_inter_model_messages(  # pylint: disable=too-many-locals,too-many-arguments
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
    tool: str = _TOOL,
    source_type: str = "inter_model_doc",
    author_model: str = "inter-model-index",
) -> int:
    """Embed each section message as a knowledge unit. Returns units indexed.

    ``cfg`` supplies ``index.processed_log`` for source-lock identity and
    exclusion reads. Export path follows ``units_export`` or cfg.

    Optional ``tool`` / ``source_type`` / ``author_model`` let Kiro steering
    reuse this fast path with distinct metadata (P1.0a).
    """
    src = Path(path)
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
            "tool": tool,
            "domain": _DOMAIN,
            "author_model": author_model,
            "verifier_model": None,
        }
        meta = {
            "id": unit_id,
            "type": unit["type"],
            "title": title,
            "source_path": path_key,
            "confidence": 1.0,
            "timestamp": unit["timestamp"] or "",
            "tool": tool,
            "start_offset": section_index,
            "domain": _DOMAIN,
            "author_model": unit["author_model"],
            "verifier_model": "",
            "source_type": source_type,
            "conversation_id": "",
            "session_id": "",
            "workspace_directory": "",
        }
        units_batch.append((unit, doc, embedding, meta))

    if not units_batch:
        return 0

    # Embeds above run unlocked; source/export locks only wrap the batch write.
    # Avoid importing ingest here (ingest lazily imports this module).
    from purge_locks import export_flock_path, source_flock

    processed_log = cfg["index"]["processed_log"]
    export_path = (
        Path(units_export)
        if units_export is not None
        else Path(cfg["index"]["units_export"]).expanduser()
    )

    def _load_processed(path: str) -> dict:
        pp = Path(path)
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

    with source_flock(cfg, path_key):
        processed = _load_processed(processed_log)
        if _path_excluded(processed, path_key):
            if verbose:
                print(f"  [skip] excluded during inter-model write {Path(path).name}")
            return 0
        with ChromaStore(chroma_dir) as store:
            from ingest_dedupe import evaluate_ingest_batch, persist_ingest_dedupe

            dedupe = evaluate_ingest_batch(store, cfg, units_batch)
            for unit, doc, embedding, meta in dedupe.accepted:
                store.add_unit(unit["id"], doc, embedding, meta)
                export_path.parent.mkdir(parents=True, exist_ok=True)
                with export_flock_path(export_path):
                    with open(export_path, "a", encoding="utf-8") as uf:
                        uf.write(json.dumps(unit) + "\n")
            persist_ingest_dedupe(cfg, dedupe)

    label = "kiro-steering" if source_type == "kiro_steering" else "inter-model"
    if verbose:
        print(
            f"  [{label}] {src.name}: {len(dedupe.accepted)} section units "
            f"({len(dedupe.exact_suppressions)} exact suppressed, "
            f"{len(dedupe.semantic_candidates)} semantic candidates)"
        )
    return len(dedupe.accepted)
