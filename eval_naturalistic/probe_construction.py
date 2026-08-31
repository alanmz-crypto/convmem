"""G3 probe construction, leakage review, and scoring-key freeze machinery."""

from __future__ import annotations

# Probe records and the fail-closed builder intentionally mirror the governed contract.
# pylint: disable=too-many-instance-attributes,too-many-locals
import copy
import re
from dataclasses import dataclass
from typing import Any

from eval_naturalistic.base import ArtifactHeaderV1
from eval_naturalistic.contract_validate import NaturalisticValidation
from eval_naturalistic.contracts import (
    CensusSampleManifestV1,
    LeakageReviewManifestV1,
    ProbeAuthorProvenanceV1,
    ProbeManifestV1,
    ScoringKeyContentV1,
    ScoringKeyV1,
    TargetRecordV1,
    TargetRegistryV1,
    seal_artifact_dict,
)
from eval_naturalistic.digest import artifact_content_digest, make_artifact_id
from eval_naturalistic.enums import (
    LeakageCheckKind,
    LeakageReviewDisposition,
    ProbeBuildOutcome,
    ProbeFamilyKind,
)


@dataclass
class ProbeConstructionConfigV1:
    """Frozen probe-construction workflow bound to sealed registry/sample authority."""

    probe_family_id: str
    scoring_key_partition_identity: str
    seal_time: str
    review_tool_version: str = "leakage-checklist-v1"


@dataclass
class ProbeDraftV1:
    """Pre-freeze probe material including author-visible content."""

    probe_id: str
    target_id: str
    episode_id: str
    probe_text: str
    probe_family_kind: ProbeFamilyKind
    probe_author_id: str
    permitted_context_digest: str
    author_provenance: ProbeAuthorProvenanceV1
    scoring_key_content: ScoringKeyContentV1


@dataclass
class LeakageChecklistResult:
    items: list[dict[str, Any]]
    disposition: LeakageReviewDisposition
    errors: list[str]

    @property
    def ok(self) -> bool:
        return self.disposition == LeakageReviewDisposition.APPROVED and not self.errors


@dataclass
class ProbeBuildResult:
    ok: bool
    probe: ProbeManifestV1 | None
    scoring_key: ScoringKeyV1 | None
    leakage_review: LeakageReviewManifestV1 | None
    key_content: ScoringKeyContentV1 | None
    errors: list[str]
    outcome: ProbeBuildOutcome | None = None


_TREATMENT_CUE_RE = re.compile(r"\b(c0|c1|control\s+condition|treatment\s+arm)\b", re.IGNORECASE)
_CONVMEM_CUE_RE = re.compile(
    r"\b(convmem|chroma|retrieval\s+rank|capture\s+state|memory\s+corpus)\b",
    re.IGNORECASE,
)
_SOURCE_PATH_RE = re.compile(
    r"(/home/|synthetic://|\.(?:py|md|jsonl|toml)\b|src-\d+)",
    re.IGNORECASE,
)
_SOURCE_LOCATION_RE = re.compile(
    r"\b(line\s+\d+|span\s+\d+|offset\s+\d+|character\s+\d+)\b",
    re.IGNORECASE,
)


def compute_text_digest(text: str) -> str:
    body = {"text": text}
    return artifact_content_digest(body)


def compute_scoring_key_content_digest(
    *,
    probe_id: str,
    target_id: str,
    ground_truth_value: str,
    rubric_version: str,
) -> str:
    """Content-only digest for scorer-partition binding (excludes header envelope)."""

    return artifact_content_digest(
        {
            "probe_id": probe_id,
            "target_id": target_id,
            "ground_truth_value": ground_truth_value,
            "rubric_version": rubric_version,
        }
    )


def _finalize_body(
    body: dict[str, Any],
    *,
    kind: str,
    schema: str,
    role: str,
    seal_time: str,
) -> dict[str, Any]:
    digest = artifact_content_digest(body)
    header = body.get("header", {})
    body["header"] = {
        **header,
        "artifact_id": make_artifact_id(kind=kind, content_digest=digest),
        "schema_version": schema,
        "content_digest": digest,
        "responsible_role": role,
    }
    return seal_artifact_dict(body, seal_time=seal_time)


