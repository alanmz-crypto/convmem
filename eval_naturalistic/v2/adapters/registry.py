"""Registry mapping legacy detect formats to V2 evidence adapter profiles."""

from __future__ import annotations

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.v2.adapters.crush_sqlite import LEGACY_FORMAT as CRUSH_FORMAT
from eval_naturalistic.v2.adapters.crush_sqlite import crush_sqlite_profile
from eval_naturalistic.v2.adapters.jsonl_derived import JSONL_FORMATS, jsonl_derived_profile
from eval_naturalistic.v2.adapters.markdown_derived import (
    MARKDOWN_FORMATS,
    markdown_derived_profile,
)
from eval_naturalistic.v2.adapters.opencode_sqlite import LEGACY_FORMAT as OPENCODE_FORMAT
from eval_naturalistic.v2.adapters.opencode_sqlite import opencode_sqlite_profile
from eval_naturalistic.v2.adapters.profile import EvidenceAdapterProfileV2
from eval_naturalistic.v2.adapters.unsupported import unsupported_profile

_SUPPORTED = {
    CRUSH_FORMAT: crush_sqlite_profile,
    OPENCODE_FORMAT: opencode_sqlite_profile,
}


def profile_for_legacy_format(legacy_format: str) -> EvidenceAdapterProfileV2:
    if legacy_format in _SUPPORTED:
        return _SUPPORTED[legacy_format]()
    if legacy_format in JSONL_FORMATS:
        return jsonl_derived_profile(legacy_format)
    if legacy_format in MARKDOWN_FORMATS:
        return markdown_derived_profile(legacy_format)
    return unsupported_profile(reason=f"legacy format '{legacy_format}' has no V2 evidence profile")


def parse_evidence_adapter_profile(data: dict) -> EvidenceAdapterProfileV2:
    profile = EvidenceAdapterProfileV2.from_dict(data)
    profile.validate()
    return profile


def resolve_profile_or_fail(legacy_format: str | None) -> EvidenceAdapterProfileV2:
    if legacy_format is None:
        return unsupported_profile(reason="missing legacy format")
    profile = profile_for_legacy_format(legacy_format)
    if profile.profile_id == "v2/evidence/unsupported":
        raise StructuralContractError(
            f"unsupported legacy format '{legacy_format}' for V2 evidence extraction"
        )
    return profile
