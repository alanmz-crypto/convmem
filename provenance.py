"""Canonical provenance policy and assertion substrate for T3 P1.

The module deliberately has no ingest, Chroma, backup, or live-data hooks.
It owns the narrow policy boundary needed by later slices: strict typed
envelope acceptance, canonical commitments, conservative integrity propagation,
monitor-minted assertion identity, and fail-closed recursive verification over
immutable in-memory authority snapshots.
"""

# This is the deliberately deep P1 policy boundary; its validation and
# snapshot mechanics are kept together rather than scattered across callers.
# pylint: disable=too-many-lines,too-many-instance-attributes,too-many-return-statements
# pylint: disable=too-many-arguments,try-except-raise

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import threading
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


SCHEMA_VERSION = "convmem/provenance-envelope-v1"
BINDING_VERSION = "convmem/provenance-binding-v1"
POLICY_VERSION = "convmem/provenance-policy-v1"
ROOT_DERIVATION = "root"

INTEGRITY_LEVELS = ("untrusted", "agent", "trusted")
PRODUCER_CLASSES = ("user", "trusted_tool", "agent", "external", "unknown")
PRODUCER_ASSURANCES = ("verified", "claimed", "unknown")
ANCESTRY_STATES = ("complete", "partial", "unknown")

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class ProvenanceError(ValueError):
    """Base class for invalid provenance data or policy operations."""


class EnvelopeValidationError(ProvenanceError):
    """An envelope is not in the strict typed acceptance domain."""


class CommitmentError(ProvenanceError):
    """An envelope commitment is absent or does not match its bytes."""


class IdentityReplayError(ProvenanceError):
    """An identity-preserving import cannot be accepted safely."""


class PinError(ProvenanceError):
    """A verification pin is closed, lost, or cannot be reclaimed safely."""


class ReclamationDisabled(PinError):
    """P1 intentionally does not reclaim authority generations."""