def validate_probe_author_not_adjudicator(
    *,
    probe_author_id: str,
    target: TargetRecordV1,
) -> NaturalisticValidation:
    errors: list[str] = []
    adjudicator_ids = set(target.adjudicator_ids)
    for record in target.adjudication_records:
        adjudicator_ids.add(record.adjudicator_id)
    if probe_author_id in adjudicator_ids:
        errors.append("probe author must not be an adjudicator for the same target")
    return NaturalisticValidation(errors=errors)


def validate_probe_author_provenance(
    provenance: ProbeAuthorProvenanceV1,
    *,
    probe_author_id: str,
    target_id: str,
) -> NaturalisticValidation:
    errors: list[str] = []
    if provenance.probe_author_id != probe_author_id:
        errors.append("probe author provenance identity mismatch")
    if provenance.target_id != target_id:
        errors.append("probe author provenance target_id mismatch")
    if not provenance.access_recorded:
        errors.append("probe author access must be explicitly recorded")
    if not provenance.treatment_blind:
        errors.append("probe author must remain treatment-blind")
    if not provenance.c0_c1_result_blind:
        errors.append("probe author must remain blind to C0/C1 outcomes")
    if not provenance.capture_retrieval_blind:
        errors.append("probe author must remain blind to capture/retrieval behavior")
    for token in provenance.forbidden_reference_tokens or []:
        if token:
            errors.append(f"probe author provenance records forbidden reference: {token}")
    return NaturalisticValidation(errors=errors)


def validate_leakage_reviewer_independence(
    *,
    reviewer_id: str,
    probe_author_id: str,
    target: TargetRecordV1,
) -> NaturalisticValidation:
    errors: list[str] = []
    if reviewer_id == probe_author_id:
        errors.append("leakage reviewer must not be the probe author")
    adjudicator_ids = set(target.adjudicator_ids)
    for record in target.adjudication_records:
        adjudicator_ids.add(record.adjudicator_id)
    if reviewer_id in adjudicator_ids:
        errors.append("leakage reviewer must not be a target adjudicator")
    return NaturalisticValidation(errors=errors)


def _token_set(text: str) -> set[str]:
    return {tok.lower() for tok in re.findall(r"[a-z0-9]+", text.lower()) if len(tok) > 2}


def _paraphrase_overlap(probe_text: str, answer_text: str) -> float:
    answer_tokens = _token_set(answer_text)
    if not answer_tokens:
        return 0.0
    probe_tokens = _token_set(probe_text)
    overlap = answer_tokens & probe_tokens
    return len(overlap) / len(answer_tokens)


