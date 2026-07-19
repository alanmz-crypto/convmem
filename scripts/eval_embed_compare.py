#!/usr/bin/env python3
"""Dual-view paired compare CLI (fixture or approved run-manifest).

Modes:
  injectable — hermetic scoring via --scores-json (fabricated clock labeled)
  subprocess — real query_units via CONVMEM_CONFIG workers (Gate 1 path)

Subprocess mode fails closed: worker errors, identity mismatches, or a
requested-but-unproven fallback abort the comparison with a nonzero exit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
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


def _sha_optional_file(path: Path) -> str:
    """Hash file content; absent file hashes as empty bytes (recorded honestly)."""
    if path.is_file():
        return _sha_file(path)
    return hashlib.sha256(b"").hexdigest()


def _parse_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"cannot parse config {path}: {exc}") from exc


def _arm_identity(arm: str, config_path: Path, chroma_dir: Path, embed_host: str) -> dict:
    """Extract and verify one arm's identity from its config file.

    Refuses when the config's embed host or chroma dir disagree with the
    authorized CLI arguments — --embed-host must be what workers actually use.
    """
    cfg = _parse_toml(config_path)
    models = cfg.get("models") or {}
    index = cfg.get("index") or {}
    cfg_host = str(models.get("ollama_host") or "")
    if cfg_host != embed_host:
        raise ValueError(
            f"{arm} config embed host {cfg_host!r} != --embed-host {embed_host!r}"
        )
    cfg_chroma = Path(str(index.get("chroma_dir") or "")).expanduser()
    if cfg_chroma.resolve(strict=False) != chroma_dir.resolve(strict=False):
        raise ValueError(
            f"{arm} config chroma_dir {cfg_chroma} != authorized {chroma_dir}"
        )
    return {
        "model_tag": str(models.get("embed_model") or "unspecified"),
        "config_sha256": _sha_file(config_path),
        "chroma_dir": str(chroma_dir.resolve(strict=False)),
        "embed_host": cfg_host,
        "enrichment_path": str(chroma_dir.parent / "decisions-approved.jsonl"),
        "enrichment_sha256": _sha_optional_file(
            chroma_dir.parent / "decisions-approved.jsonl"
        ),
    }


def _check_fallback_config_matches_arm(fallback_config: Path, arm_config: Path) -> None:
    """Fallback config must equal the arm config except models.ollama_host."""
    fb = _parse_toml(fallback_config)
    arm = _parse_toml(arm_config)
    fb_models = dict(fb.get("models") or {})
    arm_models = dict(arm.get("models") or {})
    fb_models.pop("ollama_host", None)
    arm_models.pop("ollama_host", None)
    fb_rest = {k: v for k, v in fb.items() if k != "models"}
    arm_rest = {k: v for k, v in arm.items() if k != "models"}
    if fb_models != arm_models or fb_rest != arm_rest:
        raise ValueError(
            "fallback config must differ from baseline config only in "
            "models.ollama_host"
        )


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
    parser.add_argument(
        "--exercise-fallback",
        action="store_true",
        help="Subprocess mode: prove the fallback path via --fallback-config",
    )
    parser.add_argument(
        "--fallback-config",
        type=Path,
        default=None,
        help="Config identical to baseline except models.ollama_host points at "
        "a dedicated wrong-dimension embed endpoint",
    )
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    from eval_corpus.io_atomic import atomic_write_json
    from eval_corpus.run_manifest import (
        DEFAULT_UNCERTAINTY,
        bind_compare,
        path_is_temp_contained,
    )
    from eval_corpus.runner import compare_paired_arms, measure_view_latency
    from eval_corpus.subprocess_compare import WorkerFailure

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

    # Per-arm content identities. In subprocess mode the configs are parsed and
    # verified against --embed-host and the authorized chroma dirs; in
    # injectable mode placeholders yield "unspecified" tags and empty-content
    # enrichment hashes (never fabricated 64-zero digests).
    try:
        if args.mode == "subprocess":
            baseline_id = _arm_identity(
                "baseline", baseline_config, baseline_chroma, args.embed_host
            )
            challenger_id = _arm_identity(
                "challenger", challenger_config, challenger_chroma, args.embed_host
            )
            if baseline_id["enrichment_sha256"] != challenger_id["enrichment_sha256"]:
                raise ValueError(
                    "arm enrichment mismatch: decisions-approved.jsonl must be "
                    "byte-identical across arms for a fair comparison"
                )
            enrichment_sha256 = baseline_id["enrichment_sha256"]
        else:
            baseline_id = {
                "model_tag": "unspecified",
                "config_sha256": _sha_optional_file(baseline_config),
            }
            challenger_id = {
                "model_tag": "unspecified",
                "config_sha256": _sha_optional_file(challenger_config),
            }
            enrichment_sha256 = hashlib.sha256(b"").hexdigest()
    except ValueError as exc:
        print(f"Refusing compare: {exc}", file=sys.stderr)
        return 2

    runtime = {
        "golden": golden,
        "package": package,
        "out": out,
        "baseline_chroma": baseline_chroma,
        "challenger_chroma": challenger_chroma,
        "baseline_config": baseline_config,
        "challenger_config": challenger_config,
        "baseline_model_tag": baseline_id["model_tag"],
        "challenger_model_tag": challenger_id["model_tag"],
        "baseline_config_sha256": baseline_id["config_sha256"],
        "challenger_config_sha256": challenger_id["config_sha256"],
        "embed_host": args.embed_host,
        "query_set_sha256": _sha_optional_file(golden),
        "corpus_package_sha256": _sha_optional_file(package),
        "enrichment_sha256": enrichment_sha256,
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
        report["fallback"] = {"status": "not_applicable_injectable"}
    else:
        from eval_corpus.subprocess_compare import (
            exercise_fallback_via_config,
            latency_summary,
            make_subprocess_query_fn,
            measure_warm_latency,
            run_one_shot_query,
            start_latency_worker,
            stop_latency_worker,
        )

        def expected_identity(config: Path, chroma: Path) -> dict:
            return {
                "config_path": str(config.resolve(strict=False)),
                "chroma_dir": str(chroma.resolve(strict=False)),
                "embed_host": args.embed_host,
            }

        baseline_expected = expected_identity(baseline_config, baseline_chroma)
        challenger_expected = expected_identity(challenger_config, challenger_chroma)

        try:
            # Identity probe: one one-shot per arm; banner recorded in report.
            probe_query = rows[0]["query"] if rows else "identity probe"
            baseline_probe = run_one_shot_query(
                config_path=baseline_config,
                query=probe_query,
                expected_identity=baseline_expected,
            )
            challenger_probe = run_one_shot_query(
                config_path=challenger_config,
                query=probe_query,
                expected_identity=challenger_expected,
            )

            baseline_fn = make_subprocess_query_fn(
                baseline_config, expected_identity=baseline_expected
            )
            challenger_fn = make_subprocess_query_fn(
                challenger_config, expected_identity=challenger_expected
            )
            report = compare_paired_arms(
                rows,
                baseline_fn,
                challenger_fn,
                package_units=package_units,
                uncertainty=uncertainty,
            )
        except WorkerFailure as exc:
            print(f"Compare aborted (fail closed): {exc}", file=sys.stderr)
            return 5

        report["arm_identity"] = {
            "baseline": {**baseline_id, "worker_startup": baseline_probe["startup"]},
            "challenger": {
                **challenger_id,
                "worker_startup": challenger_probe["startup"],
            },
        }
        report["embed_host"] = args.embed_host
        report["throughput"] = {
            "baseline_units_per_sec": args.baseline_units_per_sec,
            "challenger_units_per_sec": args.challenger_units_per_sec,
        }
        if not args.skip_latency:
            try:
                b_worker = start_latency_worker(
                    arm="baseline",
                    config_path=baseline_config,
                    expected_identity=baseline_expected,
                )
                c_worker = start_latency_worker(
                    arm="challenger",
                    config_path=challenger_config,
                    expected_identity=challenger_expected,
                )
            except WorkerFailure as exc:
                print(f"Compare aborted (fail closed): {exc}", file=sys.stderr)
                return 5
            try:
                lat_report = measure_warm_latency(
                    baseline=b_worker,
                    challenger=c_worker,
                    queries=[r["query"] for r in rows],
                )
                report["throughput"].update(latency_summary(lat_report))
            except WorkerFailure as exc:
                print(f"Compare aborted (fail closed): {exc}", file=sys.stderr)
                return 5
            finally:
                stop_latency_worker(b_worker)
                stop_latency_worker(c_worker)
        else:
            report["throughput"]["latency_source"] = "skipped"

        if args.exercise_fallback:
            if not args.fallback_config:
                print("--exercise-fallback requires --fallback-config", file=sys.stderr)
                return 3
            fallback_config = args.fallback_config.expanduser()
            if auth.execution_mode == "fixture" and not path_is_temp_contained(
                fallback_config
            ):
                print(
                    f"Refusing compare: fixture forbids non-temp fallback config "
                    f"{fallback_config}",
                    file=sys.stderr,
                )
                return 2
            try:
                _check_fallback_config_matches_arm(fallback_config, baseline_config)
            except ValueError as exc:
                print(f"Refusing compare: {exc}", file=sys.stderr)
                return 2
            try:
                fb = exercise_fallback_via_config(fallback_config_path=fallback_config)
            except WorkerFailure as exc:
                print(f"Compare aborted (fail closed): {exc}", file=sys.stderr)
                return 5
            if not fb["fallback_exercised"]:
                print(
                    "Compare aborted (fail closed): fallback requested but the "
                    f"fallback-only sentinel was not returned: {fb['hit_ids']}",
                    file=sys.stderr,
                )
                return 4
            report["fallback_exercised"] = True
            report["fallback"] = {
                "status": "exercised_dim_mismatch",
                "sentinel_id": fb["fallback_sentinel_id"],
                "hit_ids": fb["hit_ids"],
                "fallback_config_sha256": _sha_file(fallback_config),
            }
        else:
            report["fallback_exercised"] = False
            report["fallback"] = {"status": "not_requested"}

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
                "fallback_exercised": report["fallback_exercised"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
