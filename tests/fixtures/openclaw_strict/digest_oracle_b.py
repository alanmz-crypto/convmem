"""Digest/ID oracle B — independent LP/H with NFC + field grammar (T0b).

Builds length-prefix bytes without struct.pack. Same normative algorithm as
digest_oracle; independent implementation. Prefixes are derived from kind —
no caller-supplied kind/prefix minting.
"""
# pylint: disable=R0801  # independent digest oracle; sharing would couple digest B to peers

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Sequence

TAG_LOGICAL = "convmem-logical-id-v2"
TAG_ASSERTION = "convmem-assertion-id-v2"
TAG_SCAN = "convmem-fixture-scan-event-v1"

SUBJECT_PREFIX = {
    "finding": "find2_",
    "decision": "choice2_",
    "verification": "check2_",
}
RECORD_PREFIX = {
    "observation": "obs2_",
    "decision": "dec2_",
    "verification": "ver2_",
}

PRODUCER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,15}$")
EVENT_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
PUBLIC_REF_RE = re.compile(r"^[0-9a-f]{32}$")
STORED_ID_RE = re.compile(
    r"^(?:(?:obs2|dec2|ver2)_[a-f0-9]{64}|(?:dec_prop|obs|dec|ver)_[A-Za-z0-9_.-]+)$"
)
HANDLE_RE = re.compile(
    r"^cm1\.[a-f0-9]{32}\.(?:(?:obs2|dec2|ver2)_[a-f0-9]{64}|(?:dec_prop|obs|dec|ver)_[A-Za-z0-9_.-]+)$"
)
SHA256_LABELED_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class DigestOracleBError(ValueError):
    """Oracle B rejection."""


def _reject_surrogates(value: str) -> None:
    for ch in value:
        o = ord(ch)
        if 0xD800 <= o <= 0xDFFF:
            raise DigestOracleBError("surrogate")


def _require_already_nfc(value: str, *, field: str) -> None:
    if not isinstance(value, str):
        raise DigestOracleBError(f"not_string:{field}")
    _reject_surrogates(value)
    if value != unicodedata.normalize("NFC", value):
        raise DigestOracleBError(f"non_nfc:{field}")


def _reject_float(value: Any, *, field: str) -> None:
    if isinstance(value, float):  # reject float; bool/int are not floats
        raise DigestOracleBError(f"float_forbidden:{field}")


def _lp(value: str) -> bytes:
    if not isinstance(value, str):
        raise DigestOracleBError("lp_not_string")
    _reject_surrogates(value)
    raw = unicodedata.normalize("NFC", value).encode("utf-8")
    n = len(raw)
    if n > 0xFFFFFFFF:
        raise DigestOracleBError("lp_too_long")
    return bytes([(n >> 24) & 255, (n >> 16) & 255, (n >> 8) & 255, n & 255]) + raw


def lp(value: str) -> bytes:
    return _lp(value)


def H(tag: str, fields: Sequence[str]) -> str:  # pylint: disable=C0103  # protocol hash primitive name; oracle parity
    if not isinstance(tag, str):
        raise DigestOracleBError("tag_not_string")
    try:
        tag.encode("ascii")
    except UnicodeEncodeError as exc:
        raise DigestOracleBError("tag_not_ascii") from exc
    buf = bytearray(tag.encode("ascii"))
    buf.append(0)
    for field in fields:
        buf.extend(_lp(field))
    return hashlib.sha256(bytes(buf)).hexdigest()


def _H_fixed(tag: str, fields: Sequence[str]) -> str:  # pylint: disable=C0103  # protocol fixed-hash primitive name; oracle parity
    if tag not in {TAG_LOGICAL, TAG_ASSERTION, TAG_SCAN}:
        raise DigestOracleBError(f"unknown_tag:{tag}")
    buf = bytearray(tag.encode("ascii"))
    buf.append(0)
    for field in fields:
        buf.extend(_lp(field))
    return hashlib.sha256(bytes(buf)).hexdigest()