def run_leakage_checklist(
    probe_text: str,
    *,
    ground_truth_answer: str | None = None,
    paraphrase_threshold: float = 0.75,
    ordinary_task_exception: str | None = None,
) -> LeakageChecklistResult:
    """Mechanical leakage review; fails closed on prohibited cues."""

    items: list[dict[str, Any]] = []
    errors: list[str] = []

    def _item(kind: LeakageCheckKind, passed: bool, detail: str) -> None:
        items.append({"check_kind": kind.value, "passed": passed, "detail": detail})
        if not passed:
            errors.append(f"leakage check failed ({kind.value}): {detail}")

    answer = (ground_truth_answer or "").strip()
    probe_lower = probe_text.lower()
    if answer:
        if answer.lower() in probe_lower:
            _item(LeakageCheckKind.ANSWER_LEAKAGE, False, "answer text present in probe")
        else:
            _item(LeakageCheckKind.ANSWER_LEAKAGE, True, "no explicit answer leakage")
        overlap = _paraphrase_overlap(probe_text, answer)
        paraphrase_ok = overlap < paraphrase_threshold
        if not paraphrase_ok and ordinary_task_exception:
            paraphrase_ok = True
            _item(
                LeakageCheckKind.CLOSE_PARAPHRASE,
                True,
                f"paraphrase overlap {overlap:.2f} allowed by documented exception",
            )
        else:
            _item(
                LeakageCheckKind.CLOSE_PARAPHRASE,
                paraphrase_ok,
                f"paraphrase token overlap {overlap:.2f}",
            )
    else:
        _item(LeakageCheckKind.ANSWER_LEAKAGE, True, "no ground truth supplied for answer check")
        _item(LeakageCheckKind.CLOSE_PARAPHRASE, True, "no ground truth supplied for paraphrase check")

    path_match = _SOURCE_PATH_RE.search(probe_text)
    _item(
        LeakageCheckKind.SOURCE_PATH,
        path_match is None,
        "source path disclosed" if path_match else "no source path cue",
    )
    loc_match = _SOURCE_LOCATION_RE.search(probe_text)
    _item(
        LeakageCheckKind.SOURCE_LOCATION,
        loc_match is None,
        "source location disclosed" if loc_match else "no source location cue",
    )
    treatment_match = _TREATMENT_CUE_RE.search(probe_text)
    _item(
        LeakageCheckKind.TREATMENT_CONDITION,
        treatment_match is None,
        "treatment condition cue present" if treatment_match else "no treatment cue",
    )
    convmem_match = _CONVMEM_CUE_RE.search(probe_text)
    _item(
        LeakageCheckKind.CONVMEM_RETRIEVAL,
        convmem_match is None,
        "ConvMem/retrieval cue present" if convmem_match else "no ConvMem cue",
    )

    disposition = (
        LeakageReviewDisposition.APPROVED
        if not errors
        else LeakageReviewDisposition.REJECTED
    )
    return LeakageChecklistResult(items=items, disposition=disposition, errors=errors)


def validate_registry_sample_parent_binding(
    *,
    registry: TargetRegistryV1,
    census: CensusSampleManifestV1 | None,
    probe: ProbeManifestV1,
) -> NaturalisticValidation:
    errors: list[str] = []
    if probe.target_registry_artifact_id != registry.header.artifact_id:
        errors.append("probe target_registry_artifact_id mismatch")
    if probe.target_registry_digest != registry.header.content_digest:
        errors.append("probe target_registry_digest mismatch")
    if census is not None:
        if probe.sample_manifest_artifact_id != census.header.artifact_id:
            errors.append("probe sample_manifest_artifact_id mismatch")
        if probe.sample_manifest_digest != census.header.content_digest:
            errors.append("probe sample_manifest_digest mismatch")
    elif probe.sample_manifest_artifact_id is not None:
        errors.append("probe binds sample manifest but census authority absent")
    return NaturalisticValidation(errors=errors)


def validate_scoring_key_integrity_binding(
    probe: ProbeManifestV1,
    scoring_key: ScoringKeyV1,
    key_content: ScoringKeyContentV1,
) -> NaturalisticValidation:
    errors: list[str] = []
    if scoring_key.probe_id != probe.probe_id:
        errors.append("scoring key probe_id mismatch")
    if scoring_key.target_id != probe.target_id:
        errors.append("scoring key target_id mismatch")
    if scoring_key.key_partition_identity != probe.scoring_key_partition_identity:
        errors.append("scoring key partition identity mismatch")
    content_digest = compute_scoring_key_content_digest(
        probe_id=key_content.probe_id,
        target_id=key_content.target_id,
        ground_truth_value=key_content.ground_truth_value,
        rubric_version=key_content.rubric_version,
    )
    if scoring_key.key_content_digest != content_digest:
        errors.append("scoring key manifest digest does not bind key content")
    if probe.scoring_key_digest != scoring_key.key_content_digest:
        errors.append("probe scoring_key_digest mismatch")
    public = probe.agent_b_view()
    if "ground_truth_value" in public:
        errors.append("Agent-B view exposes ground truth")
    return NaturalisticValidation(errors=errors)


