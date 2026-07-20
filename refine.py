"""Index refinement jobs (Milestone F1)."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from chroma_store import ChromaStore, invalidate_superseded_cache, is_superseded
from domains import DEFAULT_DOMAINS, normalize_domain
from process_lock import acquire_lock, release_lock
from vector_similarity import cosine_similarity

JOB_NAMES = (
    "chroma_dedupe",
    "backfill_domain",
    "ledger_link",
    "semantic_dedupe",
    "confidence_audit",
    "redistill",
    "stale_source_flag",
)

BACKFILL_DOMAIN_PROMPT = """Pick the single best domain dotted-path for this knowledge unit.

Allowed examples: {domains}

Title: {title}
Text: {text}

Reply with ONLY the dotted-path string, nothing else."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _refine_data_dir(cfg: dict) -> Path:
    chroma = Path(cfg["index"]["chroma_dir"]).expanduser()
    return chroma.parent


def _stats_path(cfg: dict) -> Path:
    return _refine_data_dir(cfg) / "refine_stats.json"


def _lock_path(cfg: dict) -> Path:
    refine = cfg.get("refine") or {}
    if refine.get("lock_file"):
        return Path(refine["lock_file"]).expanduser()
    return _refine_data_dir(cfg) / "refine.lock"


def load_stats(cfg: dict) -> dict:
    path = _stats_path(cfg)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_stats(cfg: dict, stats: dict) -> None:
    path = _stats_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats, indent=2), encoding="utf-8")


def _undo_dir(cfg: dict, job: str) -> Path:
    d = _refine_data_dir(cfg) / "refine_undo" / job
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_undo_snapshot(cfg: dict, job: str, metas: list[dict]) -> Path | None:
    if not metas:
        return None
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = _undo_dir(cfg, job) / f"{ts}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for m in metas:
            f.write(json.dumps(m) + "\n")
    return path


class CostLimiter:
    """Per-job hourly LLM call caps (hard stop)."""

    def __init__(self, caps: dict[str, int]):
        self.caps = caps
        self.counts: dict[str, list[float]] = defaultdict(list)

    def allow(self, job: str) -> bool:
        cap = self.caps.get(job)
        if cap is None:
            return True
        now = time.time()
        window = [t for t in self.counts[job] if now - t < 3600]
        self.counts[job] = window
        return len(window) < cap

    def record(self, job: str) -> None:
        self.counts[job].append(time.time())

    def llm_calls_last_hour(self, job: str) -> int:
        now = time.time()
        return sum(1 for t in self.counts[job] if now - t < 3600)


def _pick_canonical(group: list[dict]) -> dict:
    """Highest confidence, then newest timestamp, then lowest id."""

    def key(m: dict) -> tuple:
        conf = float(m.get("confidence") or 0)
        ts = str(m.get("timestamp") or m.get("updated_at") or "")
        return (conf, ts, m.get("id", ""))

    return max(group, key=key)


APPROVED_DEDUPE_STATUSES = frozenset(
    {"approved_merge_a_canonical", "approved_merge_b_canonical"}
)


def dedupe_queue_path(cfg: dict) -> Path:
    return _refine_data_dir(cfg) / "dedupe_queue.jsonl"


def load_dedupe_queue(cfg: dict) -> list[dict]:
    path = dedupe_queue_path(cfg)
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def save_dedupe_queue(cfg: dict, rows: list[dict]) -> None:
    path = dedupe_queue_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n",
        encoding="utf-8",
    )


