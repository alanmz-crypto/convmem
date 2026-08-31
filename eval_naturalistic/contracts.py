"""G1 durable artifact contracts for the naturalistic product-value study chain."""

from __future__ import annotations

# This module is the intentionally explicit durable-schema catalog; its records mirror
# governed wire fields and therefore exceed generic module/class-size heuristics.
# pylint: disable=too-many-lines,too-many-instance-attributes
from dataclasses import dataclass, field
from typing import Any

from eval_naturalistic.base import (
    ArtifactHeaderV1,
    StructuralContractError,
    _enum_from_value,
    _require_dict,
    _require_list,
    _require_no_unknown_props,
    _require_str,
)
from eval_naturalistic.digest import (
    SCHEMA_NAMESPACE,
    artifact_content_digest,
    make_artifact_id,
)
from eval_naturalistic.enums import (
    AdmissibleSourceClass,
    CaptureDiagnosticState,
    CensusMode,
    EligibilityDisposition,
    EpisodeDisposition,
    EpisodeRegistryStatus,
    EvidenceCompletenessState,
    LeakageReviewDisposition,
    ParameterFreezeStatus,
    ProbeFamilyKind,
    ReliabilityState,
    SamplingMode,
    StudyTerminalDisposition,
    TrialCondition,
    TrialTerminalDisposition,
)


def _header_from(data: dict[str, Any]) -> ArtifactHeaderV1:
    return ArtifactHeaderV1.from_dict(_require_dict(data.get("header"), "header"))


def _header_to(header: ArtifactHeaderV1) -> dict[str, Any]:
    return header.to_dict()