def reject_post_freeze_probe_mutation(
    sealed_probe: ProbeManifestV1,
    proposed_probe: ProbeManifestV1,
) -> NaturalisticValidation:
    errors: list[str] = []
    if not sealed_probe.header.sealed:
        errors.append("reference probe must be sealed")
        return NaturalisticValidation(errors=errors)
    if sealed_probe.header.artifact_id != proposed_probe.header.artifact_id:
        errors.append("probe artifact_id substitution prohibited after freeze")
    if sealed_probe.prompt_content_digest != proposed_probe.prompt_content_digest:
        errors.append("probe prompt mutation prohibited after freeze")
    if sealed_probe.header.content_digest != proposed_probe.header.content_digest:
        errors.append("probe digest changed after freeze")
    return NaturalisticValidation(errors=errors)


def reject_probe_repair_after_outcomes(
    *,
    sealed_probe: ProbeManifestV1,
    proposed_probe: ProbeManifestV1,
    outcomes_known: bool,
) -> NaturalisticValidation:
    errors: list[str] = []
    if not outcomes_known:
        return NaturalisticValidation(errors=errors)
    mutation = reject_post_freeze_probe_mutation(sealed_probe, proposed_probe)
    errors.extend(mutation.errors)
    if mutation.errors:
        errors.append("probe repair after trial outcomes prohibited")
    return NaturalisticValidation(errors=errors)


