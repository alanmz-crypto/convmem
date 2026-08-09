"""Model identity resolution and independence classification (JudgeBench T2).

Resolves identities *before* execution using the curated registry. Classification
is fail-closed: ``unknown`` cannot be promoted to ``cross_family`` by user
declaration. Serving-provider diversity alone never proves ``cross_family``.
"""

# pylint: disable=duplicate-code

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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

    def to_record_dict(self) -> dict[str, str]:
        return {
            "configured_name": self.configured_name,
            "normalized_name": self.normalized_name,
            "serving_provider": self.serving_provider,
            "family": self.family or "",
            "base_lineage": self.base_lineage,
            "revision_digest": self.revision_digest,
            "quantization": self.quantization,
        }


def resolve_identity(
    name: str,
    registry: IdentityRegistry,
    cfg: dict,
) -> ModelIdentityV1:
    """Resolve a configured model name to a ModelIdentityV1 record."""
    configured = (name or "").strip()
    canonical = registry.resolve_alias(configured)
    digest, quant = model_digest_and_quant(cfg, configured)
    if canonical is not None:
        rec = registry.records.get(canonical)
        if rec is None:
            for item in registry.records.values():
                if item.canonical_id == canonical:
                    rec = item
                    break
        if rec is not None:
            return ModelIdentityV1(
                configured_name=configured,
                normalized_name=canonical,
                serving_provider=rec.provider,
                family=rec.family,
                base_lineage=canonical,
                revision_digest=digest,
                quantization=quant,
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
