"""Cross-artifact validation for naturalistic study G1 substrate."""

from __future__ import annotations

from typing import Any, Protocol

from eval_naturalistic.base import NaturalisticValidation
from eval_naturalistic.contracts import (
    CensusSampleManifestV1,
    ConvMemCaptureStateV1,
    EpisodeFrameV1,
    EpisodeRecordV1,
    ProbeManifestV1,
    RawEvidenceManifestV1,
    TargetRegistryV1,
    verify_artifact_digest,
)
from eval_naturalistic.digest import artifact_content_digest
from eval_naturalistic.enums import StudyTerminalDisposition


class _HasHeader(Protocol):
    header: Any

    def to_dict(self) -> dict[str, Any]: ...


def _append(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_parent_binding(
    child: _HasHeader,
    *,
    expected_parent_id: str,
    expected_parent_digest: str,
    label: str,
) -> NaturalisticValidation:
    errors: list[str] = []
    header = child.header
    if header.parent_artifact_id != expected_parent_id:
        _append(
            errors,
            f"{label}: parent_artifact_id mismatch "
            f"(expected {expected_parent_id}, got {header.parent_artifact_id})",
        )
    if header.parent_digest != expected_parent_digest:
        _append(
            errors,
            f"{label}: parent_digest mismatch "
            f"(expected {expected_parent_digest}, got {header.parent_digest})",
        )
    if header.parent_artifact_id is None or header.parent_digest is None:
        _append(errors, f"{label}: missing required parent binding")
    return NaturalisticValidation(errors=errors)


def validate_seal_immutability(
    artifact: _HasHeader,
    *,
    label: str,
    mutated_body: dict[str, Any] | None = None,
) -> NaturalisticValidation:
    errors: list[str] = []
    body = artifact.to_dict()
    header = body.get("header", {})
    if not header.get("sealed"):
        _append(errors, f"{label}: artifact is not sealed")
        return NaturalisticValidation(errors=errors)
    if not verify_artifact_digest(body):
        _append(errors, f"{label}: sealed content_digest does not match body")
    if mutated_body is not None:
        if verify_artifact_digest(mutated_body):
            _append(errors, f"{label}: mutated body still verifies against original digest")
        recomputed = artifact_content_digest(mutated_body)
        if recomputed == header.get("content_digest"):
            _append(errors, f"{label}: mutation did not change digest")
    return NaturalisticValidation(errors=errors)


def validate_role_collision(
    probe: ProbeManifestV1,
    *,
    adjudicator_ids_for_target: set[str],
) -> NaturalisticValidation:
    errors: list[str] = []
    if probe.probe_author_id in adjudicator_ids_for_target:
        _append(
            errors,
            "probe_author_id must not equal adjudicator for same target",
        )
    if not probe.adjudicator_collision_check_passed:
        _append(errors, "adjudicator_collision_check_passed must be true for valid probe")
    return NaturalisticValidation(errors=errors)


def validate_scoring_key_separation(probe: ProbeManifestV1) -> NaturalisticValidation:
    errors: list[str] = []
    public = probe.agent_b_view()
    forbidden_keys = {"key_content", "answer_key", "scoring_key_content"}
    for key in forbidden_keys:
        if key in public:
            _append(errors, f"Agent-B view must not expose {key}")
    if "scoring_key_digest" in public:
        _append(errors, "Agent-B view must not expose raw scoring_key_digest field name")
    if public.get("scoring_key_integrity_digest") != probe.scoring_key_digest:
        _append(errors, "integrity digest binding mismatch")
    return NaturalisticValidation(errors=errors)


def validate_capture_independent_registry(
    registry: TargetRegistryV1,
    capture: ConvMemCaptureStateV1,
    *,
    proposed_registry: TargetRegistryV1 | None = None,
) -> NaturalisticValidation:
    errors: list[str] = []
    if capture.target_registry_artifact_id != registry.header.artifact_id:
        _append(errors, "capture state must reference registry artifact_id")
    if capture.target_registry_digest != registry.header.content_digest:
        _append(errors, "capture state must reference registry content_digest")
    registry_target_ids = {target.target_id for target in registry.targets}
    capture_target_ids = {state.target_id for state in capture.target_states}
    if not capture_target_ids.issubset(registry_target_ids):
        _append(errors, "capture state references unknown target_ids")
    if proposed_registry is not None:
        from eval_naturalistic.adjudication import reject_capture_driven_registry_mutation

        mutation = reject_capture_driven_registry_mutation(registry, proposed_registry)
        errors.extend(mutation.errors)
    return NaturalisticValidation(errors=errors)


def validate_terminal_state_distinction(
    blocked: StudyTerminalDisposition,
    null_equiv: StudyTerminalDisposition,
) -> NaturalisticValidation:
    errors: list[str] = []
    if blocked == null_equiv:
        _append(errors, "BLOCKED_NON_ESTIMABLE must differ from COMPLETE_NULL_EQUIVALENT")
    if blocked != StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE:
        _append(errors, "expected BLOCKED_NON_ESTIMABLE disposition")
    if null_equiv != StudyTerminalDisposition.COMPLETE_NULL_EQUIVALENT:
        _append(errors, "expected COMPLETE_NULL_EQUIVALENT disposition")
    return NaturalisticValidation(errors=errors)


def validate_artifact_chain(
    *,
    frame: EpisodeFrameV1,
    episode: EpisodeRecordV1,
    evidence: RawEvidenceManifestV1,
    registry: TargetRegistryV1,
    census: CensusSampleManifestV1 | None = None,
    probe: ProbeManifestV1 | None = None,
) -> NaturalisticValidation:
    errors: list[str] = []

    if episode.frame_artifact_id != frame.header.artifact_id:
        _append(errors, "EpisodeRecord frame_artifact_id mismatch")
    if episode.frame_digest != frame.header.content_digest:
        _append(errors, "EpisodeRecord frame_digest mismatch")

    if evidence.episode_id != episode.episode_id:
        _append(errors, "RawEvidenceManifest episode_id mismatch")
    if evidence.episode_record_artifact_id != episode.header.artifact_id:
        _append(errors, "RawEvidenceManifest episode_record_artifact_id mismatch")
    if evidence.episode_record_digest != episode.header.content_digest:
        _append(errors, "RawEvidenceManifest episode_record_digest mismatch")

    if evidence.header.artifact_id not in registry.evidence_manifest_ids:
        _append(errors, "TargetRegistry missing evidence manifest id")

    episode_ids_in_registry = {entry.episode_id for entry in registry.episode_entries}
    if episode.episode_id not in episode_ids_in_registry:
        _append(errors, "TargetRegistry missing episode entry")

    if not registry.header.sealed:
        _append(errors, "TargetRegistry must be sealed before downstream artifacts")

    if census is not None:
        if census.target_registry_artifact_id != registry.header.artifact_id:
            _append(errors, "CensusSampleManifest registry artifact_id mismatch")
        if census.target_registry_digest != registry.header.content_digest:
            _append(errors, "CensusSampleManifest registry digest mismatch")
        if not registry.header.sealed:
            _append(errors, "CensusSampleManifest requires sealed registry")

    if probe is not None:
        if not registry.header.sealed:
            _append(errors, "ProbeManifest requires sealed registry")
        target_ids = {target.target_id for target in registry.targets}
        if probe.target_id not in target_ids and probe.target_id:
            _append(errors, "ProbeManifest target_id not in registry")

    for artifact, label in (
        (frame, "EpisodeFrame"),
        (episode, "EpisodeRecord"),
        (evidence, "RawEvidenceManifest"),
        (registry, "TargetRegistry"),
    ):
        result = validate_seal_immutability(artifact, label=label)
        errors.extend(result.errors)

    return NaturalisticValidation(errors=errors)


def validate_generation_integrity(
    child: _HasHeader,
    *,
    expected_parent_digest: str,
    label: str,
) -> NaturalisticValidation:
    errors: list[str] = []
    if child.header.parent_digest != expected_parent_digest:
        _append(
            errors,
            f"{label}: bound to obsolete parent generation digest",
        )
    return NaturalisticValidation(errors=errors)
