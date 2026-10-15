"""Claude verify probes, round 17 (700b6ba): the dry-run repair (run by `convmem doctor`) must not scan per decision.

Scratch only: a scratch config and store; no providers; no network.
"""

# pylint: disable=protected-access

from __future__ import annotations

from tests.test_zz_claude_verify9 import _real_session_env


def test_r1_dry_run_repair_reads_documents_without_a_scan_per_decision(tmp_path, monkeypatch) -> None:
    import chroma_readonly
    from chroma_store import UNITS, ChromaStore
    from ledger import invalidate_ledger_index_cache
    from observe import repair_empty_ledger_documents

    cfg = _real_session_env(tmp_path, monkeypatch)
    chroma_dir = cfg["index"]["chroma_dir"]
    store = ChromaStore(chroma_dir)
    try:
        col = store._collection(UNITS)
        n_fill, n_dec = 200, 20
        col.add(ids=[f"u_fill_{i}" for i in range(n_fill)], documents=[f"filler {i}" for i in range(n_fill)],
                metadatas=[{"title": f"filler {i}", "source_path": f"/scratch/f{i}.jsonl"} for i in range(n_fill)],
                embeddings=[[0.1, 0.2, 0.3] for _ in range(n_fill)])
        col.add(ids=[f"u_dec_{i}" for i in range(n_dec)], documents=[f"Decision text {i}" for i in range(n_dec)],
                metadatas=[{"ledger_id": f"dec_v17_{i}", "ledger_kind": "decision", "title": f"Decision {i}"}
                           for i in range(n_dec)],
                embeddings=[[0.1, 0.2, 0.3] for _ in range(n_dec)])
    finally:
        store.close()
    invalidate_ledger_index_cache(chroma_dir)
    passes = []
    real = chroma_readonly.iter_collection_metadata_rows

    def counting(chroma, collection, *a, **k):
        if collection == UNITS:
            passes.append(1)
        return real(chroma, collection, *a, **k)

    monkeypatch.setattr(chroma_readonly, "iter_collection_metadata_rows", counting)
    stats = repair_empty_ledger_documents(cfg, dry_run=True, verbose=False)
    print(f"\nR1 unit-collection passes={len(passes)} stats={stats}")
    assert stats["scanned"] == n_dec and stats["empty"] == 0, stats
    assert len(passes) <= 2, len(passes)
