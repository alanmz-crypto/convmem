"""Model identity resolution and independence classification (JudgeBench T2).

Resolves identities *before* execution using the curated registry. Classification
is fail-closed: ``unknown`` cannot be promoted to ``cross_family`` by user
declaration. Serving-provider diversity alone never proves ``cross_family``.
"""

# pylint: disable=duplicate-code

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval_judgebench.contracts import IndependenceClass
from eval_judgebench.identity_registry import IdentityRegistry, load_identity_registry
from eval_provenance import model_digest_and_quant


class CanonicalPreflightError(ValueError):
    """Canonical calibration/baseline/update refused due to independence class."""


@dataclass
class ModelIdentityV1:
    configured_name: str
    normalized_name: str
    serving_provider: str
    family: str | None
    base_lineage: str
    revision_digest: str
    quantization: str
    alias_provenance: str | None = None
    alias_metadata: dict[str, Any] | None = None

    def to_record_dict(self) -> dict[str, str]:
        return {
            "configured_name": self.configured_name,
            "normalized_name": self.normalized_name,
            "serving_provider": self.serving_provider,
            "family": self.family or "",
            "base_lineage": self.base_lineage,
            "revision_digest": self.revision_digest,
            "quantization": self.quantization,
            "alias_provenance": self.alias_provenance or "",
        }


def resolve_identity(
    name: str,
    registry: IdentityRegistry,
    cfg: dict,
    *,
    offline: bool = False,
) -> ModelIdentityV1:
    """Resolve a configured model name to a ModelIdentityV1 record."""
    configured = (name or "").strip()
    canonical = registry.resolve_alias(configured)
    if offline:
        metadata = (cfg.get("judgebench") or {}).get("identity_metadata") or {}
        item = metadata.get(configured) or metadata.get(canonical) or {}
        digest = str(item.get("revision_digest") or "")
        quant = str(item.get("quantization") or "")
    else:
        digest, quant = model_digest_and_quant(cfg, configured)
    if canonical is not None:
        rec = registry.record_for(configured)
        if rec is not None:
            return ModelIdentityV1(
                configured_name=configured,
                normalized_name=canonical,
                serving_provider=rec.provider,
                family=rec.family,
                base_lineage=canonical,
                revision_digest=digest,
                quantization=quant,
                alias_provenance=registry.alias_provenance(configured),
                alias_metadata=registry.alias_metadata(configured),
            )
    normalized = configured.lower() if configured else ""
    return ModelIdentityV1(
        configured_name=configured,
        normalized_name=normalized,
        serving_provider="",
        family=None,
        base_lineage=normalized,
        revision_digest=digest,
        quantization=quant,
    )


def preflight_identity_pair(
    judge_name: str,
    under_test_name: str,
    *,
    registry: IdentityRegistry,
    cfg: dict,
    under_test_provider: str | None = None,
    offline: bool = False,
) -> IndependenceClass:
    """Resolve and validate one frozen-origin comparison before a request.

    The provider recorded in a frozen origin is part of provenance.  A missing
    or conflicting provider is not evidence of independence and therefore
    fails closed instead of being repaired from the caller's identity.
    """
    judge = resolve_identity(judge_name, registry, cfg, offline=offline)
    under_test = resolve_identity(under_test_name, registry, cfg, offline=offline)
    if under_test_provider is not None:
        expected = registry.record_for(under_test_name)
        if (
            expected is None
            or not under_test_provider
            or expected.provider != under_test_provider
        ):
            raise CanonicalPreflightError(
                "canonical run refused: frozen candidate provider conflict or unknown "
                f"for {under_test_name!r}"
            )
    result = classify_independence(judge, under_test)
    assert_canonical_preflight(result)
    return result


def preflight_registry_v2_origins(
    judge_names: Iterable[str],
    *,
    registry: IdentityRegistry,
    under_test_name: str = "gpt-5-codex-sol",
    cfg: dict | None = None,
) -> dict[str, IndependenceClass]:
    """Check the authorized frozen-origin matrix without any provider call."""
    settings = cfg or {}
    results: dict[str, IndependenceClass] = {}
    for judge_name in judge_names:
        results[judge_name] = preflight_identity_pair(
            judge_name,
            under_test_name,
            registry=registry,
            cfg=settings,
            under_test_provider="openai",
            offline=True,
        )
    return results


def classify_independence(
    judge: ModelIdentityV1,
    under_test: ModelIdentityV1,
    *,
    under_test_human_curated: bool = False,
) -> IndependenceClass:
    """Classify judge vs under-test independence without substring guessing."""
    if under_test_human_curated:
        return IndependenceClass.NOT_APPLICABLE
    if judge.base_lineage and judge.base_lineage == under_test.base_lineage:
        return IndependenceClass.SELF
    if judge.family is None or under_test.family is None:
        return IndependenceClass.UNKNOWN
    if judge.family != under_test.family:
        return IndependenceClass.CROSS_FAMILY
    return IndependenceClass.SAME_FAMILY


def assert_canonical_preflight(independence: IndependenceClass) -> None:
    """Refuse canonical calibration without independence or curated provenance.

    ``not_applicable`` is valid only when the candidate is explicitly marked
    human-curated.  It is not an independence claim and cannot be used for a
    model-generated candidate.
    """
    if independence not in {
        IndependenceClass.CROSS_FAMILY,
        IndependenceClass.NOT_APPLICABLE,
    }:
        raise CanonicalPreflightError(
            f"canonical run refused: independence class {independence.value!r} "
            "(requires cross_family or human-curated not_applicable)"
        )


def load_registry(path: Path | str) -> IdentityRegistry:
    """Convenience wrapper around the JudgeBench identity registry loader."""
    return load_identity_registry(path)