def _tombstone_semantic_duplicate(
    store: ChromaStore,
    cfg: dict,
    *,
    tombstone_id: str,
    canonical_id: str,
    verbose: bool = True,
) -> bool:
    """Mark tombstone_id superseded by canonical_id (semantic dedupe approval)."""
    if tombstone_id == canonical_id:
        return False
    row = store.get_unit(tombstone_id)
    if not row:
        if verbose:
            print(f"  [skip] missing tombstone unit {tombstone_id[:8]}", file=sys.stderr)
        return False
    meta = dict(row.get("metadata") or {})
    if is_superseded(meta):
        if verbose:
            print(
                f"  [skip] already tombstoned {tombstone_id[:8]}",
                file=sys.stderr,
            )
        return False
    canon = store.get_unit(canonical_id)
    if not canon:
        raise ValueError(f"canonical unit not found: {canonical_id}")
    if is_superseded(canon.get("metadata") or {}):
        raise ValueError(f"canonical unit is tombstoned: {canonical_id}")
    meta["id"] = tombstone_id
    write_undo_snapshot(cfg, "semantic_dedupe", [meta])
    new_meta = dict(meta)
    new_meta["superseded"] = True
    new_meta["superseded_by"] = canonical_id
    new_meta["updated_at"] = _now_iso()
    store.update_unit_metadata(tombstone_id, new_meta)
    invalidate_superseded_cache(store.chroma_dir)
    if verbose:
        print(
            f"  [tombstone] {tombstone_id[:8]} → {canonical_id[:8]}",
            file=sys.stderr,
        )
    return True


def apply_dedupe_queue_record(
    store: ChromaStore,
    cfg: dict,
    record: dict,
    *,
    verbose: bool = True,
) -> dict:
    """Apply one approved dedupe_queue row to Chroma (idempotent)."""
    stats = {"tombstoned": 0, "skipped": 0, "errors": 0}
    if record.get("chroma_applied"):
        stats["skipped"] += 1
        return stats
    status = record.get("status")
    if status not in APPROVED_DEDUPE_STATUSES:
        stats["skipped"] += 1
        return stats
    tombstone_id = (record.get("tombstone_id") or "").strip()
    canonical_id = (record.get("canonical_id") or "").strip()
    if not tombstone_id or not canonical_id:
        stats["errors"] += 1
        if verbose:
            print("  [error] approved row missing tombstone_id/canonical_id", file=sys.stderr)
        return stats
    try:
        if _tombstone_semantic_duplicate(
            store,
            cfg,
            tombstone_id=tombstone_id,
            canonical_id=canonical_id,
            verbose=verbose,
        ):
            stats["tombstoned"] += 1
        else:
            stats["skipped"] += 1
    except Exception as e:
        stats["errors"] += 1
        if verbose:
            print(f"  [error] {tombstone_id[:8]}: {e}", file=sys.stderr)
    return stats


def apply_approved_dedupe(
    target: str,
    *,
    verbose: bool = True,
) -> dict:
    """Apply approved dedupe_queue rows. target: 1-based line number or 'all'."""
    from config import load_config

    cfg = load_config()
    rows = load_dedupe_queue(cfg)
    if not rows:
        return {"processed": 0, "tombstoned": 0, "skipped": 0, "errors": 0}

    if target.strip().lower() == "all":
        indices = list(range(len(rows)))
    else:
        try:
            line = int(target)
        except ValueError as e:
            raise ValueError(
                f"--approve-dedupe expects 1-based line number or 'all', got {target!r}"
            ) from e
        if line < 1 or line > len(rows):
            raise ValueError(f"dedupe_queue line {line} out of range (1–{len(rows)})")
        indices = [line - 1]

    store = ChromaStore(cfg["index"]["chroma_dir"])
    totals = {"processed": 0, "tombstoned": 0, "skipped": 0, "errors": 0}
    try:
        for idx in indices:
            rec = rows[idx]
            row_stats = apply_dedupe_queue_record(store, cfg, rec, verbose=verbose)
            totals["processed"] += 1
            for k in ("tombstoned", "skipped", "errors"):
                totals[k] += row_stats[k]
            if row_stats["tombstoned"] or (
                row_stats["skipped"] and rec.get("status") in APPROVED_DEDUPE_STATUSES
            ):
                if row_stats["tombstoned"]:
                    rec["chroma_applied"] = True
                    rec["chroma_applied_at"] = _now_iso()
                elif rec.get("chroma_applied") is not True:
                    unit = store.get_unit((rec.get("tombstone_id") or ""))
                    if unit and is_superseded(unit.get("metadata") or {}):
                        rec["chroma_applied"] = True
                        rec["chroma_applied_at"] = rec.get("chroma_applied_at") or _now_iso()
        save_dedupe_queue(cfg, rows)

        all_stats = load_stats(cfg)
        all_stats.setdefault("jobs", {})
        all_stats["jobs"]["approve_dedupe"] = {
            "last_run": _now_iso(),
            **totals,
        }
        save_stats(cfg, all_stats)
        try:
            from brief import refresh_brief_after_change

            refresh_brief_after_change(cfg)
        except Exception:
            pass
        return totals
    finally:
        store.close()


