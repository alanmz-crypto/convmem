"""Phase A completion: capture CLI/extract, shadow orchestration, runner, isolation."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent


def _fake_embed(dimensions: int = 8):
    def _embed(text: str) -> list[float]:
        base = (sum(ord(c) for c in text) % 97) / 97.0
        return [base + (i * 0.001) for i in range(dimensions)]

    return _embed


def _seed_mini_chroma(chroma_dir: Path) -> None:
    from chroma_store import ChromaStore

    store = ChromaStore(str(chroma_dir))
    try:
        store.add_unit(
            "keep-1",
            "hello keep",
            [0.1] * 8,
            {"id": "keep-1", "title": "Keep", "tool": "t", "source_path": "site:x"},
        )
        store.add_unit(
            "tomb-1",
            "bye tomb",
            [0.2] * 8,
            {
                "id": "tomb-1",
                "title": "Tomb",
                "tool": "t",
                "source_path": "site:x",
                "superseded": True,
            },
        )
    finally:
        store.close()


class CaptureExtractTests(unittest.TestCase):
    def test_one_txn_extract_and_package(self):
        from eval_corpus.capture import extract_chroma_capture_slice, run_capture

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            _seed_mini_chroma(chroma)
            export = root / "knowledge_units.jsonl"
            processed = root / "processed.json"
            export.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "id": "keep-1",
                                "summary": "hello",
                                "keywords": ["keep"],
                                "tool": "t",
                                "source_path": "site:x",
                            }
                        ),
                        json.dumps(
                            {
                                "id": "tomb-1",
                                "summary": "bye",
                                "keywords": ["tomb"],
                                "tool": "t",
                                "source_path": "site:x",
                            }
                        ),
                        json.dumps(
                            {
                                "id": "keep-1",
                                "summary": "hello",
                                "keywords": ["keep", "dup"],
                                "tool": "t",
                                "source_path": "site:x",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            processed.write_text("{}", encoding="utf-8")
            slice_ = extract_chroma_capture_slice(chroma)
            self.assertIn("tomb-1", slice_["superseded_ids"])
            self.assertEqual(slice_["documents"]["keep-1"], "hello keep")

            cap = root / "capture"
            result = run_capture(
                export_src=export,
                processed_src=processed,
                capture_dir=cap,
                chroma_dir=chroma,
            )
            self.assertEqual(result["capture_report"]["status"], "OK")
            self.assertTrue((cap / "corpus_package.jsonl").is_file())
            self.assertTrue((cap / "chroma_extract.json").is_file())
            # tomb excluded via superseded
            ids = [
                json.loads(line)["id"]
                for line in (cap / "corpus_package.jsonl").read_text().splitlines()
                if line.strip()
            ]
            self.assertEqual(ids, ["keep-1"])
            self.assertNotIn("tomb-1", ids)

    def test_capture_outputs_atomic_no_tmp_left(self):
        from eval_corpus.capture import capture_export_and_processed

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            export = root / "knowledge_units.jsonl"
            processed = root / "processed.json"
            export.write_text(json.dumps({"id": "a", "summary": "s"}) + "\n", encoding="utf-8")
            processed.write_text("{}", encoding="utf-8")
            cap = root / "capture"
            capture_export_and_processed(
                export_src=export, processed_src=processed, capture_dir=cap
            )
            leftovers = list(cap.glob("*.tmp")) + list(cap.glob(".*.tmp"))
            self.assertEqual(leftovers, [])
            self.assertTrue((cap / "capture_report.json").is_file())


class CaptureCLISmokeTests(unittest.TestCase):
    def test_refuse_without_auth(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO / "scripts" / "eval_corpus_capture.py"),
                "--export",
                "/tmp/x",
                "--processed",
                "/tmp/y",
                "--capture-dir",
                "/tmp/z",
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("authorize-r2b", proc.stderr)

    def test_hermetic_cli_with_auth(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            _seed_mini_chroma(chroma)
            export = root / "ku.jsonl"
            processed = root / "processed.json"
            export.write_text(
                json.dumps(
                    {
                        "id": "keep-1",
                        "summary": "hello",
                        "keywords": ["k"],
                        "tool": "t",
                        "source_path": "site:x",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            processed.write_text("{}", encoding="utf-8")
            cap = root / "capture"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(REPO / "scripts" / "eval_corpus_capture.py"),
                    "--authorize-r2b",
                    "--export",
                    str(export),
                    "--processed",
                    str(processed),
                    "--capture-dir",
                    str(cap),
                    "--chroma-dir",
                    str(chroma),
                ],
                cwd=str(REPO),
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "OK")
            self.assertEqual(payload["unit_count"], 1)


class ShadowOrchestrationTests(unittest.TestCase):
    def test_build_resume_with_fake_embeddings(self):
        import chromadb

        from eval_corpus.fingerprint import corpus_fingerprint_hex
        from eval_corpus.reconstruct import build_canonical_unit, normalized_shadow_metadata
        from eval_corpus.shadow_build import (
            collection_metadata_from_manifest,
            run_shadow_build,
            write_build_manifest,
        )

        units = [
            build_canonical_unit(
                {
                    "id": "a",
                    "summary": "alpha",
                    "keywords": ["k"],
                    "tool": "t",
                    "source_path": "/tmp/a",
                }
            ),
            build_canonical_unit(
                {
                    "id": "b",
                    "summary": "beta",
                    "keywords": ["k"],
                    "tool": "t",
                    "source_path": "/tmp/b",
                }
            ),
        ]
        fp = corpus_fingerprint_hex(units)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            manifest = {
                "embed_model": "fake-embed",
                "embed_dimensions": 8,
                "unit_corpus_fingerprint": fp,
                "unit_count": 2,
                "batch_size": 1,
                "schema_version": "1",
                "build_timestamp": "2026-07-19T00:00:00Z",
            }
            # Partial store: create collection with full manifest metadata, add only unit a
            man_path = root / "build-manifest.json"
            sha = write_build_manifest(man_path, manifest)
            meta = collection_metadata_from_manifest(manifest, manifest_sha256=sha)
            create_meta = {
                k: (v if isinstance(v, (str, int, float, bool)) else str(v))
                for k, v in meta.items()
            }
            client = chromadb.PersistentClient(path=str(chroma))
            col = client.get_or_create_collection(
                name="knowledge_units", metadata=create_meta
            )
            emb = _fake_embed(8)(units[0]["document"])
            col.add(
                ids=["a"],
                documents=[units[0]["document"]],
                metadatas=[normalized_shadow_metadata(units[0])],
                embeddings=[emb],
            )

            result_resume = run_shadow_build(
                units=units,
                chroma_dir=chroma,
                manifest=manifest,
                embed_fn=_fake_embed(8),
                batch_size=1,
                resume=True,
                manifest_path=man_path,
                result_path=root / "build-result.json",
                journal_path=root / "build-journal.jsonl",
            )
            self.assertEqual(result_resume["skipped_count"], 1)
            self.assertEqual(result_resume["added_count"], 1)

            # Second resume is a no-op
            result_noop = run_shadow_build(
                units=units,
                chroma_dir=chroma,
                manifest=manifest,
                embed_fn=_fake_embed(8),
                batch_size=1,
                resume=True,
                manifest_path=man_path,
                result_path=root / "build-result2.json",
                journal_path=root / "build-journal.jsonl",
            )
            self.assertEqual(result_noop["skipped_count"], 2)
            self.assertEqual(result_noop["added_count"], 0)

    def test_shadow_cli_refuse_and_fake_smoke(self):
        from eval_corpus.fingerprint import corpus_fingerprint_hex
        from eval_corpus.reconstruct import build_canonical_unit

        unit = build_canonical_unit(
            {
                "id": "z",
                "summary": "zulu",
                "keywords": ["k"],
                "tool": "t",
                "source_path": "/tmp/z",
            }
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg = root / "pkg.jsonl"
            pkg.write_text(json.dumps(unit, sort_keys=True) + "\n", encoding="utf-8")
            manifest = {
                "embed_model": "fake-embed",
                "embed_dimensions": 8,
                "unit_corpus_fingerprint": corpus_fingerprint_hex([unit]),
                "unit_count": 1,
                "batch_size": 1,
                "schema_version": "1",
            }
            man = root / "manifest.json"
            man.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(REPO / "scripts" / "eval_shadow_embed.py")],
                cwd=str(REPO),
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 2)

            chroma = root / "chroma"
            proc2 = subprocess.run(
                [
                    sys.executable,
                    str(REPO / "scripts" / "eval_shadow_embed.py"),
                    "--authorize-r4",
                    "--package",
                    str(pkg),
                    "--manifest",
                    str(man),
                    "--chroma-dir",
                    str(chroma),
                    "--embed-mode",
                    "fake",
                    "--result",
                    str(root / "result.json"),
                ],
                cwd=str(REPO),
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc2.returncode, 0, proc2.stderr)
            self.assertEqual(json.loads(proc2.stdout)["status"], "OK")


class RunnerMetricsLatencyTests(unittest.TestCase):
    def test_both_views_and_latency_without_models(self):
        from eval_corpus.runner import (
            evaluate_both_views,
            latency_report_to_dict,
            measure_both_views_latency,
            view_report_to_dict,
        )

        rows = [
            {
                "query": "dec_1 please",
                "acceptable_ids": ["dec_1"],
                "top_k": 2,
                "relevant_complete": True,
            }
        ]
        calls: list[str] = []

        def query_fn(query, *, top_k, eval_view):
            calls.append(eval_view)
            if eval_view == "embedding_influenced":
                return [
                    {"id": "u0", "metadata": {"ledger_id": "dec_other"}},
                    {"id": "u1", "metadata": {"ledger_id": "dec_1"}},
                ][:top_k]
            return [{"id": "u1", "metadata": {"ledger_id": "dec_1"}}][:top_k]

        reports = evaluate_both_views(rows, query_fn)
        self.assertIn("embedding_influenced", reports)
        self.assertIn("operational_pipeline", reports)
        self.assertTrue(reports["operational_pipeline"].p_at_1)
        self.assertFalse(reports["embedding_influenced"].p_at_1)
        self.assertTrue(reports["embedding_influenced"].hit_at_k)
        as_dict = view_report_to_dict(reports["embedding_influenced"])
        self.assertEqual(as_dict["view"], "embedding_influenced")

        # Fake clock: each pair of calls advances 10ms
        state = {"t": 0.0}

        def clock():
            state["t"] += 0.005
            return state["t"]

        lat = measure_both_views_latency(
            ["q1", "q2"], query_fn, top_k=2, warmup=0, clock=clock
        )
        self.assertEqual(set(lat), {"embedding_influenced", "operational_pipeline"})
        d = latency_report_to_dict(lat["embedding_influenced"])
        self.assertEqual(d["count"], 2)
        self.assertGreater(d["mean_ms"], 0)
        self.assertIn("embedding_influenced", calls)


class DoctorSqliteRoTests(unittest.TestCase):
    def test_reads_collection_metadata_via_sqlite(self):
        from chroma_readonly import collection_config_metadata
        from doctor import DoctorCheck, _check_embed_collection_identity

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            import chromadb

            client = chromadb.PersistentClient(path=str(chroma))
            client.get_or_create_collection(
                name="knowledge_units",
                metadata={
                    "hnsw:space": "cosine",
                    "convmem:embed_model": "nomic-embed-text",
                    "convmem:embed_dimensions": 768,
                },
            )
            meta = collection_config_metadata(chroma, "knowledge_units")
            self.assertEqual(meta.get("convmem:embed_model"), "nomic-embed-text")

            cfg = {
                "index": {"chroma_dir": str(chroma)},
                "models": {"embed_model": "nomic-embed-text"},
            }
            # Doctor must not import/open PersistentClient for this check
            import doctor as doctor_mod

            self.assertFalse(hasattr(doctor_mod, "open_chroma_for_verify"))
            check = _check_embed_collection_identity(cfg)
            self.assertIsInstance(check, DoctorCheck)
            self.assertTrue(check.ok)
            self.assertEqual(check.effective_status(), "pass")

            cfg_bad = {
                "index": {"chroma_dir": str(chroma)},
                "models": {"embed_model": "other-model"},
            }
            check2 = _check_embed_collection_identity(cfg_bad)
            self.assertFalse(check2.ok)


class IsolationSentinelTests(unittest.TestCase):
    def test_capture_does_not_touch_unreachable_live_sentinel(self):
        from eval_corpus.capture import run_capture

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            live_sentinel = root / "LIVE_SENTINEL_DO_NOT_TOUCH"
            live_sentinel.mkdir()
            canary = live_sentinel / "canary.txt"
            canary.write_text("untouched\n", encoding="utf-8")
            st_before = canary.stat()

            chroma = root / "fixture-chroma"
            _seed_mini_chroma(chroma)
            export = root / "ku.jsonl"
            processed = root / "processed.json"
            export.write_text(
                json.dumps(
                    {
                        "id": "keep-1",
                        "summary": "hello",
                        "keywords": ["k"],
                        "tool": "t",
                        "source_path": "site:x",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            processed.write_text("{}", encoding="utf-8")

            opened: list[str] = []
            real_open = open

            def tracking_open(file, *args, **kwargs):
                path = str(file)
                if "LIVE_SENTINEL_DO_NOT_TOUCH" in path:
                    opened.append(path)
                return real_open(file, *args, **kwargs)

            with patch("builtins.open", tracking_open):
                run_capture(
                    export_src=export,
                    processed_src=processed,
                    capture_dir=root / "capture",
                    chroma_dir=chroma,
                )
            self.assertEqual(opened, [])
            st_after = canary.stat()
            self.assertEqual(st_before.st_mtime_ns, st_after.st_mtime_ns)
            self.assertEqual(canary.read_text(encoding="utf-8"), "untouched\n")

    def test_unreachable_live_chroma_not_required_for_fixture_capture(self):
        from eval_corpus.capture import run_capture

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            missing_live = root / "no" / "such" / "live" / "chroma"
            export = root / "ku.jsonl"
            processed = root / "processed.json"
            export.write_text(
                json.dumps(
                    {
                        "id": "a",
                        "summary": "s",
                        "keywords": [],
                        "tool": "t",
                        "source_path": "site:x",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            processed.write_text("{}", encoding="utf-8")
            # No chroma_dir → must succeed without live store
            result = run_capture(
                export_src=export,
                processed_src=processed,
                capture_dir=root / "capture",
                chroma_dir=None,
            )
            self.assertEqual(result["capture_report"]["status"], "OK")
            self.assertFalse(missing_live.exists())


class DoctorLegacyWarnStillWorks(unittest.TestCase):
    def test_missing_chroma_warn(self):
        from doctor import _check_embed_collection_identity

        cfg = {
            "index": {"chroma_dir": "/tmp/missing-chroma-xyz-phase-a"},
            "models": {"embed_model": "nomic-embed-text"},
        }
        check = _check_embed_collection_identity(cfg)
        self.assertEqual(check.effective_status(), "warn")


if __name__ == "__main__":
    unittest.main()
