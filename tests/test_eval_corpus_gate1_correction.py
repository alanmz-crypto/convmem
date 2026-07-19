"""Gate 1 correction: binders, isolation, fallback, adversarial, schema fixtures."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# pylint: disable=too-many-lines,too-many-locals,duplicate-code
REPO = Path(__file__).resolve().parent.parent


class CanonicalOverlapPolicyTests(unittest.TestCase):
    def test_one_unit_canonical_not_pass(self):
        from eval_corpus.validate import validate_overlap

        units = [
            {
                "id": "u1",
                "document": "hello",
                "source_type": "conversation",
            }
        ]
        live = {"u1": "hello"}
        out = validate_overlap(units, live, capture_id="c1", policy="canonical")
        self.assertNotEqual(out["overall"], "PASS")
        self.assertEqual(out["overall"], "UNRESOLVED")

    def test_fixture_policy_allows_sparse_pass(self):
        from eval_corpus.validate import validate_overlap

        units = [{"id": "u1", "document": "hello", "source_type": "conversation"}]
        out = validate_overlap(
            units, {"u1": "hello"}, capture_id="c1", policy="fixture"
        )
        self.assertEqual(out["overall"], "PASS")


class OperationBinderAdversarialTests(unittest.TestCase):
    def test_empty_operations_refuse(self):
        from eval_corpus.run_manifest import assert_operation_allowed

        with self.assertRaises(PermissionError):
            assert_operation_allowed({"operations": []}, "capture")

    def test_real_self_hash_without_sidecar_refuse(self):
        from eval_corpus.run_manifest import (
            bind_capture,
            make_real_run_manifest_for_tests,
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = {
                "export": str(root / "e.jsonl"),
                "processed": str(root / "p.json"),
                "capture_dir": str(root / "cap"),
                "chroma_dir": str(root / "chroma"),
            }
            for p in paths.values():
                Path(p).parent.mkdir(parents=True, exist_ok=True)
                Path(p).write_text("x\n", encoding="utf-8")
            body = make_real_run_manifest_for_tests(
                paths=paths, operations=["capture"]
            )
            man = root / "run.json"
            man.write_text(json.dumps(body), encoding="utf-8")
            # No sidecar
            with self.assertRaises(PermissionError) as ctx:
                bind_capture(
                    authorize_fixture=False,
                    run_manifest_path=man,
                    runtime=paths,
                )
            self.assertIn("sidecar", str(ctx.exception).lower())

    def test_sidecar_ok_path_mismatch_refuse(self):
        from eval_corpus.run_manifest import (
            bind_capture,
            make_real_run_manifest_for_tests,
            write_approval_sidecar,
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = {
                "export": str(root / "e.jsonl"),
                "processed": str(root / "p.json"),
                "capture_dir": str(root / "cap"),
                "chroma_dir": str(root / "chroma"),
            }
            for p in paths.values():
                Path(p).parent.mkdir(parents=True, exist_ok=True)
                Path(p).write_text("x\n", encoding="utf-8")
            body = make_real_run_manifest_for_tests(
                paths=paths, operations=["capture"]
            )
            man = root / "run.json"
            man.write_text(json.dumps(body), encoding="utf-8")
            write_approval_sidecar(man)
            bad = dict(paths)
            bad["chroma_dir"] = str(root / "other_chroma")
            Path(bad["chroma_dir"]).mkdir()
            with self.assertRaises(PermissionError):
                bind_capture(
                    authorize_fixture=False,
                    run_manifest_path=man,
                    runtime=bad,
                )

    def test_tmp_substring_decoy_refuse(self):
        from eval_corpus.run_manifest import path_is_temp_contained

        decoy = Path.home() / "Projects" / "evil-tmp-escape" / "tmp" / "x"
        # Even if created, must not count as temp containment
        self.assertFalse(path_is_temp_contained(decoy))

    def test_compare_extra_field_refuse(self):
        from eval_corpus.run_manifest import bind_compare

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            runtime = {
                "compare_mode": "subprocess",
                "golden": root / "g.jsonl",
                "package": root / "p.jsonl",
                "out": root / "o.json",
                "baseline_chroma": root / "bc",
                "challenger_chroma": root / "cc",
                "baseline_config": root / "b.toml",
                "challenger_config": root / "c.toml",
                "baseline_model_tag": "fake-a",
                "challenger_model_tag": "fake-b",
                "baseline_config_sha256": "0" * 64,
                "challenger_config_sha256": "0" * 64,
                "embed_host": "http://127.0.0.1:1",
                "query_set_sha256": "0" * 64,
                "corpus_package_sha256": "0" * 64,
                "enrichment_sha256": "0" * 64,
                "extra": "nope",
            }
            for k in (
                "golden",
                "package",
                "out",
                "baseline_config",
                "challenger_config",
            ):
                Path(runtime[k]).write_text("x\n", encoding="utf-8")
            for k in ("baseline_chroma", "challenger_chroma"):
                Path(runtime[k]).mkdir()
            with self.assertRaises(PermissionError) as ctx:
                bind_compare(
                    authorize_fixture=True,
                    run_manifest_path=None,
                    runtime=runtime,
                )
            self.assertIn("extra", str(ctx.exception))

    def test_per_arm_build_model_tags(self):
        """One real manifest can authorize distinct baseline/challenger models."""
        from eval_corpus.run_manifest import (
            bind_baseline_build,
            bind_challenger_build,
            make_real_run_manifest_for_tests,
            write_approval_sidecar,
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = {
                "package": str(root / "pkg.jsonl"),
                "manifest": str(root / "bm.json"),
                "chroma_dir": str(root / "chroma"),
                "result": str(root / "result.json"),
                "journal": str(root / "journal.jsonl"),
                "capture_dir": str(root / "cap"),
            }
            for p in paths.values():
                Path(p).parent.mkdir(parents=True, exist_ok=True)
            body = make_real_run_manifest_for_tests(
                paths=paths,
                operations=["baseline_build", "challenger_build"],
                model_tag="nomic-embed-text",
                baseline_model_tag="nomic-embed-text",
                challenger_model_tag="challenger-embed-x",
            )
            man = root / "run.json"
            man.write_text(json.dumps(body), encoding="utf-8")
            write_approval_sidecar(man)

            def runtime(tag: str) -> dict:
                return {
                    **paths,
                    "model_tag": tag,
                    "embed_host": "http://127.0.0.1:0",
                    "corpus_package_sha256": "b" * 64,
                    "unit_corpus_fingerprint": "c" * 64,
                    "config_identity_sha256": "f" * 64,
                    "enrichment_sha256": "e" * 64,
                    "build_identity": "test-build",
                }

            ctx = bind_baseline_build(
                authorize_fixture=False,
                run_manifest_path=man,
                runtime=runtime("nomic-embed-text"),
            )
            self.assertTrue(ctx.require_corpus_acceptance)
            ctx = bind_challenger_build(
                authorize_fixture=False,
                run_manifest_path=man,
                runtime=runtime("challenger-embed-x"),
            )
            self.assertTrue(ctx.require_corpus_acceptance)
            with self.assertRaises(PermissionError):
                bind_baseline_build(
                    authorize_fixture=False,
                    run_manifest_path=man,
                    runtime=runtime("challenger-embed-x"),
                )
            with self.assertRaises(PermissionError):
                bind_challenger_build(
                    authorize_fixture=False,
                    run_manifest_path=man,
                    runtime=runtime("nomic-embed-text"),
                )

    def test_model_exec_required_for_ollama(self):
        from eval_corpus.run_manifest import (
            bind_model_execution,
            make_real_run_manifest_for_tests,
            write_approval_sidecar,
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            chroma.mkdir()
            paths = {
                "embed_host": "http://127.0.0.1:9",
                "chroma_dir": str(chroma),
            }
            body = make_real_run_manifest_for_tests(
                paths={
                    "export": str(root / "e"),
                    "processed": str(root / "p"),
                    "capture_dir": str(root / "c"),
                    "chroma_dir": str(chroma),
                    "embed_host": paths["embed_host"],
                },
                operations=["baseline_build"],  # no model_exec
                model_tag="nomic",
            )
            man = root / "run.json"
            man.write_text(json.dumps(body), encoding="utf-8")
            write_approval_sidecar(man)
            with self.assertRaises(PermissionError):
                bind_model_execution(
                    authorize_fixture=False,
                    run_manifest_path=man,
                    runtime={
                        "model_tag": "nomic",
                        "embed_host": paths["embed_host"],
                        "chroma_dir": chroma,
                    },
                )


class MethodologySchemaFixtureTests(unittest.TestCase):
    def test_categories_present_not_real_pilot(self):
        qpath = REPO / "tests/fixtures/eval_methodology_schema_queries.jsonl"
        rows = [
            json.loads(l)
            for l in qpath.read_text().splitlines()
            if l.strip()
        ]
        cats = {r["category"] for r in rows}
        required = {
            "architecture",
            "debugging",
            "current-state",
            "exact-identifier",
            "cross-surface",
            "temporal",
            "known-failure",
        }
        self.assertTrue(required.issubset(cats))
        self.assertGreaterEqual(len(rows), 25)
        self.assertLessEqual(len(rows), 40)
        # Must not claim these are live corpus IDs
        self.assertTrue(qpath.name.startswith("eval_methodology_schema_"))


class SubprocessIsolationAndFallbackTests(unittest.TestCase):
    def test_shadow_vs_canary_and_dim_mismatch_fallback(self):
        from eval_corpus.embed_adapters import (
            fake_embed_fn,
            start_canary_embed_server,
            start_fake_embed_server,
            stop_fake_embed_server,
        )
        from eval_corpus.fingerprint import corpus_fingerprint_hex, package_sha256_hex
        from eval_corpus.reconstruct import build_canonical_unit
        from eval_corpus.shadow_build import run_shadow_build
        from eval_corpus.shadow_config import generate_shadow_config
        from eval_corpus.subprocess_compare import (
            FALLBACK_SENTINEL_ID,
            FALLBACK_SENTINEL_TOKEN,
            exercise_dim_mismatch_fallback,
            run_one_shot_query,
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Unreachable live paths + canary endpoint
            live_root = root / "LIVE_UNREACHABLE"
            live_root.mkdir()
            live_chroma = live_root / "chroma"
            live_chroma.mkdir()
            (live_root / "decisions-approved.jsonl").write_text(
                json.dumps(
                    {
                        "id": "dec_prop_LIVE_SHOULD_NOT_APPEAR",
                        "summary": "LIVE_ENRICHMENT_SHOULD_NOT_APPEAR",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            canary_srv, canary_url, _ct, canary_state = start_canary_embed_server()
            shadow_srv, shadow_url, _st, shadow_state = start_fake_embed_server(
                dimensions=8
            )
            try:
                unit = build_canonical_unit(
                    {
                        "id": "ord_shadow_1",
                        "summary": "shadow ordinary retrieval unit about widgets",
                        "keywords": ["widgets", "shadow"],
                        "tool": "t",
                        "source_path": "site:shadow",
                    }
                )
                sentinel = build_canonical_unit(
                    {
                        "id": FALLBACK_SENTINEL_ID,
                        "summary": f"keyword only {FALLBACK_SENTINEL_TOKEN}",
                        "keywords": [FALLBACK_SENTINEL_TOKEN, "fallback"],
                        "tool": "t",
                        "source_path": "site:shadow",
                    }
                )
                units = [unit, sentinel]
                arm = root / "arm"
                arm.mkdir()
                chroma = arm / "chroma"
                manifest = {
                    "embed_model": "fake-embed",
                    "embed_dimensions": 8,
                    "unit_corpus_fingerprint": corpus_fingerprint_hex(units),
                    "package_sha256": package_sha256_hex(units),
                    "unit_count": len(units),
                    "batch_size": 2,
                    "schema_version": "1",
                }
                run_shadow_build(
                    units=units,
                    chroma_dir=chroma,
                    manifest=manifest,
                    embed_fn=fake_embed_fn(8),
                    manifest_path=arm / "manifest.json",
                    result_path=arm / "result.json",
                )
                # Frozen shadow enrichment (unique)
                enrich = {
                    "id": "dec_prop_FROZEN_SHADOW_Q7",
                    "summary": "FROZEN_SHADOW_ENRICHMENT_TOKEN_Q7 unique",
                    "status": "approved",
                }
                (arm / "decisions-approved.jsonl").write_text(
                    json.dumps(enrich) + "\n", encoding="utf-8"
                )
                live_cfg = {
                    "index": {
                        "chroma_dir": str(live_chroma),
                        "processed_log": str(live_root / "processed.json"),
                        "units_export": str(live_root / "ku.jsonl"),
                    },
                    "models": {
                        "embed_model": "nomic-embed-text",
                        "ollama_host": canary_url,
                        "rerank_model": "x",
                    },
                    "query": {"rerank": False},
                    "eval": {"retrieval_view": "embedding_influenced"},
                }
                cfg_path, violations = generate_shadow_config(
                    live_cfg=live_cfg,
                    out_dir=arm / "cfg",
                    chroma_dir=chroma,
                    embed_model="fake-embed",
                    ollama_host=shadow_url,
                )
                self.assertEqual(violations, [])
                before_canary = canary_state.snapshot_count()
                before_shadow = shadow_state.snapshot_count()
                payload = run_one_shot_query(
                    config_path=cfg_path,
                    query="widgets shadow retrieval",
                    top_k=5,
                    eval_view="embedding_influenced",
                )
                self.assertEqual(payload["returncode"], 0, payload.get("stderr"))
                startup = payload["startup"]
                self.assertEqual(startup["embed_host"], shadow_url)
                self.assertEqual(
                    Path(startup["chroma_dir"]).resolve(), chroma.resolve()
                )
                self.assertEqual(
                    Path(startup["data_dir"]).resolve(), arm.resolve()
                )
                self.assertGreater(shadow_state.snapshot_count(), before_shadow)
                self.assertEqual(canary_state.snapshot_count(), before_canary)

                # SQLite must remain present/readable (do not rename/remove it).
                sqlite = chroma / "chroma.sqlite3"
                self.assertTrue(sqlite.is_file())

                def force(flag: bool) -> None:
                    shadow_state.force_wrong_dim = flag
                    shadow_state.wrong_dimensions = 3

                fb = exercise_dim_mismatch_fallback(
                    config_path=cfg_path,
                    shadow_state_force_wrong=force,
                )
                self.assertTrue(fb["fallback_exercised"], fb)
                self.assertTrue(sqlite.is_file())
                from chroma_readonly import collection_metadata_rows

                rows = collection_metadata_rows(chroma, "knowledge_units")
                self.assertTrue(any(r.get("id") == FALLBACK_SENTINEL_ID for r in rows))
                self.assertEqual(canary_state.snapshot_count(), before_canary)
            finally:
                stop_fake_embed_server(shadow_srv)
                stop_fake_embed_server(canary_srv)


class WarmLatencyWorkerSmokeTests(unittest.TestCase):
    def test_persistent_workers_report_startup_separately(self):
        from eval_corpus.embed_adapters import (
            fake_embed_fn,
            start_fake_embed_server,
            stop_fake_embed_server,
        )
        from eval_corpus.fingerprint import corpus_fingerprint_hex, package_sha256_hex
        from eval_corpus.reconstruct import build_canonical_unit
        from eval_corpus.shadow_build import run_shadow_build
        from eval_corpus.shadow_config import generate_shadow_config
        from eval_corpus.subprocess_compare import (
            latency_summary,
            measure_warm_latency,
            start_latency_worker,
            stop_latency_worker,
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            srv, url, _t, _s = start_fake_embed_server(dimensions=8)
            try:
                unit = build_canonical_unit(
                    {
                        "id": "lat1",
                        "summary": "latency unit text alpha",
                        "keywords": ["latency"],
                        "tool": "t",
                        "source_path": "site:x",
                    }
                )
                units = [unit]
                configs = []
                for arm in ("baseline", "challenger"):
                    arm_dir = root / arm
                    arm_dir.mkdir()
                    chroma = arm_dir / "chroma"
                    manifest = {
                        "embed_model": "fake-embed",
                        "embed_dimensions": 8,
                        "unit_corpus_fingerprint": corpus_fingerprint_hex(units),
                        "package_sha256": package_sha256_hex(units),
                        "unit_count": 1,
                        "batch_size": 1,
                        "schema_version": "1",
                    }
                    run_shadow_build(
                        units=units,
                        chroma_dir=chroma,
                        manifest=manifest,
                        embed_fn=fake_embed_fn(8),
                        manifest_path=arm_dir / "m.json",
                        result_path=arm_dir / "r.json",
                    )
                    live_cfg = {
                        "index": {"chroma_dir": str(root / "dead")},
                        "models": {
                            "embed_model": "x",
                            "ollama_host": "http://127.0.0.1:1",
                            "rerank_model": "x",
                        },
                        "query": {"rerank": False},
                        "eval": {},
                    }
                    cfg, _v = generate_shadow_config(
                        live_cfg=live_cfg,
                        out_dir=arm_dir / "cfg",
                        chroma_dir=chroma,
                        embed_model="fake-embed",
                        ollama_host=url,
                    )
                    configs.append(cfg)
                b = start_latency_worker(arm="baseline", config_path=configs[0])
                c = start_latency_worker(arm="challenger", config_path=configs[1])
                try:
                    report = measure_warm_latency(
                        baseline=b,
                        challenger=c,
                        queries=["latency unit text alpha"],
                        top_k=3,
                    )
                    # Shrink protocol in test? Full 5+20 is slow but required.
                    summary = latency_summary(report)
                    self.assertEqual(
                        summary["latency_source"], "warm_persistent_workers"
                    )
                    self.assertIn("process_startup_ms", summary)
                    self.assertNotIn(
                        summary["process_startup_ms"]["baseline"],
                        summary["retrieval_ms"]["embedding_influenced"]["baseline"][
                            "samples"
                        ],
                    )
                    self.assertEqual(
                        summary["retrieval_ms"]["embedding_influenced"]["baseline"]["n"],
                        20,
                    )
                    self.assertEqual(
                        summary["retrieval_ms"]["operational_pipeline"]["challenger"]["n"],
                        20,
                    )
                finally:
                    stop_latency_worker(b)
                    stop_latency_worker(c)
            finally:
                stop_fake_embed_server(srv)


def _build_arm(
    *,
    arm_dir: Path,
    units: list[dict],
    embed_host: str,
    live_cfg: dict,
) -> tuple[Path, Path]:
    """Shadow-build one arm and generate its config; returns (chroma, config)."""
    from eval_corpus.embed_adapters import fake_embed_fn
    from eval_corpus.fingerprint import corpus_fingerprint_hex, package_sha256_hex
    from eval_corpus.shadow_build import run_shadow_build
    from eval_corpus.shadow_config import generate_shadow_config

    arm_dir.mkdir(parents=True, exist_ok=True)
    chroma = arm_dir / "chroma"
    manifest = {
        "embed_model": "fake-embed",
        "embed_dimensions": 8,
        "unit_corpus_fingerprint": corpus_fingerprint_hex(units),
        "package_sha256": package_sha256_hex(units),
        "unit_count": len(units),
        "batch_size": 4,
        "schema_version": "1",
    }
    run_shadow_build(
        units=units,
        chroma_dir=chroma,
        manifest=manifest,
        embed_fn=fake_embed_fn(8),
        manifest_path=arm_dir / "manifest.json",
        result_path=arm_dir / "result.json",
    )
    cfg, violations = generate_shadow_config(
        live_cfg=live_cfg,
        out_dir=arm_dir / "cfg",
        chroma_dir=chroma,
        embed_model="fake-embed",
        ollama_host=embed_host,
    )
    assert not violations
    return chroma, cfg


class EndToEndSubprocessCompareTests(unittest.TestCase):
    """Codex re-verify finding 4: full loop through eval_embed_compare.py."""

    def test_full_subprocess_compare_loop(self):
        from eval_corpus.embed_adapters import (
            start_canary_embed_server,
            start_fake_embed_server,
            stop_fake_embed_server,
        )
        from eval_corpus.reconstruct import build_canonical_unit
        from eval_corpus.shadow_config import generate_shadow_config
        from eval_corpus.subprocess_compare import (
            FALLBACK_SENTINEL_ID,
            FALLBACK_SENTINEL_TOKEN,
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            canary_srv, canary_url, _ct, canary_state = start_canary_embed_server()
            shadow_srv, shadow_url, _st, shadow_state = start_fake_embed_server(
                dimensions=8
            )
            # Dedicated always-wrong-dimension endpoint for the fallback proof.
            wrong_srv, wrong_url, _wt, wrong_state = start_fake_embed_server(
                dimensions=8
            )
            wrong_state.wrong_dimensions = 3
            wrong_state.force_wrong_dim = True
            try:
                units = [
                    build_canonical_unit(
                        {
                            "id": "ord_e2e_1",
                            "summary": "end to end widgets alpha retrieval unit",
                            "keywords": ["widgets", "alpha"],
                            "tool": "t",
                            "source_path": "site:e2e",
                        }
                    ),
                    build_canonical_unit(
                        {
                            "id": "ord_e2e_2",
                            "summary": "end to end gizmos beta retrieval unit",
                            "keywords": ["gizmos", "beta"],
                            "tool": "t",
                            "source_path": "site:e2e",
                        }
                    ),
                    build_canonical_unit(
                        {
                            "id": FALLBACK_SENTINEL_ID,
                            "summary": f"keyword only {FALLBACK_SENTINEL_TOKEN}",
                            "keywords": [FALLBACK_SENTINEL_TOKEN, "fallback"],
                            "tool": "t",
                            "source_path": "site:e2e",
                        }
                    ),
                ]
                live_cfg = {
                    "index": {"chroma_dir": str(root / "LIVE_UNREACHABLE" / "chroma")},
                    "models": {
                        "embed_model": "nomic-embed-text",
                        "ollama_host": canary_url,
                        "rerank_model": "x",
                    },
                    "query": {"rerank": False},
                    "eval": {"retrieval_view": "embedding_influenced"},
                }
                arms: dict[str, tuple[Path, Path]] = {}
                enrich_line = (
                    json.dumps(
                        {
                            "id": "dec_prop_FROZEN_E2E",
                            "summary": "FROZEN_E2E_ENRICHMENT unique",
                            "status": "approved",
                        }
                    )
                    + "\n"
                )
                for arm in ("baseline", "challenger"):
                    arm_dir = root / arm
                    chroma, cfg = _build_arm(
                        arm_dir=arm_dir,
                        units=units,
                        embed_host=shadow_url,
                        live_cfg=live_cfg,
                    )
                    # Frozen enrichment, byte-identical across arms.
                    (arm_dir / "decisions-approved.jsonl").write_text(
                        enrich_line, encoding="utf-8"
                    )
                    arms[arm] = (chroma, cfg)

                # Fallback config: baseline arm, wrong-dim endpoint only.
                fb_cfg, fb_violations = generate_shadow_config(
                    live_cfg=live_cfg,
                    out_dir=root / "baseline" / "fallback_cfg",
                    chroma_dir=arms["baseline"][0],
                    embed_model="fake-embed",
                    ollama_host=wrong_url,
                )
                self.assertEqual(fb_violations, [])

                golden = root / "golden.jsonl"
                golden_rows = [
                    {
                        "query": "widgets alpha retrieval",
                        "relevant": [{"id": "ord_e2e_1", "namespace": "unit_id"}],
                        "recipe_stratum": "ordinary",
                    },
                    {
                        "query": "gizmos beta retrieval",
                        "relevant": [{"id": "ord_e2e_2", "namespace": "unit_id"}],
                        "recipe_stratum": "ordinary",
                    },
                ]
                golden.write_text(
                    "\n".join(json.dumps(r) for r in golden_rows) + "\n",
                    encoding="utf-8",
                )
                package = root / "package.jsonl"
                package.write_text(
                    "\n".join(json.dumps(u) for u in units) + "\n", encoding="utf-8"
                )
                out = root / "compare.json"

                before_canary = canary_state.snapshot_count()
                before_shadow = shadow_state.snapshot_count()
                argv = [
                    sys.executable,
                    str(REPO / "scripts/eval_embed_compare.py"),
                    "--authorize-fixture",
                    "--mode",
                    "subprocess",
                    "--golden",
                    str(golden),
                    "--package",
                    str(package),
                    "--out",
                    str(out),
                    "--baseline-chroma",
                    str(arms["baseline"][0]),
                    "--challenger-chroma",
                    str(arms["challenger"][0]),
                    "--baseline-config",
                    str(arms["baseline"][1]),
                    "--challenger-config",
                    str(arms["challenger"][1]),
                    "--embed-host",
                    shadow_url,
                    "--exercise-fallback",
                    "--fallback-config",
                    str(fb_cfg),
                ]
                proc = subprocess.run(
                    argv, cwd=str(REPO), capture_output=True, text=True, check=False
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                report = json.loads(out.read_text(encoding="utf-8"))

                # Both arms, both views scored.
                for arm in ("baseline", "challenger"):
                    for view in ("embedding_influenced", "operational_pipeline"):
                        self.assertIn(view, report["diagnostic_views"][arm])
                        self.assertEqual(
                            report["diagnostic_views"][arm][view]["count"], 2
                        )

                # Shadow endpoint served traffic; live canary saw zero requests.
                self.assertGreater(shadow_state.snapshot_count(), before_shadow)
                self.assertEqual(canary_state.snapshot_count(), before_canary)

                # Startup identities match authorized paths/hosts, per arm.
                for arm in ("baseline", "challenger"):
                    startup = report["arm_identity"][arm]["worker_startup"]
                    self.assertEqual(startup["embed_host"], shadow_url)
                    self.assertEqual(
                        Path(startup["chroma_dir"]).resolve(),
                        arms[arm][0].resolve(),
                    )
                    self.assertEqual(
                        Path(startup["config_path"]).resolve(),
                        arms[arm][1].resolve(),
                    )
                    self.assertEqual(
                        report["arm_identity"][arm]["model_tag"], "fake-embed"
                    )
                self.assertNotEqual(
                    report["arm_identity"]["baseline"]["config_sha256"],
                    report["arm_identity"]["challenger"]["config_sha256"],
                )

                # Provenance block: recomputed identity + per-arm contents.
                prov = report["provenance"]
                self.assertEqual(prov["unit_count"], 3)
                self.assertEqual(len(prov["package_sha256"]), 64)
                self.assertEqual(len(prov["unit_corpus_fingerprint"]), 64)
                self.assertIsNone(prov["approved_manifest_body_sha256"])
                self.assertIsNone(prov["run_manifest_file_sha256"])
                self.assertIsNone(prov["build_result_sha256"])
                for arm in ("baseline", "challenger"):
                    coll = prov["collections"][arm]
                    self.assertEqual(coll["actual_row_count"], 3)
                    self.assertEqual(
                        coll["actual_id_set_fingerprint"],
                        prov["package_id_set_fingerprint"],
                    )
                    self.assertEqual(
                        coll["stored_metadata"]["convmem:embed_model"], "fake-embed"
                    )

                # Fallback sentinel returned and recorded.
                self.assertTrue(report["fallback_exercised"])
                self.assertEqual(
                    report["fallback"]["sentinel_id"], FALLBACK_SENTINEL_ID
                )
                self.assertIn(FALLBACK_SENTINEL_ID, report["fallback"]["hit_ids"])

                # Warm latency reported separately from process startup.
                tp = report["throughput"]
                self.assertEqual(tp["latency_source"], "warm_persistent_workers")
                self.assertEqual(tp["warmups_discarded"], 5)
                self.assertEqual(tp["timed_repetitions"], 20)
                self.assertIn("process_startup_ms", tp)
                for view in ("embedding_influenced", "operational_pipeline"):
                    for arm in ("baseline", "challenger"):
                        self.assertEqual(tp["retrieval_ms"][view][arm]["n"], 20)
                        for sample in tp["retrieval_ms"][view][arm]["samples"]:
                            self.assertGreater(sample, 0.0)
            finally:
                stop_fake_embed_server(shadow_srv)
                stop_fake_embed_server(canary_srv)
                stop_fake_embed_server(wrong_srv)

    def test_worker_failure_stops_comparison(self):
        """A broken arm must abort the compare, not fabricate misses.

        The challenger store passes the read-only provenance gate, but its
        config carries a non-integer query.top_k_candidates, so query_units
        crashes inside the worker after provenance passed — the compare must
        exit 5, not report empty hits.
        """
        from eval_corpus.embed_adapters import (
            start_fake_embed_server,
            stop_fake_embed_server,
        )
        from eval_corpus.reconstruct import build_canonical_unit

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            srv, url, _t, _s = start_fake_embed_server(dimensions=8)
            try:
                units = [
                    build_canonical_unit(
                        {
                            "id": "ord_fail_1",
                            "summary": "fail closed widgets unit",
                            "keywords": ["widgets"],
                            "tool": "t",
                            "source_path": "site:x",
                        }
                    )
                ]
                live_cfg = {
                    "index": {"chroma_dir": str(root / "dead")},
                    "models": {
                        "embed_model": "x",
                        "ollama_host": "http://127.0.0.1:1",
                        "rerank_model": "x",
                    },
                    "query": {"rerank": False},
                    "eval": {},
                }
                b_chroma, b_cfg = _build_arm(
                    arm_dir=root / "baseline",
                    units=units,
                    embed_host=url,
                    live_cfg=live_cfg,
                )
                c_chroma, c_cfg = _build_arm(
                    arm_dir=root / "challenger",
                    units=units,
                    embed_host=url,
                    live_cfg=live_cfg,
                )
                # Poison the challenger worker config (parses fine; identity
                # checks pass; query_units crashes on int("bogus")).
                text = c_cfg.read_text(encoding="utf-8")
                self.assertIn("rerank = false", text)
                c_cfg.write_text(
                    text.replace(
                        "rerank = false",
                        'rerank = false\ntop_k_candidates = "bogus"',
                    ),
                    encoding="utf-8",
                )
                for arm_dir in (root / "baseline", root / "challenger"):
                    (arm_dir / "decisions-approved.jsonl").write_text(
                        "", encoding="utf-8"
                    )
                golden = root / "golden.jsonl"
                golden.write_text(
                    json.dumps(
                        {
                            "query": "fail closed widgets",
                            "relevant": [{"id": "ord_fail_1", "namespace": "unit_id"}],
                            "recipe_stratum": "ordinary",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                package = root / "package.jsonl"
                package.write_text(
                    json.dumps(units[0]) + "\n", encoding="utf-8"
                )
                out = root / "compare.json"
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(REPO / "scripts/eval_embed_compare.py"),
                        "--authorize-fixture",
                        "--mode",
                        "subprocess",
                        "--skip-latency",
                        "--golden",
                        str(golden),
                        "--package",
                        str(package),
                        "--out",
                        str(out),
                        "--baseline-chroma",
                        str(b_chroma),
                        "--challenger-chroma",
                        str(c_chroma),
                        "--baseline-config",
                        str(b_cfg),
                        "--challenger-config",
                        str(c_cfg),
                        "--embed-host",
                        url,
                    ],
                    cwd=str(REPO),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 5, proc.stderr)
                self.assertIn("fail closed", proc.stderr)
                self.assertFalse(out.exists())
            finally:
                stop_fake_embed_server(srv)

    def test_embed_host_mismatch_refused(self):
        """--embed-host must match what the worker configs actually use."""
        from eval_corpus.embed_adapters import (
            start_fake_embed_server,
            stop_fake_embed_server,
        )
        from eval_corpus.reconstruct import build_canonical_unit

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            srv, url, _t, _s = start_fake_embed_server(dimensions=8)
            try:
                units = [
                    build_canonical_unit(
                        {
                            "id": "ord_h_1",
                            "summary": "host mismatch unit",
                            "keywords": ["host"],
                            "tool": "t",
                            "source_path": "site:x",
                        }
                    )
                ]
                live_cfg = {
                    "index": {"chroma_dir": str(root / "dead")},
                    "models": {
                        "embed_model": "x",
                        "ollama_host": "http://127.0.0.1:1",
                        "rerank_model": "x",
                    },
                    "query": {"rerank": False},
                    "eval": {},
                }
                arms = {}
                for arm in ("baseline", "challenger"):
                    arms[arm] = _build_arm(
                        arm_dir=root / arm,
                        units=units,
                        embed_host=url,
                        live_cfg=live_cfg,
                    )
                golden = root / "golden.jsonl"
                golden.write_text(
                    json.dumps(
                        {
                            "query": "host mismatch",
                            "relevant": [{"id": "ord_h_1", "namespace": "unit_id"}],
                            "recipe_stratum": "ordinary",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                package = root / "package.jsonl"
                package.write_text(json.dumps(units[0]) + "\n", encoding="utf-8")
                out = root / "compare.json"
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(REPO / "scripts/eval_embed_compare.py"),
                        "--authorize-fixture",
                        "--mode",
                        "subprocess",
                        "--skip-latency",
                        "--golden",
                        str(golden),
                        "--package",
                        str(package),
                        "--out",
                        str(out),
                        "--baseline-chroma",
                        str(arms["baseline"][0]),
                        "--challenger-chroma",
                        str(arms["challenger"][0]),
                        "--baseline-config",
                        str(arms["baseline"][1]),
                        "--challenger-config",
                        str(arms["challenger"][1]),
                        "--embed-host",
                        "http://127.0.0.1:65500",  # not what configs use
                    ],
                    cwd=str(REPO),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("embed host", proc.stderr)
                self.assertFalse(out.exists())
            finally:
                stop_fake_embed_server(srv)


class CollectionProvenanceGateTests(unittest.TestCase):
    """Codex final gate: compare must verify both shadow collections against
    the approved package — stored metadata AND actual contents — before any
    worker starts. Each tamper flips exactly one field so the failing guard
    is unambiguous."""

    COLLECTION = "knowledge_units"

    def _tamper(self, chroma_dir: Path, sql: str, params: tuple = ()) -> None:
        import sqlite3

        conn = sqlite3.connect(chroma_dir / "chroma.sqlite3")
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def _run_compare(self, ctx: dict) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(REPO / "scripts/eval_embed_compare.py"),
                "--authorize-fixture",
                "--mode",
                "subprocess",
                "--skip-latency",
                "--golden",
                str(ctx["golden"]),
                "--package",
                str(ctx["package"]),
                "--out",
                str(ctx["out"]),
                "--baseline-chroma",
                str(ctx["arms"]["baseline"][0]),
                "--challenger-chroma",
                str(ctx["arms"]["challenger"][0]),
                "--baseline-config",
                str(ctx["arms"]["baseline"][1]),
                "--challenger-config",
                str(ctx["arms"]["challenger"][1]),
                "--embed-host",
                ctx["url"],
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            check=False,
        )

    def _setup_valid_pair(self, root: Path, url: str) -> dict:
        from eval_corpus.reconstruct import build_canonical_unit

        units = [
            build_canonical_unit(
                {
                    "id": f"ord_prov_{i}",
                    "summary": f"provenance unit {i} widgets",
                    "keywords": ["widgets", f"p{i}"],
                    "tool": "t",
                    "source_path": "site:x",
                }
            )
            for i in (1, 2)
        ]
        live_cfg = {
            "index": {"chroma_dir": str(root / "dead")},
            "models": {
                "embed_model": "x",
                "ollama_host": "http://127.0.0.1:1",
                "rerank_model": "x",
            },
            "query": {"rerank": False},
            "eval": {},
        }
        arms = {}
        for arm in ("baseline", "challenger"):
            arms[arm] = _build_arm(
                arm_dir=root / arm,
                units=units,
                embed_host=url,
                live_cfg=live_cfg,
            )
            (root / arm / "decisions-approved.jsonl").write_text("", encoding="utf-8")
        golden = root / "golden.jsonl"
        golden.write_text(
            json.dumps(
                {
                    "query": "provenance widgets",
                    "relevant": [{"id": "ord_prov_1", "namespace": "unit_id"}],
                    "recipe_stratum": "ordinary",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        package = root / "package.jsonl"
        package.write_text(
            "\n".join(json.dumps(u) for u in units) + "\n", encoding="utf-8"
        )
        return {
            "units": units,
            "arms": arms,
            "golden": golden,
            "package": package,
            "out": root / "compare.json",
            "url": url,
            "live_cfg": live_cfg,
        }

    def test_isolated_provenance_mismatches_refuse(self):
        from eval_corpus.embed_adapters import (
            start_fake_embed_server,
            stop_fake_embed_server,
        )

        srv, url, _t, _s = start_fake_embed_server(dimensions=8)
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                ctx = self._setup_valid_pair(root, url)
                c_chroma = ctx["arms"]["challenger"][0]
                pristine = root / "challenger_chroma_pristine"
                shutil.copytree(c_chroma, pristine)

                meta_update = (
                    "UPDATE collection_metadata SET str_value=? "
                    "WHERE key=? AND collection_id IN "
                    "(SELECT id FROM collections WHERE name=?)"
                )
                content_row_subquery = (
                    "SELECT e.id FROM embeddings e "
                    "JOIN segments s ON e.segment_id=s.id "
                    "JOIN collections c ON s.collection=c.id "
                    "WHERE c.name=? AND s.scope='METADATA' AND e.embedding_id=?"
                )
                cases = [
                    (
                        "fingerprint_only",
                        meta_update,
                        ("0" * 64, "convmem:unit_corpus_fingerprint", self.COLLECTION),
                        "convmem:unit_corpus_fingerprint",
                    ),
                    (
                        "package_sha_only",
                        meta_update,
                        ("1" * 64, "convmem:package_sha256", self.COLLECTION),
                        "convmem:package_sha256",
                    ),
                    (
                        "model_only",
                        meta_update,
                        ("other-model", "convmem:embed_model", self.COLLECTION),
                        "convmem:embed_model",
                    ),
                    (
                        "unit_count_only",
                        "UPDATE collection_metadata SET int_value=99, str_value=NULL "
                        "WHERE key='convmem:unit_count' AND collection_id IN "
                        "(SELECT id FROM collections WHERE name=?)",
                        (self.COLLECTION,),
                        "convmem:unit_count",
                    ),
                    (
                        "missing_provenance",
                        "DELETE FROM collection_metadata "
                        "WHERE key LIKE 'convmem:%' AND collection_id IN "
                        "(SELECT id FROM collections WHERE name=?)",
                        (self.COLLECTION,),
                        "missing shadow provenance",
                    ),
                    (
                        "incomplete_collection_correct_metadata",
                        f"DELETE FROM embeddings WHERE id IN ({content_row_subquery})",
                        (self.COLLECTION, "ord_prov_2"),
                        "actual row count",
                    ),
                    (
                        "substituted_id_same_count",
                        "UPDATE embeddings SET embedding_id='ord_SUBSTITUTED' "
                        f"WHERE id IN ({content_row_subquery})",
                        (self.COLLECTION, "ord_prov_2"),
                        "actual id set",
                    ),
                ]
                for name, sql, params, expect in cases:
                    with self.subTest(case=name):
                        shutil.rmtree(c_chroma)
                        shutil.copytree(pristine, c_chroma)
                        self._tamper(c_chroma, sql, params)
                        proc = self._run_compare(ctx)
                        self.assertEqual(proc.returncode, 2, proc.stderr)
                        self.assertIn("provenance", proc.stderr)
                        self.assertIn(expect, proc.stderr)
                        self.assertFalse(ctx["out"].exists())

                # Untampered control: restore and confirm the pair still passes
                # the gate (refutes "gate always refuses").
                shutil.rmtree(c_chroma)
                shutil.copytree(pristine, c_chroma)
                proc = self._run_compare(ctx)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertTrue(ctx["out"].exists())
        finally:
            stop_fake_embed_server(srv)

    def test_composite_different_corpus_refused(self):
        """Challenger built from a different unit set (composite mismatch)."""
        from eval_corpus.embed_adapters import (
            start_fake_embed_server,
            stop_fake_embed_server,
        )
        from eval_corpus.reconstruct import build_canonical_unit

        srv, url, _t, _s = start_fake_embed_server(dimensions=8)
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                ctx = self._setup_valid_pair(root, url)
                other_units = [
                    build_canonical_unit(
                        {
                            "id": "ord_other_1",
                            "summary": "a different corpus entirely",
                            "keywords": ["other"],
                            "tool": "t",
                            "source_path": "site:y",
                        }
                    )
                ]
                # Fresh directory: chromadb caches PersistentClient state per
                # path in-process, so rebuilding under the same path would
                # trip the resume guard instead of the compare gate.
                ctx["arms"]["challenger"] = _build_arm(
                    arm_dir=root / "challenger_other",
                    units=other_units,
                    embed_host=url,
                    live_cfg=ctx["live_cfg"],
                )
                (root / "challenger_other" / "decisions-approved.jsonl").write_text(
                    "", encoding="utf-8"
                )
                proc = self._run_compare(ctx)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("provenance", proc.stderr)
                self.assertFalse(ctx["out"].exists())
        finally:
            stop_fake_embed_server(srv)

    def test_duplicate_package_ids_refused(self):
        from eval_corpus.embed_adapters import (
            start_fake_embed_server,
            stop_fake_embed_server,
        )

        srv, url, _t, _s = start_fake_embed_server(dimensions=8)
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                ctx = self._setup_valid_pair(root, url)
                dup = ctx["units"][0]
                ctx["package"].write_text(
                    "\n".join(json.dumps(u) for u in [*ctx["units"], dup]) + "\n",
                    encoding="utf-8",
                )
                proc = self._run_compare(ctx)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("duplicate package ids", proc.stderr)
                self.assertFalse(ctx["out"].exists())
        finally:
            stop_fake_embed_server(srv)


class RealManifestCompareTests(unittest.TestCase):
    """Codex re-verify (c545a9e): real approved manifests must bind or prohibit
    every evidence-affecting compare control. Temp-only; no live writes."""

    def _compare_argv(self, *, manifest: Path, golden: Path, package: Path,
                      out: Path, arms: dict, url: str, extra: list[str]) -> list[str]:
        return [
            sys.executable,
            str(REPO / "scripts/eval_embed_compare.py"),
            "--run-manifest",
            str(manifest),
            "--mode",
            "subprocess",
            "--golden",
            str(golden),
            "--package",
            str(package),
            "--out",
            str(out),
            "--baseline-chroma",
            str(arms["baseline"][0]),
            "--challenger-chroma",
            str(arms["challenger"][0]),
            "--baseline-config",
            str(arms["baseline"][1]),
            "--challenger-config",
            str(arms["challenger"][1]),
            "--embed-host",
            url,
            *extra,
        ]

    def test_real_manifest_binds_evidence_controls(self):
        from eval_corpus.embed_adapters import (
            start_fake_embed_server,
            stop_fake_embed_server,
        )
        from eval_corpus.io_atomic import sha256_file
        from eval_corpus.reconstruct import build_canonical_unit
        from eval_corpus.run_manifest import (
            make_real_run_manifest_for_tests,
            write_approval_sidecar,
        )

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            srv, url, _t, _s = start_fake_embed_server(dimensions=8)
            try:
                units = [
                    build_canonical_unit(
                        {
                            "id": "ord_real_1",
                            "summary": "real manifest widgets unit",
                            "keywords": ["widgets"],
                            "tool": "t",
                            "source_path": "site:x",
                        }
                    )
                ]
                live_cfg = {
                    "index": {"chroma_dir": str(root / "dead")},
                    "models": {
                        "embed_model": "x",
                        "ollama_host": "http://127.0.0.1:1",
                        "rerank_model": "x",
                    },
                    "query": {"rerank": False},
                    "eval": {},
                }
                arms = {}
                enrich_line = (
                    json.dumps({"id": "dec_prop_REAL", "summary": "frozen"}) + "\n"
                )
                for arm in ("baseline", "challenger"):
                    arms[arm] = _build_arm(
                        arm_dir=root / arm,
                        units=units,
                        embed_host=url,
                        live_cfg=live_cfg,
                    )
                    (root / arm / "decisions-approved.jsonl").write_text(
                        enrich_line, encoding="utf-8"
                    )
                golden = root / "golden.jsonl"
                golden.write_text(
                    json.dumps(
                        {
                            "query": "real manifest widgets",
                            "relevant": [{"id": "ord_real_1", "namespace": "unit_id"}],
                            "recipe_stratum": "ordinary",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                package = root / "package.jsonl"
                package.write_text(json.dumps(units[0]) + "\n", encoding="utf-8")
                out = root / "compare.json"

                manifest_paths = {
                    "golden": str(golden),
                    "package": str(package),
                    "out": str(out),
                    "baseline_chroma": str(arms["baseline"][0]),
                    "challenger_chroma": str(arms["challenger"][0]),
                    "baseline_config": str(arms["baseline"][1]),
                    "challenger_config": str(arms["challenger"][1]),
                    "embed_host": url,
                    "baseline_build_result": str(root / "baseline" / "result.json"),
                    "challenger_build_result": str(root / "challenger" / "result.json"),
                }
                bound = {
                    "query_set_sha256": sha256_file(golden),
                    "corpus_package_sha256": sha256_file(package),
                    "enrichment_sha256": sha256_file(
                        root / "baseline" / "decisions-approved.jsonl"
                    ),
                    "model_tag": "fake-embed",
                    "baseline_model_tag": "fake-embed",
                    "challenger_model_tag": "fake-embed",
                    "baseline_config_sha256": sha256_file(arms["baseline"][1]),
                    "challenger_config_sha256": sha256_file(arms["challenger"][1]),
                }

                def write_manifest(name: str, **extra_fields) -> Path:
                    fields = {**bound, **extra_fields}
                    body = make_real_run_manifest_for_tests(
                        paths=manifest_paths,
                        operations=["compare"],
                        **fields,
                    )
                    man = root / name
                    man.write_text(json.dumps(body), encoding="utf-8")
                    write_approval_sidecar(man)
                    return man

                man_skip_ok = write_manifest("run_a.json", allow_skip_latency=True)
                man_no_skip = write_manifest("run_b.json")

                # Happy path: authorized skip; throughput from bound build results.
                proc = subprocess.run(
                    self._compare_argv(
                        manifest=man_skip_ok,
                        golden=golden,
                        package=package,
                        out=out,
                        arms=arms,
                        url=url,
                        extra=["--skip-latency"],
                    ),
                    cwd=str(REPO),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                report = json.loads(out.read_text(encoding="utf-8"))
                self.assertEqual(report["run_manifest_execution_mode"], "real")
                tp = report["throughput"]
                self.assertEqual(
                    tp["units_per_sec_source"], "manifest_bound_build_results"
                )
                for arm in ("baseline", "challenger"):
                    build_result = json.loads(
                        (root / arm / "result.json").read_text(encoding="utf-8")
                    )
                    self.assertEqual(
                        tp[f"{arm}_units_per_sec"], build_result["units_per_sec"]
                    )
                prov = report["provenance"]
                self.assertEqual(prov["unit_count"], 1)
                self.assertEqual(
                    prov["approved_manifest_body_sha256"],
                    json.loads(man_skip_ok.read_text(encoding="utf-8"))[
                        "ryan_approved_manifest_sha256"
                    ],
                )
                self.assertEqual(
                    prov["run_manifest_file_sha256"], sha256_file(man_skip_ok)
                )
                for arm in ("baseline", "challenger"):
                    self.assertEqual(
                        prov["build_result_sha256"][arm],
                        sha256_file(root / arm / "result.json"),
                    )
                    self.assertEqual(
                        prov["collections"][arm]["actual_row_count"], 1
                    )
                out.unlink()

                refusal_cases = [
                    # Injectable mode with a real manifest: binder mismatch.
                    (
                        man_skip_ok,
                        ["--skip-latency"],
                        {"--mode": "injectable"},
                        "mismatch",
                    ),
                    # CLI-supplied throughput numbers.
                    (
                        man_skip_ok,
                        ["--skip-latency", "--baseline-units-per-sec", "5.0"],
                        {},
                        "units-per-sec",
                    ),
                    # Latency skip without manifest authorization.
                    (man_no_skip, ["--skip-latency"], {}, "allow_skip_latency"),
                    # Fallback without manifest binding.
                    (
                        man_skip_ok,
                        [
                            "--skip-latency",
                            "--exercise-fallback",
                            "--fallback-config",
                            str(arms["baseline"][1]),
                        ],
                        {},
                        "fallback",
                    ),
                ]
                for man, extra, replace, expect in refusal_cases:
                    argv = self._compare_argv(
                        manifest=man,
                        golden=golden,
                        package=package,
                        out=out,
                        arms=arms,
                        url=url,
                        extra=extra,
                    )
                    for flag, value in replace.items():
                        argv[argv.index(flag) + 1] = value
                    if "--mode" in replace and replace["--mode"] == "injectable":
                        argv += ["--scores-json", str(golden)]
                    proc = subprocess.run(
                        argv, cwd=str(REPO), capture_output=True, text=True, check=False
                    )
                    with self.subTest(expect=expect):
                        self.assertEqual(proc.returncode, 2, proc.stderr)
                        self.assertIn(expect, proc.stderr)
                        self.assertFalse(out.exists())

                # Real mode requires frozen enrichment files to exist.
                for arm in ("baseline", "challenger"):
                    (root / arm / "decisions-approved.jsonl").unlink()
                man_no_enrich = write_manifest(
                    "run_c.json",
                    allow_skip_latency=True,
                    enrichment_sha256=hashlib.sha256(b"").hexdigest(),
                )
                proc = subprocess.run(
                    self._compare_argv(
                        manifest=man_no_enrich,
                        golden=golden,
                        package=package,
                        out=out,
                        arms=arms,
                        url=url,
                        extra=["--skip-latency"],
                    ),
                    cwd=str(REPO),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("frozen enrichment", proc.stderr)
                self.assertFalse(out.exists())
            finally:
                stop_fake_embed_server(srv)


if __name__ == "__main__":
    unittest.main()