def _reject_surrogates(value: Any, *, path: str = "$") -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise EnvelopeValidationError(f"invalid Unicode surrogate at {path}")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise EnvelopeValidationError(f"non-string object key at {path}")
            _reject_surrogates(child, path=f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_surrogates(child, path=f"{path}[{index}]")


def _validate_json_value(value: Any, *, path: str = "$") -> None:
    """Validate the finite, UTF-8 JSON domain used before canonicalization."""

    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, str):
            _reject_surrogates(value, path=path)
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise EnvelopeValidationError(f"non-finite number at {path}")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise EnvelopeValidationError(f"non-string object key at {path}")
            _validate_json_value(child, path=f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_json_value(child, path=f"{path}[{index}]")
        return
    raise EnvelopeValidationError(
        f"unsupported JSON value {type(value).__name__} at {path}"
    )


def _canonical_json_bytes(value: Any) -> bytes:
    _validate_json_value(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise EnvelopeValidationError(f"value is not canonical JSON: {exc}") from exc


def canonical_bytes(value: Any) -> bytes:
    """Return the versioned ConvMem canonical JSON representation."""

    return _canonical_json_bytes(value)


def sha256_hex(value: bytes | str) -> str:
    """Return a lowercase SHA-256 digest for bytes or UTF-8 text."""

    payload = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(payload).hexdigest()


def canonical_hash(value: Any) -> str:
    """Hash a value using the same canonical profile as commitments."""

    return sha256_hex(canonical_bytes(value))


def _strict_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EnvelopeValidationError(f"duplicate object key: {key}")
        result[key] = value
    return result


def _reject_json_constant(token: str) -> None:
    raise EnvelopeValidationError(f"undefined JSON number: {token}")


def parse_json(payload: str | bytes) -> Any:
    """Parse strict JSON before a value can enter canonicalization."""

    try:
        value = json.loads(
            payload,
            object_pairs_hook=_strict_object_pairs,
            parse_constant=_reject_json_constant,
        )
    except EnvelopeValidationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EnvelopeValidationError(f"invalid JSON: {exc}") from exc
    _validate_json_value(value)
    return value


_SCHEMA_SEMANTIC_SPEC = {
    "schema_version": SCHEMA_VERSION,
    "binding_version": BINDING_VERSION,
    "profile": "conv-mem-canonical-json-v1",
    "object_keys": "strings, sorted lexicographically",
    "strings": "valid Unicode scalar values, UTF-8, no lone surrogates",
    "numbers": "finite JSON numbers only; no NaN or Infinity",
    "lists": "order is semantic and preserved",
    "nulls": "null is distinct from omission; envelope optional fields are explicit null or typed values",
    "unknown_fields": "rejected by the typed envelope acceptance boundary",
}
SCHEMA_SEMANTICS_BYTES = _canonical_json_bytes(_SCHEMA_SEMANTIC_SPEC)
SCHEMA_SEMANTICS_SHA256 = sha256_hex(SCHEMA_SEMANTICS_BYTES)


_REQUIRED_FIELDS = {
    "schema_version",
    "binding_version",
    "schema_semantics_sha256",
    "assertion_id",
    "root_bindings",
    "input_bindings",
    "producer_class",
    "producer_assurance",
    "derivation_kind",
    "transformer_class",
    "transformer_identity",
    "transformer_version",
    "transformer_artifact_sha256",
    "transformer_recipe_id",
    "transformer_recipe_sha256",
    "selection_parameters",
    "provider_payload_sha256",
    "recipe_config_sha256",
    "ancestry_completeness",
    "provenance_policy_version",
    "provenance_policy_sha256",
}
_OPTIONAL_FIELDS = {"effective_integrity", "provenance_commitment"}
_ALLOWED_FIELDS = _REQUIRED_FIELDS | _OPTIONAL_FIELDS
def _require_string(value: Any, field: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        raise EnvelopeValidationError(f"{field} must be a non-empty string")
    _reject_surrogates(value, path=field)
    return value


def _require_hash(value: Any, field: str, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise EnvelopeValidationError(f"{field} must be lowercase SHA-256 hex")


def _require_uuid4(value: Any, field: str = "assertion_id") -> str:
    if not isinstance(value, str) or not _UUID4_RE.fullmatch(value):
        raise EnvelopeValidationError(f"{field} must be canonical lowercase UUIDv4")
    parsed = uuid.UUID(value)
    if parsed.version != 4 or parsed.variant != uuid.RFC_4122:
        raise EnvelopeValidationError(f"{field} must be RFC 4122 UUIDv4")
    return value


def _validate_root_binding(binding: Any, index: int) -> None:
    path = f"root_bindings[{index}]"
    if not isinstance(binding, Mapping):
        raise EnvelopeValidationError(f"{path} must be an object")
    required = {
        "source_identity",
        "record_locator",
        "raw_record_sha256",
        "input_view_sha256",
        "origin_class",
        "origin_assurance",
        "origin_evidence",
    }
    if set(binding) != required:
        raise EnvelopeValidationError(f"{path} has an invalid field set")
    _require_string(binding["source_identity"], f"{path}.source_identity")
    _require_string(binding["record_locator"], f"{path}.record_locator")
    _require_hash(binding["raw_record_sha256"], f"{path}.raw_record_sha256")
    _require_hash(binding["input_view_sha256"], f"{path}.input_view_sha256")
    _require_string(binding["origin_class"], f"{path}.origin_class")
    if binding["origin_assurance"] not in PRODUCER_ASSURANCES:
        raise EnvelopeValidationError(f"{path}.origin_assurance is not supported")
    evidence = binding["origin_evidence"]
    if not isinstance(evidence, Mapping) or set(evidence) != {
        "channel_class",
        "channel_locator",
        "channel_evidence_sha256",
    }:
        raise EnvelopeValidationError(f"{path}.origin_evidence is invalid")
    _require_string(evidence["channel_class"], f"{path}.origin_evidence.channel_class")
    _require_string(evidence["channel_locator"], f"{path}.origin_evidence.channel_locator")
    _require_hash(
        evidence["channel_evidence_sha256"],
        f"{path}.origin_evidence.channel_evidence_sha256",
    )


def _validate_input_binding(binding: Any, index: int) -> None:
    path = f"input_bindings[{index}]"
    if not isinstance(binding, Mapping) or set(binding) != {
        "parent_assertion_id",
        "parent_provenance_commitment",
        "exact_input_view_sha256",
    }:
        raise EnvelopeValidationError(f"{path} is invalid")
    _require_uuid4(binding["parent_assertion_id"], f"{path}.parent_assertion_id")
    _require_hash(
        binding["parent_provenance_commitment"],
        f"{path}.parent_provenance_commitment",
    )
    _require_hash(binding["exact_input_view_sha256"], f"{path}.exact_input_view_sha256")


def validate_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and copy an envelope in the strict typed domain."""

    if not isinstance(envelope, Mapping):
        raise EnvelopeValidationError("envelope must be an object")
    keys = set(envelope)
    missing = _REQUIRED_FIELDS - keys
    unknown = keys - _ALLOWED_FIELDS
    if missing:
        raise EnvelopeValidationError(f"missing envelope fields: {sorted(missing)}")
    if unknown:
        raise EnvelopeValidationError(f"unknown envelope fields: {sorted(unknown)}")
    result = _thaw_value(envelope)
    _validate_json_value(result)
    if result["schema_version"] != SCHEMA_VERSION:
        raise EnvelopeValidationError("unsupported schema_version")
    if result["binding_version"] != BINDING_VERSION:
        raise EnvelopeValidationError("unsupported binding_version")
    _require_hash(result["schema_semantics_sha256"], "schema_semantics_sha256")
    if result["schema_semantics_sha256"] != SCHEMA_SEMANTICS_SHA256:
        raise EnvelopeValidationError("schema semantic specification digest mismatch")
    _require_uuid4(result["assertion_id"])
    if not isinstance(result["root_bindings"], (list, tuple)):
        raise EnvelopeValidationError("root_bindings must be a list")
    if not isinstance(result["input_bindings"], (list, tuple)):
        raise EnvelopeValidationError("input_bindings must be a list")
    if bool(result["root_bindings"]) == bool(result["input_bindings"]):
        raise EnvelopeValidationError("exactly one binding family must be non-empty")
    for index, binding in enumerate(result["root_bindings"]):
        _validate_root_binding(binding, index)
    for index, binding in enumerate(result["input_bindings"]):
        _validate_input_binding(binding, index)
    if result["producer_class"] not in PRODUCER_CLASSES:
        raise EnvelopeValidationError("producer_class is not supported")
    if result["producer_assurance"] not in PRODUCER_ASSURANCES:
        raise EnvelopeValidationError("producer_assurance is not supported")
    _require_string(result["derivation_kind"], "derivation_kind")
    _require_string(result["transformer_class"], "transformer_class")
    _require_string(result["transformer_identity"], "transformer_identity")
    _require_string(result["transformer_version"], "transformer_version")
    _require_hash(result["transformer_artifact_sha256"], "transformer_artifact_sha256", nullable=True)
    _require_string(result["transformer_recipe_id"], "transformer_recipe_id")
    _require_hash(result["transformer_recipe_sha256"], "transformer_recipe_sha256")
    if not isinstance(result["selection_parameters"], Mapping):
        raise EnvelopeValidationError("selection_parameters must be an object")
    _require_hash(result["provider_payload_sha256"], "provider_payload_sha256", nullable=True)
    _require_hash(result["recipe_config_sha256"], "recipe_config_sha256", nullable=True)
    if result["ancestry_completeness"] not in ANCESTRY_STATES:
        raise EnvelopeValidationError("ancestry_completeness is not supported")
    _require_string(result["provenance_policy_version"], "provenance_policy_version")
    _require_hash(result["provenance_policy_sha256"], "provenance_policy_sha256")
    if "effective_integrity" in result and result["effective_integrity"] not in INTEGRITY_LEVELS:
        raise EnvelopeValidationError("effective_integrity cache is invalid")
    if "provenance_commitment" in result:
        _require_hash(result["provenance_commitment"], "provenance_commitment")
    return result


def authoritative_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Return the validated commitment preimage without cache fields."""

    result = validate_envelope(envelope)
    result.pop("effective_integrity", None)
    result.pop("provenance_commitment", None)
    return result


def canonical_envelope_bytes(envelope: Mapping[str, Any]) -> bytes:
    """Canonicalize only a validated typed envelope."""

    return canonical_bytes(authoritative_envelope(envelope))


def provenance_commitment(envelope: Mapping[str, Any]) -> str:
    """Compute the authoritative SHA-256 provenance commitment."""

    return sha256_hex(canonical_envelope_bytes(envelope))


def parse_envelope(payload: str | bytes) -> dict[str, Any]:
    """Strictly parse and validate a serialized envelope."""

    parsed = parse_json(payload)
    if not isinstance(parsed, Mapping):
        raise EnvelopeValidationError("serialized envelope must be an object")
    return validate_envelope(parsed)


def _new_uuid4() -> str:
    value = str(uuid.uuid4())
    _require_uuid4(value)
    return value


def _copy_mapping(value: Mapping[str, Any]) -> MappingProxyType:
    return MappingProxyType({key: _freeze_value(child) for key, child in value.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_value(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(child) for child in value)
    return copy.deepcopy(value)


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw_value(child) for child in value]
    return copy.deepcopy(value)


@dataclass(frozen=True)
class TransformerRule:
    """One exact transformer allowlist entry."""

    transformer_class: str
    transformer_identity: str
    transformer_version: str
    recipe_id: str
    cap: str
    preservation_contract: str | None = None
    artifact_sha256: str | None = None

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (
            self.transformer_class,
            self.transformer_identity,
            self.transformer_version,
            self.recipe_id,
        )


@dataclass(frozen=True)
class PolicyDefinition:
    """Immutable policy semantics and exact transformer allowlist."""

    version: str
    semantic_bytes: bytes
    rules: tuple[TransformerRule, ...] = ()

    @property
    def semantic_sha256(self) -> str:
        return sha256_hex(self.semantic_bytes)

    def rule_for(self, envelope: Mapping[str, Any]) -> TransformerRule | None:
        key = (
            envelope["transformer_class"],
            envelope["transformer_identity"],
            envelope["transformer_version"],
            envelope["transformer_recipe_id"],
        )
        return next((rule for rule in self.rules if rule.key == key), None)

    def transformer_cap(self, envelope: Mapping[str, Any]) -> str:
        transformer_class = envelope["transformer_class"]
        if transformer_class in {"llm", "summarize", "distill", "rewrite", "classify"}:
            return "agent"
        rule = self.rule_for(envelope)
        if rule is None:
            return "untrusted"
        if rule.cap not in INTEGRITY_LEVELS:
            return "untrusted"
        if rule.cap == "trusted":
            if not rule.preservation_contract:
                return "untrusted"
            if not rule.artifact_sha256:
                return "untrusted"
            if envelope.get("transformer_artifact_sha256") != rule.artifact_sha256:
                return "untrusted"
        return rule.cap


def _default_policy() -> PolicyDefinition:
    semantic = {
        "policy_version": POLICY_VERSION,
        "transformer_caps": {
            "llm": "agent",
            "summarize": "agent",
            "distill": "agent",
            "rewrite": "agent",
            "classify": "agent",
        },
        "unknown_transformers": "untrusted",
        "trusted_cap_requires": [
            "exact class/identity/version/recipe",
            "tested preservation contract",
            "immutable artifact sha256",
        ],
    }
    return PolicyDefinition(POLICY_VERSION, _canonical_json_bytes(semantic))


@dataclass(frozen=True)
class AssertionRecord:
    """An authoritative envelope and its commitment in a registry snapshot."""

    assertion_id: str
    envelope: Mapping[str, Any]
    commitment: str
    generation: str

    def as_dict(self) -> dict[str, Any]:
        result = _thaw_value(self.envelope)
        result["provenance_commitment"] = self.commitment
        return result


@dataclass(frozen=True)
class VerificationResult:
    """Observable result of one recursive verification operation."""

    assertion_id: str
    effective_integrity: str
    status: str
    reason: str | None
    authority_generation: str
    policy_snapshot: str

    @property
    def verified(self) -> bool:
        return self.status == "verified"


@dataclass(frozen=True)
class _AuthoritySnapshot:
    generation: str
    policy_snapshot: str
    records: Mapping[str, AssertionRecord]
    policies: Mapping[str, PolicyDefinition]
    recipes: Mapping[str, bytes]
    schema_semantics: Mapping[tuple[str, str], bytes]


class VerificationPin:
    """Operation-scope immutable authority/policy snapshot pin."""

    def __init__(self, registry: "ProvenanceRegistry", snapshot: _AuthoritySnapshot):
        self._registry = registry
        self.snapshot = snapshot
        self._closed = False
        registry._pin_opened(snapshot.generation)  # pylint: disable=protected-access

    @property
    def generation(self) -> str:
        return self.snapshot.generation

    @property
    def policy_snapshot(self) -> str:
        return self.snapshot.policy_snapshot

    def ensure_active(self) -> None:
        if self._closed:
            raise PinError("verification pin is closed")
        if not self._registry._pin_exists(self.snapshot.generation):  # pylint: disable=protected-access
            raise PinError("bound verification state was lost")

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._registry._pin_closed(self.snapshot.generation)  # pylint: disable=protected-access

    def __enter__(self) -> "VerificationPin":
        self.ensure_active()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class ProvenanceRegistry:
    """Copy-on-write authority registry used by P1 and hermetic tests.

    P1 deliberately chooses the simplest allowed retention mechanism: authority
    generations are never reclaimed by this module. A pinned generation is
    therefore stable even when a newer generation is published.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._counter = 0
        self._records: dict[str, AssertionRecord] = {}
        self._policies: dict[str, PolicyDefinition] = {POLICY_VERSION: _default_policy()}
        self._recipes: dict[str, bytes] = {
            "root-v1": b"convmem:root-recipe-v1",
        }
        self._schema_semantics: dict[tuple[str, str], bytes] = {
            (SCHEMA_VERSION, BINDING_VERSION): SCHEMA_SEMANTICS_BYTES
        }
        self._snapshots: dict[str, _AuthoritySnapshot] = {}
        self._active_pins: dict[str, int] = {}
        self._publish_snapshot()

    @property
    def current_generation(self) -> str:
        with self._lock:
            return self._current_snapshot().generation

    @property
    def current_policy(self) -> PolicyDefinition:
        with self._lock:
            return self._policies[POLICY_VERSION]

    def _policy_snapshot_digest(self) -> str:
        policies = {
            version: {
                "semantic_sha256": policy.semantic_sha256,
                "rules": [rule.__dict__ for rule in policy.rules],
            }
            for version, policy in sorted(self._policies.items())
        }
        recipes = {key: sha256_hex(value) for key, value in sorted(self._recipes.items())}
        schemas = {
            f"{schema}|{binding}": sha256_hex(value)
            for (schema, binding), value in sorted(self._schema_semantics.items())
        }
        return canonical_hash({"policies": policies, "recipes": recipes, "schemas": schemas})

    def _publish_snapshot(self) -> _AuthoritySnapshot:
        self._counter += 1
        generation = f"p1-g{self._counter:08d}"
        records = {
            key: AssertionRecord(
                record.assertion_id,
                _copy_mapping(record.envelope),
                record.commitment,
                generation,
            )
            for key, record in self._records.items()
        }
        snapshot = _AuthoritySnapshot(
            generation=generation,
            policy_snapshot=self._policy_snapshot_digest(),
            records=MappingProxyType(records),
            policies=MappingProxyType(dict(self._policies)),
            recipes=MappingProxyType(dict(self._recipes)),
            schema_semantics=MappingProxyType(dict(self._schema_semantics)),
        )
        self._snapshots[generation] = snapshot
        return snapshot

    def _current_snapshot(self) -> _AuthoritySnapshot:
        return self._snapshots[max(self._snapshots, key=lambda key: int(key.rsplit("g", 1)[1]))]

    def _pin_opened(self, generation: str) -> None:
        with self._lock:
            if generation not in self._snapshots:
                raise PinError("cannot pin unavailable generation")
            self._active_pins[generation] = self._active_pins.get(generation, 0) + 1

    def _pin_closed(self, generation: str) -> None:
        with self._lock:
            count = self._active_pins.get(generation, 0)
            if count <= 1:
                self._active_pins.pop(generation, None)
            else:
                self._active_pins[generation] = count - 1

    def _pin_exists(self, generation: str) -> bool:
        with self._lock:
            return generation in self._snapshots

    def pin(self) -> VerificationPin:
        with self._lock:
            return VerificationPin(self, self._current_snapshot())

    def reclaim(self, generation: str) -> None:
        """Reject all P1 reclamation; active pins can never be invalidated."""

        with self._lock:
            if generation in self._active_pins:
                raise PinError("active verification pin prevents reclamation")
            raise ReclamationDisabled("P1 authority-generation reclamation is disabled")

    def register_policy(
        self,
        version: str,
        semantic_spec: Mapping[str, Any] | bytes,
        *,
        rules: Sequence[TransformerRule] = (),
    ) -> PolicyDefinition:
        _require_string(version, "policy version")
        semantic_bytes = (
            semantic_spec
            if isinstance(semantic_spec, bytes)
            else canonical_bytes(semantic_spec)
        )
        policy = PolicyDefinition(version, semantic_bytes, tuple(rules))
        with self._lock:
            self._policies[version] = policy
            self._publish_snapshot()
        return policy

    def register_recipe(self, recipe_id: str, semantic_spec: Mapping[str, Any] | bytes) -> str:
        _require_string(recipe_id, "recipe id")
        semantic_bytes = (
            semantic_spec
            if isinstance(semantic_spec, bytes)
            else canonical_bytes(semantic_spec)
        )
        with self._lock:
            self._recipes[recipe_id] = semantic_bytes
            self._publish_snapshot()
        return sha256_hex(semantic_bytes)

    def register_schema_semantics(
        self, schema_version: str, binding_version: str, semantic_spec: Mapping[str, Any] | bytes
    ) -> str:
        _require_string(schema_version, "schema version")
        _require_string(binding_version, "binding version")
        semantic_bytes = (
            semantic_spec
            if isinstance(semantic_spec, bytes
            )
            else canonical_bytes(semantic_spec)
        )
        with self._lock:
            self._schema_semantics[(schema_version, binding_version)] = semantic_bytes
            self._publish_snapshot()
        return sha256_hex(semantic_bytes)

    def _store_record(self, envelope: Mapping[str, Any]) -> AssertionRecord:
        validated = validate_envelope(envelope)
        commitment = provenance_commitment(validated)
        assertion_id = validated["assertion_id"]
        with self._lock:
            if assertion_id in self._records:
                raise IdentityReplayError("assertion_id is already reserved")
            provisional = AssertionRecord(assertion_id, _copy_mapping(validated), commitment, "")
            self._records[assertion_id] = provisional
            snapshot = self._publish_snapshot()
            return snapshot.records[assertion_id]

    def mint(self, envelope: Mapping[str, Any]) -> AssertionRecord:
        """Mint a fresh monitor identity; callers may not provide an ID."""

        candidate = _thaw_value(envelope)
        if candidate.get("assertion_id"):
            raise IdentityReplayError("only the monitor may mint assertion_id")
        candidate.pop("effective_integrity", None)
        candidate.pop("provenance_commitment", None)
        for _attempt in range(8):
            candidate["assertion_id"] = _new_uuid4()
            try:
                return self._store_record(candidate)
            except IdentityReplayError as exc:
                if "already reserved" not in str(exc):
                    raise
        raise IdentityReplayError("unable to reserve a fresh assertion_id")

    def import_replay(
        self, envelope: Mapping[str, Any], commitment: str | None = None
    ) -> tuple[AssertionRecord, bool]:
        """Import a valid exported identity or return an idempotent replay.

        A supplied ID is accepted only with a matching commitment and a
        recursively verifiable parent graph. Missing or divergent identity
        material is rejected and can never overwrite an existing row.
        """

        candidate = validate_envelope(envelope)
        expected = provenance_commitment(candidate)
        supplied = commitment or candidate.get("provenance_commitment")
        if supplied != expected:
            raise IdentityReplayError("identity-preserving import commitment mismatch")
        with self.pin() as pin:
            result = self._verify(candidate["assertion_id"], pin, candidate_override=candidate)
            if not result.verified:
                raise IdentityReplayError(f"identity-preserving import is not verifiable: {result.reason}")
        with self._lock:
            existing = self._records.get(candidate["assertion_id"])
            if existing:
                same_envelope = authoritative_envelope(existing.envelope) == authoritative_envelope(candidate)
                if existing.commitment == expected and same_envelope:
                    return existing, True
                raise IdentityReplayError("existing assertion has divergent envelope or commitment")
            stored = self._store_record(candidate)
            return stored, False

    def mint_untrusted_replacement(self, envelope: Mapping[str, Any]) -> AssertionRecord:
        """Retain invalid replay content only under a fresh untrusted identity."""

        candidate = _thaw_value(envelope)
        candidate.pop("assertion_id", None)
        candidate["producer_assurance"] = "unknown"
        candidate["ancestry_completeness"] = "unknown"
        return self.mint(candidate)

    def get(self, assertion_id: str, pin: VerificationPin | None = None) -> AssertionRecord | None:
        """Resolve an assertion from the current or explicitly pinned snapshot."""

        _require_uuid4(assertion_id)
        if pin:
            pin.ensure_active()
            return pin.snapshot.records.get(assertion_id)
        with self.pin() as operation:
            return operation.snapshot.records.get(assertion_id)

    def verify(self, assertion_id: str, pin: VerificationPin | None = None) -> VerificationResult:
        """Recursively recompute integrity against one immutable snapshot."""

        _require_uuid4(assertion_id)
        if pin is not None:
            pin.ensure_active()
            return self._verify(assertion_id, pin)
        with self.pin() as operation:
            return self._verify(assertion_id, operation)

    def _degraded(self, assertion_id: str, pin: VerificationPin, reason: str) -> VerificationResult:
        return VerificationResult(
            assertion_id,
            "untrusted",
            "degraded",
            reason,
            pin.generation,
            pin.policy_snapshot,
        )

    def _verify(
        self,
        assertion_id: str,
        pin: VerificationPin,
        *,
        candidate_override: Mapping[str, Any] | None = None,
        visited: set[str] | None = None,
    ) -> VerificationResult:
        pin.ensure_active()
        visited = visited or set()
        if assertion_id in visited:
            return self._degraded(assertion_id, pin, "cycle detected")
        visited.add(assertion_id)
        envelope = candidate_override or pin.snapshot.records.get(assertion_id)
        if envelope is None:
            return self._degraded(assertion_id, pin, "missing assertion")
        if isinstance(envelope, AssertionRecord):
            envelope = envelope.envelope
        try:
            validated = validate_envelope(envelope)
            expected = provenance_commitment(validated)
            stored = pin.snapshot.records.get(assertion_id)
            if stored and stored.commitment != expected:
                return self._degraded(assertion_id, pin, "stored commitment mismatch")
            if validated.get("provenance_commitment") not in (None, expected):
                return self._degraded(assertion_id, pin, "envelope commitment mismatch")
            schema_bytes = pin.snapshot.schema_semantics.get(
                (validated["schema_version"], validated["binding_version"])
            )
            if schema_bytes is None or sha256_hex(schema_bytes) != validated["schema_semantics_sha256"]:
                return self._degraded(assertion_id, pin, "schema semantic bytes unavailable or changed")
            policy = pin.snapshot.policies.get(validated["provenance_policy_version"])
            if policy is None or policy.semantic_sha256 != validated["provenance_policy_sha256"]:
                return self._degraded(assertion_id, pin, "policy semantic bytes unavailable or changed")
            recipe_bytes = pin.snapshot.recipes.get(validated["transformer_recipe_id"])
            if recipe_bytes is None or sha256_hex(recipe_bytes) != validated["transformer_recipe_sha256"]:
                return self._degraded(assertion_id, pin, "recipe semantic bytes unavailable or changed")
            if validated["ancestry_completeness"] != "complete":
                return self._degraded(assertion_id, pin, "ancestry is incomplete")
            if validated["input_bindings"]:
                parent_levels: list[str] = []
                for binding in validated["input_bindings"]:
                    parent_id = binding["parent_assertion_id"]
                    parent = pin.snapshot.records.get(parent_id)
                    if parent is None:
                        return self._degraded(assertion_id, pin, "missing parent")
                    if parent.commitment != binding["parent_provenance_commitment"]:
                        return self._degraded(assertion_id, pin, "parent commitment mismatch")
                    parent_result = self._verify(parent_id, pin, visited=set(visited))
                    if not parent_result.verified:
                        return self._degraded(assertion_id, pin, f"parent degraded: {parent_result.reason}")
                    parent_levels.append(parent_result.effective_integrity)
                cap = policy.transformer_cap(validated)
                integrity = _meet([*parent_levels, cap])
            else:
                integrity = _root_integrity(validated["root_bindings"])
            if validated.get("effective_integrity") not in (None, integrity):
                return self._degraded(assertion_id, pin, "effective-integrity cache mismatch")
            return VerificationResult(
                assertion_id,
                integrity,
                "verified",
                None,
                pin.generation,
                pin.policy_snapshot,
            )
        except (EnvelopeValidationError, CommitmentError, PinError) as exc:
            return self._degraded(assertion_id, pin, str(exc))


def _meet(levels: Sequence[str]) -> str:
    if not levels:
        return "untrusted"
    try:
        return min(levels, key=INTEGRITY_LEVELS.index)
    except ValueError:
        return "untrusted"


def _root_integrity(bindings: Sequence[Mapping[str, Any]]) -> str:
    if not bindings:
        return "untrusted"
    if all(
        binding["origin_assurance"] == "verified"
        and binding["origin_evidence"]["channel_class"] != "unverified"
        and binding["origin_evidence"]["channel_locator"] != "unverified://none"
        for binding in bindings
    ):
        return "trusted"
    return "untrusted"


def base_envelope(
    *,
    assertion_id: str | None = None,
    root_bindings: Sequence[Mapping[str, Any]] = (),
    input_bindings: Sequence[Mapping[str, Any]] = (),
    producer_class: str = "unknown",
    producer_assurance: str = "unknown",
    derivation_kind: str = ROOT_DERIVATION,
    transformer_class: str = "root",
    transformer_identity: str = "monitor",
    transformer_version: str = "1",
    transformer_artifact_sha256: str | None = None,
    transformer_recipe_id: str = "root-v1",
    transformer_recipe_sha256: str | None = None,
    selection_parameters: Mapping[str, Any] | None = None,
    provider_payload_sha256: str | None = None,
    recipe_config_sha256: str | None = None,
    ancestry_completeness: str = "complete",
    provenance_policy_version: str = POLICY_VERSION,
    provenance_policy_sha256: str | None = None,
) -> dict[str, Any]:
    """Build a typed envelope template; ``ProvenanceRegistry.mint`` assigns ID."""

    if transformer_recipe_sha256 is None:
        transformer_recipe_sha256 = sha256_hex(b"convmem:root-recipe-v1")
    if provenance_policy_sha256 is None:
        provenance_policy_sha256 = _default_policy().semantic_sha256
    result = {
        "schema_version": SCHEMA_VERSION,
        "binding_version": BINDING_VERSION,
        "schema_semantics_sha256": SCHEMA_SEMANTICS_SHA256,
        "assertion_id": assertion_id,
        "root_bindings": list(copy.deepcopy(root_bindings)),
        "input_bindings": list(copy.deepcopy(input_bindings)),
        "producer_class": producer_class,
        "producer_assurance": producer_assurance,
        "derivation_kind": derivation_kind,
        "transformer_class": transformer_class,
        "transformer_identity": transformer_identity,
        "transformer_version": transformer_version,
        "transformer_artifact_sha256": transformer_artifact_sha256,
        "transformer_recipe_id": transformer_recipe_id,
        "transformer_recipe_sha256": transformer_recipe_sha256,
        "selection_parameters": dict(selection_parameters or {}),
        "provider_payload_sha256": provider_payload_sha256,
        "recipe_config_sha256": recipe_config_sha256,
        "ancestry_completeness": ancestry_completeness,
        "provenance_policy_version": provenance_policy_version,
        "provenance_policy_sha256": provenance_policy_sha256,
    }
    if assertion_id is None:
        result.pop("assertion_id")
    return result


def root_binding(
    *,
    source_identity: str,
    record_locator: str,
    raw_record_sha256: str,
    input_view_sha256: str,
    origin_class: str = "external",
    origin_assurance: str = "unknown",
    channel_class: str = "unverified",
    channel_locator: str = "unverified://none",
    channel_evidence_sha256: str | None = None,
) -> dict[str, Any]:
    """Build a root binding with explicit origin evidence."""

    return {
        "source_identity": source_identity,
        "record_locator": record_locator,
        "raw_record_sha256": raw_record_sha256,
        "input_view_sha256": input_view_sha256,
        "origin_class": origin_class,
        "origin_assurance": origin_assurance,
        "origin_evidence": {
            "channel_class": channel_class,
            "channel_locator": channel_locator,
            "channel_evidence_sha256": channel_evidence_sha256 or sha256_hex(b"no-authenticated-evidence"),
        },
    }


def input_binding(parent: AssertionRecord, *, exact_input_view_sha256: str) -> dict[str, Any]:
    """Build an immutable parent identity/commitment edge."""

    _require_hash(exact_input_view_sha256, "exact_input_view_sha256")
    return {
        "parent_assertion_id": parent.assertion_id,
        "parent_provenance_commitment": parent.commitment,
        "exact_input_view_sha256": exact_input_view_sha256,
    }


__all__ = [
    "ANCESTRY_STATES",
    "AssertionRecord",
    "BINDING_VERSION",
    "CommitmentError",
    "EnvelopeValidationError",
    "INTEGRITY_LEVELS",
    "IdentityReplayError",
    "POLICY_VERSION",
    "PinError",
    "ProvenanceError",
    "ProvenanceRegistry",
    "ReclamationDisabled",
    "ROOT_DERIVATION",
    "SCHEMA_SEMANTICS_BYTES",
    "SCHEMA_SEMANTICS_SHA256",
    "SCHEMA_VERSION",
    "TransformerRule",
    "VerificationPin",
    "VerificationResult",
    "authoritative_envelope",
    "base_envelope",
    "canonical_bytes",
    "canonical_envelope_bytes",
    "canonical_hash",
    "input_binding",
    "parse_envelope",
    "parse_json",
    "provenance_commitment",
    "root_binding",
    "sha256_hex",
    "validate_envelope",
]