def job_chroma_dedupe(
    store: ChromaStore,
    cfg: dict,
    *,
    limit: int | None = None,
    verbose: bool = True,
) -> dict:
    metas = store.units_metadata(include_superseded=True)
    by_lid: dict[str, list[dict]] = defaultdict(list)
    for m in metas:
        if is_superseded(m):
            continue
        lid = (m.get("ledger_id") or "").strip()
        if not lid:
            continue
        uid = m.get("id")
        if not uid:
            continue
        by_lid[lid].append(m)

    stats = {"processed": 0, "tombstoned": 0, "skipped": 0, "errors": 0, "llm_calls": 0}
    groups = [(lid, g) for lid, g in by_lid.items() if len(g) > 1]
    if limit is not None:
        groups = groups[:limit]

    for lid, group in groups:
        canonical = _pick_canonical(group)
        canon_id = canonical["id"]
        to_tombstone = [m for m in group if m["id"] != canon_id]
        if not to_tombstone:
            stats["skipped"] += 1
            continue
        write_undo_snapshot(cfg, "chroma_dedupe", to_tombstone)
        for m in to_tombstone:
            chroma_id = m["id"]
            new_meta = dict(m)
            new_meta["superseded"] = True
            new_meta["superseded_by"] = canon_id
            new_meta["updated_at"] = _now_iso()
            try:
                store.update_unit_metadata(chroma_id, new_meta)
                stats["tombstoned"] += 1
                if verbose:
                    print(
                        f"  [tombstone] {lid}  {m['id'][:8]} → {canon_id[:8]}",
                        file=sys.stderr,
                    )
            except Exception as e:
                stats["errors"] += 1
                if verbose:
                    print(f"  [error] {m['id']}: {e}", file=sys.stderr)
        if stats["tombstoned"]:
            invalidate_superseded_cache(store.chroma_dir)
        stats["processed"] += 1
    return stats


def _untagged(meta: dict) -> bool:
    d = meta.get("domain")
    return d is None or str(d).strip() == ""


def job_backfill_domain(
    store: ChromaStore,
    cfg: dict,
    *,
    limit: int | None = None,
    verbose: bool = True,
    limiter: CostLimiter | None = None,
) -> dict:
    from llm import generate

    models = cfg["models"]
    stats = {"processed": 0, "updated": 0, "skipped": 0, "errors": 0, "llm_calls": 0}
    domain_list = ", ".join(DEFAULT_DOMAINS[:20]) + ", …"

    candidates = [m for m in store.units_metadata(include_superseded=False) if _untagged(m)]
    if limit is not None:
        candidates = candidates[:limit]

    for m in candidates:
        uid = m.get("id")
        if not uid:
            stats["skipped"] += 1
            continue
        if limiter and not limiter.allow("backfill_domain"):
            if verbose:
                print("  [stop] backfill_domain hourly cap reached", file=sys.stderr)
            break

        unit = store.get_unit(uid)
        title = (m.get("title") or "").strip()
        text = (unit.get("document") or title)[:2000] if unit else title
        if not title and not text:
            stats["skipped"] += 1
            continue

        prompt = BACKFILL_DOMAIN_PROMPT.format(
            domains=domain_list, title=title, text=text
        )
        try:
            raw = generate(
                prompt,
                model=models.get("distill_model", "deepseek-v4-flash"),
                ollama_host=models["ollama_host"],
                deepseek_base_url=models.get("deepseek_base_url", "https://api.deepseek.com"),
            )
            if limiter:
                limiter.record("backfill_domain")
            stats["llm_calls"] += 1
        except Exception as e:
            stats["errors"] += 1
            if verbose:
                print(f"  [error] classify {uid[:8]}: {e}", file=sys.stderr)
            continue

        domain = normalize_domain(raw.strip().split()[0] if raw else None)
        write_undo_snapshot(cfg, "backfill_domain", [m])
        new_meta = dict(m)
        new_meta["domain"] = domain
        new_meta["updated_at"] = _now_iso()
        try:
            store.update_unit_metadata(uid, new_meta)
            stats["updated"] += 1
            if verbose:
                print(f"  [domain] {uid[:8]} → {domain}", file=sys.stderr)
        except Exception as e:
            stats["errors"] += 1
            if verbose:
                print(f"  [error] update {uid[:8]}: {e}", file=sys.stderr)
        stats["processed"] += 1
    return stats


