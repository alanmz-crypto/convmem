#!/usr/bin/env python3
"""Per-arm query worker for Gate 1 subprocess compare.

Loads configuration exclusively via CONVMEM_CONFIG (must be set before imports
that read config at module load). Emits a startup identity banner, then either:
  - one-shot: answer a single query and exit (isolation proof)
  - serve: long-lived line protocol for warm latency measurement
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _verify_current_model(cfg: dict) -> dict[str, object]:
    """Resolve the model on the exact configured host and require its digest."""
    models = cfg.get("models") or {}
    eval_cfg = cfg.get("eval") or {}
    if str(eval_cfg.get("embedding_request_contract") or "") != "ollama.embed.v1":
        return {}
    from eval_corpus.ollama_identity import OllamaEmbedClient

    client = OllamaEmbedClient(str(models.get("ollama_host") or ""))
    identity = client.resolve_model(str(models.get("embed_model") or ""))
    expected = str(models.get("embed_model_digest") or "")
    if not expected or str(identity.get("model_digest") or "") != expected:
        raise RuntimeError("configured Ollama model digest does not match the approved digest")
    loaded = client.resolve_loaded_model(
        str(models.get("embed_model") or ""),
        expected,
    )
    identity["loaded_model"] = loaded
    identity["residency_status"] = "resident" if loaded is not None else "not_resident"
    return identity


def _residency_evidence(before: dict[str, object], after: dict[str, object]) -> dict[str, object]:
    before_loaded = before.get("loaded_model")
    after_loaded = after.get("loaded_model")
    expected = str(before.get("model_digest") or "")
    before_digest = str((before_loaded or {}).get("model_digest") or "")
    after_digest = str((after_loaded or {}).get("model_digest") or "")
    return {
        "residency_before": before.get("residency_status"),
        "residency_after": after.get("residency_status"),
        "loaded_model_before": before_loaded,
        "loaded_model_after": after_loaded,
        "warm_residency_verified": bool(
            expected and before_digest == expected and after_digest == expected
        ),
    }


def _startup_banner(cfg: dict) -> dict:
    chroma = str(Path(cfg["index"]["chroma_dir"]).expanduser().resolve())
    # data_dir: parent of chroma or explicit if present
    data_dir = str(Path(chroma).parent.resolve())
    models = cfg.get("models") or {}
    resolved_identity: dict[str, object] = {}
    eval_cfg = cfg.get("eval") or {}
    if str(eval_cfg.get("embedding_request_contract") or "") == "ollama.embed.v1":
        resolved_identity = _verify_current_model(cfg)
    return {
        "type": "startup",
        "config_path": os.environ.get("CONVMEM_CONFIG", ""),
        "chroma_dir": chroma,
        "data_dir": data_dir,
        "embed_host": str(models.get("ollama_host") or ""),
        "embed_model": str(models.get("embed_model") or ""),
        "embed_model_digest": str(
            resolved_identity.get("model_digest")
            or models.get("embed_model_digest")
            or ""
        ),
        "embed_model_variant": str(resolved_identity.get("variant") or ""),
        "embed_model_quantization": str(resolved_identity.get("quantization") or ""),
        "embed_dimensions": int(eval_cfg.get("embedding_dimensions") or 0),
        "residency_status": str(resolved_identity.get("residency_status") or "unknown"),
        "loaded_model": resolved_identity.get("loaded_model"),
        "pid": os.getpid(),
    }


def _run_query(query: str, top_k: int, eval_view: str) -> tuple[list[dict], dict]:
    # Import only after CONVMEM_CONFIG is present so config.py picks it up.
    from query import QueryUnitTrace, query_units

    trace = QueryUnitTrace()
    hits = query_units(
        query, top_k=top_k, eval_view=eval_view, retrieval_trace=trace
    )
    # Normalize for JSON
    out = []
    for h in hits:
        out.append(
            {
                "id": h.get("id"),
                "metadata": h.get("metadata") or {},
                "document": h.get("document"),
                "distance": h.get("distance"),
                "score": h.get("score"),
            }
        )
    return out, {
        "retrieval_mode": trace.retrieval_mode,
        "vector_query_attempted": trace.vector_query_attempted,
        "fallback_used": trace.fallback_used,
        "vector_candidates": [dict(candidate) for candidate in trace.candidates],
        "query_vector_fingerprint": trace.query_vector_fingerprint,
        "query_vector_dimension": trace.query_vector_dimension,
        "query_vector_finite": trace.query_vector_finite,
        "query_vector_norm": trace.query_vector_norm,
        "embedding_request_diagnostics": trace.embedding_request_diagnostics,
        "enrichment_reader": trace.enrichment_reader,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eval query arm worker")
    parser.add_argument(
        "--mode",
        choices=("one-shot", "serve"),
        default="one-shot",
    )
    parser.add_argument("--query", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--eval-view",
        default="embedding_influenced",
        choices=("embedding_influenced", "operational_pipeline", "exact_vector"),
    )
    args = parser.parse_args(argv)

    if not os.environ.get("CONVMEM_CONFIG"):
        print("CONVMEM_CONFIG required before worker start", file=sys.stderr)
        return 2

    sys.path.insert(0, str(REPO))
    # Force config module to see env (import order)
    import importlib

    import config as config_mod

    importlib.reload(config_mod)
    cfg = config_mod.load_config()
    banner = _startup_banner(cfg)
    print(json.dumps(banner, sort_keys=True), flush=True)

    if args.mode == "one-shot":
        if not args.query:
            print(json.dumps({"type": "error", "error": "query required"}), flush=True)
            return 3
        model_before = _verify_current_model(cfg)
        t0 = time.perf_counter()
        hits, evidence = _run_query(args.query, args.top_k, args.eval_view)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        model_after = _verify_current_model(cfg)
        print(
            json.dumps(
                {
                    "type": "result",
                    "hits": hits,
                    "elapsed_ms": elapsed_ms,
                    "eval_view": args.eval_view,
                    **_residency_evidence(model_before, model_after),
                    **evidence,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 0

    # Long-lived serve: each stdin line is JSON {query, top_k?, eval_view?}
    print(json.dumps({"type": "ready"}), flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        if line == "QUIT":
            break
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            print(json.dumps({"type": "error", "error": str(exc)}), flush=True)
            continue
        q = str(req.get("query") or "")
        top_k = int(req.get("top_k") or args.top_k)
        view = str(req.get("eval_view") or args.eval_view)
        try:
            model_before = _verify_current_model(cfg)
            t0 = time.perf_counter()
            hits, evidence = _run_query(q, top_k, view)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            model_after = _verify_current_model(cfg)
            err = None
        except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001 — surface to parent
            elapsed_ms = 0.0
            hits = []
            evidence = {
                "retrieval_mode": "failed",
                "vector_query_attempted": False,
                "fallback_used": False,
            }
            err = str(exc)
        print(
            json.dumps(
                {
                    "type": "result",
                    "hits": hits,
                    "elapsed_ms": elapsed_ms,
                    "eval_view": view,
                    "error": err,
                    **(_residency_evidence(model_before, model_after) if err is None else {}),
                    **evidence,
                },
                sort_keys=True,
            ),
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