def build_sealed_probe_bundle(
    *,
    registry: TargetRegistryV1,
    census: CensusSampleManifestV1 | None,
    target: TargetRecordV1,
    draft: ProbeDraftV1,
    leakage_reviewer_id: str,
    config: ProbeConstructionConfigV1,
    ground_truth_answer: str | None = None,
    ordinary_task_exception: str | None = None,
) -> ProbeBuildResult:
    """Construct, leakage-review, and freeze probe + scoring-key artifacts."""

    errors: list[str] = []

    if not registry.header.sealed:
        errors.append("TargetRegistry must be sealed before probe construction")
    if census is not None and not census.header.sealed:
        errors.append("CensusSampleManifest must be sealed before probe construction")

    role = validate_probe_author_not_adjudicator(
        probe_author_id=draft.probe_author_id,
        target=target,
    )
    errors.extend(role.errors)

    provenance = validate_probe_author_provenance(
        draft.author_provenance,
        probe_author_id=draft.probe_author_id,
        target_id=draft.target_id,
    )
    errors.extend(provenance.errors)

    reviewer = validate_leakage_reviewer_independence(
        reviewer_id=leakage_reviewer_id,
        probe_author_id=draft.probe_author_id,
        target=target,
    )
    errors.extend(reviewer.errors)

    checklist = run_leakage_checklist(
        draft.probe_text,
        ground_truth_answer=ground_truth_answer or draft.scoring_key_content.ground_truth_value,
        ordinary_task_exception=ordinary_task_exception,
    )

    prompt_digest = compute_text_digest(draft.probe_text)
    provenance_digest = artifact_content_digest(draft.author_provenance.to_dict())

    if errors:
        return ProbeBuildResult(
            ok=False,
            probe=None,
            scoring_key=None,
            leakage_review=None,
            key_content=None,
            errors=errors,
            outcome=ProbeBuildOutcome.ROLE_OR_PROVENANCE_REJECTED,
        )

    if not checklist.ok:
        return ProbeBuildResult(
            ok=False,
            probe=None,
            scoring_key=None,
            leakage_review=None,
            key_content=None,
            errors=list(checklist.errors),
            outcome=ProbeBuildOutcome.LEAKAGE_REJECTED,
        )

    key_content_digest_val = compute_scoring_key_content_digest(
        probe_id=draft.probe_id,
        target_id=draft.target_id,
        ground_truth_value=draft.scoring_key_content.ground_truth_value,
        rubric_version=draft.scoring_key_content.rubric_version,
    )

    key_content_body = {
        "header": ArtifactHeaderV1(
            artifact_id="pending",
            schema_version=ScoringKeyContentV1.SCHEMA,
            parent_artifact_id=None,
            parent_digest=None,
            created_at=config.seal_time,
            seal_time=None,
            responsible_role="scorer_partition",
            content_digest=None,
            sealed=False,
        ).to_dict(),
        **{k: v for k, v in draft.scoring_key_content.to_dict().items() if k != "header"},
    }

    parent_id = census.header.artifact_id if census is not None else registry.header.artifact_id
    parent_digest = (
        census.header.content_digest if census is not None else registry.header.content_digest
    )

    probe_body = {
        "header": ArtifactHeaderV1(
            artifact_id="pending",
            schema_version=ProbeManifestV1.SCHEMA,
            parent_artifact_id=parent_id,
            parent_digest=parent_digest,
            created_at=config.seal_time,
            seal_time=None,
            responsible_role="probe_author",
            content_digest=None,
            sealed=False,
        ).to_dict(),
        "probe_id": draft.probe_id,
        "target_id": draft.target_id,
        "episode_id": draft.episode_id,
        "probe_family_id": config.probe_family_id,
        "probe_family_kind": draft.probe_family_kind.value,
        "probe_author_id": draft.probe_author_id,
        "leakage_reviewer_id": leakage_reviewer_id,
        "adjudicator_collision_check_passed": True,
        "leakage_review_disposition": LeakageReviewDisposition.APPROVED.value,
        "prompt_content_digest": prompt_digest,
        "permitted_context_digest": draft.permitted_context_digest,
        "probe_author_provenance_digest": provenance_digest,
        "target_registry_artifact_id": registry.header.artifact_id,
        "target_registry_digest": registry.header.content_digest,
        "sample_manifest_artifact_id": census.header.artifact_id if census else None,
        "sample_manifest_digest": census.header.content_digest if census else None,
        "scoring_key_digest": key_content_digest_val,
        "scoring_key_partition_identity": config.scoring_key_partition_identity,
        "leakage_review_manifest_id": "pending",
        "leakage_review_digest": "pending",
    }
    probe_dict = _finalize_body(
        probe_body,
        kind="probe",
        schema=ProbeManifestV1.SCHEMA,
        role="probe_author",
        seal_time=config.seal_time,
    )
    probe = ProbeManifestV1.from_dict(probe_dict)

    review_body: dict[str, Any] = {
        "header": ArtifactHeaderV1(
            artifact_id="pending",
            schema_version=LeakageReviewManifestV1.SCHEMA,
            parent_artifact_id=probe.header.artifact_id,
            parent_digest=probe.header.content_digest,
            created_at=config.seal_time,
            seal_time=None,
            responsible_role="leakage_reviewer",
            content_digest=None,
            sealed=False,
        ).to_dict(),
        "probe_id": draft.probe_id,
        "probe_digest": probe.header.content_digest,
        "reviewer_id": leakage_reviewer_id,
        "disposition": LeakageReviewDisposition.APPROVED.value,
        "checklist_items": checklist.items,
        "review_tool_version": config.review_tool_version,
        "sign_off_time": config.seal_time,
    }
    if ordinary_task_exception is not None:
        review_body["exception_record"] = ordinary_task_exception
    review_dict = _finalize_body(
        review_body,
        kind="leakage_review",
        schema=LeakageReviewManifestV1.SCHEMA,
        role="leakage_reviewer",
        seal_time=config.seal_time,
    )
    leakage_review = LeakageReviewManifestV1.from_dict(review_dict)

    probe_body_updated = copy.deepcopy(probe.to_dict())
    probe_body_updated["leakage_review_manifest_id"] = leakage_review.header.artifact_id
    probe_body_updated["leakage_review_digest"] = leakage_review.header.content_digest
    probe_body_updated["header"] = {
        **probe_body_updated["header"],
        "content_digest": None,
        "artifact_id": "pending",
        "sealed": False,
        "seal_time": None,
    }
    probe_dict = _finalize_body(
        probe_body_updated,
        kind="probe",
        schema=ProbeManifestV1.SCHEMA,
        role="probe_author",
        seal_time=config.seal_time,
    )
    probe = ProbeManifestV1.from_dict(probe_dict)

    key_body = {
        "header": ArtifactHeaderV1(
            artifact_id="pending",
            schema_version=ScoringKeyV1.SCHEMA,
            parent_artifact_id=probe.header.artifact_id,
            parent_digest=probe.header.content_digest,
            created_at=config.seal_time,
            seal_time=None,
            responsible_role="scorer_partition",
            content_digest=None,
            sealed=False,
        ).to_dict(),
        "probe_id": probe.probe_id,
        "target_id": probe.target_id,
        "key_partition_identity": config.scoring_key_partition_identity,
        "key_content_digest": key_content_digest_val,
    }
    key_dict = _finalize_body(
        key_body,
        kind="scoring_key",
        schema=ScoringKeyV1.SCHEMA,
        role="scorer_partition",
        seal_time=config.seal_time,
    )
    scoring_key = ScoringKeyV1.from_dict(key_dict)

    key_content_body["header"] = {
        **key_content_body["header"],
        "parent_artifact_id": scoring_key.header.artifact_id,
        "parent_digest": scoring_key.header.content_digest,
    }
    key_content_body = _finalize_body(
        key_content_body,
        kind="scoring_key_content",
        schema=ScoringKeyContentV1.SCHEMA,
        role="scorer_partition",
        seal_time=config.seal_time,
    )
    key_content = ScoringKeyContentV1.from_dict(key_content_body)

    binding = validate_scoring_key_integrity_binding(probe, scoring_key, key_content)
    parent = validate_registry_sample_parent_binding(registry=registry, census=census, probe=probe)
    errors.extend(binding.errors)
    errors.extend(parent.errors)

    if errors:
        return ProbeBuildResult(
            ok=False,
            probe=None,
            scoring_key=None,
            leakage_review=leakage_review,
            key_content=key_content,
            errors=errors,
            outcome=ProbeBuildOutcome.PROTOCOL_INVALID,
        )

    return ProbeBuildResult(
        ok=True,
        probe=probe,
        scoring_key=scoring_key,
        leakage_review=leakage_review,
        key_content=key_content,
        errors=[],
        outcome=ProbeBuildOutcome.SEALED,
    )


