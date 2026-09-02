"""Hermetic fixtures for Naturalistic V2 adapter profile tests."""

from __future__ import annotations

from eval_naturalistic.v2.adapters.capability import (
    AttachmentMaterialSpanCapability,
)
from eval_naturalistic.v2.adapters.crush_sqlite import crush_sqlite_profile
from eval_naturalistic.v2.adapters.profile import EvidenceAdapterProfileV2


def crush_profile_with_attachment_loss() -> EvidenceAdapterProfileV2:
    profile = crush_sqlite_profile()
    vector = profile.capability_vector.with_overrides(
        attachment_material_span_completeness=AttachmentMaterialSpanCapability.MISSING.value
    )
    return profile.with_capability_vector(vector)


def valid_profile_dict(profile: EvidenceAdapterProfileV2) -> dict:
    return profile.to_dict()
