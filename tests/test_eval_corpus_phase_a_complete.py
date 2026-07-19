"""Phase A / Gate 1 hermetic tests updated for Chroma-required capture + run-manifest auth."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parent.parent


def _fake_embed(dimensions: int = 8):
    def _embed(text: str) -> list[float]:
        base = (sum(ord(c) for c in text) % 97) / 97.0
        return [base + (i * 0.001) for i in range(dimensions)]

    return _embed


def _seed_mini_chroma(chroma_dir: Path, doc: str = "hello keep") -> None:
    from chroma_store import ChromaStore

    store = ChromaStore(str(chroma_dir))
    try:
        store.add_unit(
            "keep-1",
            doc,
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
            _seed_mini_chroma(chroma, doc="hello keep")
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
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            processed.write_text("{}", encoding="utf-8")
            slice_ = extract_chroma_capture_slice(chroma)
            self.assertIn("tomb-1", slice_["superseded_ids"])
            cap = root / "capture"
            result = run_capture(
                export_src=export,
                processed_src=processed,
                capture_dir=cap,
                chroma_dir=chroma,
            )
            # Canonical 40/30/30 quotas: sparse hermetic capture is UNRESOLVED.
            self.assertEqual(result["capture_report"]["status"], "UNRESOLVED")
            ids = [
                json.loads(line)["id"]
                for line in (cap / "corpus_package.jsonl").read_text().splitlines()
                if line.strip()
            ]
            self.assertEqual(ids, ["keep-1"])


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
                "--chroma-dir",
                "/tmp/c",
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("authorize-fixture", proc.stderr)

    def test_hermetic_cli_with_auth(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            _seed_mini_chroma(chroma, doc="hello keep")
            export = root / "ku.jsonl"
            processed = root / "processed.json"
            export.write_text(
                json.dumps(
                    {
                        "id": "keep-1",
                        "summary": "hello",
                        "keywords": ["keep"],
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
                    "--authorize-fixture",
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
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["status"], "UNRESOLVED")


class ShadowOrchestrationTests(unittest.TestCase):
    def test_build_resume_with_fake_embeddings(self):
        import chromadb

        from eval_corpus.embed_adapters import fake_embed_fn
        from eval_corpus.fingerprint import corpus_fingerprint_hex, package_sha256_hex
        from eval_corpus.reconstruct import build_canonical_unit, normalized_shadow_metadata
        from eval_corpus.shadow_build import (
            chroma_safe_metadata,
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
        pkg = package_sha256_hex(units)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            manifest = {
                "embed_model": "fake-embed",
                "embed_dimensions": 8,
                "unit_corpus_fingerprint": fp,
                "package_sha256": pkg,
                "unit_count": 2,
                "batch_size": 1,
                "schema_version": "1",
                "build_timestamp": "2026-07-19T00:00:00Z",
            }
            man_path = root / "build-manifest.json"
            sha = write_build_manifest(man_path, manifest)
            meta = collection_metadata_from_manifest(
                manifest, manifest_sha256=sha, package_sha256=pkg
            )
            create_meta = {
                k: (v if isinstance(v, (str, int, float, bool)) else str(v))
                for k, v in meta.items()
            }
            client = chromadb.PersistentClient(path=str(chroma))
            col = client.get_or_create_collection(
                name="knowledge_units", metadata=create_meta
            )
            emb = fake_embed_fn(8)(units[0]["document"])
            col.add(
                ids=["a"],
                documents=[units[0]["document"]],
                metadatas=[chroma_safe_metadata(normalized_shadow_metadata(units[0]))],
                embeddings=[emb],
            )
            result_resume = run_shadow_build(
                units=units,
                chroma_dir=chroma,
                manifest=manifest,
                embed_fn=fake_embed_fn(8),
                batch_size=1,
                resume=True,
                manifest_path=man_path,
                result_path=root / "build-result.json",
                journal_path=root / "build-journal.jsonl",
            )
            self.assertEqual(result_resume["skipped_count"], 1)
            self.assertEqual(result_resume["added_count"], 1)

    def test_shadow_cli_refuse_and_fake_smoke(self):
        from eval_corpus.fingerprint import corpus_fingerprint_hex, package_sha256_hex
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
                "package_sha256": package_sha256_hex([unit]),
                "unit_count": 1,
                "batch_size": 1,
                "schema_version": "1",
            }
            man = root / "manifest.json"
            man.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            proc = subprocess.run(
                [sys.executable, str(REPO / "scripts" / "eval_shadow_embed.py"),
                 "--package", str(pkg), "--manifest", str(man),
                 "--chroma-dir", str(root / "c")],
                cwd=str(REPO),
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 2)
            proc2 = subprocess.run(
                [
                    sys.executable,
                    str(REPO / "scripts" / "eval_shadow_embed.py"),
                    "--authorize-fixture",
                    "--package",
                    str(pkg),
                    "--manifest",
                    str(man),
                    "--chroma-dir",
                    str(root / "chroma"),
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
            _seed_mini_chroma(chroma, doc="hello keep")
            export = root / "ku.jsonl"
            processed = root / "processed.json"
            export.write_text(
                json.dumps(
                    {
                        "id": "keep-1",
                        "summary": "hello",
                        "keywords": ["keep"],
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
            self.assertEqual(canary.stat().st_mtime_ns, st_before.st_mtime_ns)


class QueryViewTests(unittest.TestCase):
    @patch("query.ollama_embed", return_value=[0.1, 0.2])
    @patch("query.open_chroma_for_read")
    @patch("query._ledger_lookup_hits")
    @patch("query._apply_keyword_rank", side_effect=lambda t, r: r)
    @patch("query._merge_priority_hits")
    def test_embedding_influenced_skips_ledger(
        self, merge, _kw, ledger_hits, open_chroma, _embed
    ):
        from query import query_units

        store = MagicMock()
        store.query_units.return_value = [
            {"id": "1", "distance": 0.1, "metadata": {"domain": "coding.tooling"}}
        ]
        open_chroma.return_value = store
        ledger_hits.return_value = [{"id": "ledger"}]
        merge.side_effect = lambda results, extras: results + extras
        cfg = {
            "models": {"embed_model": "nomic-embed-text", "ollama_host": "http://x", "rerank_model": "r"},
            "index": {"chroma_dir": "/tmp/chroma"},
            "query": {"rerank": False, "top_k_candidates": 5, "recency_weight": 0},
            "eval": {"retrieval_view": "embedding_influenced"},
        }
        out = query_units("q", top_k=5, cfg=cfg)
        ledger_hits.assert_not_called()
        merge.assert_not_called()
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