def validate_probe_freeze(
    *,
    registry: TargetRegistryV1,
    census: CensusSampleManifestV1 | None,
    probe: ProbeManifestV1,
    scoring_key: ScoringKeyV1,
    leakage_review: LeakageReviewManifestV1,
    key_content: ScoringKeyContentV1,
) -> NaturalisticValidation:
    """Validate a frozen probe bundle against G3 invariants."""

    errors: list[str] = []
    if not probe.header.sealed:
        errors.append("probe must be sealed")
    if not scoring_key.header.sealed:
        errors.append("scoring key must be sealed")
    if not leakage_review.header.sealed:
        errors.append("leakage review must be sealed")
    if leakage_review.disposition != LeakageReviewDisposition.APPROVED:
        errors.append("leakage review must be approved for authoritative freeze")
    if probe.leakage_review_disposition != LeakageReviewDisposition.APPROVED:
        errors.append("probe leakage_review_disposition must be approved")
    if probe.leakage_review_manifest_id != leakage_review.header.artifact_id:
        errors.append("probe leakage review manifest binding mismatch")
    if probe.leakage_review_digest != leakage_review.header.content_digest:
        errors.append("probe leakage review digest mismatch")

    parent = validate_registry_sample_parent_binding(registry=registry, census=census, probe=probe)
    binding = validate_scoring_key_integrity_binding(probe, scoring_key, key_content)
    errors.extend(parent.errors)
    errors.extend(binding.errors)

    from eval_naturalistic.contract_validate import validate_scoring_key_separation

    separation = validate_scoring_key_separation(probe)
    errors.extend(separation.errors)

    return NaturalisticValidation(errors=errors)
