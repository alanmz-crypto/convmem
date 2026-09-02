"""Adversarial tests for the V2-02C source-backed capability boundary."""

from __future__ import annotations

import copy
import hashlib
import unittest
from dataclasses import replace

from eval_naturalistic.base import StructuralContractError, strip_digest_metadata
from eval_naturalistic.digest import canonical_artifact_bytes
from eval_naturalistic.v2.adapters.capability_manifest import (
    CapabilityManifestV2,
    derive_capability_manifest,
    parse_capability_manifest_v2,
    verify_capability_manifest,
)
from eval_naturalistic.v2.adapters.profile import profile_content_digest
from eval_naturalistic.v2.adapters.registry import profile_for_legacy_format
from eval_naturalistic.v2.authority_issuance import SealedP1AuthorityV2
from eval_naturalistic.v2.contracts import EvidenceSealManifestV2
from eval_naturalistic.v2.identity import OccurrenceReferenceV2
from tests.fixtures.naturalistic_v2_p1 import (
    sample_availability,
    sample_sealed_authority_bundle,
)


class NaturalisticV2CapabilityAuthorityTests(unittest.TestCase):
    def _bundle(self, **kwargs):
        kwargs.setdefault(
            "adapter_implementation_digest",
            profile_for_legacy_format("sqlite_crush").adapter_implementation_digest,
        )
        p1, p0, issuance = sample_sealed_authority_bundle(**kwargs)
        capability = derive_capability_manifest(
            p1,
            legacy_format="sqlite_crush",
            p0_repository=p0,
            issuance_repository=issuance,
        )
        return p1, p0, issuance, capability

    def test_verified_occurrence_derives_legitimate_capability(self) -> None:
        p1, p0, issuance, capability = self._bundle()
        self.assertEqual(
            capability.manifest.occurrence_reference.to_dict(),
            p1.manifest.occurrence_reference.to_dict(),
        )
        self.assertEqual(
            capability.manifest.p1_authority_digest,
            p1.manifest.header.content_digest,
        )
        self.assertIs(
            verify_capability_manifest(
                capability,
                p1_authority=p1,
                p0_repository=p0,
                issuance_repository=issuance,
            ),
            capability,
        )

    def test_raw_occurrence_or_claim_object_cannot_derive_capability(self) -> None:
        occurrence = OccurrenceReferenceV2(
            source_system_id="sys-crush",
            tenant_or_realm_id="tenant-1",
            authority_scope_id="scope-1",
            occurrence_namespace_id="claimed",
            physical_source_instance_id="claimed",
            native_id_namespace="crush.message",
            native_record_id="msg-1",
            source_revision_or_asof_id="rev-1",
        )
        with self.assertRaises(TypeError):
            derive_capability_manifest(  # type: ignore[arg-type]
                occurrence,
                legacy_format="sqlite_crush",
                issuance_repository=object(),
            )
        with self.assertRaises(TypeError):
            derive_capability_manifest(  # type: ignore[arg-type]
                {"occurrence_reference": occurrence.to_dict()},
                legacy_format="sqlite_crush",
                issuance_repository=object(),
            )

    def test_fabricated_self_consistent_p1_claim_is_rejected_by_source_authority(self) -> None:
        p1, p0, issuance, _ = self._bundle()
        forged = copy.deepcopy(p1.to_dict())
        forged["occurrence_reference"]["physical_source_instance_id"] = "forged-instance"
        forged["occurrence_reference"]["native_record_id"] = "forged-record"
        forged["header"]["content_digest"] = None
        forged["header"]["artifact_id"] = "pending"
        forged["header"]["sealed"] = False
        forged_digest = hashlib.sha256(
            canonical_artifact_bytes(strip_digest_metadata(forged))
        ).hexdigest()
        forged["header"]["content_digest"] = forged_digest
        forged["header"]["artifact_id"] = f"nps2_evidence-seal-manifest-v2_{forged_digest}"
        forged["header"]["sealed"] = True
        forged_manifest = EvidenceSealManifestV2.from_dict(forged)
        forged_p1 = SealedP1AuthorityV2(
            manifest=forged_manifest,
            canonical_bytes=canonical_artifact_bytes(forged_manifest.to_dict()),
            content_digest=forged_digest,
        )
        with self.assertRaises(StructuralContractError):
            derive_capability_manifest(
                forged_p1,
                legacy_format="sqlite_crush",
                p0_repository=p0,
                issuance_repository=issuance,
            )

    def test_capability_for_occurrence_a_cannot_verify_against_occurrence_b(self) -> None:
        p1_a, p0_a, issuance_a, capability_a = self._bundle()
        occurrence_b = replace(
            p1_a.manifest.occurrence_reference,
            physical_source_instance_id="phys-b",
            native_record_id="msg-b",
            occurrence_namespace_id="ns-b",
        )
        p1_b, p0_b, issuance_b, _ = self._bundle(occurrence=occurrence_b)
        self.assertNotEqual(
            p1_a.manifest.occurrence_reference.identity_key(),
            p1_b.manifest.occurrence_reference.identity_key(),
        )
        with self.assertRaises(StructuralContractError):
            verify_capability_manifest(
                capability_a,
                p1_authority=p1_b,
                p0_repository=p0_b,
                issuance_repository=issuance_b,
            )
        # The legitimate source A remains valid against its own authority.
        verify_capability_manifest(
            capability_a,
            p1_authority=p1_a,
            p0_repository=p0_a,
            issuance_repository=issuance_a,
        )

    def test_changed_capability_content_with_stale_identity_is_rejected(self) -> None:
        p1, p0, issuance, capability = self._bundle()
        changed = capability.to_dict()
        changed["capability_vector"]["evidence_completeness"] = "UNKNOWN"
        with self.assertRaises(StructuralContractError):
            verify_capability_manifest(
                changed,
                p1_authority=p1,
                p0_repository=p0,
                issuance_repository=issuance,
            )

    def test_caller_cannot_select_capability_digest_or_profile_label_as_authority(self) -> None:
        p1, p0, issuance, _ = self._bundle()
        with self.assertRaises(TypeError):
            # Intentional negative control: the public API must not accept a
            # caller-selected digest, even when the runtime would reject it.
            # pylint: disable=unexpected-keyword-arg
            derive_capability_manifest(  # type: ignore[call-arg]
                p1,
                legacy_format="sqlite_crush",
                capability_digest="b" * 64,
                p0_repository=p0,
                issuance_repository=issuance,
            )
        with self.assertRaises(StructuralContractError):
            derive_capability_manifest(
                p1,
                legacy_format="caller-selected-profile",
                p0_repository=p0,
                issuance_repository=issuance,
            )

    def test_profile_must_match_the_verified_p1_adapter_identity(self) -> None:
        profile = profile_for_legacy_format("sqlite_crush")
        p1, p0, issuance = sample_sealed_authority_bundle(
            adapter_implementation_digest=profile.adapter_implementation_digest,
        )
        with self.assertRaises(StructuralContractError):
            derive_capability_manifest(
                p1,
                legacy_format="sqlite_opencode",
                p0_repository=p0,
                issuance_repository=issuance,
            )

    def test_serialized_reload_requires_the_same_source_backed_p1_authority(self) -> None:
        p1, p0, issuance, capability = self._bundle()
        with self.assertRaises(StructuralContractError):
            parse_capability_manifest_v2(capability.canonical_bytes)
        reloaded = parse_capability_manifest_v2(
            capability.canonical_bytes,
            p1_authority=p1,
            p0_repository=p0,
            issuance_repository=issuance,
        )
        self.assertEqual(reloaded.to_dict(), capability.to_dict())

    def test_malformed_or_unknown_authority_reference_is_rejected(self) -> None:
        p1, p0, issuance, capability = self._bundle()
        unknown = copy.deepcopy(capability.to_dict())
        unknown["unknown_authority_reference"] = "not-allowed"
        with self.assertRaises(StructuralContractError):
            verify_capability_manifest(
                unknown,
                p1_authority=p1,
                p0_repository=p0,
                issuance_repository=issuance,
            )
        malformed = copy.deepcopy(capability.to_dict())
        malformed["p1_authority_digest"] = "not-a-digest"
        with self.assertRaises(StructuralContractError):
            verify_capability_manifest(
                malformed,
                p1_authority=p1,
                p0_repository=p0,
                issuance_repository=issuance,
            )

    def test_legitimate_roundtrip_preserves_canonical_identity(self) -> None:
        p1, p0, issuance, capability = self._bundle()
        parsed = CapabilityManifestV2.from_canonical_bytes(capability.canonical_bytes)
        self.assertEqual(parsed.to_dict(), capability.to_dict())
        self.assertEqual(parsed.header.artifact_id, capability.manifest.header.artifact_id)
        verified = verify_capability_manifest(
            parsed.to_dict(),
            p1_authority=p1,
            p0_repository=p0,
            issuance_repository=issuance,
        )
        self.assertEqual(verified.content_digest, capability.content_digest)

    def test_distinct_legitimate_occurrences_do_not_collapse_on_shared_labels(self) -> None:
        p1_a, p0_a, issuance_a, capability_a = self._bundle()
        occurrence_b = replace(
            p1_a.manifest.occurrence_reference,
            physical_source_instance_id="phys-b",
            native_record_id="msg-b",
            occurrence_namespace_id="ns-b",
        )
        p1_b, p0_b, issuance_b, capability_b = self._bundle(occurrence=occurrence_b)
        self.assertNotEqual(
            capability_a.manifest.occurrence_reference.identity_key(),
            capability_b.manifest.occurrence_reference.identity_key(),
        )
        self.assertNotEqual(
            capability_a.manifest.header.artifact_id,
            capability_b.manifest.header.artifact_id,
        )
        verify_capability_manifest(
            capability_a,
            p1_authority=p1_a,
            p0_repository=p0_a,
            issuance_repository=issuance_a,
        )
        verify_capability_manifest(
            capability_b,
            p1_authority=p1_b,
            p0_repository=p0_b,
            issuance_repository=issuance_b,
        )

    def test_issue_263_availability_axes_are_carried_without_collapse(self) -> None:
        availability = sample_availability(
            verbatim=sample_availability().verbatim_evidence_availability.UNAVAILABLE,
        )
        p1, _p0, _issuance, capability = self._bundle(availability=availability)
        self.assertEqual(
            capability.manifest.condition_neutral_evidence_availability.source_presence.value,
            "PRESENT",
        )
        self.assertEqual(
            capability.manifest.condition_neutral_evidence_availability.verbatim_evidence_availability.value,
            "UNAVAILABLE",
        )
        self.assertEqual(
            capability.manifest.condition_neutral_evidence_availability,
            p1.manifest.condition_neutral_evidence_availability,
        )

    def test_profile_authority_digest_changes_with_profile_content(self) -> None:
        profile = profile_for_legacy_format("sqlite_crush")
        changed = profile.with_capability_vector(
            profile.capability_vector.with_overrides(evidence_completeness="UNKNOWN")
        )
        self.assertNotEqual(profile_content_digest(profile), profile_content_digest(changed))


if __name__ == "__main__":
    unittest.main()
