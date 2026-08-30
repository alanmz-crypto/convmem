"""Unforgeable possession tokens gating trusted R2b v2 authority transitions."""

from __future__ import annotations

import hashlib
import inspect
import json
import secrets
from enum import Enum
from typing import Any

from eval_corpus.r2b_v2.lock_custodian import LockCustodianError


class AuthorityCapabilityError(RuntimeError):
    """Capability issuance, validation, or consumption failure."""


class MintPhase(str, Enum):
    CENSUS = "census"
    LEASE = "lease"
    SOURCE = "source"


_TRUST_CLASS_PRODUCTION = "production"
_TRUST_CLASS_HERMETIC = "hermetic_test"

_CAPABILITY_ISSUER_SECRET = secrets.token_bytes(32)

_CANONICAL_ISSUER_MODULES = frozenset(
    {
        "eval_corpus.r2b_v2.coverage.proof",
        "eval_corpus.r2b_v2.lease",
    }
)

_consumed_capability_ids: set[str] = set()


def _binding_digest(phase: MintPhase, payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"phase": phase.value, **payload},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _assert_canonical_issuer() -> None:
    frame = inspect.currentframe()
    if frame is not None:
        frame = frame.f_back
    if frame is not None:
        frame = frame.f_back
    while frame is not None:
        module = frame.f_globals.get("__name__", "")
        if module in _CANONICAL_ISSUER_MODULES:
            return
        frame = frame.f_back
    raise AuthorityCapabilityError(
        "capability issuance forbidden outside canonical lifecycle"
    )


class AuthorityMintCapability:
    """Single-use possession token — not constructible or copyable by callers."""

    __slots__ = (
        "_binding_digest",
        "_capability_id",
        "_census_stage",
        "_issuer_secret",
        "_phase",
        "_trust_class",
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise AuthorityCapabilityError(
            "AuthorityMintCapability cannot be constructed by callers"
        )

    def __bool__(self) -> bool:
        raise AuthorityCapabilityError(
            "AuthorityMintCapability is not reducible to a boolean authority claim"
        )

    def __copy__(self) -> AuthorityMintCapability:
        raise AuthorityCapabilityError("AuthorityMintCapability cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]) -> AuthorityMintCapability:
        raise AuthorityCapabilityError("AuthorityMintCapability cannot be deep-copied")

    def __reduce__(self) -> Any:
        raise AuthorityCapabilityError("AuthorityMintCapability is not serializable")

    @classmethod
    def _issue(
        cls,
        *,
        phase: MintPhase,
        binding: dict[str, Any],
        trust_class: str,
    ) -> AuthorityMintCapability:
        _assert_canonical_issuer()
        if trust_class not in (_TRUST_CLASS_PRODUCTION, _TRUST_CLASS_HERMETIC):
            raise AuthorityCapabilityError("invalid trust class for capability issuance")
        cap = object.__new__(cls)
        cap._issuer_secret = _CAPABILITY_ISSUER_SECRET  # pylint: disable=attribute-defined-outside-init
        cap._phase = phase  # pylint: disable=attribute-defined-outside-init
        cap._binding_digest = _binding_digest(phase, binding)  # pylint: disable=attribute-defined-outside-init
        cap._capability_id = secrets.token_hex(16)  # pylint: disable=attribute-defined-outside-init
        cap._trust_class = trust_class  # pylint: disable=attribute-defined-outside-init
        cap._census_stage = 0  # pylint: disable=attribute-defined-outside-init
        return cap

    def _validate_binding(self, *, phase: MintPhase, binding: dict[str, Any]) -> None:
        if self._issuer_secret is not _CAPABILITY_ISSUER_SECRET:
            raise AuthorityCapabilityError("forged capability issuer secret")
        if self._phase is not phase:
            raise AuthorityCapabilityError("capability phase mismatch")
        expected = _binding_digest(phase, binding)
        if self._binding_digest != expected:
            raise AuthorityCapabilityError("capability binding mismatch")
        if self._capability_id in _consumed_capability_ids:
            raise AuthorityCapabilityError("capability already consumed or replayed")

    def _consume_census_register(self, *, binding: dict[str, Any]) -> str:
        self._validate_binding(phase=MintPhase.CENSUS, binding=binding)
        if self._census_stage != 0:
            raise AuthorityCapabilityError("census capability register stage invalid")
        self._census_stage = 1
        return self._trust_class

    def _consume_census_mint(self, *, binding: dict[str, Any]) -> str:
        self._validate_binding(phase=MintPhase.CENSUS, binding=binding)
        if self._census_stage != 1:
            raise AuthorityCapabilityError("census capability mint stage invalid")
        self._census_stage = 2
        _consumed_capability_ids.add(self._capability_id)
        return self._trust_class

    def _consume_lease(self, *, binding: dict[str, Any]) -> str:
        self._validate_binding(phase=MintPhase.LEASE, binding=binding)
        _consumed_capability_ids.add(self._capability_id)
        return self._trust_class

    def _consume_source(self, *, binding: dict[str, Any]) -> str:
        self._validate_binding(phase=MintPhase.SOURCE, binding=binding)
        _consumed_capability_ids.add(self._capability_id)
        return self._trust_class

    @property
    def trust_class(self) -> str:
        if self._issuer_secret is not _CAPABILITY_ISSUER_SECRET:
            raise AuthorityCapabilityError("forged capability issuer secret")
        return self._trust_class


def issue_census_capability(
    *,
    coverage_digest: str,
    gate_identity: str,
    code_revision: str,
    trust_class: str,
) -> AuthorityMintCapability:
    return AuthorityMintCapability._issue(  # pylint: disable=protected-access
        phase=MintPhase.CENSUS,
        binding={
            "coverage_digest": coverage_digest,
            "gate_identity": gate_identity,
            "code_revision": code_revision,
        },
        trust_class=trust_class,
    )


def issue_lease_capability(
    *,
    custodian_id: str,
    gate_path: str,
    gate_inode: int,
    run_id: str,
    grant_digest: str,
    authority_digest: str,
    trust_class: str,
) -> AuthorityMintCapability:
    return AuthorityMintCapability._issue(  # pylint: disable=protected-access
        phase=MintPhase.LEASE,
        binding={
            "custodian_id": custodian_id,
            "gate_path": gate_path,
            "gate_inode": gate_inode,
            "run_id": run_id,
            "grant_digest": grant_digest,
            "authority_digest": authority_digest,
        },
        trust_class=trust_class,
    )


def issue_source_capability(
    *,
    lease_handle_id: str,
    coverage_handle_id: str,
    open_evidence_digest: str,
    trust_class: str,
) -> AuthorityMintCapability:
    return AuthorityMintCapability._issue(  # pylint: disable=protected-access
        phase=MintPhase.SOURCE,
        binding={
            "lease_handle_id": lease_handle_id,
            "coverage_handle_id": coverage_handle_id,
            "open_evidence_digest": open_evidence_digest,
        },
        trust_class=trust_class,
    )


def verify_live_custodian_lock(custodian: Any) -> None:
    try:
        custodian.verify()
    except LockCustodianError as exc:
        raise LockCustodianError(
            "custodian no longer possesses exclusive kernel lock"
        ) from exc


def reset_capabilities_for_tests() -> None:
    _consumed_capability_ids.clear()


def trust_class_for_gate_policy(policy_class: str) -> str:
    if policy_class == "test_fixture":
        return _TRUST_CLASS_HERMETIC
    if policy_class == "production":
        return _TRUST_CLASS_PRODUCTION
    raise AuthorityCapabilityError("untrusted gate policy class")
