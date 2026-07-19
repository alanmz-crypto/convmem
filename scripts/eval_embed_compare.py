#!/usr/bin/env python3
"""Dual-view paired compare CLI (fixture or approved run-manifest).

Modes:
  injectable — hermetic scoring via --scores-json (fabricated clock labeled)
  subprocess — real query_units via CONVMEM_CONFIG workers (Gate 1 path)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eval embed paired compare")
    parser.add_argument("--authorize-fixture", action="store_true")
    parser.add_argument("--run-manifest", type=Path, default=None)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="comparison manifest JSON")
    parser.add_argument(
        "--mode",
        choices=("injectable", "subprocess"),
        default="injectable",
    )
    parser.add_argument(
        "--scores-json",
        type=Path,
        help="Hermetic injectable: {baseline: {query: [hits]}, challenger: {...}}",
    )
    parser.add_argument("--baseline-chroma", type=Path, default=None)
    parser.add_argument("--challenger-chroma", type=Path, default=None)
    parser.add_argument("--baseline-config", type=Path, default=None)
    parser.add_argument("--challenger-config", type=Path, default=None)
    parser.add_argument("--embed-host", default="http://127.0.0.1:0")
    parser.add_argument("--baseline-units-per-sec", type=float, default=None)
    parser.add_argument("--challenger-units-per-sec", type=float, default=None)
    parser.add_argument(
        "--skip-latency",
        action="store_true",
        help="Subprocess mode: skip warm latency (still runs scoring one-shots)",
    )
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    from eval_corpus.io_atomic import atomic_write_json
    from eval_corpus.run_manifest import DEFAULT_UNCERTAINTY, bind_compare
    from eval_corpus.runner import compare_paired_arms, measure_view_latency

    golden = args.golden.expanduser()
    package = args.package.expanduser()
    out = args.out.expanduser()

    # Placeholder temp paths for injectable fixture when arms not supplied
    if args.mode == "injectable":
        base = out.parent
        baseline_chroma = (args.baseline_chroma or (base / "baseline_chroma")).expanduser()
        challenger_chroma = (args.challenger_chroma or (base / "challenger_chroma")).expanduser()
        baseline_config = (args.baseline_config or (base / "baseline.toml")).expanduser()
        challenger_config = (args.challenger_config or (base / "challenger.toml")).expanduser()
        # Ensure parents exist for path resolution; files need not exist for auth
        for p in (baseline_chroma, challenger_chroma):
            p.mkdir(parents=True, exist_ok=True)
        for p in (baseline_config, challenger_config):
            if not p.exists():
                p.write_text("# placeholder\n", encoding="utf-8")
    else:
        if not all(
            [
                args.baseline_chroma,
                args.challenger_chroma,
                args.baseline_config,
                args.challenger_config,
            ]
        ):
            print(
                "subprocess mode requires --baseline-chroma --challenger-chroma "
                "--baseline-config --challenger-config",
                file=sys.stderr,
            )
            return 3
        baseline_chroma = args.baseline_chroma.expanduser()
        challenger_chroma = args.challenger_chroma.expanduser()
        baseline_config = args.baseline_config.expanduser()
        challenger_config = args.challenger_config.expanduser()

    runtime = {
        "golden": golden,
        "package": package,
        "out": out,
        "baseline_chroma": baseline_chroma,
        "challenger_chroma": challenger_chroma,
        "baseline_config": baseline_config,
        "challenger_config": challenger_config,
        "embed_host": args.embed_host,
        "query_set_sha256": _sha_file(golden) if golden.is_file() else "0" * 64,
        "corpus_package_sha256": _sha_file(package) if package.is_file() else "0" * 64,
        "config_identity_sha256": _sha_file(baseline_config)
        if baseline_config.is_file()
        else "0" * 64,
        "enrichment_sha256": "0" * 64,
    }

    try:
        auth = bind_compare(
            authorize_fixture=args.authorize_fixture,
            run_manifest_path=args.run_manifest,
            runtime=runtime,
        )
    except Exception as exc:
        print(f"Refusing compare: {exc}", file=sys.stderr)
        return 2

    uncertainty = {**DEFAULT_UNCERTAINTY}
    for k in DEFAULT_UNCERTAINTY:
        if k in auth.manifest:
            uncertainty[k] = auth.manifest[k]

    rows = _load_jsonl(golden)
    package_units = _load_jsonl(package)

    if args.mode == "injectable":
        if not args.scores_json:
            print("injectable mode requires --scores-json", file=sys.stderr)
            return 3
        scores = json.loads(args.scores_json.expanduser().read_text(encoding="utf-8"))

        def make_fn(arm: str):
            table = scores[arm]

            def _fn(query, *, top_k, eval_view):
                hits = list(table.get(query) or [])
                return hits[:top_k]

            return _fn

        report = compare_paired_arms(
            rows,
            make_fn("baseline"),
            make_fn("challenger"),
            package_units=package_units,
            uncertainty=uncertainty,
        )
        queries = [r["query"] for r in rows]
        state = {"t": 0.0}

        def clock():
            state["t"] += 0.01
            return state["t"]

        lat = measure_view_latency(
            queries,
            make_fn("baseline"),
            view="embedding_influenced",
            clock=clock,
        )
        report["throughput"] = {
            "retrieval_queries_per_sec": round(1000.0 / lat.mean_ms, 6) if lat.mean_ms else 0.0,
            "baseline_units_per_sec": args.baseline_units_per_sec,
            "challenger_units_per_sec": args.challenger_units_per_sec,
            "latency_source": "fabricated_clock",
        }
        report["fallback_exercised"] = False
    else:
        from eval_corpus.subprocess_compare import (
            latency_summary,
            make_subprocess_query_fn,
            measure_warm_latency,
            start_latency_worker,
            stop_latency_worker,
        )

        baseline_fn = make_subprocess_query_fn(baseline_config)
        challenger_fn = make_subprocess_query_fn(challenger_config)
        report = compare_paired_arms(
            rows,
            baseline_fn,
            challenger_fn,
            package_units=package_units,
            uncertainty=uncertainty,
        )
        report["throughput"] = {
            "baseline_units_per_sec": args.baseline_units_per_sec,
            "challenger_units_per_sec": args.challenger_units_per_sec,
        }
        if not args.skip_latency:
            b_worker = start_latency_worker(arm="baseline", config_path=baseline_config)
            c_worker = start_latency_worker(arm="challenger", config_path=challenger_config)
            try:
                lat_report = measure_warm_latency(
                    baseline=b_worker,
                    challenger=c_worker,
                    queries=[r["query"] for r in rows],
                )
                report["throughput"].update(latency_summary(lat_report))
            finally:
                stop_latency_worker(b_worker)
                stop_latency_worker(c_worker)
        else:
            report["throughput"]["latency_source"] = "skipped"
        report["fallback_exercised"] = False

    report["run_manifest_execution_mode"] = auth.execution_mode
    report["compare_mode"] = args.mode
    report["not_promotion_authority"] = True
    atomic_write_json(out, report)
    print(
        json.dumps(
            {
                "out": str(out),
                "verdict": report.get("uncertainty", {}).get("verdict"),
                "mode": args.mode,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
