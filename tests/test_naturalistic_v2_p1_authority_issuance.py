"""V2-01C — P1 authority issuance, sealing, and adversarial verification tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.v2.authority_issuance import (
    EvidenceSealManifestDraftV2,
    IssuedOccurrenceReferenceV2,
    SealedP1AuthorityV2,
    issue_occurrence_reference,
    verify_sealed_p1_authority,
)
from eval_naturalistic.v2.contracts import EvidenceSealManifestV2
from eval_naturalistic.v2.identity import (
    LineageEdgeV2,
    LineageRelationKind,
    reject_hash_or_locator_identity,
)
from eval_naturalistic.v2.lineage_attestation import (
    LineageAttestationRepository,
    occurrence_commitment_digest,
    verify_lineage_edge_attestation,
)
from eval_naturalistic.v2.p0_construct import InMemoryConstructFreezeRepository
from eval_naturalistic.v2.validators import parse_evidence_seal_manifest_v2
from tests.fixtures.naturalistic_v2_p1 import (
    ALT_DIGEST,
    FIXED_DIGEST,
    clone_lineage_edge,
    construct_freeze_content_digest,
    sample_availability,
    sample_construct_parent,
    sample_occurrence,
    sample_p0_repository,
    sample_seal_manifest,
    sample_sealed_authority,
    sample_verified_source_authority,
)


class NaturalisticV2P1AuthorityIssuanceTests(unittest.TestCase):
    def _sealed_dict(self) -> dict:
        repo = sample_p0_repository()
        sealed = sample_sealed_authority(p0_repository=repo)
        return sealed.to_dict()

    def test_valid_issuance_succeeds(self) -> None:
        issued = issue_occurrence_reference(sample_verified_source_authority())
        self.assertTrue(issued.issuance_digest)
        self.assertTrue(issued.issuer_implementation_revision)

    def test_sealed_bytes_reconstruct_independently(self) -> None:
        repo = sample_p0_repository()
        sealed = sample_sealed_authority(p0_repository=repo)
        reparsed = verify_sealed_p1_authority(
            sealed.to_dict(), p0_repository=repo
        )
        self.assertEqual(sealed.content_digest, reparsed.content_digest)

    def test_digest_id_recomputation_succeeds(self) -> None:
        repo = sample_p0_repository()
        sealed = sample_sealed_authority(p0_repository=repo)
        self.assertEqual(sealed.manifest.header.content_digest, sealed.content_digest)

    def test_required_parents_verify(self) -> None:
        repo = sample_p0_repository()
        sealed = sample_sealed_authority(p0_repository=repo)
        parents = sealed.manifest.immediate_parents
        self.assertTrue(any(p.parent_kind == "construct_freeze" for p in parents))

    def test_sealed_false_rejected(self) -> None:
        repo = sample_p0_repository()
        data = self._sealed_dict()
        data["header"]["sealed"] = False
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data, p0_repository=repo)

    def test_missing_seal_time_rejected(self) -> None:
        repo = sample_p0_repository()
        data = self._sealed_dict()
        del data["header"]["seal_time"]
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data, p0_repository=repo)

    def test_malformed_seal_time_rejected(self) -> None:
        data = self._sealed_dict()
        data["header"]["seal_time"] = ""
        with self.assertRaises(StructuralContractError):
            parse_evidence_seal_manifest_v2(data)

    def test_mismatched_content_digest_rejected(self) -> None:
        repo = sample_p0_repository()
        data = self._sealed_dict()
        data["header"]["content_digest"] = ALT_DIGEST
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data, p0_repository=repo)

    def test_mismatched_artifact_id_rejected(self) -> None:
        repo = sample_p0_repository()
        data = self._sealed_dict()
        data["header"]["artifact_id"] = "nps2_wrong_artifact_id"
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data, p0_repository=repo)

    def test_wrong_artifact_kind_rejected(self) -> None:
        repo = sample_p0_repository()
        data = self._sealed_dict()
        data["header"]["schema_version"] = "convmem/naturalistic/raw-evidence-manifest-v1"
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data, p0_repository=repo)

    def test_wrong_stage_rejected(self) -> None:
        repo = sample_p0_repository()
        data = self._sealed_dict()
        data["header"]["schema_version"] = "convmem/naturalistic/v2/wrong-stage-v2"
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data, p0_repository=repo)

    def test_missing_required_parent_rejected(self) -> None:
        repo = sample_p0_repository()
        data = self._sealed_dict()
        data["immediate_parents"] = []
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data, p0_repository=repo)

    def test_wrong_parent_digest_rejected(self) -> None:
        repo = sample_p0_repository()
        data = sample_sealed_authority(p0_repository=repo).to_dict()
        data["immediate_parents"][0]["parent_digest"] = ALT_DIGEST
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data, p0_repository=repo)

    def test_construct_freeze_mismatch_rejected(self) -> None:
        repo = sample_p0_repository()
        data = sample_sealed_authority(p0_repository=repo).to_dict()
        data["construct_freeze_digest"] = ALT_DIGEST
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data, p0_repository=repo)

    def test_post_seal_body_mutation_rejected(self) -> None:
        repo = sample_p0_repository()
        data = self._sealed_dict()
        data["episode_id"] = "mutated-episode"
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data, p0_repository=repo)

    def test_verify_without_p0_repository_rejected(self) -> None:
        data = self._sealed_dict()
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data)

    def test_arbitrary_occurrence_strings_not_issued_identity(self) -> None:
        repo = sample_p0_repository()
        seal = sample_seal_manifest(p0_repository=repo)
        with self.assertRaises(TypeError):
            EvidenceSealManifestV2(
                header=seal.header,
                construct_freeze_digest=construct_freeze_content_digest(repo),
                episode_id="episode-1",
                occurrence_reference=seal.occurrence_reference,
                occurrence_issuance_digest=FIXED_DIGEST,
                issuer_implementation_revision="rev",
                source_authority_digest=FIXED_DIGEST,
                physical_instance_id="phys-a",
                revision_or_asof_id="rev-1",
                evidence_snapshot_id="snap-1",
                evidence_complete_envelope_digest=FIXED_DIGEST,
                canonical_content_digest=FIXED_DIGEST,
                canonicalization_profile_digest=FIXED_DIGEST,
                adapter_implementation_digest=FIXED_DIGEST,
                condition_neutral_evidence_availability=sample_availability(),
                immediate_parents=(sample_construct_parent(repo),),
            )

    def test_locator_used_as_identity_rejected(self) -> None:
        with self.assertRaises(StructuralContractError):
            reject_hash_or_locator_identity({"locator": "/tmp/x", "source_path": "/tmp/y"})

    def test_content_hash_used_as_identity_rejected(self) -> None:
        with self.assertRaises(StructuralContractError):
            reject_hash_or_locator_identity({"content_digest": FIXED_DIGEST})

    def test_native_id_reuse_after_delete_recreate(self) -> None:
        first = issue_occurrence_reference(
            sample_verified_source_authority(physical_instance="inst-1")
        )
        second = issue_occurrence_reference(
            sample_verified_source_authority(physical_instance="inst-2")
        )
        self.assertNotEqual(first.issuance_digest, second.issuance_digest)

    def test_clone_import_restore_collision(self) -> None:
        original = issue_occurrence_reference(
            sample_verified_source_authority(physical_instance="orig")
        )
        clone = issue_occurrence_reference(
            sample_verified_source_authority(physical_instance="clone", namespace="ns-clone")
        )
        self.assertNotEqual(original.issuance_digest, clone.issuance_digest)

    def test_malformed_boolean_false_string_rejected(self) -> None:
        with self.assertRaises(StructuralContractError):
            LineageEdgeV2.from_dict({
                "logical_lineage_id": "lineage-1",
                "from_physical_instance_id": "a",
                "to_physical_instance_id": "b",
                "relation_kind": "CLONE",
                "issuer_attested": "false",
                "child_occurrence_digest": FIXED_DIGEST,
                "parent_occurrence_digest": ALT_DIGEST,
            })

    def test_arbitrary_lineage_claim_rejected(self) -> None:
        with self.assertRaises(StructuralContractError):
            LineageEdgeV2.from_dict({
                "logical_lineage_id": "lineage-1",
                "from_physical_instance_id": "a",
                "to_physical_instance_id": "b",
                "relation_kind": "CLONE",
                "issuer_attested": True,
                "child_occurrence_digest": FIXED_DIGEST,
                "parent_occurrence_digest": ALT_DIGEST,
            })

    def test_lineage_attestation_without_evidence_rejected(self) -> None:
        with self.assertRaises(StructuralContractError):
            LineageEdgeV2.from_dict({
                "logical_lineage_id": "lineage-1",
                "from_physical_instance_id": "a",
                "to_physical_instance_id": "b",
                "relation_kind": "CLONE",
                "issuer_attested": True,
                "child_occurrence_digest": FIXED_DIGEST,
                "parent_occurrence_digest": ALT_DIGEST,
            })

    def test_lineage_bound_to_wrong_occurrence_rejected(self) -> None:
        child = sample_occurrence(physical_instance="phys-a")
        parent = sample_occurrence(physical_instance="phys-b", namespace="ns-b")
        repo = LineageAttestationRepository()
        edge = clone_lineage_edge(
            child_occurrence=child,
            parent_occurrence=parent,
            from_instance="phys-a",
            to_instance="phys-b",
            lineage_repository=repo,
        )
        with self.assertRaises(StructuralContractError):
            verify_lineage_edge_attestation(
                edge,
                child_occurrence=child,
                parent_occurrence=sample_occurrence(physical_instance="wrong"),
                repository=repo,
            )

    def test_raw_unfinalized_p1_rejected_by_consumer(self) -> None:
        repo = sample_p0_repository()
        issued = issue_occurrence_reference(sample_verified_source_authority())
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=construct_freeze_content_digest(repo),
            episode_id="episode-1",
            issued_occurrence=issued,
            evidence_complete_envelope_digest=FIXED_DIGEST,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
            condition_neutral_evidence_availability=sample_availability(),
            immediate_parents=(sample_construct_parent(repo),),
            responsible_role="evidence_capture",
            created_at="2026-08-31T00:00:00Z",
        )
        body = draft._body_without_seal_metadata()
        with self.assertRaises(StructuralContractError):
            parse_evidence_seal_manifest_v2({
                "header": {
                    "artifact_id": "nps2_unsealed",
                    "schema_version": EvidenceSealManifestV2.SCHEMA,
                    "created_at": "2026-08-31T00:00:00Z",
                    "responsible_role": "evidence_capture",
                    "sealed": False,
                },
                **body,
            })

    def test_finalized_bytes_modified_after_issuance_rejected(self) -> None:
        repo = sample_p0_repository()
        sealed = sample_sealed_authority(p0_repository=repo)
        data = sealed.to_dict()
        data["canonical_content_digest"] = ALT_DIGEST
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data, p0_repository=repo)


if __name__ == "__main__":
    unittest.main()
