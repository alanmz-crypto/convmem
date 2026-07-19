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


def _startup_banner(cfg: dict) -> dict:
    chroma = str(Path(cfg["index"]["chroma_dir"]).expanduser().resolve())
    # data_dir: parent of chroma or explicit if present
    data_dir = str(Path(chroma).parent.resolve())
    models = cfg.get("models") or {}
    return {
        "type": "startup",
        "config_path": os.environ.get("CONVMEM_CONFIG", ""),
        "chroma_dir": chroma,
        "data_dir": data_dir,
        "embed_host": str(models.get("ollama_host") or ""),
        "embed_model": str(models.get("embed_model") or ""),
        "pid": os.getpid(),
    }


def _run_query(query: str, top_k: int, eval_view: str) -> list[dict]:
    # Import only after CONVMEM_CONFIG is present so config.py picks it up.
    from query import query_units

    hits = query_units(query, top_k=top_k, eval_view=eval_view)
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
    return out


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
        choices=("embedding_influenced", "operational_pipeline"),
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
        t0 = time.perf_counter()
        hits = _run_query(args.query, args.top_k, args.eval_view)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        print(
            json.dumps(
                {
                    "type": "result",
                    "hits": hits,
                    "elapsed_ms": elapsed_ms,
                    "eval_view": args.eval_view,
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
        t0 = time.perf_counter()
        try:
            hits = _run_query(q, top_k, view)
            err = None
        except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001 — surface to parent
            hits = []
            err = str(exc)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        print(
            json.dumps(
                {
                    "type": "result",
                    "hits": hits,
                    "elapsed_ms": elapsed_ms,
                    "eval_view": view,
                    "error": err,
                },
                sort_keys=True,
            ),
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
