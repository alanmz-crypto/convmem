"""Gate 1: capture/adjudication, provenance, methodology, adversarial guards."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _seed_chroma(chroma_dir: Path, rows: list[tuple[str, str, dict]]) -> None:
    from chroma_store import ChromaStore

    store = ChromaStore(str(chroma_dir))
    try:
        for i, (uid, doc, meta) in enumerate(rows):
            store.add_unit(uid, doc, [0.1 * (i + 1)] * 8, meta)
    finally:
        store.close()


class PairedStatsTests(unittest.TestCase):
    def test_ties_all_wins_balanced_and_bootstrap_seed(self):
        from eval_corpus.paired_stats import label_challenger, paired_outcomes

        ties = paired_outcomes([1, 1, 1], [1, 1, 1], tie_epsilon=0.0)
        r = label_challenger(
            outcomes=ties,
            significance_alpha=0.05,
            confidence_level=0.95,
            bootstrap_seed=1,
            bootstrap_resamples=200,
            minimum_non_tied_pairs=1,
        )
        self.assertEqual(r["verdict"], "INCONCLUSIVE")
        self.assertEqual(r["ties"], 3)

        wins = paired_outcomes([0] * 25, [1] * 25, tie_epsilon=0.0)
        r2 = label_challenger(
            outcomes=wins,
            significance_alpha=0.05,
            confidence_level=0.95,
            bootstrap_seed=7,
            bootstrap_resamples=500,
            minimum_non_tied_pairs=20,
        )
        self.assertEqual(r2["verdict"], "BETTER")

        # 14-11 style with high minimum → inconclusive
        base = [1] * 11 + [0] * 14
        chal = [0] * 11 + [1] * 14
        mid = paired_outcomes(base, chal, tie_epsilon=0.0)
        r3 = label_challenger(
            outcomes=mid,
            significance_alpha=0.05,
            confidence_level=0.95,
            bootstrap_seed=3,
            bootstrap_resamples=500,
            minimum_non_tied_pairs=30,
        )
        self.assertEqual(r3["verdict"], "INCONCLUSIVE")

        a = label_challenger(
            outcomes=wins,
            significance_alpha=0.05,
            confidence_level=0.95,
            bootstrap_seed=99,
            bootstrap_resamples=300,
            minimum_non_tied_pairs=20,
        )
        b = label_challenger(
            outcomes=wins,
            significance_alpha=0.05,
            confidence_level=0.95,
            bootstrap_seed=99,
            bootstrap_resamples=300,
            minimum_non_tied_pairs=20,
        )
        self.assertEqual(a["ci_low"], b["ci_low"])
        self.assertEqual(a["ci_high"], b["ci_high"])


class RecipeStratumTests(unittest.TestCase):
    def test_mixed_and_mismatch(self):
        from eval_corpus.recipe_strata import (
            index_package_units,
            resolve_relevant_recipes,
            validate_recipe_stratum,
        )
        from eval_corpus.reconstruct import build_canonical_unit

        units = [
            build_canonical_unit(
                {
                    "id": "a",
                    "summary": "s",
                    "keywords": [],
                    "tool": "t",
                    "source_path": "/tmp/a",
                }
            ),
            build_canonical_unit(
                {
                    "id": "b",
                    "title": "T",
                    "summary": "s",
                    "keywords": [],
                    "tool": "inter-model",
                    "source_path": "/repo/docs/inter-model/x.md",
                }
            ),
        ]
        idx = index_package_units(units)
        resolved = resolve_relevant_recipes(
            [
                {"namespace": "unit_id", "id": "a"},
                {"namespace": "unit_id", "id": "b"},
            ],
            idx,
        )
        validate_recipe_stratum("mixed", resolved)
        with self.assertRaises(ValueError):
            validate_recipe_stratum("ordinary", resolved)


class CaptureAdjudicationTests(unittest.TestCase):
    def test_capture_complete_and_separate_acceptance(self):
        from eval_corpus.adjudicate import emit_corpus_acceptance, verify_corpus_acceptance_hashes
        from eval_corpus.capture import run_capture
        from eval_corpus.io_atomic import sha256_file

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            doc = "hello keep"
            _seed_chroma(
                chroma,
                [
                    (
                        "keep-1",
                        doc,
                        {
                            "id": "keep-1",
                            "title": "Keep",
                            "tool": "t",
                            "source_path": "site:x",
                            "ledger_id": "obs_keep",
                        },
                    )
                ],
            )
            export = root / "ku.jsonl"
            # document reconstruction for ordinary = summary + keywords
            export.write_text(
                json.dumps(
                    {
                        "id": "keep-1",
                        "summary": "hello",
                        "keywords": ["keep"],
                        "tool": "t",
                        "source_path": "site:x",
                        "ledger_id": "obs_keep",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            processed = root / "processed.json"
            processed.write_text("{}", encoding="utf-8")
            cap = root / "capture"
            result = run_capture(
                export_src=export,
                processed_src=processed,
                capture_dir=cap,
                chroma_dir=chroma,
            )
            self.assertEqual(result["capture_report"]["status"], "CAPTURE_COMPLETE")
            self.assertFalse(result["capture_report"]["corpus_accepted"])
            spot = json.loads((cap / "historical_spot_check.json").read_text())
            self.assertNotIn("adjudications", spot)
            spot_sha = sha256_file(cap / "historical_spot_check.json")

            adjs = {"adjudications": [{"id": sid, "verdict": "ok"} for sid in spot["sample_ids"]]}
            adj_path = cap / "adjudications.json"
            adj_path.write_text(json.dumps(adjs), encoding="utf-8")
            acc = emit_corpus_acceptance(
                capture_dir=cap, adjudications_path=adj_path, reviewer="test"
            )
            self.assertEqual(acc["status"], "CORPUS_ACCEPTED")
            self.assertEqual(sha256_file(cap / "historical_spot_check.json"), spot_sha)
            self.assertEqual(verify_corpus_acceptance_hashes(cap), [])


class RunManifestAuthTests(unittest.TestCase):
    def test_fixture_rejects_external_and_missing_manifest(self):
        from eval_corpus.run_manifest import assert_capture_authorized, make_fixture_run_manifest

        with self.assertRaises(PermissionError):
            assert_capture_authorized(
                authorize_fixture=False,
                run_manifest_path=None,
                export=Path("/tmp/x"),
                processed=Path("/tmp/y"),
                capture_dir=Path("/tmp/z"),
                chroma_dir=Path("/tmp/c"),
            )
        m = make_fixture_run_manifest(
            paths={"chroma_dir": str(Path.home() / ".local/share/convmem/eval/x")}
        )
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.json"
            p.write_text(json.dumps(m), encoding="utf-8")
            from eval_corpus.run_manifest import validate_run_manifest_schema

            self.assertTrue(validate_run_manifest_schema(json.loads(p.read_text())))


class ShadowProvenanceTests(unittest.TestCase):
    def test_fingerprint_batch_manifest_guards(self):
        from eval_corpus.fingerprint import corpus_fingerprint_hex, package_sha256_hex
        from eval_corpus.reconstruct import build_canonical_unit
        from eval_corpus.shadow_build import run_shadow_build
        from eval_corpus.embed_adapters import fake_embed_fn

        unit = build_canonical_unit(
            {
                "id": "z",
                "summary": "zulu",
                "keywords": ["k"],
                "tool": "t",
                "source_path": "/tmp/z",
            }
        )
        units = [unit]
        fp = corpus_fingerprint_hex(units)
        pkg = package_sha256_hex(units)
        manifest = {
            "embed_model": "fake",
            "embed_dimensions": 8,
            "unit_corpus_fingerprint": fp,
            "package_sha256": pkg,
            "unit_count": 1,
            "batch_size": 1,
            "schema_version": "1",
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # false fingerprint
            with self.assertRaises(ValueError):
                run_shadow_build(
                    units=units,
                    chroma_dir=root / "c1",
                    manifest={**manifest, "unit_corpus_fingerprint": "nope"},
                    embed_fn=fake_embed_fn(8),
                    manifest_path=root / "m1.json",
                )
            # batch mismatch
            with self.assertRaises(ValueError):
                run_shadow_build(
                    units=units,
                    chroma_dir=root / "c2",
                    manifest=manifest,
                    embed_fn=fake_embed_fn(8),
                    batch_size=2,
                    manifest_path=root / "m2.json",
                )
            # happy + write-once
            run_shadow_build(
                units=units,
                chroma_dir=root / "c3",
                manifest=manifest,
                embed_fn=fake_embed_fn(8),
                manifest_path=root / "m3.json",
                result_path=root / "r3.json",
            )
            with self.assertRaises(RuntimeError):
                run_shadow_build(
                    units=units,
                    chroma_dir=root / "c4",
                    manifest={**manifest, "embed_model": "other"},
                    embed_fn=fake_embed_fn(8),
                    manifest_path=root / "m3.json",
                )


class CompareCLISmokeTests(unittest.TestCase):
    def test_injectable_compare_inconclusive_small_n(self):
        golden = REPO / "tests/fixtures/eval_pilot_queries.jsonl"
        package = REPO / "tests/fixtures/eval_pilot_package.jsonl"
        rows = [json.loads(l) for l in golden.read_text().splitlines() if l.strip()][:5]
        scores = {"baseline": {}, "challenger": {}}
        for r in rows:
            q = r["query"]
            rid = r["relevant"][0]["id"]
            ns = r["relevant"][0]["namespace"]
            if ns == "unit_id":
                hit = {"id": rid, "metadata": {}}
            else:
                hit = {"id": "x", "metadata": {"ledger_id": rid}}
            scores["baseline"][q] = [hit]
            scores["challenger"][q] = [hit]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            g = root / "g.jsonl"
            g.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            s = root / "scores.json"
            s.write_text(json.dumps(scores))
            out = root / "cmp.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(REPO / "scripts/eval_embed_compare.py"),
                    "--authorize-fixture",
                    "--golden",
                    str(g),
                    "--package",
                    str(package),
                    "--scores-json",
                    str(s),
                    "--out",
                    str(out),
                ],
                cwd=str(REPO),
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads(out.read_text())
            self.assertEqual(report["uncertainty"]["verdict"], "INCONCLUSIVE")
            self.assertTrue(report["not_promotion_authority"])


class CaptureCLISmokeTests(unittest.TestCase):
    def test_refuse_without_auth_and_hermetic_ok(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO / "scripts/eval_corpus_capture.py"),
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


if __name__ == "__main__":
    unittest.main()
