"""JudgeBench offline runner tests (JudgeBench T4)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_judgebench.contracts import (
    Contradiction,
    Coverage,
    IndependenceClass,
    InvocationStatus,
    JudgeInvocationV1,
    SemanticJudgmentV1,
    Support,
    Verdict,
)
from eval_judgebench.runner import CorpusLoadError, load_corpus, run_judgebench
from eval_model_identity import CanonicalPreflightError

CORPUS = (
    Path(__file__).resolve().parent.parent
    / "eval_corpus/fixtures/judgebench/semantic-v1"
)
REGISTRY = (
    Path(__file__).resolve().parent.parent
    / "eval_corpus/fixtures/judgebench/identity-registry-v1.json"
)
CFG = {"models": {"ollama_host": "http://localhost:11434"}}


class RunnerDryRunTests(unittest.TestCase):
    @patch("eval_judgebench.runner.ollama_version", return_value="0.5.0")
    @patch("eval_model_identity.model_digest_and_quant", return_value=("remote", ""))
    def test_empty_corpus_dry_run(self, _mock_digest, _mock_ver):
        result = run_judgebench(
            CORPUS,
            cfg=CFG,
            judge_model="deepseek-v4-pro",
            under_test_model="llama3.1:8b",
            registry_path=REGISTRY,
            semantic_judge=None,
        )
        self.assertEqual(result.cases, [])
        self.assertEqual(result.independence_class, IndependenceClass.CROSS_FAMILY)
        self.assertEqual(result.gold_hash_before, result.gold_hash_after)
        self.assertIn("comparison_signature_digest", result.provenance)

    @patch("eval_model_identity.model_digest_and_quant", return_value=("remote", ""))
    def test_same_family_preflight_refused_for_canonical(self, _mock):
        with self.assertRaises(CanonicalPreflightError):
            run_judgebench(
                CORPUS,
                cfg=CFG,
                judge_model="deepseek-v4-pro",
                under_test_model="deepseek-v4-flash",
                registry_path=REGISTRY,
            )

    @patch("eval_judgebench.runner.ollama_version", return_value="0.5.0")
    @patch("eval_model_identity.model_digest_and_quant", return_value=("remote", ""))
    def test_gold_hash_unchanged_after_run(self, _mock_digest, _mock_ver):
        result = run_judgebench(
            CORPUS,
            cfg=CFG,
            judge_model="deepseek-v4-pro",
            under_test_model="llama3.1:8b",
            registry_path=REGISTRY,
        )
        self.assertEqual(result.gold_hash_before, result.gold_hash_after)

    def test_corrupt_manifest_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text("{not json", encoding="utf-8")
            (root / "cases.jsonl").write_text("", encoding="utf-8")
            (root / "gold.jsonl").write_text("", encoding="utf-8")
            with self.assertRaises(CorpusLoadError):
                load_corpus(root)

    @patch("eval_judgebench.runner.ollama_version", return_value="0.5.0")
    @patch("eval_model_identity.model_digest_and_quant", return_value=("remote", ""))
    def test_provider_error_not_semantic_fail(self, _mock_digest, _mock_ver):
        def _boom(_case):
            raise RuntimeError("provider down")

        result = run_judgebench(
            CORPUS,
            cfg=CFG,
            judge_model="deepseek-v4-pro",
            under_test_model="llama3.1:8b",
            registry_path=REGISTRY,
            semantic_judge=_boom,
        )
        self.assertEqual(result.cases, [])


class RunnerWithCaseTests(unittest.TestCase):
    @patch("eval_judgebench.runner.ollama_version", return_value="0.5.0")
    @patch("eval_model_identity.model_digest_and_quant", return_value=("remote", ""))
    def test_single_case_with_mock_judge(self, _mock_digest, _mock_ver):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rubric_dir = root / "rubrics"
            rubric_dir.mkdir()
            rubric_src = CORPUS / "rubrics" / "synthesis-grounded-v1.json"
            (rubric_dir / "synthesis-grounded-v1.json").write_text(
                rubric_src.read_text(encoding="utf-8"), encoding="utf-8"
            )
            manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
            manifest["case_count"] = 1
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            case = {
                "case_id": "c1",
                "rubric_id": "synthesis-grounded-v1",
                "candidate_mode": "model_generated",
            }
            (root / "cases.jsonl").write_text(json.dumps(case) + "\n", encoding="utf-8")
            gold = {"case_id": "c1", "verdict": "pass", "expected_candidate_mode": "model_generated"}
            (root / "gold.jsonl").write_text(json.dumps(gold) + "\n", encoding="utf-8")

            def _judge(_case):
                return JudgeInvocationV1(
                    status=InvocationStatus.OK,
                    judge_identity="deepseek-v4-pro",
                    under_test_identity="llama3.1:8b",
                    independence_class=IndependenceClass.CROSS_FAMILY,
                    semantic_judgment=None,
                )

            result = run_judgebench(
                root,
                cfg=CFG,
                judge_model="deepseek-v4-pro",
                under_test_model="llama3.1:8b",
                registry_path=REGISTRY,
                semantic_judge=_judge,
            )
            self.assertEqual(len(result.cases), 1)
            self.assertEqual(result.cases[0].case_id, "c1")

    @patch("eval_judgebench.runner.ollama_version", return_value="0.5.0")
    @patch("eval_model_identity.model_digest_and_quant", return_value=("remote", ""))
    def test_conformance_verdict_matches_gold(self, _mock_digest, _mock_ver):
        """CHK-007 mechanical hook: pinned mock judge disposition matches locked gold."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rubric_dir = root / "rubrics"
            rubric_dir.mkdir()
            rubric_src = CORPUS / "rubrics" / "synthesis-grounded-v1.json"
            (rubric_dir / "synthesis-grounded-v1.json").write_text(
                rubric_src.read_text(encoding="utf-8"), encoding="utf-8"
            )
            manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
            manifest["case_count"] = 1
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            case = {
                "case_id": "conf-1",
                "rubric_id": "synthesis-grounded-v1",
                "candidate_mode": "model_generated",
            }
            (root / "cases.jsonl").write_text(json.dumps(case) + "\n", encoding="utf-8")
            gold = {
                "case_id": "conf-1",
                "verdict": "pass",
                "expected_candidate_mode": "model_generated",
            }
            (root / "gold.jsonl").write_text(json.dumps(gold) + "\n", encoding="utf-8")
            judgment = SemanticJudgmentV1(
                support=Support.FULL,
                coverage=Coverage.COMPLETE,
                contradiction=Contradiction.NONE,
                verdict=Verdict.PASS,
            )

            def _judge(_case):
                return JudgeInvocationV1(
                    status=InvocationStatus.OK,
                    judge_identity="deepseek-v4-pro",
                    under_test_identity="llama3.1:8b",
                    independence_class=IndependenceClass.CROSS_FAMILY,
                    semantic_judgment=judgment,
                )

            result = run_judgebench(
                root,
                cfg=CFG,
                judge_model="deepseek-v4-pro",
                under_test_model="llama3.1:8b",
                registry_path=REGISTRY,
                semantic_judge=_judge,
            )
            self.assertTrue(result.cases[0].agrees_with_gold)
            self.assertEqual(result.cases[0].invocation.status, InvocationStatus.OK)


if __name__ == "__main__":
    unittest.main()
