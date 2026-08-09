"""Unit tests for eval_model_identity (JudgeBench T2)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_judgebench.contracts import IndependenceClass
from eval_model_identity import (
    CanonicalPreflightError,
    ModelIdentityV1,
    assert_canonical_preflight,
    classify_independence,
    load_registry,
    resolve_identity,
)

REGISTRY = (
    Path(__file__).resolve().parent.parent
    / "eval_corpus/fixtures/judgebench/identity-registry-v1.json"
)
CFG = {"models": {"ollama_host": "http://localhost:11434"}}


def _identity(
    *,
    configured: str,
    normalized: str,
    provider: str = "ollama",
    family: str | None = "llama",
    lineage: str | None = None,
) -> ModelIdentityV1:
    return ModelIdentityV1(
        configured_name=configured,
        normalized_name=normalized,
        serving_provider=provider,
        family=family,
        base_lineage=lineage or normalized,
        revision_digest="abc",
        quantization="Q4_K_M",
    )


class ResolveIdentityTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry(REGISTRY)

    @patch("eval_model_identity.model_digest_and_quant", return_value=("d1", "Q4"))
    def test_alias_resolves_to_canonical(self, _mock):
        ident = resolve_identity("qwen3-coder:30b", self.registry, CFG)
        self.assertEqual(ident.normalized_name, "qwen3-coder")
        self.assertEqual(ident.family, "qwen")

    @patch("eval_model_identity.model_digest_and_quant", return_value=("", ""))
    def test_unknown_name_has_no_family(self, _mock):
        ident = resolve_identity("totally-unknown-model", self.registry, CFG)
        self.assertIsNone(ident.family)
        self.assertEqual(ident.base_lineage, "totally-unknown-model")


class ClassifyIndependenceTests(unittest.TestCase):
    def test_same_canonical_is_self_including_quant_alias(self):
        judge = _identity(configured="qwen3-coder:30b", normalized="qwen3-coder", family="qwen")
        under = _identity(configured="qwen3-coder:latest", normalized="qwen3-coder", family="qwen")
        self.assertEqual(classify_independence(judge, under), IndependenceClass.SELF)

    def test_same_family_different_lineage(self):
        judge = _identity(
            configured="deepseek-v4-pro",
            normalized="deepseek-v4-pro",
            provider="deepseek",
            family="deepseek",
            lineage="deepseek-v4-pro",
        )
        under = _identity(
            configured="deepseek-v4-flash",
            normalized="deepseek-v4-flash",
            provider="deepseek",
            family="deepseek",
            lineage="deepseek-v4-flash",
        )
        self.assertEqual(classify_independence(judge, under), IndependenceClass.SAME_FAMILY)

    def test_cross_family_when_both_families_known(self):
        judge = _identity(
            configured="deepseek-v4-pro",
            normalized="deepseek-v4-pro",
            provider="deepseek",
            family="deepseek",
            lineage="deepseek-v4-pro",
        )
        under = _identity(
            configured="llama3.1:8b",
            normalized="llama3.1:8b",
            family="llama",
            lineage="llama3.1:8b",
        )
        self.assertEqual(classify_independence(judge, under), IndependenceClass.CROSS_FAMILY)

    def test_unknown_when_family_missing(self):
        judge = _identity(configured="deepseek-v4-pro", normalized="deepseek-v4-pro", family="deepseek")
        under = _identity(configured="mystery", normalized="mystery", family=None)
        self.assertEqual(classify_independence(judge, under), IndependenceClass.UNKNOWN)

    def test_not_applicable_for_human_curated(self):
        judge = _identity(configured="deepseek-v4-pro", normalized="deepseek-v4-pro", family="deepseek")
        under = _identity(configured="curated", normalized="curated", family=None)
        result = classify_independence(judge, under, under_test_human_curated=True)
        self.assertEqual(result, IndependenceClass.NOT_APPLICABLE)

    def test_provider_diversity_does_not_imply_cross_family(self):
        judge = _identity(
            configured="deepseek-v4-pro",
            normalized="deepseek-v4-pro",
            provider="deepseek",
            family="deepseek",
            lineage="deepseek-v4-pro",
        )
        under = _identity(
            configured="deepseek-v4-flash",
            normalized="deepseek-v4-flash",
            provider="other-provider",
            family="deepseek",
            lineage="deepseek-v4-flash",
        )
        self.assertEqual(classify_independence(judge, under), IndependenceClass.SAME_FAMILY)


class CanonicalPreflightTests(unittest.TestCase):
    def test_cross_family_allowed(self):
        assert_canonical_preflight(IndependenceClass.CROSS_FAMILY)

    def test_unknown_fail_closed(self):
        with self.assertRaises(CanonicalPreflightError):
            assert_canonical_preflight(IndependenceClass.UNKNOWN)

    def test_self_fail_closed(self):
        with self.assertRaises(CanonicalPreflightError):
            assert_canonical_preflight(IndependenceClass.SELF)


if __name__ == "__main__":
    unittest.main()