def _norm_key(title: str) -> str:
    return re.sub(r"\s+", " ", title.lower().strip())[:80]


def job_ledger_link(
    store: ChromaStore,
    cfg: dict,
    *,
    limit: int | None = None,
    verbose: bool = True,
) -> dict:
    """Queue candidate observation pairs (same site + similar title) for review."""
    stats = {"processed": 0, "queued": 0, "skipped": 0, "errors": 0, "llm_calls": 0}
    queue_path = _refine_data_dir(cfg) / "link_queue.jsonl"
    obs = [
        m
        for m in store.units_metadata(include_superseded=False)
        if (m.get("ledger_kind") or m.get("type") or "") in ("observation", "solution")
    ]
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for m in obs:
        site = (m.get("site") or "").strip().lower()
        title = _norm_key(m.get("title") or "")
        if not title:
            continue
        buckets[(site, title)].append(m)

    pairs: list[tuple[dict, dict]] = []
    for group in buckets.values():
        if len(group) < 2:
            continue
        base = group[0]
        for other in group[1:]:
            if base.get("ledger_id") != other.get("ledger_id"):
                pairs.append((base, other))

    if limit is not None:
        pairs = pairs[:limit]

    with queue_path.open("a", encoding="utf-8") as qf:
        for a, b in pairs:
            rec = {
                "ledger_id_a": a.get("ledger_id"),
                "ledger_id_b": b.get("ledger_id"),
                "site": a.get("site"),
                "title": a.get("title"),
                "queued_at": _now_iso(),
            }
            qf.write(json.dumps(rec) + "\n")
            stats["queued"] += 1
            if verbose:
                print(
                    f"  [link] {a.get('ledger_id')} ↔ {b.get('ledger_id')}",
                    file=sys.stderr,
                )
        stats["processed"] = len(pairs)
    return stats


