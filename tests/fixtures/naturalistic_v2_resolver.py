"""Hermetic fixtures for Naturalistic V2 P2 resolver tests."""

from __future__ import annotations

from eval_naturalistic.digest import artifact_content_digest
from eval_naturalistic.v2.adapters.registry import profile_for_legacy_format
from eval_naturalistic.v2.adapters.unsupported import unsupported_profile
from eval_naturalistic.v2.contracts import EvidenceAvailabilityManifestV2
from eval_naturalistic.v2.evidence import (
    SourcePresenceV2,
    SummaryEvidenceAvailabilityV2,
    VerbatimEvidenceAvailabilityV2,
)
from eval_naturalistic.v2.adapters.profile import EvidenceAdapterProfileV2
from eval_naturalistic.v2.resolver import ResolverInputV2
from tests.fixtures.naturalistic_v2_p1 import (
    FIXED_DIGEST,
    sample_availability,
    sample_availability_manifest,
    sample_seal_manifest,
)


def _bind_availability_manifest(seal, availability) -> EvidenceAvailabilityManifestV2:
    avail_manifest = sample_availability_manifest(seal, availability=availability)
    avail_dict = avail_manifest.to_dict()
    avail_dict["evidence_seal_digest"] = artifact_content_digest(seal.to_dict())
    return EvidenceAvailabilityManifestV2.from_dict(avail_dict)


def crush_resolver_input(
    *,
    verbatim: VerbatimEvidenceAvailabilityV2 = VerbatimEvidenceAvailabilityV2.AVAILABLE,
    summary: SummaryEvidenceAvailabilityV2 = SummaryEvidenceAvailabilityV2.AVAILABLE,
    legacy_format: str = "sqlite_crush",
) -> ResolverInputV2:
    availability = sample_availability(
        presence=SourcePresenceV2.PRESENT,
        verbatim=verbatim,
        summary=summary,
    )
    seal = sample_seal_manifest(availability=availability)
    avail_manifest = _bind_availability_manifest(seal, availability)
    return ResolverInputV2(
        construct_freeze_digest=FIXED_DIGEST,
        evidence_seal=seal,
        evidence_availability=avail_manifest,
        adapter_profile=profile_for_legacy_format(legacy_format),
        legacy_format=legacy_format,
        query_occurrence_reference=seal.occurrence_reference,
    )


def summary_only_resolver_input(
    profile: EvidenceAdapterProfileV2,
    *,
    legacy_format: str = "sqlite_crush",
) -> ResolverInputV2:
    availability = sample_availability(
        presence=SourcePresenceV2.PRESENT,
        verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
        summary=SummaryEvidenceAvailabilityV2.AVAILABLE,
    )
    seal = sample_seal_manifest(availability=availability)
    avail_manifest = _bind_availability_manifest(seal, availability)
    return ResolverInputV2(
        construct_freeze_digest=FIXED_DIGEST,
        evidence_seal=seal,
        evidence_availability=avail_manifest,
        adapter_profile=profile,
        legacy_format=legacy_format,
        query_occurrence_reference=seal.occurrence_reference,
    )


def unsupported_resolver_input() -> ResolverInputV2:
    availability = sample_availability(
        presence=SourcePresenceV2.PRESENT,
        verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
        summary=SummaryEvidenceAvailabilityV2.UNAVAILABLE,
    )
    seal = sample_seal_manifest(availability=availability)
    avail_manifest = _bind_availability_manifest(seal, availability)
    return ResolverInputV2(
        construct_freeze_digest=FIXED_DIGEST,
        evidence_seal=seal,
        evidence_availability=avail_manifest,
        adapter_profile=unsupported_profile(reason="sqlite_kiro"),
        legacy_format="sqlite_kiro",
        query_occurrence_reference=seal.occurrence_reference,
    )