@dataclass
class ParameterSlotV1:
    slot_name: str
    freeze_status: ParameterFreezeStatus
    value: str | None = None
    authority: str | None = None
    construct_defining: bool = False

    _FIELDS = {"slot_name", "freeze_status", "value", "authority", "construct_defining"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParameterSlotV1:
        data = _require_dict(data, "ParameterSlotV1")
        _require_no_unknown_props(data, cls._FIELDS, "ParameterSlotV1")
        return cls(
            slot_name=_require_str(data["slot_name"], "slot_name"),
            freeze_status=_enum_from_value(
                ParameterFreezeStatus, data["freeze_status"], "freeze_status"
            ),
            value=data.get("value"),
            authority=data.get("authority"),
            construct_defining=bool(data.get("construct_defining", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "slot_name": self.slot_name,
            "freeze_status": self.freeze_status.value,
            "construct_defining": self.construct_defining,
        }
        if self.value is not None:
            out["value"] = self.value
        if self.authority is not None:
            out["authority"] = self.authority
        return out


@dataclass
class EpisodeFrameV1:
    """Prospective study authority frozen before ordinary work."""

    header: ArtifactHeaderV1
    study_id: str
    frame_version: str
    episode_population_policy_id: str
    inclusion_exclusion_policy_id: str
    episode_count_contract_id: str
    observation_window_contract_id: str
    episode_close_rule_id: str
    context_gap_schedule_id: str
    model_build_settings_id: str
    ordinary_tool_environment_id: str
    eligibility_unitization_policy_id: str
    adjudicator_workflow_id: str
    census_sampling_policy_id: str
    probe_role_policy_id: str
    outcome_estimand_policy_id: str
    terminal_state_policy_id: str
    parent_revision_id: str | None
    parent_revision_digest: str | None
    parameter_slots: list[ParameterSlotV1] = field(default_factory=list)

    SCHEMA = f"{SCHEMA_NAMESPACE}/episode-frame-v1"
    _FIELDS = {
        "header",
        "study_id",
        "frame_version",
        "episode_population_policy_id",
        "inclusion_exclusion_policy_id",
        "episode_count_contract_id",
        "observation_window_contract_id",
        "episode_close_rule_id",
        "context_gap_schedule_id",
        "model_build_settings_id",
        "ordinary_tool_environment_id",
        "eligibility_unitization_policy_id",
        "adjudicator_workflow_id",
        "census_sampling_policy_id",
        "probe_role_policy_id",
        "outcome_estimand_policy_id",
        "terminal_state_policy_id",
        "parent_revision_id",
        "parent_revision_digest",
        "parameter_slots",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpisodeFrameV1:
        data = _require_dict(data, "EpisodeFrameV1")
        _require_no_unknown_props(data, cls._FIELDS, "EpisodeFrameV1")
        slots = [
            ParameterSlotV1.from_dict(item)
            for item in _require_list(data.get("parameter_slots", []), "parameter_slots")
        ]
        return cls(
            header=_header_from(data),
            study_id=_require_str(data["study_id"], "study_id"),
            frame_version=_require_str(data["frame_version"], "frame_version"),
            episode_population_policy_id=_require_str(
                data["episode_population_policy_id"], "episode_population_policy_id"
            ),
            inclusion_exclusion_policy_id=_require_str(
                data["inclusion_exclusion_policy_id"], "inclusion_exclusion_policy_id"
            ),
            episode_count_contract_id=_require_str(
                data["episode_count_contract_id"], "episode_count_contract_id"
            ),
            observation_window_contract_id=_require_str(
                data["observation_window_contract_id"], "observation_window_contract_id"
            ),
            episode_close_rule_id=_require_str(
                data["episode_close_rule_id"], "episode_close_rule_id"
            ),
            context_gap_schedule_id=_require_str(
                data["context_gap_schedule_id"], "context_gap_schedule_id"
            ),
            model_build_settings_id=_require_str(
                data["model_build_settings_id"], "model_build_settings_id"
            ),
            ordinary_tool_environment_id=_require_str(
                data["ordinary_tool_environment_id"], "ordinary_tool_environment_id"
            ),
            eligibility_unitization_policy_id=_require_str(
                data["eligibility_unitization_policy_id"],
                "eligibility_unitization_policy_id",
            ),
            adjudicator_workflow_id=_require_str(
                data["adjudicator_workflow_id"], "adjudicator_workflow_id"
            ),
            census_sampling_policy_id=_require_str(
                data["census_sampling_policy_id"], "census_sampling_policy_id"
            ),
            probe_role_policy_id=_require_str(
                data["probe_role_policy_id"], "probe_role_policy_id"
            ),
            outcome_estimand_policy_id=_require_str(
                data["outcome_estimand_policy_id"], "outcome_estimand_policy_id"
            ),
            terminal_state_policy_id=_require_str(
                data["terminal_state_policy_id"], "terminal_state_policy_id"
            ),
            parent_revision_id=data.get("parent_revision_id"),
            parent_revision_digest=data.get("parent_revision_digest"),
            parameter_slots=slots,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "header": _header_to(self.header),
            "study_id": self.study_id,
            "frame_version": self.frame_version,
            "episode_population_policy_id": self.episode_population_policy_id,
            "inclusion_exclusion_policy_id": self.inclusion_exclusion_policy_id,
            "episode_count_contract_id": self.episode_count_contract_id,
            "observation_window_contract_id": self.observation_window_contract_id,
            "episode_close_rule_id": self.episode_close_rule_id,
            "context_gap_schedule_id": self.context_gap_schedule_id,
            "model_build_settings_id": self.model_build_settings_id,
            "ordinary_tool_environment_id": self.ordinary_tool_environment_id,
            "eligibility_unitization_policy_id": self.eligibility_unitization_policy_id,
            "adjudicator_workflow_id": self.adjudicator_workflow_id,
            "census_sampling_policy_id": self.census_sampling_policy_id,
            "probe_role_policy_id": self.probe_role_policy_id,
            "outcome_estimand_policy_id": self.outcome_estimand_policy_id,
            "terminal_state_policy_id": self.terminal_state_policy_id,
            "parameter_slots": [slot.to_dict() for slot in self.parameter_slots],
        }
        if self.parent_revision_id is not None:
            out["parent_revision_id"] = self.parent_revision_id
        if self.parent_revision_digest is not None:
            out["parent_revision_digest"] = self.parent_revision_digest
        return out

    def with_computed_identity(self, *, kind: str = "frame") -> EpisodeFrameV1:
        body = self.to_dict()
        digest = artifact_content_digest(body)
        header = self.header
        header = ArtifactHeaderV1(
            artifact_id=make_artifact_id(kind=kind, content_digest=digest),
            schema_version=self.SCHEMA,
            parent_artifact_id=header.parent_artifact_id,
            parent_digest=header.parent_digest,
            created_at=header.created_at,
            seal_time=header.seal_time,
            responsible_role=header.responsible_role,
            content_digest=digest,
            sealed=header.sealed,
        )
        return EpisodeFrameV1(header=header, **{k: v for k, v in self.__dict__.items() if k != "header"})


@dataclass
class EpisodeRecordV1:
    """One prospectively selected episode bound to its frame."""

    header: ArtifactHeaderV1
    episode_id: str
    frame_artifact_id: str
    frame_digest: str
    selection_position: int
    scheduled_window_start: str
    scheduled_window_end: str
    disposition: EpisodeDisposition

    SCHEMA = f"{SCHEMA_NAMESPACE}/episode-record-v1"
    _FIELDS = {
        "header",
        "episode_id",
        "frame_artifact_id",
        "frame_digest",
        "selection_position",
        "scheduled_window_start",
        "scheduled_window_end",
        "disposition",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpisodeRecordV1:
        data = _require_dict(data, "EpisodeRecordV1")
        _require_no_unknown_props(data, cls._FIELDS, "EpisodeRecordV1")
        return cls(
            header=_header_from(data),
            episode_id=_require_str(data["episode_id"], "episode_id"),
            frame_artifact_id=_require_str(data["frame_artifact_id"], "frame_artifact_id"),
            frame_digest=_require_str(data["frame_digest"], "frame_digest"),
            selection_position=int(data["selection_position"]),
            scheduled_window_start=_require_str(
                data["scheduled_window_start"], "scheduled_window_start"
            ),
            scheduled_window_end=_require_str(
                data["scheduled_window_end"], "scheduled_window_end"
            ),
            disposition=_enum_from_value(
                EpisodeDisposition, data["disposition"], "disposition"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": _header_to(self.header),
            "episode_id": self.episode_id,
            "frame_artifact_id": self.frame_artifact_id,
            "frame_digest": self.frame_digest,
            "selection_position": self.selection_position,
            "scheduled_window_start": self.scheduled_window_start,
            "scheduled_window_end": self.scheduled_window_end,
            "disposition": self.disposition.value,
        }


@dataclass
class EvidenceSourceV1:
    source_id: str
    source_class: AdmissibleSourceClass
    locator: str
    event_time: str
    capture_time: str
    content_digest: str
    version: str | None = None

    _FIELDS = {
        "source_id",
        "source_class",
        "locator",
        "event_time",
        "capture_time",
        "content_digest",
        "version",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceSourceV1:
        data = _require_dict(data, "EvidenceSourceV1")
        _require_no_unknown_props(data, cls._FIELDS, "EvidenceSourceV1")
        return cls(
            source_id=_require_str(data["source_id"], "source_id"),
            source_class=_enum_from_value(
                AdmissibleSourceClass, data["source_class"], "source_class"
            ),
            locator=_require_str(data["locator"], "locator"),
            event_time=_require_str(data["event_time"], "event_time"),
            capture_time=_require_str(data["capture_time"], "capture_time"),
            content_digest=_require_str(data["content_digest"], "content_digest"),
            version=data.get("version"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "source_id": self.source_id,
            "source_class": self.source_class.value,
            "locator": self.locator,
            "event_time": self.event_time,
            "capture_time": self.capture_time,
            "content_digest": self.content_digest,
        }
        if self.version is not None:
            out["version"] = self.version
        return out


@dataclass
class RawEvidenceManifestV1:
    """Complete raw-evidence authority for one episode."""

    header: ArtifactHeaderV1
    episode_id: str
    episode_record_artifact_id: str
    episode_record_digest: str
    sources: list[EvidenceSourceV1]
    completeness_state: EvidenceCompletenessState
    missing_source_explanation: str | None

    SCHEMA = f"{SCHEMA_NAMESPACE}/raw-evidence-manifest-v1"
    _FIELDS = {
        "header",
        "episode_id",
        "episode_record_artifact_id",
        "episode_record_digest",
        "sources",
        "completeness_state",
        "missing_source_explanation",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RawEvidenceManifestV1:
        data = _require_dict(data, "RawEvidenceManifestV1")
        _require_no_unknown_props(data, cls._FIELDS, "RawEvidenceManifestV1")
        return cls(
            header=_header_from(data),
            episode_id=_require_str(data["episode_id"], "episode_id"),
            episode_record_artifact_id=_require_str(
                data["episode_record_artifact_id"], "episode_record_artifact_id"
            ),
            episode_record_digest=_require_str(
                data["episode_record_digest"], "episode_record_digest"
            ),
            sources=[
                EvidenceSourceV1.from_dict(item)
                for item in _require_list(data["sources"], "sources")
            ],
            completeness_state=_enum_from_value(
                EvidenceCompletenessState, data["completeness_state"], "completeness_state"
            ),
            missing_source_explanation=data.get("missing_source_explanation"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "header": _header_to(self.header),
            "episode_id": self.episode_id,
            "episode_record_artifact_id": self.episode_record_artifact_id,
            "episode_record_digest": self.episode_record_digest,
            "sources": [source.to_dict() for source in self.sources],
            "completeness_state": self.completeness_state.value,
        }
        if self.missing_source_explanation is not None:
            out["missing_source_explanation"] = self.missing_source_explanation
        return out


@dataclass
class TargetSpanBindingV1:
    source_id: str
    span_start: int
    span_end: int

    _FIELDS = {"source_id", "span_start", "span_end"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TargetSpanBindingV1:
        data = _require_dict(data, "TargetSpanBindingV1")
        _require_no_unknown_props(data, cls._FIELDS, "TargetSpanBindingV1")
        return cls(
            source_id=_require_str(data["source_id"], "source_id"),
            span_start=int(data["span_start"]),
            span_end=int(data["span_end"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "span_start": self.span_start,
            "span_end": self.span_end,
        }


@dataclass
class AdjudicationRecordV1:
    adjudicator_id: str
    disposition: EligibilityDisposition
    rationale: str

    _FIELDS = {"adjudicator_id", "disposition", "rationale"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdjudicationRecordV1:
        data = _require_dict(data, "AdjudicationRecordV1")
        _require_no_unknown_props(data, cls._FIELDS, "AdjudicationRecordV1")
        return cls(
            adjudicator_id=_require_str(data["adjudicator_id"], "adjudicator_id"),
            disposition=_enum_from_value(
                EligibilityDisposition, data["disposition"], "disposition"
            ),
            rationale=_require_str(data["rationale"], "rationale"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "adjudicator_id": self.adjudicator_id,
            "disposition": self.disposition.value,
            "rationale": self.rationale,
        }


@dataclass
class TargetRecordV1:
    target_id: str
    episode_id: str
    span_bindings: list[TargetSpanBindingV1]
    eligibility_disposition: EligibilityDisposition
    ground_truth_partition_digest: str | None
    provenance_requirement: str | None
    admissibility_rationale: str | None
    unitization_rationale: str | None
    duplicate_of_target_id: str | None
    parent_target_id: str | None
    ambiguity_state: str | None
    secondary_strata: list[str]
    adjudication_records: list[AdjudicationRecordV1]
    resolution_identity: str | None
    adjudicator_ids: list[str]

    _FIELDS = {
        "target_id",
        "episode_id",
        "span_bindings",
        "eligibility_disposition",
        "ground_truth_partition_digest",
        "provenance_requirement",
        "admissibility_rationale",
        "unitization_rationale",
        "duplicate_of_target_id",
        "parent_target_id",
        "ambiguity_state",
        "secondary_strata",
        "adjudication_records",
        "resolution_identity",
        "adjudicator_ids",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TargetRecordV1:
        data = _require_dict(data, "TargetRecordV1")
        _require_no_unknown_props(data, cls._FIELDS, "TargetRecordV1")
        return cls(
            target_id=_require_str(data["target_id"], "target_id"),
            episode_id=_require_str(data["episode_id"], "episode_id"),
            span_bindings=[
                TargetSpanBindingV1.from_dict(item)
                for item in _require_list(data["span_bindings"], "span_bindings")
            ],
            eligibility_disposition=_enum_from_value(
                EligibilityDisposition, data["eligibility_disposition"], "eligibility_disposition"
            ),
            ground_truth_partition_digest=data.get("ground_truth_partition_digest"),
            provenance_requirement=data.get("provenance_requirement"),
            admissibility_rationale=data.get("admissibility_rationale"),
            unitization_rationale=data.get("unitization_rationale"),
            duplicate_of_target_id=data.get("duplicate_of_target_id"),
            parent_target_id=data.get("parent_target_id"),
            ambiguity_state=data.get("ambiguity_state"),
            secondary_strata=list(data.get("secondary_strata", [])),
            adjudication_records=[
                AdjudicationRecordV1.from_dict(item)
                for item in _require_list(data.get("adjudication_records", []), "adjudication_records")
            ],
            resolution_identity=data.get("resolution_identity"),
            adjudicator_ids=list(data.get("adjudicator_ids", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "target_id": self.target_id,
            "episode_id": self.episode_id,
            "span_bindings": [span.to_dict() for span in self.span_bindings],
            "eligibility_disposition": self.eligibility_disposition.value,
            "secondary_strata": self.secondary_strata,
            "adjudication_records": [rec.to_dict() for rec in self.adjudication_records],
            "adjudicator_ids": self.adjudicator_ids,
        }
        for key in (
            "ground_truth_partition_digest",
            "provenance_requirement",
            "admissibility_rationale",
            "unitization_rationale",
            "duplicate_of_target_id",
            "parent_target_id",
            "ambiguity_state",
            "resolution_identity",
        ):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        return out


@dataclass
class EpisodeRegistryEntryV1:
    episode_id: str
    registry_status: EpisodeRegistryStatus
    evidence_manifest_digest: str
    target_ids: list[str]

    _FIELDS = {"episode_id", "registry_status", "evidence_manifest_digest", "target_ids"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpisodeRegistryEntryV1:
        data = _require_dict(data, "EpisodeRegistryEntryV1")
        _require_no_unknown_props(data, cls._FIELDS, "EpisodeRegistryEntryV1")
        return cls(
            episode_id=_require_str(data["episode_id"], "episode_id"),
            registry_status=_enum_from_value(
                EpisodeRegistryStatus, data["registry_status"], "registry_status"
            ),
            evidence_manifest_digest=_require_str(
                data["evidence_manifest_digest"], "evidence_manifest_digest"
            ),
            target_ids=list(data.get("target_ids", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "registry_status": self.registry_status.value,
            "evidence_manifest_digest": self.evidence_manifest_digest,
            "target_ids": self.target_ids,
        }


@dataclass
class TargetRegistryV1:
    """Sealed target census authority; schema only in G1."""

    header: ArtifactHeaderV1
    evidence_manifest_ids: list[str]
    episode_entries: list[EpisodeRegistryEntryV1]
    targets: list[TargetRecordV1]
    registry_policy_version: str

    SCHEMA = f"{SCHEMA_NAMESPACE}/target-registry-v1"
    _FIELDS = {
        "header",
        "evidence_manifest_ids",
        "episode_entries",
        "targets",
        "registry_policy_version",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TargetRegistryV1:
        data = _require_dict(data, "TargetRegistryV1")
        _require_no_unknown_props(data, cls._FIELDS, "TargetRegistryV1")
        return cls(
            header=_header_from(data),
            evidence_manifest_ids=list(
                _require_list(data["evidence_manifest_ids"], "evidence_manifest_ids")
            ),
            episode_entries=[
                EpisodeRegistryEntryV1.from_dict(item)
                for item in _require_list(data["episode_entries"], "episode_entries")
            ],
            targets=[
                TargetRecordV1.from_dict(item)
                for item in _require_list(data.get("targets", []), "targets")
            ],
            registry_policy_version=_require_str(
                data["registry_policy_version"], "registry_policy_version"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": _header_to(self.header),
            "evidence_manifest_ids": self.evidence_manifest_ids,
            "episode_entries": [entry.to_dict() for entry in self.episode_entries],
            "targets": [target.to_dict() for target in self.targets],
            "registry_policy_version": self.registry_policy_version,
        }


@dataclass
class SampleRosterEntryV1:
    episode_id: str
    target_ids: list[str]
    inclusion_probability: float | None

    _FIELDS = {"episode_id", "target_ids", "inclusion_probability"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SampleRosterEntryV1:
        data = _require_dict(data, "SampleRosterEntryV1")
        _require_no_unknown_props(data, cls._FIELDS, "SampleRosterEntryV1")
        return cls(
            episode_id=_require_str(data["episode_id"], "episode_id"),
            target_ids=list(data.get("target_ids", [])),
            inclusion_probability=data.get("inclusion_probability"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "episode_id": self.episode_id,
            "target_ids": self.target_ids,
        }
        if self.inclusion_probability is not None:
            out["inclusion_probability"] = self.inclusion_probability
        return out


@dataclass
class CensusSampleManifestV1:
    header: ArtifactHeaderV1
    census_mode: CensusMode
    sampling_mode: SamplingMode
    target_registry_artifact_id: str
    target_registry_digest: str
    sampling_rule_identity: str
    random_seed_identity: str | None
    selected_roster: list[SampleRosterEntryV1]
    unsampled_roster_digest: str

    SCHEMA = f"{SCHEMA_NAMESPACE}/census-sample-manifest-v1"
    _FIELDS = {
        "header",
        "census_mode",
        "sampling_mode",
        "target_registry_artifact_id",
        "target_registry_digest",
        "sampling_rule_identity",
        "random_seed_identity",
        "selected_roster",
        "unsampled_roster_digest",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CensusSampleManifestV1:
        data = _require_dict(data, "CensusSampleManifestV1")
        _require_no_unknown_props(data, cls._FIELDS, "CensusSampleManifestV1")
        return cls(
            header=_header_from(data),
            census_mode=_enum_from_value(CensusMode, data["census_mode"], "census_mode"),
            sampling_mode=_enum_from_value(
                SamplingMode, data["sampling_mode"], "sampling_mode"
            ),
            target_registry_artifact_id=_require_str(
                data["target_registry_artifact_id"], "target_registry_artifact_id"
            ),
            target_registry_digest=_require_str(
                data["target_registry_digest"], "target_registry_digest"
            ),
            sampling_rule_identity=_require_str(
                data["sampling_rule_identity"], "sampling_rule_identity"
            ),
            random_seed_identity=data.get("random_seed_identity"),
            selected_roster=[
                SampleRosterEntryV1.from_dict(item)
                for item in _require_list(data["selected_roster"], "selected_roster")
            ],
            unsampled_roster_digest=_require_str(
                data["unsampled_roster_digest"], "unsampled_roster_digest"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "header": _header_to(self.header),
            "census_mode": self.census_mode.value,
            "sampling_mode": self.sampling_mode.value,
            "target_registry_artifact_id": self.target_registry_artifact_id,
            "target_registry_digest": self.target_registry_digest,
            "sampling_rule_identity": self.sampling_rule_identity,
            "selected_roster": [entry.to_dict() for entry in self.selected_roster],
            "unsampled_roster_digest": self.unsampled_roster_digest,
        }
        if self.random_seed_identity is not None:
            out["random_seed_identity"] = self.random_seed_identity
        return out


@dataclass
class ProbeAuthorProvenanceV1:
    """Records bounded, explicit probe-author access and blindness claims."""

    probe_author_id: str
    target_id: str
    access_recorded: bool
    treatment_blind: bool
    c0_c1_result_blind: bool
    capture_retrieval_blind: bool
    permitted_views: list[str]
    forbidden_reference_tokens: list[str] = field(default_factory=list)

    _FIELDS = {
        "probe_author_id",
        "target_id",
        "access_recorded",
        "treatment_blind",
        "c0_c1_result_blind",
        "capture_retrieval_blind",
        "permitted_views",
        "forbidden_reference_tokens",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProbeAuthorProvenanceV1:
        data = _require_dict(data, "ProbeAuthorProvenanceV1")
        _require_no_unknown_props(data, cls._FIELDS, "ProbeAuthorProvenanceV1")
        return cls(
            probe_author_id=_require_str(data["probe_author_id"], "probe_author_id"),
            target_id=_require_str(data["target_id"], "target_id"),
            access_recorded=bool(data["access_recorded"]),
            treatment_blind=bool(data["treatment_blind"]),
            c0_c1_result_blind=bool(data["c0_c1_result_blind"]),
            capture_retrieval_blind=bool(data["capture_retrieval_blind"]),
            permitted_views=list(_require_list(data["permitted_views"], "permitted_views")),
            forbidden_reference_tokens=list(data.get("forbidden_reference_tokens", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_author_id": self.probe_author_id,
            "target_id": self.target_id,
            "access_recorded": self.access_recorded,
            "treatment_blind": self.treatment_blind,
            "c0_c1_result_blind": self.c0_c1_result_blind,
            "capture_retrieval_blind": self.capture_retrieval_blind,
            "permitted_views": self.permitted_views,
            "forbidden_reference_tokens": self.forbidden_reference_tokens,
        }


@dataclass
class ScoringKeyContentV1:
    """Answer-bearing scoring material kept in the scorer partition."""

    header: ArtifactHeaderV1
    probe_id: str
    target_id: str
    ground_truth_value: str
    rubric_version: str

    SCHEMA = f"{SCHEMA_NAMESPACE}/scoring-key-content-v1"
    _FIELDS = {
        "header",
        "probe_id",
        "target_id",
        "ground_truth_value",
        "rubric_version",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScoringKeyContentV1:
        data = _require_dict(data, "ScoringKeyContentV1")
        _require_no_unknown_props(data, cls._FIELDS, "ScoringKeyContentV1")
        return cls(
            header=_header_from(data),
            probe_id=_require_str(data["probe_id"], "probe_id"),
            target_id=_require_str(data["target_id"], "target_id"),
            ground_truth_value=_require_str(data["ground_truth_value"], "ground_truth_value"),
            rubric_version=_require_str(data["rubric_version"], "rubric_version"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": _header_to(self.header),
            "probe_id": self.probe_id,
            "target_id": self.target_id,
            "ground_truth_value": self.ground_truth_value,
            "rubric_version": self.rubric_version,
        }


@dataclass
class LeakageReviewManifestV1:
    """Independent leakage reviewer sign-off bound to a probe digest."""

    header: ArtifactHeaderV1
    probe_id: str
    probe_digest: str
    reviewer_id: str
    disposition: LeakageReviewDisposition
    checklist_items: list[dict[str, Any]]
    review_tool_version: str
    sign_off_time: str
    exception_record: str | None = None

    SCHEMA = f"{SCHEMA_NAMESPACE}/leakage-review-manifest-v1"
    _FIELDS = {
        "header",
        "probe_id",
        "probe_digest",
        "reviewer_id",
        "disposition",
        "checklist_items",
        "review_tool_version",
        "sign_off_time",
        "exception_record",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LeakageReviewManifestV1:
        data = _require_dict(data, "LeakageReviewManifestV1")
        _require_no_unknown_props(data, cls._FIELDS, "LeakageReviewManifestV1")
        return cls(
            header=_header_from(data),
            probe_id=_require_str(data["probe_id"], "probe_id"),
            probe_digest=_require_str(data["probe_digest"], "probe_digest"),
            reviewer_id=_require_str(data["reviewer_id"], "reviewer_id"),
            disposition=_enum_from_value(
                LeakageReviewDisposition, data["disposition"], "disposition"
            ),
            checklist_items=list(_require_list(data["checklist_items"], "checklist_items")),
            review_tool_version=_require_str(data["review_tool_version"], "review_tool_version"),
            sign_off_time=_require_str(data["sign_off_time"], "sign_off_time"),
            exception_record=data.get("exception_record"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "header": _header_to(self.header),
            "probe_id": self.probe_id,
            "probe_digest": self.probe_digest,
            "reviewer_id": self.reviewer_id,
            "disposition": self.disposition.value,
            "checklist_items": self.checklist_items,
            "review_tool_version": self.review_tool_version,
            "sign_off_time": self.sign_off_time,
        }
        if self.exception_record is not None:
            out["exception_record"] = self.exception_record
        return out


@dataclass
class ScoringKeyV1:
    """Separately sealable scoring authority."""

    header: ArtifactHeaderV1
    probe_id: str
    target_id: str
    key_partition_identity: str
    key_content_digest: str

    SCHEMA = f"{SCHEMA_NAMESPACE}/scoring-key-v1"
    _FIELDS = {
        "header",
        "probe_id",
        "target_id",
        "key_partition_identity",
        "key_content_digest",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScoringKeyV1:
        data = _require_dict(data, "ScoringKeyV1")
        _require_no_unknown_props(data, cls._FIELDS, "ScoringKeyV1")
        return cls(
            header=_header_from(data),
            probe_id=_require_str(data["probe_id"], "probe_id"),
            target_id=_require_str(data["target_id"], "target_id"),
            key_partition_identity=_require_str(
                data["key_partition_identity"], "key_partition_identity"
            ),
            key_content_digest=_require_str(data["key_content_digest"], "key_content_digest"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": _header_to(self.header),
            "probe_id": self.probe_id,
            "target_id": self.target_id,
            "key_partition_identity": self.key_partition_identity,
            "key_content_digest": self.key_content_digest,
        }


@dataclass
class ProbeManifestV1:
    """Agent-B-facing probe authority without answer-bearing key content."""

    header: ArtifactHeaderV1
    probe_id: str
    target_id: str
    episode_id: str
    probe_family_id: str
    probe_family_kind: ProbeFamilyKind
    probe_author_id: str
    leakage_reviewer_id: str
    adjudicator_collision_check_passed: bool
    leakage_review_disposition: LeakageReviewDisposition
    prompt_content_digest: str
    permitted_context_digest: str
    probe_author_provenance_digest: str
    target_registry_artifact_id: str
    target_registry_digest: str
    sample_manifest_artifact_id: str | None
    sample_manifest_digest: str | None
    scoring_key_digest: str
    scoring_key_partition_identity: str
    leakage_review_manifest_id: str
    leakage_review_digest: str

    SCHEMA = f"{SCHEMA_NAMESPACE}/probe-manifest-v1"
    _FIELDS = {
        "header",
        "probe_id",
        "target_id",
        "episode_id",
        "probe_family_id",
        "probe_family_kind",
        "probe_author_id",
        "leakage_reviewer_id",
        "adjudicator_collision_check_passed",
        "leakage_review_disposition",
        "prompt_content_digest",
        "permitted_context_digest",
        "probe_author_provenance_digest",
        "target_registry_artifact_id",
        "target_registry_digest",
        "sample_manifest_artifact_id",
        "sample_manifest_digest",
        "scoring_key_digest",
        "scoring_key_partition_identity",
        "leakage_review_manifest_id",
        "leakage_review_digest",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProbeManifestV1:
        data = _require_dict(data, "ProbeManifestV1")
        _require_no_unknown_props(data, cls._FIELDS, "ProbeManifestV1")
        return cls(
            header=_header_from(data),
            probe_id=_require_str(data["probe_id"], "probe_id"),
            target_id=_require_str(data["target_id"], "target_id"),
            episode_id=_require_str(data["episode_id"], "episode_id"),
            probe_family_id=_require_str(data["probe_family_id"], "probe_family_id"),
            probe_family_kind=_enum_from_value(
                ProbeFamilyKind, data["probe_family_kind"], "probe_family_kind"
            ),
            probe_author_id=_require_str(data["probe_author_id"], "probe_author_id"),
            leakage_reviewer_id=_require_str(
                data["leakage_reviewer_id"], "leakage_reviewer_id"
            ),
            adjudicator_collision_check_passed=bool(
                data["adjudicator_collision_check_passed"]
            ),
            leakage_review_disposition=_enum_from_value(
                LeakageReviewDisposition,
                data["leakage_review_disposition"],
                "leakage_review_disposition",
            ),
            prompt_content_digest=_require_str(
                data["prompt_content_digest"], "prompt_content_digest"
            ),
            permitted_context_digest=_require_str(
                data["permitted_context_digest"], "permitted_context_digest"
            ),
            probe_author_provenance_digest=_require_str(
                data["probe_author_provenance_digest"], "probe_author_provenance_digest"
            ),
            target_registry_artifact_id=_require_str(
                data["target_registry_artifact_id"], "target_registry_artifact_id"
            ),
            target_registry_digest=_require_str(
                data["target_registry_digest"], "target_registry_digest"
            ),
            sample_manifest_artifact_id=data.get("sample_manifest_artifact_id"),
            sample_manifest_digest=data.get("sample_manifest_digest"),
            scoring_key_digest=_require_str(data["scoring_key_digest"], "scoring_key_digest"),
            scoring_key_partition_identity=_require_str(
                data["scoring_key_partition_identity"],
                "scoring_key_partition_identity",
            ),
            leakage_review_manifest_id=_require_str(
                data["leakage_review_manifest_id"], "leakage_review_manifest_id"
            ),
            leakage_review_digest=_require_str(
                data["leakage_review_digest"], "leakage_review_digest"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "header": _header_to(self.header),
            "probe_id": self.probe_id,
            "target_id": self.target_id,
            "episode_id": self.episode_id,
            "probe_family_id": self.probe_family_id,
            "probe_family_kind": self.probe_family_kind.value,
            "probe_author_id": self.probe_author_id,
            "leakage_reviewer_id": self.leakage_reviewer_id,
            "adjudicator_collision_check_passed": self.adjudicator_collision_check_passed,
            "leakage_review_disposition": self.leakage_review_disposition.value,
            "prompt_content_digest": self.prompt_content_digest,
            "permitted_context_digest": self.permitted_context_digest,
            "probe_author_provenance_digest": self.probe_author_provenance_digest,
            "target_registry_artifact_id": self.target_registry_artifact_id,
            "target_registry_digest": self.target_registry_digest,
            "scoring_key_digest": self.scoring_key_digest,
            "scoring_key_partition_identity": self.scoring_key_partition_identity,
            "leakage_review_manifest_id": self.leakage_review_manifest_id,
            "leakage_review_digest": self.leakage_review_digest,
        }
        if self.sample_manifest_artifact_id is not None:
            out["sample_manifest_artifact_id"] = self.sample_manifest_artifact_id
        if self.sample_manifest_digest is not None:
            out["sample_manifest_digest"] = self.sample_manifest_digest
        return out

    def agent_b_view(self) -> dict[str, Any]:
        """Public representation: binds key digest only, never key content."""

        view = self.to_dict()
        forbidden = {"scoring_key_digest", "scoring_key_partition_identity"}
        for key in forbidden:
            view.pop(key, None)
        view["scoring_key_integrity_digest"] = self.scoring_key_digest
        return view


@dataclass
class TargetCaptureStateV1:
    """Per-target capture diagnostic; cannot alter registry membership."""

    target_id: str
    capture_state: CaptureDiagnosticState
    capture_manifest_digest: str | None

    _FIELDS = {"target_id", "capture_state", "capture_manifest_digest"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TargetCaptureStateV1:
        data = _require_dict(data, "TargetCaptureStateV1")
        _require_no_unknown_props(data, cls._FIELDS, "TargetCaptureStateV1")
        return cls(
            target_id=_require_str(data["target_id"], "target_id"),
            capture_state=_enum_from_value(
                CaptureDiagnosticState, data["capture_state"], "capture_state"
            ),
            capture_manifest_digest=data.get("capture_manifest_digest"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "target_id": self.target_id,
            "capture_state": self.capture_state.value,
        }
        if self.capture_manifest_digest is not None:
            out["capture_manifest_digest"] = self.capture_manifest_digest
        return out


@dataclass
class ConvMemCaptureStateV1:
    """Post-registry capture diagnostics; structurally separate from TargetRegistry."""

    header: ArtifactHeaderV1
    target_registry_artifact_id: str
    target_registry_digest: str
    target_states: list[TargetCaptureStateV1]

    SCHEMA = f"{SCHEMA_NAMESPACE}/convmem-capture-state-v1"
    _FIELDS = {
        "header",
        "target_registry_artifact_id",
        "target_registry_digest",
        "target_states",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConvMemCaptureStateV1:
        data = _require_dict(data, "ConvMemCaptureStateV1")
        _require_no_unknown_props(data, cls._FIELDS, "ConvMemCaptureStateV1")
        return cls(
            header=_header_from(data),
            target_registry_artifact_id=_require_str(
                data["target_registry_artifact_id"], "target_registry_artifact_id"
            ),
            target_registry_digest=_require_str(
                data["target_registry_digest"], "target_registry_digest"
            ),
            target_states=[
                TargetCaptureStateV1.from_dict(item)
                for item in _require_list(data["target_states"], "target_states")
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": _header_to(self.header),
            "target_registry_artifact_id": self.target_registry_artifact_id,
            "target_registry_digest": self.target_registry_digest,
            "target_states": [state.to_dict() for state in self.target_states],
        }


@dataclass
class TrialIdentityV1:
    header: ArtifactHeaderV1
    trial_id: str
    session_identity: str
    condition: TrialCondition
    environment_manifest_id: str
    probe_id: str
    raw_trace_identity: str
    terminal_disposition: TrialTerminalDisposition

    SCHEMA = f"{SCHEMA_NAMESPACE}/trial-identity-v1"
    _FIELDS = {
        "header",
        "trial_id",
        "session_identity",
        "condition",
        "environment_manifest_id",
        "probe_id",
        "raw_trace_identity",
        "terminal_disposition",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrialIdentityV1:
        data = _require_dict(data, "TrialIdentityV1")
        _require_no_unknown_props(data, cls._FIELDS, "TrialIdentityV1")
        return cls(
            header=_header_from(data),
            trial_id=_require_str(data["trial_id"], "trial_id"),
            session_identity=_require_str(data["session_identity"], "session_identity"),
            condition=_enum_from_value(TrialCondition, data["condition"], "condition"),
            environment_manifest_id=_require_str(
                data["environment_manifest_id"], "environment_manifest_id"
            ),
            probe_id=_require_str(data["probe_id"], "probe_id"),
            raw_trace_identity=_require_str(data["raw_trace_identity"], "raw_trace_identity"),
            terminal_disposition=_enum_from_value(
                TrialTerminalDisposition, data["terminal_disposition"], "terminal_disposition"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": _header_to(self.header),
            "trial_id": self.trial_id,
            "session_identity": self.session_identity,
            "condition": self.condition.value,
            "environment_manifest_id": self.environment_manifest_id,
            "probe_id": self.probe_id,
            "raw_trace_identity": self.raw_trace_identity,
            "terminal_disposition": self.terminal_disposition.value,
        }


@dataclass
class AgentBTraceV1:
    header: ArtifactHeaderV1
    trial_id: str
    trace_digest: str
    final_response_digest: str

    SCHEMA = f"{SCHEMA_NAMESPACE}/agent-b-trace-v1"
    _FIELDS = {"header", "trial_id", "trace_digest", "final_response_digest"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentBTraceV1:
        data = _require_dict(data, "AgentBTraceV1")
        _require_no_unknown_props(data, cls._FIELDS, "AgentBTraceV1")
        return cls(
            header=_header_from(data),
            trial_id=_require_str(data["trial_id"], "trial_id"),
            trace_digest=_require_str(data["trace_digest"], "trace_digest"),
            final_response_digest=_require_str(
                data["final_response_digest"], "final_response_digest"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": _header_to(self.header),
            "trial_id": self.trial_id,
            "trace_digest": self.trace_digest,
            "final_response_digest": self.final_response_digest,
        }


@dataclass
class ActionLatencyRecordV1:
    header: ArtifactHeaderV1
    trial_id: str
    action_count: int
    latency_ms_total: int
    record_digest: str

    SCHEMA = f"{SCHEMA_NAMESPACE}/action-latency-v1"
    _FIELDS = {"header", "trial_id", "action_count", "latency_ms_total", "record_digest"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionLatencyRecordV1:
        data = _require_dict(data, "ActionLatencyRecordV1")
        _require_no_unknown_props(data, cls._FIELDS, "ActionLatencyRecordV1")
        return cls(
            header=_header_from(data),
            trial_id=_require_str(data["trial_id"], "trial_id"),
            action_count=int(data["action_count"]),
            latency_ms_total=int(data["latency_ms_total"]),
            record_digest=_require_str(data["record_digest"], "record_digest"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": _header_to(self.header),
            "trial_id": self.trial_id,
            "action_count": self.action_count,
            "latency_ms_total": self.latency_ms_total,
            "record_digest": self.record_digest,
        }


@dataclass
class TargetScoreV1:
    header: ArtifactHeaderV1
    target_id: str
    trial_id: str
    normalized_score: float | None
    reliability_state: ReliabilityState

    SCHEMA = f"{SCHEMA_NAMESPACE}/target-score-v1"
    _FIELDS = {"header", "target_id", "trial_id", "normalized_score", "reliability_state"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TargetScoreV1:
        data = _require_dict(data, "TargetScoreV1")
        _require_no_unknown_props(data, cls._FIELDS, "TargetScoreV1")
        return cls(
            header=_header_from(data),
            target_id=_require_str(data["target_id"], "target_id"),
            trial_id=_require_str(data["trial_id"], "trial_id"),
            normalized_score=data.get("normalized_score"),
            reliability_state=_enum_from_value(
                ReliabilityState, data["reliability_state"], "reliability_state"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "header": _header_to(self.header),
            "target_id": self.target_id,
            "trial_id": self.trial_id,
            "reliability_state": self.reliability_state.value,
        }
        if self.normalized_score is not None:
            out["normalized_score"] = self.normalized_score
        return out


@dataclass
class EpisodeOutcomeV1:
    header: ArtifactHeaderV1
    episode_id: str
    registry_status: EpisodeRegistryStatus
    conditional_effect: float | None
    reliability_state: ReliabilityState
    opportunity_component: float | None

    SCHEMA = f"{SCHEMA_NAMESPACE}/episode-outcome-v1"
    _FIELDS = {
        "header",
        "episode_id",
        "registry_status",
        "conditional_effect",
        "reliability_state",
        "opportunity_component",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpisodeOutcomeV1:
        data = _require_dict(data, "EpisodeOutcomeV1")
        _require_no_unknown_props(data, cls._FIELDS, "EpisodeOutcomeV1")
        return cls(
            header=_header_from(data),
            episode_id=_require_str(data["episode_id"], "episode_id"),
            registry_status=_enum_from_value(
                EpisodeRegistryStatus, data["registry_status"], "registry_status"
            ),
            conditional_effect=data.get("conditional_effect"),
            reliability_state=_enum_from_value(
                ReliabilityState, data["reliability_state"], "reliability_state"
            ),
            opportunity_component=data.get("opportunity_component"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "header": _header_to(self.header),
            "episode_id": self.episode_id,
            "registry_status": self.registry_status.value,
            "reliability_state": self.reliability_state.value,
        }
        if self.conditional_effect is not None:
            out["conditional_effect"] = self.conditional_effect
        if self.opportunity_component is not None:
            out["opportunity_component"] = self.opportunity_component
        return out


@dataclass
class StudyAnalysisV1:
    header: ArtifactHeaderV1
    terminal_disposition: StudyTerminalDisposition
    opportunity_prevalence: float | None
    conditional_episode_effect: float | None
    reliability_state: ReliabilityState
    sparse_state: ReliabilityState

    SCHEMA = f"{SCHEMA_NAMESPACE}/study-analysis-v1"
    _FIELDS = {
        "header",
        "terminal_disposition",
        "opportunity_prevalence",
        "conditional_episode_effect",
        "reliability_state",
        "sparse_state",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StudyAnalysisV1:
        data = _require_dict(data, "StudyAnalysisV1")
        _require_no_unknown_props(data, cls._FIELDS, "StudyAnalysisV1")
        return cls(
            header=_header_from(data),
            terminal_disposition=_enum_from_value(
                StudyTerminalDisposition, data["terminal_disposition"], "terminal_disposition"
            ),
            opportunity_prevalence=data.get("opportunity_prevalence"),
            conditional_episode_effect=data.get("conditional_episode_effect"),
            reliability_state=_enum_from_value(
                ReliabilityState, data["reliability_state"], "reliability_state"
            ),
            sparse_state=_enum_from_value(
                ReliabilityState, data["sparse_state"], "sparse_state"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "header": _header_to(self.header),
            "terminal_disposition": self.terminal_disposition.value,
            "reliability_state": self.reliability_state.value,
            "sparse_state": self.sparse_state.value,
        }
        if self.opportunity_prevalence is not None:
            out["opportunity_prevalence"] = self.opportunity_prevalence
        if self.conditional_episode_effect is not None:
            out["conditional_episode_effect"] = self.conditional_episode_effect
        return out



# --- G5C corrective: prospective manifest, boundary ledger, opportunity identity ---

import copy

from eval_naturalistic.enums import (
    InformationSufficiencyState,
    MissingnessComparabilityState,
    OutcomeReasonCode,
    ProtocolValidityState,
    ScoreEvaluabilityState,
    ScorerIntegrityState,
    ScorerReliabilityDispositionState,
    StudyStageId,
    TrialEvidenceCaptureState,
)

PROSPECTIVE_POLICY_FIELD_NAMES = (
    "opportunity_authority_rule",
    "failure_reason_taxonomy",
    "missing_outcome_bounds_policy",
    "orthogonal_state_precedence",
    "paired_replay_policy",
    "scorer_integrity_policy",
    "scorer_reliability_policy",
)

PROSPECTIVE_INFORMATION_SLOT_NAMES = frozenset(
    {
        "meaningful_advantage",
        "equivalence_margin",
        "target_bearing_episode_information_floor",
        "secondary_information_floor",
        "precision_confidence_criterion",
        "sparse_reliability_criterion",
        "scorer_reliability_gate",
        "terminal_disposition_rules",
    }
)

PLACEHOLDER_MARKERS = frozenset({"", "PENDING", "TBD", "placeholder", "not_applicable_without_rule"})


def _is_placeholder_text(value: str | None) -> bool:
    if value is None:
        return True
    stripped = value.strip()
    if not stripped:
        return True
    return stripped.upper() in PLACEHOLDER_MARKERS or stripped.lower() in PLACEHOLDER_MARKERS


@dataclass
class ProspectiveManifestV1:
    """Complete prospective manifest: eight information slots plus frozen policy fields."""

    header: ArtifactHeaderV1
    study_id: str
    frame_artifact_id: str
    frame_digest: str
    information_slots: list[ParameterSlotV1]
    opportunity_authority_rule: str
    failure_reason_taxonomy: list[str]
    missing_outcome_bounds_policy: str
    orthogonal_state_precedence: list[str]
    paired_replay_policy: str
    scorer_integrity_policy: str
    scorer_reliability_policy: str
    logged_freeze_digest: str | None = None

    SCHEMA = f"{SCHEMA_NAMESPACE}/prospective-manifest-v1"
    _FIELDS = {
        "header",
        "study_id",
        "frame_artifact_id",
        "frame_digest",
        "information_slots",
        "opportunity_authority_rule",
        "failure_reason_taxonomy",
        "missing_outcome_bounds_policy",
        "orthogonal_state_precedence",
        "paired_replay_policy",
        "scorer_integrity_policy",
        "scorer_reliability_policy",
        "logged_freeze_digest",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProspectiveManifestV1:
        data = _require_dict(data, "ProspectiveManifestV1")
        _require_no_unknown_props(data, cls._FIELDS, "ProspectiveManifestV1")
        slots = [
            ParameterSlotV1.from_dict(item)
            for item in _require_list(data.get("information_slots", []), "information_slots")
        ]
        taxonomy = [
            _require_str(item, "failure_reason_taxonomy[]")
            for item in _require_list(data["failure_reason_taxonomy"], "failure_reason_taxonomy")
        ]
        precedence = [
            _require_str(item, "orthogonal_state_precedence[]")
            for item in _require_list(data["orthogonal_state_precedence"], "orthogonal_state_precedence")
        ]
        return cls(
            header=_header_from(data),
            study_id=_require_str(data["study_id"], "study_id"),
            frame_artifact_id=_require_str(data["frame_artifact_id"], "frame_artifact_id"),
            frame_digest=_require_str(data["frame_digest"], "frame_digest"),
            information_slots=slots,
            opportunity_authority_rule=_require_str(
                data["opportunity_authority_rule"], "opportunity_authority_rule"
            ),
            failure_reason_taxonomy=taxonomy,
            missing_outcome_bounds_policy=_require_str(
                data["missing_outcome_bounds_policy"], "missing_outcome_bounds_policy"
            ),
            orthogonal_state_precedence=precedence,
            paired_replay_policy=_require_str(data["paired_replay_policy"], "paired_replay_policy"),
            scorer_integrity_policy=_require_str(
                data["scorer_integrity_policy"], "scorer_integrity_policy"
            ),
            scorer_reliability_policy=_require_str(
                data["scorer_reliability_policy"], "scorer_reliability_policy"
            ),
            logged_freeze_digest=data.get("logged_freeze_digest"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "header": _header_to(self.header),
            "study_id": self.study_id,
            "frame_artifact_id": self.frame_artifact_id,
            "frame_digest": self.frame_digest,
            "information_slots": [slot.to_dict() for slot in self.information_slots],
            "opportunity_authority_rule": self.opportunity_authority_rule,
            "failure_reason_taxonomy": list(self.failure_reason_taxonomy),
            "missing_outcome_bounds_policy": self.missing_outcome_bounds_policy,
            "orthogonal_state_precedence": list(self.orthogonal_state_precedence),
            "paired_replay_policy": self.paired_replay_policy,
            "scorer_integrity_policy": self.scorer_integrity_policy,
            "scorer_reliability_policy": self.scorer_reliability_policy,
        }
        if self.logged_freeze_digest is not None:
            out["logged_freeze_digest"] = self.logged_freeze_digest
        return out


@dataclass
class StageBoundaryPredicateResultV1:
    predicate_name: str
    passed: bool
    detail: str | None = None

    _FIELDS = {"predicate_name", "passed", "detail"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StageBoundaryPredicateResultV1:
        data = _require_dict(data, "StageBoundaryPredicateResultV1")
        _require_no_unknown_props(data, cls._FIELDS, "StageBoundaryPredicateResultV1")
        passed = data["passed"]
        if not isinstance(passed, bool):
            raise StructuralContractError("StageBoundaryPredicateResultV1: passed must be boolean")
        return cls(
            predicate_name=_require_str(data["predicate_name"], "predicate_name"),
            passed=passed,
            detail=data.get("detail"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "predicate_name": self.predicate_name,
            "passed": self.passed,
        }
        if self.detail is not None:
            out["detail"] = self.detail
        return out


@dataclass
class StageBoundaryLedgerEntryV1:
    """One individual T0–T10 boundary record."""

    stage_id: StudyStageId
    input_artifact_digest: str
    required_predicates: list[StageBoundaryPredicateResultV1]
    validator_identity: str
    validator_version: str
    output_artifact_digest: str | None
    guarantees_exported: list[str]
    next_stage_assumptions: list[str]
    failure_reasons: list[str]
    passed: bool

    _FIELDS = {
        "stage_id",
        "input_artifact_digest",
        "required_predicates",
        "validator_identity",
        "validator_version",
        "output_artifact_digest",
        "guarantees_exported",
        "next_stage_assumptions",
        "failure_reasons",
        "passed",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StageBoundaryLedgerEntryV1:
        data = _require_dict(data, "StageBoundaryLedgerEntryV1")
        _require_no_unknown_props(data, cls._FIELDS, "StageBoundaryLedgerEntryV1")
        passed = data["passed"]
        if not isinstance(passed, bool):
            raise StructuralContractError("StageBoundaryLedgerEntryV1: passed must be boolean")
        return cls(
            stage_id=_enum_from_value(StudyStageId, data["stage_id"], "stage_id"),
            input_artifact_digest=_require_str(data["input_artifact_digest"], "input_artifact_digest"),
            required_predicates=[
                StageBoundaryPredicateResultV1.from_dict(item)
                for item in _require_list(data["required_predicates"], "required_predicates")
            ],
            validator_identity=_require_str(data["validator_identity"], "validator_identity"),
            validator_version=_require_str(data["validator_version"], "validator_version"),
            output_artifact_digest=data.get("output_artifact_digest"),
            guarantees_exported=[
                _require_str(item, "guarantees_exported[]")
                for item in _require_list(data["guarantees_exported"], "guarantees_exported")
            ],
            next_stage_assumptions=[
                _require_str(item, "next_stage_assumptions[]")
                for item in _require_list(data["next_stage_assumptions"], "next_stage_assumptions")
            ],
            failure_reasons=[
                _require_str(item, "failure_reasons[]")
                for item in _require_list(data.get("failure_reasons", []), "failure_reasons")
            ],
            passed=passed,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "stage_id": self.stage_id.value,
            "input_artifact_digest": self.input_artifact_digest,
            "required_predicates": [item.to_dict() for item in self.required_predicates],
            "validator_identity": self.validator_identity,
            "validator_version": self.validator_version,
            "guarantees_exported": list(self.guarantees_exported),
            "next_stage_assumptions": list(self.next_stage_assumptions),
            "failure_reasons": list(self.failure_reasons),
            "passed": self.passed,
        }
        if self.output_artifact_digest is not None:
            out["output_artifact_digest"] = self.output_artifact_digest
        return out


@dataclass
class StageBoundaryLedgerV1:
    entries: list[StageBoundaryLedgerEntryV1]

    _FIELDS = {"entries"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StageBoundaryLedgerV1:
        data = _require_dict(data, "StageBoundaryLedgerV1")
        _require_no_unknown_props(data, cls._FIELDS, "StageBoundaryLedgerV1")
        return cls(
            entries=[
                StageBoundaryLedgerEntryV1.from_dict(item)
                for item in _require_list(data["entries"], "entries")
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        return {"entries": [entry.to_dict() for entry in self.entries]}

    def derived_group_summaries(self) -> dict[str, bool]:
        by_stage = {entry.stage_id: entry.passed for entry in self.entries}
        return {
            "T0_T2": all(by_stage.get(stage, False) for stage in StudyStageId if stage.value in {"T0", "T1", "T2"}),
            "T3_T5": all(by_stage.get(stage, False) for stage in StudyStageId if stage.value in {"T3", "T4", "T5"}),
            "T6_T7": all(by_stage.get(stage, False) for stage in StudyStageId if stage.value in {"T6", "T7"}),
            "T8_T10": all(
                by_stage.get(stage, False) for stage in StudyStageId if stage.value in {"T8", "T9", "T10"}
            ),
        }


@dataclass
class EpisodeOpportunityIdentityV1:
    """Immutable episode-opportunity identity bound to sealed registry authority."""

    episode_opportunity_id: str
    episode_id: str
    registry_artifact_id: str
    registry_digest: str

    _FIELDS = {"episode_opportunity_id", "episode_id", "registry_artifact_id", "registry_digest"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpisodeOpportunityIdentityV1:
        data = _require_dict(data, "EpisodeOpportunityIdentityV1")
        _require_no_unknown_props(data, cls._FIELDS, "EpisodeOpportunityIdentityV1")
        return cls(
            episode_opportunity_id=_require_str(data["episode_opportunity_id"], "episode_opportunity_id"),
            episode_id=_require_str(data["episode_id"], "episode_id"),
            registry_artifact_id=_require_str(data["registry_artifact_id"], "registry_artifact_id"),
            registry_digest=_require_str(data["registry_digest"], "registry_digest"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_opportunity_id": self.episode_opportunity_id,
            "episode_id": self.episode_id,
            "registry_artifact_id": self.registry_artifact_id,
            "registry_digest": self.registry_digest,
        }


@dataclass
class OutcomeAxisRecordV1:
    """Separate outcome axes for one episode-opportunity."""

    episode_opportunity_id: str
    convmem_capture_state: CaptureDiagnosticState
    c0_trial_capture: TrialEvidenceCaptureState
    c1_trial_capture: TrialEvidenceCaptureState
    c0_score_evaluability: ScoreEvaluabilityState
    c1_score_evaluability: ScoreEvaluabilityState
    protocol_integrity_valid: bool
    scorer_reliability_state: ScorerReliabilityDispositionState
    reason_codes: list[str]

    _FIELDS = {
        "episode_opportunity_id",
        "convmem_capture_state",
        "c0_trial_capture",
        "c1_trial_capture",
        "c0_score_evaluability",
        "c1_score_evaluability",
        "protocol_integrity_valid",
        "scorer_reliability_state",
        "reason_codes",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OutcomeAxisRecordV1:
        data = _require_dict(data, "OutcomeAxisRecordV1")
        _require_no_unknown_props(data, cls._FIELDS, "OutcomeAxisRecordV1")
        protocol_valid = data["protocol_integrity_valid"]
        if not isinstance(protocol_valid, bool):
            raise StructuralContractError("OutcomeAxisRecordV1: protocol_integrity_valid must be boolean")
        return cls(
            episode_opportunity_id=_require_str(data["episode_opportunity_id"], "episode_opportunity_id"),
            convmem_capture_state=_enum_from_value(
                CaptureDiagnosticState, data["convmem_capture_state"], "convmem_capture_state"
            ),
            c0_trial_capture=_enum_from_value(
                TrialEvidenceCaptureState, data["c0_trial_capture"], "c0_trial_capture"
            ),
            c1_trial_capture=_enum_from_value(
                TrialEvidenceCaptureState, data["c1_trial_capture"], "c1_trial_capture"
            ),
            c0_score_evaluability=_enum_from_value(
                ScoreEvaluabilityState, data["c0_score_evaluability"], "c0_score_evaluability"
            ),
            c1_score_evaluability=_enum_from_value(
                ScoreEvaluabilityState, data["c1_score_evaluability"], "c1_score_evaluability"
            ),
            protocol_integrity_valid=protocol_valid,
            scorer_reliability_state=_enum_from_value(
                ScorerReliabilityDispositionState,
                data["scorer_reliability_state"],
                "scorer_reliability_state",
            ),
            reason_codes=[
                _require_str(item, "reason_codes[]")
                for item in _require_list(data.get("reason_codes", []), "reason_codes")
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_opportunity_id": self.episode_opportunity_id,
            "convmem_capture_state": self.convmem_capture_state.value,
            "c0_trial_capture": self.c0_trial_capture.value,
            "c1_trial_capture": self.c1_trial_capture.value,
            "c0_score_evaluability": self.c0_score_evaluability.value,
            "c1_score_evaluability": self.c1_score_evaluability.value,
            "protocol_integrity_valid": self.protocol_integrity_valid,
            "scorer_reliability_state": self.scorer_reliability_state.value,
            "reason_codes": list(self.reason_codes),
        }


@dataclass
class OrthogonalStateRecordV1:
    protocol_validity: ProtocolValidityState
    information_sufficiency: InformationSufficiencyState
    missingness_comparability: MissingnessComparabilityState
    scorer_integrity: ScorerIntegrityState
    scorer_reliability: ScorerReliabilityDispositionState
    reason_codes: list[str]
    precedence_path: list[str]

    _FIELDS = {
        "protocol_validity",
        "information_sufficiency",
        "missingness_comparability",
        "scorer_integrity",
        "scorer_reliability",
        "reason_codes",
        "precedence_path",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrthogonalStateRecordV1:
        data = _require_dict(data, "OrthogonalStateRecordV1")
        _require_no_unknown_props(data, cls._FIELDS, "OrthogonalStateRecordV1")
        return cls(
            protocol_validity=_enum_from_value(
                ProtocolValidityState, data["protocol_validity"], "protocol_validity"
            ),
            information_sufficiency=_enum_from_value(
                InformationSufficiencyState, data["information_sufficiency"], "information_sufficiency"
            ),
            missingness_comparability=_enum_from_value(
                MissingnessComparabilityState,
                data["missingness_comparability"],
                "missingness_comparability",
            ),
            scorer_integrity=_enum_from_value(
                ScorerIntegrityState, data["scorer_integrity"], "scorer_integrity"
            ),
            scorer_reliability=_enum_from_value(
                ScorerReliabilityDispositionState,
                data["scorer_reliability"],
                "scorer_reliability",
            ),
            reason_codes=[
                _require_str(item, "reason_codes[]")
                for item in _require_list(data.get("reason_codes", []), "reason_codes")
            ],
            precedence_path=[
                _require_str(item, "precedence_path[]")
                for item in _require_list(data.get("precedence_path", []), "precedence_path")
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_validity": self.protocol_validity.value,
            "information_sufficiency": self.information_sufficiency.value,
            "missingness_comparability": self.missingness_comparability.value,
            "scorer_integrity": self.scorer_integrity.value,
            "scorer_reliability": self.scorer_reliability.value,
            "reason_codes": list(self.reason_codes),
            "precedence_path": list(self.precedence_path),
        }


def make_pending_information_slots() -> list[ParameterSlotV1]:
    return [
        ParameterSlotV1(
            slot_name=name,
            freeze_status=ParameterFreezeStatus.PENDING,
            construct_defining=True,
        )
        for name in sorted(PROSPECTIVE_INFORMATION_SLOT_NAMES)
    ]


def make_complete_prospective_policy_text() -> dict[str, Any]:
  return {
    "opportunity_authority_rule": "sealed_target_registry_is_sole_denominator_authority",
    "failure_reason_taxonomy": [code.value for code in OutcomeReasonCode],
    "missing_outcome_bounds_policy": "deterministic_worst_best_on_unit_interval_for_valid_missing_only",
    "orthogonal_state_precedence": [
        "protocol_invalidity",
        "environment_or_scorer_integrity_invalidity",
        "insufficient_opportunity_or_information",
        "below_threshold_reliability_or_inconclusive_bounds",
        "effect_interpretation_deferred_to_later_study",
    ],
    "paired_replay_policy": "fresh_symmetric_replay_single_convmem_difference",
    "scorer_integrity_policy": "condition_neutral_packages_no_unblinding",
    "scorer_reliability_policy": "below_threshold_blocks_not_invalidates",
  }


def make_frozen_synthetic_information_slots() -> list[ParameterSlotV1]:
    """Fixture-only frozen slot values for synthetic T0 freeze exercises — not live parameters."""

    authority = "synthetic-t0-freeze-authority-v1"
    return [
        ParameterSlotV1(
            slot_name=name,
            freeze_status=ParameterFreezeStatus.FROZEN,
            value=f"synthetic-fixture-{name}-v1",
            authority=authority,
            construct_defining=True,
        )
        for name in sorted(PROSPECTIVE_INFORMATION_SLOT_NAMES)
    ]


def make_pending_prospective_manifest(*, frame: EpisodeFrameV1) -> ProspectiveManifestV1:
    policy = make_complete_prospective_policy_text()
    header = ArtifactHeaderV1(
        artifact_id="pending",
        schema_version=ProspectiveManifestV1.SCHEMA,
        parent_artifact_id=frame.header.artifact_id,
        parent_digest=frame.header.content_digest,
        created_at="2026-08-30T00:00:00Z",
        seal_time=None,
        responsible_role="study_owner",
        content_digest=None,
        sealed=False,
    )
    return ProspectiveManifestV1(
        header=header,
        study_id=frame.study_id,
        frame_artifact_id=frame.header.artifact_id,
        frame_digest=frame.header.content_digest or "",
        information_slots=make_pending_information_slots(),
        opportunity_authority_rule=policy["opportunity_authority_rule"],
        failure_reason_taxonomy=policy["failure_reason_taxonomy"],
        missing_outcome_bounds_policy=policy["missing_outcome_bounds_policy"],
        orthogonal_state_precedence=policy["orthogonal_state_precedence"],
        paired_replay_policy=policy["paired_replay_policy"],
        scorer_integrity_policy=policy["scorer_integrity_policy"],
        scorer_reliability_policy=policy["scorer_reliability_policy"],
        logged_freeze_digest=None,
    )


def make_frozen_prospective_manifest(*, frame: EpisodeFrameV1) -> ProspectiveManifestV1:
    """Synthetic manifest eligible for FRAME_FROZEN transition (fixture values only)."""

    policy = make_complete_prospective_policy_text()
    header = ArtifactHeaderV1(
        artifact_id="pending",
        schema_version=ProspectiveManifestV1.SCHEMA,
        parent_artifact_id=frame.header.artifact_id,
        parent_digest=frame.header.content_digest,
        created_at="2026-08-30T00:00:00Z",
        seal_time=None,
        responsible_role="study_owner",
        content_digest=None,
        sealed=False,
    )
    return ProspectiveManifestV1(
        header=header,
        study_id=frame.study_id,
        frame_artifact_id=frame.header.artifact_id,
        frame_digest=frame.header.content_digest or "",
        information_slots=make_frozen_synthetic_information_slots(),
        opportunity_authority_rule=policy["opportunity_authority_rule"],
        failure_reason_taxonomy=policy["failure_reason_taxonomy"],
        missing_outcome_bounds_policy=policy["missing_outcome_bounds_policy"],
        orthogonal_state_precedence=policy["orthogonal_state_precedence"],
        paired_replay_policy=policy["paired_replay_policy"],
        scorer_integrity_policy=policy["scorer_integrity_policy"],
        scorer_reliability_policy=policy["scorer_reliability_policy"],
        logged_freeze_digest=None,
    )


def validate_prospective_manifest_structural(
    serialized_body: dict[str, Any],
    *,
    require_logged_freeze: bool = False,
) -> NaturalisticValidation:
    """Validate canonical serialized manifest bytes — not builder flags."""

    from eval_naturalistic.base import NaturalisticValidation

    errors: list[str] = []
    try:
        manifest = ProspectiveManifestV1.from_dict(serialized_body)
    except StructuralContractError as exc:
        return NaturalisticValidation(errors=[str(exc)])

    present_slots = {slot.slot_name for slot in manifest.information_slots}
    missing_slots = sorted(PROSPECTIVE_INFORMATION_SLOT_NAMES - present_slots)
    if missing_slots:
        errors.append("incomplete prospective manifest: missing information slots: " + ", ".join(missing_slots))
    extra_slots = sorted(present_slots - PROSPECTIVE_INFORMATION_SLOT_NAMES)
    if extra_slots:
        errors.append("prospective manifest has unknown information slots: " + ", ".join(extra_slots))

    for slot in manifest.information_slots:
        if slot.freeze_status == ParameterFreezeStatus.FROZEN and _is_placeholder_text(slot.value):
            errors.append(f"slot '{slot.slot_name}' falsely marked frozen with placeholder value")
        if slot.freeze_status == ParameterFreezeStatus.NOT_APPLICABLE and not slot.authority:
            errors.append(f"slot '{slot.slot_name}' not_applicable without frozen rule")

    for field_name in PROSPECTIVE_POLICY_FIELD_NAMES:
        value = getattr(manifest, field_name)
        if field_name == "failure_reason_taxonomy":
            if not value:
                errors.append("failure_reason_taxonomy must not be empty")
            elif any(_is_placeholder_text(item) for item in value):
                errors.append("failure_reason_taxonomy contains placeholder entries")
        elif field_name == "orthogonal_state_precedence":
            if not value:
                errors.append("orthogonal_state_precedence must not be empty")
        elif _is_placeholder_text(value):
            errors.append(f"prospective manifest policy field '{field_name}' is placeholder or empty")

    if _is_placeholder_text(manifest.frame_digest):
        errors.append("frame_digest must not be placeholder")
    if require_logged_freeze:
        if not manifest.logged_freeze_digest:
            errors.append("logged freeze digest required before stage advance")
        else:
            body_for_digest = copy.deepcopy(serialized_body)
            body_for_digest.pop("logged_freeze_digest", None)
            derived = artifact_content_digest(body_for_digest)
            if manifest.logged_freeze_digest != derived:
                errors.append("logged freeze digest does not match serialized artifact digest")

    if manifest.logged_freeze_digest is None:
        rederived = artifact_content_digest(serialized_body)
        header_digest = manifest.header.content_digest
        if header_digest is not None and header_digest != rederived:
            errors.append("header content_digest does not match re-derived serialized digest")

    return NaturalisticValidation(errors=errors)


def validate_prospective_manifest_freeze_transition(
    serialized_body: dict[str, Any],
    *,
    require_logged_freeze: bool = True,
) -> NaturalisticValidation:
    """Reject FRAME_FROZEN when required information slots remain draft-state PENDING."""

    from eval_naturalistic.base import NaturalisticValidation

    structural = validate_prospective_manifest_structural(
        serialized_body,
        require_logged_freeze=require_logged_freeze,
    )
    errors = list(structural.errors)
    if errors:
        return NaturalisticValidation(errors=errors)

    try:
        manifest = ProspectiveManifestV1.from_dict(serialized_body)
    except StructuralContractError as exc:
        return NaturalisticValidation(errors=[str(exc)])

    for slot in manifest.information_slots:
        if slot.slot_name not in PROSPECTIVE_INFORMATION_SLOT_NAMES:
            continue
        if slot.freeze_status == ParameterFreezeStatus.PENDING:
            errors.append(
                f"slot '{slot.slot_name}' must not remain pending at FRAME_FROZEN"
            )
        elif slot.freeze_status == ParameterFreezeStatus.FROZEN:
            if _is_placeholder_text(slot.value):
                errors.append(
                    f"slot '{slot.slot_name}' frozen without substantive value at FRAME_FROZEN"
                )
            if not slot.authority:
                errors.append(
                    f"slot '{slot.slot_name}' frozen without authority at FRAME_FROZEN"
                )
        elif slot.freeze_status == ParameterFreezeStatus.NOT_APPLICABLE:
            if not slot.authority:
                errors.append(
                    f"slot '{slot.slot_name}' not_applicable without frozen rule at FRAME_FROZEN"
                )
        else:
            errors.append(
                f"slot '{slot.slot_name}' has invalid freeze status at FRAME_FROZEN"
            )

    return NaturalisticValidation(errors=errors)


def verify_handoff_artifact_digest(*, logged_digest: str, handed_artifact: dict[str, Any]) -> NaturalisticValidation:
    from eval_naturalistic.base import NaturalisticValidation

    body_for_digest = copy.deepcopy(handed_artifact)
    body_for_digest.pop("logged_freeze_digest", None)
    actual = artifact_content_digest(body_for_digest)
    if logged_digest != actual:
        return NaturalisticValidation(
            errors=[
                f"handoff artifact digest mismatch (logged={logged_digest}, actual={actual})"
            ]
        )
    return NaturalisticValidation(errors=[])


def reject_arm_dependent_registry_rule(rule_text: str) -> NaturalisticValidation:
    from eval_naturalistic.base import NaturalisticValidation

    lowered = rule_text.lower()
    forbidden = (
        "condition",
        "capture",
        "retrieval",
        "c0",
        "c1",
        "convmem",
        "score",
        "outcome",
        "result",
    )
    hits = sorted({token for token in forbidden if token in lowered})
    if hits:
        return NaturalisticValidation(
            errors=[
                "registry rule must not depend on arm/capture/results: matched "
                + ", ".join(hits)
            ]
        )
    return NaturalisticValidation(errors=[])

def seal_artifact_dict(body: dict[str, Any], *, seal_time: str) -> dict[str, Any]:
    """Compute digest and mark an artifact body sealed."""

    header = _require_dict(body.get("header"), "header")
    digest = artifact_content_digest(body)
    header = {
        **header,
        "content_digest": digest,
        "seal_time": seal_time,
        "sealed": True,
    }
    return {**body, "header": header}


def verify_artifact_digest(body: dict[str, Any]) -> bool:
    header = _require_dict(body.get("header"), "header")
    expected = header.get("content_digest")
    if expected is None:
        return False
    return artifact_content_digest(body) == expected