def job_semantic_dedupe(
    store: ChromaStore,
    cfg: dict,
    *,
    limit: int | None = None,
    verbose: bool = True,
    limiter: CostLimiter | None = None,
) -> dict:
    refine = cfg.get("refine") or {}
    threshold = float(refine.get("dedupe_similarity", 0.92))
    max_depth = int(refine.get("queue_max_depth", 100))
    queue_path = _refine_data_dir(cfg) / "dedupe_queue.jsonl"
    existing = 0
    if queue_path.is_file():
        existing = sum(1 for _ in queue_path.open())
    if existing >= max_depth:
        if verbose:
            print(f"  [pause] dedupe_queue depth {existing} >= {max_depth}", file=sys.stderr)
        return {"processed": 0, "queued": 0, "skipped": 0, "errors": 0, "llm_calls": 0}

    units = store.get_units_with_embeddings(include_superseded=False)
    rows: list[tuple[str, dict, list[float]]] = [
        (u["id"], u["metadata"], u["embedding"]) for u in units
    ]

    stats = {"processed": 0, "queued": 0, "skipped": 0, "errors": 0, "llm_calls": 0}
    batch_cap = limit or int(refine.get("batch_size", 10))
    seen_pairs: set[tuple[str, str]] = set()

    for i, (uid_a, meta_a, emb_a) in enumerate(rows):
        if stats["queued"] >= batch_cap:
            break
        dom_a = meta_a.get("domain") or "general"
        for uid_b, meta_b, emb_b in rows[i + 1 : i + 50]:
            if meta_a.get("domain") != meta_b.get("domain") and dom_a != "general":
                continue
            pair = tuple(sorted([uid_a, uid_b]))
            if pair in seen_pairs:
                continue
            sim = cosine_similarity(emb_a, emb_b)
            if sim < threshold:
                continue
            seen_pairs.add(pair)
            if limiter and not limiter.allow("semantic_dedupe"):
                if verbose:
                    print("  [stop] semantic_dedupe hourly cap", file=sys.stderr)
                return stats
            rec = {
                "id_a": uid_a,
                "id_b": uid_b,
                "similarity": round(sim, 4),
                "title_a": meta_a.get("title"),
                "title_b": meta_b.get("title"),
                "domain": dom_a,
                "queued_at": _now_iso(),
                "status": "pending",
            }
            with queue_path.open("a", encoding="utf-8") as qf:
                qf.write(json.dumps(rec) + "\n")
            stats["queued"] += 1
            stats["processed"] += 1
            if verbose:
                print(f"  [dedupe?] {sim:.3f}  {uid_a[:8]} ~ {uid_b[:8]}", file=sys.stderr)
    return stats


def job_confidence_audit(
    store: ChromaStore,
    cfg: dict,
    *,
    limit: int | None = None,
    verbose: bool = True,
    **_: Any,
) -> dict:
    bins = Counter()
    for m in store.units_metadata(include_superseded=False):
        try:
            c = float(m.get("confidence") or 0)
        except (TypeError, ValueError):
            c = 0.0
        bucket = f"{int(c * 10) / 10:.1f}"
        bins[bucket] += 1

    histogram = dict(sorted(bins.items()))
    stats = load_stats(cfg)
    stats["confidence_audit"] = {
        "ran_at": _now_iso(),
        "histogram": histogram,
        "total_units": sum(bins.values()),
    }
    save_stats(cfg, stats)
    if verbose:
        print(f"  [audit] confidence histogram: {histogram}", file=sys.stderr)
    return {
        "processed": 1,
        "histogram_bins": len(histogram),
        "total_units": sum(bins.values()),
        "skipped": 0,
        "errors": 0,
        "llm_calls": 0,
    }


def job_redistill(
    store: ChromaStore,
    cfg: dict,
    *,
    limit: int | None = None,
    verbose: bool = True,
) -> dict:
    stats_blob = load_stats(cfg)
    if "confidence_audit" not in stats_blob:
        print(
            "redistill requires confidence_audit to have run first. "
            "Run: convmem refine --once --job confidence_audit",
            file=sys.stderr,
        )
        sys.exit(1)

    refine = cfg.get("refine") or {}
    min_conf = float(refine.get("min_confidence_redistill", 0.6))
    stats = {"processed": 0, "skipped": 0, "errors": 0, "llm_calls": 0}
    if verbose:
        print(
            "  [redistill] gated pass OK — full chunk re-distill not enabled in F1 v1 "
            "(requires source chunk replay)",
            file=sys.stderr,
        )
    # Flag low-confidence units for a future pass; no processed.json touch yet.
    low = [
        m
        for m in store.units_metadata(include_superseded=False)
        if float(m.get("confidence") or 0) < min_conf
    ]
    if limit is not None:
        low = low[:limit]
    stats_blob.setdefault("redistill_queue", {})
    stats_blob["redistill_queue"] = {
        "flagged_at": _now_iso(),
        "count": len(low),
        "sample_ids": [m.get("id") for m in low[:20]],
    }
    save_stats(cfg, stats_blob)
    stats["processed"] = len(low)
    return stats


