# pylint: disable=duplicate-code
"""Disposable Phase 0 shadow replay into a marked temporary Chroma root."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Literal, Mapping

from chroma_store import UNITS, ChromaStore, open_chroma_for_read
from shadow_ledger import projection_state_hash, resolve_path, sha256_canonical

REPLAY_MARKER_NAME = ".convmem_shadow_replay_ok"
CHECKPOINT_NAME = ".convmem_shadow_replay_checkpoint.json"
ReplayMode = Literal["stub", "live"]

ARCHITECTURE_CATEGORIES = (
    "missing-in-shadow",
    "missing-in-Chroma",
    "state mismatch",
    "projection mismatch",
    "unknown embed provenance",
    "duplicates",
    "corrupt records",
    "extras",
)


class ReplayTargetError(ValueError):
    """Raised when the disposable root is unsafe."""


class LiveEmbedError(RuntimeError):
    """Raised when live embedding mode cannot reach the local model."""


class CorruptShadowError(ValueError):
    """Raised when a shadow ledger line is corrupt; checkpoint must not advance."""

    def __init__(self, message: str, *, line: int) -> None:
        super().__init__(message)
        self.line = line


@dataclass
class ReplayResult:  # pylint: disable=too-many-instance-attributes
    mode: ReplayMode
    replay_root: Path
    projected_count: int
    duplicates: int
    corrupt_at_line: int | None
    checkpoint: dict[str, Any]
    shadow_final: dict[str, dict[str, Any]]
    touched_ids: set[str]
    findings: list[dict[str, Any]] = field(default_factory=list)
    state_equal: bool = False
    projection_equal: bool = False
    mutation_sink_forced_none: bool = True


def iter_shadow_events(ledger_path: Path) -> Iterator[dict[str, Any]]:
    """Yield parsed events; raise CorruptShadowError on first bad line."""
    path = Path(ledger_path)
    if not path.is_file():
        yield from ()
        return
    with open(path, encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CorruptShadowError(
                    f"corrupt shadow record at line {lineno}", line=lineno
                ) from exc
            if not isinstance(obj, dict):
                raise CorruptShadowError(
                    f"non-object shadow record at line {lineno}", line=lineno
                )
            yield obj


def reduce_final_states(
    events: Iterator[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], int]:
    """Apply first valid event_id; count later duplicates; keep last state per entity."""
    seen_ids: set[str] = set()
    final: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for event in events:
        eid = str(event.get("event_id") or "")
        if eid and eid in seen_ids:
            duplicates += 1
            continue
        if eid:
            seen_ids.add(eid)
        entity = str(event.get("stable_entity_id") or "")
        if not entity:
            continue
        final[entity] = event
    return final, duplicates


def assert_safe_replay_root(
    target: Path,
    *,
    production_chroma_root: Path,
) -> Path:
    """Refuse production root, parent, child, symlink alias, nonempty unmarked."""
    target = Path(target)
    prod = resolve_path(production_chroma_root)
    try:
        resolved = target.resolve()
    except OSError as exc:
        raise ReplayTargetError(str(exc)) from exc
    if resolved == prod:
        raise ReplayTargetError("refuse production chroma root")
    if resolved in prod.parents:
        raise ReplayTargetError("refuse parent of production chroma root")
    try:
        resolved.relative_to(prod)
        raise ReplayTargetError("refuse child of production chroma root")
    except ValueError:
        pass
    # Symlink before resolve already collapsed; also refuse if the path itself is a link.
    if target.exists() and target.is_symlink():
        raise ReplayTargetError("refuse symlink replay target")
    if resolved.exists() and resolved.is_symlink():
        raise ReplayTargetError("refuse symlink replay target")
    if target.exists() or resolved.exists():
        check = resolved if resolved.exists() else target
        if any(check.iterdir()):
            marker = check / REPLAY_MARKER_NAME
            if not marker.is_file():
                raise ReplayTargetError("refuse nonempty unmarked replay target")
    return resolved


def prepare_replay_root(
    target: Path, *, production_chroma_root: Path
) -> Path:
    root = assert_safe_replay_root(
        target, production_chroma_root=production_chroma_root
    )
    root.mkdir(parents=True, exist_ok=True)
    marker = root / REPLAY_MARKER_NAME
    if not marker.exists():
        marker.write_text("convmem shadow replay disposable root\n", encoding="utf-8")
        os.chmod(marker, 0o600)
    return root


def stub_embedding(dims: int, *, entity_id: str) -> list[float]:
    """Deterministic placeholder embedding; no network."""
    if dims < 1:
        raise ValueError("embed_dims must be >= 1")
    digest = hashlib.sha256(entity_id.encode("utf-8")).digest()
    out: list[float] = []
    i = 0
    while len(out) < dims:
        block = hashlib.sha256(digest + i.to_bytes(4, "big")).digest()
        for b in block:
            out.append((b / 255.0) * 0.02)
            if len(out) >= dims:
                break
        i += 1
    return out


def open_replay_store(replay_root: Path) -> ChromaStore:
    """Open disposable write store with mutation_sink forced None (no recursion)."""
    return ChromaStore(str(replay_root), mutation_sink=None)


def checkpoint_path(replay_root: Path) -> Path:
    return Path(replay_root) / CHECKPOINT_NAME


def load_checkpoint(replay_root: Path) -> dict[str, Any]:
    path = checkpoint_path(replay_root)
    if not path.is_file():
        return {
            "last_sequence": None,
            "last_event_id": None,
            "projected_events": 0,
            "status": "empty",
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_checkpoint(replay_root: Path, checkpoint: Mapping[str, Any]) -> None:
    path = checkpoint_path(replay_root)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(dict(checkpoint), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def _embed_for_event(
    event: Mapping[str, Any],
    *,
    mode: ReplayMode,
    ollama_host: str | None,
    embed_model: str | None,
) -> list[float]:
    dims = event.get("embed_dims")
    if dims is None:
        dims = 8
    dims = int(dims)
    entity = str(event.get("stable_entity_id") or "")
    if mode == "stub":
        return stub_embedding(dims, entity_id=entity)
    # live — explicit local only; never fall back to stub
    host = (ollama_host or "").strip()
    model = (embed_model or "").strip()
    if not host or not model:
        raise LiveEmbedError("live mode requires ollama_host and embed_model")
    try:
        from llm import ollama_embed
    except Exception as exc:  # pragma: no cover
        raise LiveEmbedError(f"live embed import failed: {exc}") from exc
    post = event.get("post_state") or {}
    text = post.get("document") or ""
    try:
        vec = list(ollama_embed(str(text), model=model, host=host))
    except Exception as exc:
        raise LiveEmbedError(f"live embed unreachable: {exc}") from exc
    if not vec:
        raise LiveEmbedError("live embed returned empty vector")
    return vec


def project_event(
    store: ChromaStore,
    event: Mapping[str, Any],
    *,
    mode: ReplayMode,
    ollama_host: str | None = None,
    embed_model: str | None = None,
) -> None:
    """Project one shadow event into the disposable store (sink must be None)."""
    if store.mutation_sink is not None:
        raise RuntimeError("replay projector refused non-None mutation_sink")
    entity = str(event.get("stable_entity_id") or "")
    if not entity:
        return
    post = event.get("post_state") or {}
    deleted = bool(post.get("deleted"))
    if deleted:
        if store.get_unit(entity) is not None:
            collection = getattr(store, "_collection")(UNITS)  # pylint: disable=protected-access
            collection.delete(ids=[entity])
        return
    document = post.get("document")
    if document is None:
        document = ""
    meta = dict(post.get("metadata") or {})
    meta.setdefault("id", entity)
    emb = _embed_for_event(
        event, mode=mode, ollama_host=ollama_host, embed_model=embed_model
    )
    store.add_unit(entity, str(document), emb, meta)


def compare_touched(
    *,
    shadow_final: dict[str, dict[str, Any]],
    chroma_units: dict[str, dict[str, Any]],
    touched_ids: set[str],
) -> list[dict[str, Any]]:
    """Two-level comparison categories for touched IDs (Architecture vocabulary)."""
    findings: list[dict[str, Any]] = []
    for eid in sorted(touched_ids):
        s = shadow_final.get(eid)
        c = chroma_units.get(eid)
        if s is None and c is not None:
            findings.append({"category": "missing-in-shadow", "id": eid})
            continue
        if s is not None and c is None:
            post = s.get("post_state") or {}
            if post.get("deleted"):
                continue
            findings.append({"category": "missing-in-Chroma", "id": eid})
            continue
        if s is None and c is None:
            continue
        assert s is not None and c is not None
        post = s.get("post_state") or {}
        deleted = bool(post.get("deleted"))
        c_doc = c.get("document")
        c_meta = c.get("metadata") or {}
        c_hash = projection_state_hash(
            stable_entity_id=eid,
            deleted=False,
            document=c_doc,
            metadata=c_meta,
        )
        if deleted:
            findings.append({"category": "extras", "id": eid})
            continue
        if s.get("state_hash") != c_hash:
            findings.append({"category": "state mismatch", "id": eid})
        doc_hash = s.get("document_hash")
        if doc_hash and doc_hash != sha256_canonical(c_doc):
            findings.append({"category": "projection mismatch", "id": eid})
        s_model = s.get("embed_model") or "unknown"
        c_model = c_meta.get("embed_model") or "unknown"
        if s_model == "unknown" or c_model == "unknown":
            findings.append(
                {
                    "category": "unknown embed provenance",
                    "id": eid,
                    "detail": "UNVERIFIABLE",
                }
            )
    return findings


def equality_flags(findings: list[dict[str, Any]]) -> tuple[bool, bool]:
    """Return (state_equal, projection_equal). Raw vectors never consulted."""
    state_blockers = {
        "missing-in-shadow",
        "missing-in-Chroma",
        "state mismatch",
        "extras",
        "corrupt records",
    }
    proj_blockers = state_blockers | {"projection mismatch"}
    cats = {f["category"] for f in findings}
    # unknown embed provenance is UNVERIFIABLE — not state FAIL, not projection PASS
    state_equal = cats.isdisjoint(state_blockers)
    projection_equal = cats.isdisjoint(proj_blockers) and (
        "unknown embed provenance" not in cats
    )
    return state_equal, projection_equal


def _load_production_units(
    production_chroma_root: Path,
    touched_ids: set[str],
) -> dict[str, dict[str, Any]]:
    store = open_chroma_for_read(str(production_chroma_root))
    try:
        out: dict[str, dict[str, Any]] = {}
        for eid in touched_ids:
            row = store.get_unit(eid)
            if row is not None:
                out[eid] = {
                    "document": row.get("document"),
                    "metadata": row.get("metadata") or {},
                }
        return out
    finally:
        store.close()


def run_disposable_replay(  # pylint: disable=too-many-arguments
    *,
    ledger_path: Path,
    replay_root: Path,
    production_chroma_root: Path,
    mode: ReplayMode = "stub",
    touched_ids: set[str] | None = None,
    production_units: dict[str, dict[str, Any]] | None = None,
    ollama_host: str | None = None,
    embed_model: str | None = None,
    shadow_cfg_eligible: Mapping[str, Any] | None = None,
) -> ReplayResult:
    """Project shadow events into a marked temp root and compare touched IDs.

    ``shadow_cfg_eligible`` may describe an enabled production cfg; the projector
    still forces ``mutation_sink=None`` and never opens the write factory for
    injection.
    """
    del shadow_cfg_eligible  # documented intentionally; never used for injection
    if mode not in ("stub", "live"):
        raise ValueError(f"unsupported replay mode: {mode}")
    root = prepare_replay_root(
        replay_root, production_chroma_root=production_chroma_root
    )
    checkpoint = load_checkpoint(root)
    store = open_replay_store(root)
    assert store.mutation_sink is None

    projected = int(checkpoint.get("projected_events") or 0)
    duplicates = 0
    seen_ids: set[str] = set()
    if checkpoint.get("last_event_id"):
        # Resume: treat prior projected event_ids as seen (single last id + count).
        # Full resume of all IDs is not required for Phase 0 fresh-root runs.
        seen_ids.add(str(checkpoint["last_event_id"]))
    corrupt_at: int | None = None
    events_for_final: list[dict[str, Any]] = []

    try:
        try:
            for event in iter_shadow_events(Path(ledger_path)):
                events_for_final.append(event)
                eid = str(event.get("event_id") or "")
                if eid and eid in seen_ids:
                    duplicates += 1
                    continue
                if eid:
                    seen_ids.add(eid)
                project_event(
                    store,
                    event,
                    mode=mode,
                    ollama_host=ollama_host,
                    embed_model=embed_model,
                )
                projected += 1
                checkpoint = {
                    "last_sequence": event.get("sequence"),
                    "last_event_id": eid or None,
                    "projected_events": projected,
                    "status": "ok",
                }
                save_checkpoint(root, checkpoint)
        except CorruptShadowError as exc:
            corrupt_at = exc.line
            checkpoint = {
                **checkpoint,
                "status": "stopped_corrupt",
                "corrupt_at_line": exc.line,
            }
            save_checkpoint(root, checkpoint)
    finally:
        store.close()

    shadow_final, reduce_dups = reduce_final_states(iter(events_for_final))
    # Prefer live duplicate count from projection loop (includes resume skips).
    duplicates = max(duplicates, reduce_dups)
    if touched_ids is None:
        touched = set(shadow_final.keys())
    else:
        touched = set(touched_ids)

    if production_units is None:
        chroma_units = _load_production_units(Path(production_chroma_root), touched)
    else:
        chroma_units = production_units

    findings = compare_touched(
        shadow_final=shadow_final,
        chroma_units=chroma_units,
        touched_ids=touched,
    )
    if duplicates:
        findings.append({"category": "duplicates", "count": duplicates})
    if corrupt_at is not None:
        findings.append({"category": "corrupt records", "line": corrupt_at})

    state_equal, projection_equal = equality_flags(findings)
    return ReplayResult(
        mode=mode,
        replay_root=root,
        projected_count=projected,
        duplicates=duplicates,
        corrupt_at_line=corrupt_at,
        checkpoint=checkpoint,
        shadow_final=shadow_final,
        touched_ids=touched,
        findings=findings,
        state_equal=state_equal,
        projection_equal=projection_equal,
        mutation_sink_forced_none=True,
    )