def encode_canonical_bytes(value: Any) -> bytes:
    def sort_tree(node: Any, path: str) -> Any:
        _reject_float(node, field=path)
        if isinstance(node, str):
            _reject_surrogates(node)
            return node
        if isinstance(node, dict):
            return {k: sort_tree(node[k], f"{path}.{k}") for k in sorted(node.keys())}
        if isinstance(node, list):
            return [sort_tree(x, f"{path}[{i}]") for i, x in enumerate(node)]
        return node

    ordered = sort_tree(value, "$")
    return json.dumps(
        ordered,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=False,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_labeled(data: bytes) -> str:
    return f"sha256:{sha256_hex(data)}"


def _validate_site_normalized(site: str) -> str:
    _require_already_nfc(site, field="authority_site")
    if not site or site != site.lower():
        raise DigestOracleBError("authority_site_not_normalized")
    if "_" in site or "/" in site or ":" in site or "@" in site or " " in site:
        raise DigestOracleBError("authority_site_grammar")
    if site.startswith(".") or site.endswith(".") or ".." in site:
        raise DigestOracleBError("authority_site_grammar")
    return site


def owner_digest(*, scope_sha256: str, registry_sha256: str, project_binding_id: str) -> str:
    _require_already_nfc(project_binding_id, field="project_binding_id")
    if not SHA256_LABELED_RE.fullmatch(scope_sha256):
        raise DigestOracleBError("scope_sha256_grammar")
    if not SHA256_LABELED_RE.fullmatch(registry_sha256):
        raise DigestOracleBError("registry_sha256_grammar")
    obj = {
        "schema": "convmem.strict-owner.v1",
        "scope_sha256": scope_sha256,
        "registry_sha256": registry_sha256,
        "project_binding_id": project_binding_id,
    }
    return sha256_labeled(encode_canonical_bytes(obj))


def fixture_scan_event_id(
    *, source_registration_id: str, source_identity: str, event_key: str
) -> str:
    _require_already_nfc(source_registration_id, field="source_registration_id")
    _require_already_nfc(source_identity, field="source_identity")
    _require_already_nfc(event_key, field="event_key")
    if not 1 <= len(event_key) <= 256 or not EVENT_KEY_RE.fullmatch(event_key):
        raise DigestOracleBError("event_key_grammar")
    return "evt_" + _H_fixed(
        TAG_SCAN, (source_registration_id, source_identity, event_key)
    )


def logical_id(
    *,
    project_binding_id: str,
    source_identity: str,
    authority_site: str,
    producer: str,
    logical_key: str,
    subject_kind: str,
    target_assertion_id_or_empty: str = "",
) -> str:
    _require_already_nfc(project_binding_id, field="project_binding_id")
    _require_already_nfc(source_identity, field="source_identity")
    site = _validate_site_normalized(authority_site)
    _require_already_nfc(producer, field="producer")
    if not PRODUCER_RE.fullmatch(producer):
        raise DigestOracleBError("producer_grammar")
    _require_already_nfc(logical_key, field="logical_key")
    if not 1 <= len(logical_key) <= 256:
        raise DigestOracleBError("logical_key_length")
    if subject_kind not in SUBJECT_PREFIX:
        raise DigestOracleBError(f"subject_kind:{subject_kind}")
    prefix = SUBJECT_PREFIX[subject_kind]
    if subject_kind == "verification":
        if not target_assertion_id_or_empty:
            raise DigestOracleBError("verification_requires_target")
        _require_already_nfc(
            target_assertion_id_or_empty, field="target_assertion_id_or_empty"
        )
        if not re.fullmatch(
            r"(?:obs2|dec2|ver2)_[a-f0-9]{64}", target_assertion_id_or_empty
        ):
            raise DigestOracleBError("target_assertion_grammar")
    else:
        if target_assertion_id_or_empty != "":
            raise DigestOracleBError("non_verification_target_must_be_empty")
    digest = _H_fixed(
        TAG_LOGICAL,
        (
            project_binding_id,
            source_identity,
            site,
            producer,
            logical_key,
            subject_kind,
            target_assertion_id_or_empty,
        ),
    )
    return f"{prefix}{digest}"


def assertion_id(
    *,
    project_binding_id: str,
    source_registration_id: str,
    source_event_id: str,
    record_kind: str,
    logical_id_value: str,
) -> str:
    _require_already_nfc(project_binding_id, field="project_binding_id")
    _require_already_nfc(source_registration_id, field="source_registration_id")
    _require_already_nfc(source_event_id, field="source_event_id")
    _require_already_nfc(logical_id_value, field="logical_id")
    if record_kind not in RECORD_PREFIX:
        raise DigestOracleBError(f"record_kind:{record_kind}")
    prefix = RECORD_PREFIX[record_kind]
    expected_logical = {
        "observation": "find2_",
        "decision": "choice2_",
        "verification": "check2_",
    }[record_kind]
    if not logical_id_value.startswith(expected_logical):
        raise DigestOracleBError("kind_prefix_mismatch")
    if not re.fullmatch(r"evt_[0-9a-f]{64}", source_event_id):
        raise DigestOracleBError("source_event_id_grammar")
    digest = _H_fixed(
        TAG_ASSERTION,
        (
            project_binding_id,
            source_registration_id,
            source_event_id,
            record_kind,
            logical_id_value,
        ),
    )
    return f"{prefix}{digest}"


def citation_ref(
    *,
    project_binding_id: str,
    assertion_id_value: str,
    provenance_commitment: str,
) -> str:
    _require_already_nfc(project_binding_id, field="project_binding_id")
    _require_already_nfc(assertion_id_value, field="assertion_id")
    if not SHA256_LABELED_RE.fullmatch(provenance_commitment):
        raise DigestOracleBError("provenance_commitment_grammar")
    obj = {
        "schema": "convmem.strict-citation-ref.v1",
        "project_binding_id": project_binding_id,
        "assertion_id": assertion_id_value,
        "provenance_commitment": provenance_commitment,
    }
    return "cite1_" + sha256_hex(encode_canonical_bytes(obj))


def receipt_ref(receipt_payload_sha256_hex64: str) -> str:
    if receipt_payload_sha256_hex64.startswith("sha256:"):
        receipt_payload_sha256_hex64 = receipt_payload_sha256_hex64[len("sha256:") :]
    if not HEX64_RE.fullmatch(receipt_payload_sha256_hex64):
        raise DigestOracleBError("receipt_payload_hex_grammar")
    return "capture_" + receipt_payload_sha256_hex64


def public_handle(*, public_ref: str, stored_external_id: str) -> str:
    _require_already_nfc(public_ref, field="public_ref")
    _require_already_nfc(stored_external_id, field="stored_external_id")
    if not PUBLIC_REF_RE.fullmatch(public_ref):
        raise DigestOracleBError("public_ref_grammar")
    if not STORED_ID_RE.fullmatch(stored_external_id):
        raise DigestOracleBError("stored_external_id_grammar")
    handle = f"cm1.{public_ref}.{stored_external_id}"
    if len(handle) > 200:
        raise DigestOracleBError("handle_too_long")
    if not HANDLE_RE.fullmatch(handle):
        raise DigestOracleBError("handle_grammar")
    return handle


def semantic_digest_bytes(record: dict[str, Any]) -> bytes:
    excluded = {
        "semantic_sha256",
        "payload_sha256",
        "decision_disposition_ref",
        "supersession_disposition_ref",
        "provenance_envelope",
    }
    body = {k: v for k, v in record.items() if k not in excluded}
    return encode_canonical_bytes(body)


def payload_digest_bytes(record: dict[str, Any]) -> bytes:
    body = {k: v for k, v in record.items() if k != "payload_sha256"}
    return encode_canonical_bytes(body)


def exclude_named_field_bytes(obj: dict[str, Any], field: str) -> bytes:
    """Parent self-hash rule: canonical bytes excluding only the named payload-hash field."""
    if not isinstance(obj, dict):
        raise DigestOracleBError("exclude_not_object")
    if not isinstance(field, str) or not field:
        raise DigestOracleBError("exclude_field_invalid")
    body = {k: v for k, v in obj.items() if k != field}
    return encode_canonical_bytes(body)


def labeled_self_hash(obj: dict[str, Any], field: str) -> str:
    """sha256: hex of exclude_named_field_bytes(obj, field)."""
    return sha256_labeled(exclude_named_field_bytes(obj, field))