def job_stale_source_flag(
    store: ChromaStore,
    cfg: dict,
    *,
    limit: int | None = None,
    verbose: bool = True,
) -> dict:
    stats = {"processed": 0, "updated": 0, "skipped": 0, "errors": 0, "llm_calls": 0}
    metas = store.units_metadata(include_superseded=False)
    if limit is not None:
        metas = metas[:limit]
    for m in metas:
        src = (m.get("source_path") or "").strip()
        if not src or src.startswith("site:") or src.startswith("ledger:"):
            stats["skipped"] += 1
            continue
        path = Path(src).expanduser()
        if path.is_file():
            stats["skipped"] += 1
            continue
        write_undo_snapshot(cfg, "stale_source_flag", [m])
        new_meta = dict(m)
        new_meta["source_available"] = False
        new_meta["updated_at"] = _now_iso()
        try:
            store.update_unit_metadata(m["id"], new_meta)
            stats["updated"] += 1
        except Exception:
            stats["errors"] += 1
        stats["processed"] += 1
    return stats


_JOBS: dict[str, Callable[..., dict]] = {
    "chroma_dedupe": job_chroma_dedupe,
    "backfill_domain": job_backfill_domain,
    "ledger_link": job_ledger_link,
    "semantic_dedupe": job_semantic_dedupe,
    "confidence_audit": job_confidence_audit,
    "redistill": job_redistill,
    "stale_source_flag": job_stale_source_flag,
}


def _cost_caps(cfg: dict) -> dict[str, int]:
    refine_section = cfg.get("refine") or {}
    cost_section = refine_section.get("cost") or {}
    return {
        "backfill_domain": int(cost_section.get("backfill_domain_calls_per_hour", 60)),
        "redistill": int(cost_section.get("redistill_calls_per_hour", 15)),
        "semantic_dedupe": int(cost_section.get("semantic_dedupe_calls_per_hour", 20)),
    }


def run_job(
    job: str,
    *,
    limit: int | None = None,
    verbose: bool = True,
) -> dict:
    from config import load_config

    if job not in _JOBS:
        raise ValueError(f"Unknown job {job!r}. Choose from: {', '.join(JOB_NAMES)}")

    cfg = load_config()
    store = ChromaStore(cfg["index"]["chroma_dir"])
    limiter = CostLimiter(_cost_caps(cfg))

    kwargs: dict[str, Any] = {"limit": limit, "verbose": verbose}
    if job in ("backfill_domain", "semantic_dedupe"):
        kwargs["limiter"] = limiter

    try:
        result = _JOBS[job](store, cfg, **kwargs)
        result.setdefault("llm_calls", 0)

        all_stats = load_stats(cfg)
        all_stats.setdefault("jobs", {})
        all_stats["jobs"][job] = {
            "last_run": _now_iso(),
            **result,
        }
        save_stats(cfg, all_stats)
        try:
            from brief import refresh_brief_after_change

            refresh_brief_after_change(cfg)
        except Exception:
            pass
        return result
    finally:
        store.close()


def run_refine_daemon(*, verbose: bool = True, use_lock: bool = True) -> None:
    from config import load_config

    cfg = load_config()
    refine = cfg.get("refine") or {}
    jobs = refine.get("jobs") or [
        "chroma_dedupe",
        "backfill_domain",
        "ledger_link",
        "semantic_dedupe",
    ]
    interval = float(refine.get("interval_seconds", 300))
    batch = int(refine.get("batch_size", 10))
    lock_path = _lock_path(cfg)

    if use_lock:
        acquire_lock(lock_path, label="refine")

    if verbose:
        print(
            f"[refine] daemon started jobs={jobs} interval={interval}s pid={os.getpid()}",
            file=sys.stderr,
        )

    try:
        while True:
            for job in jobs:
                if job not in _JOBS:
                    continue
                if verbose:
                    print(f"[refine] job {job}", file=sys.stderr)
                run_job(job, limit=batch, verbose=verbose)
            time.sleep(interval)
    except KeyboardInterrupt:
        if verbose:
            print("\n[refine] stopping", file=sys.stderr)
    finally:
        if use_lock:
            release_lock(lock_path)


def print_stats() -> dict:
    from config import load_config

    cfg = load_config()
    stats = load_stats(cfg)
    print(json.dumps(stats, indent=2))
    return stats
