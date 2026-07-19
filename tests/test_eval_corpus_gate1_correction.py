"""Gate 1 correction: binders, isolation, fallback, adversarial, schema fixtures."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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
                "golden": root / "g.jsonl",
                "package": root / "p.jsonl",
                "out": root / "o.json",
                "baseline_chroma": root / "bc",
                "challenger_chroma": root / "cc",
                "baseline_config": root / "b.toml",
                "challenger_config": root / "c.toml",
                "embed_host": "http://127.0.0.1:1",
                "query_set_sha256": "0" * 64,
                "corpus_package_sha256": "0" * 64,
                "config_identity_sha256": "0" * 64,
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
                        summary["retrieval_ms"]["ops_pipeline"]["challenger"]["n"],
                        20,
                    )
                finally:
                    stop_latency_worker(b)
                    stop_latency_worker(c)
            finally:
                stop_fake_embed_server(srv)


if __name__ == "__main__":
    unittest.main()
