"""Strict bound-read scope, registry, selectors, and row authorization (T1)."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import idna

from canonical_json import canonical_json_bytes
from domains import domain_matches as _domain_matches_child

OMITTED: object = object()

_DOMAIN_RE = re.compile(r"^[a-z0-9_]+(?:\.[a-z0-9_]+)*$")
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_BINDING_ID_RE = re.compile(r"^project:[A-Za-z0-9._:-]+:v[0-9]+$")
_PUBLIC_REF_RE = re.compile(r"^[0-9a-f]{32}$")
_LINEAGE_RE = re.compile(r"^[0-9a-f]{32}$")
_ISSUER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_PRODUCER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,15}$")
_SOURCE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SOURCE_CLASS_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,63}$")

IDENTITY_MATCH_EXACT = "exact"
EVENT_ID_RESOLVER_FIXTURE = "fixture_scan_event_v1"
SITE_MODES = frozenset({"exact", "not_applicable"})
CAPTURE_CLASSES = frozenset({"synthetic_fixture", "controlled_capture"})

FORBIDDEN_SOURCE_KEYS = frozenset(
    {
        "_convmem_auth",
        "_convmem_state",
    }
)
FORBIDDEN_SOURCE_PREFIXES = ("_convmem_auth", "_convmem_state")
AUTHORITY_LIKE_KEYS = frozenset(
    {
        "project_binding_id",
        "source_registration_id",
        "authority_site",
        "authority_domain",
        "authority_snapshot",
        "authority_manifest_sha256",
        "disposition_sha256",
        "semantic_sha256",
        "payload_sha256",
        "logical_id",
        "assertion_id",
        "source_event_id",
        "provenance_commitment",
        "decision_disposition_ref",
        "supersession_disposition_ref",
    }
)


class BoundScopeError(ValueError):
    """Fail-closed scope/registry/selector/authorization error."""


def _reject_surrogates(text: str, *, field: str) -> None:
    for ch in text:
        code = ord(ch)
        if 0xD800 <= code <= 0xDFFF:
            raise BoundScopeError(f"surrogate:{field}")


def require_already_nfc(text: Any, *, field: str) -> str:
    """Reject non-string and noncanonical NFC. Never repairs."""

    if not isinstance(text, str):
        raise BoundScopeError(f"not_string:{field}")
    _reject_surrogates(text, field=field)
    if text != unicodedata.normalize("NFC", text):
        raise BoundScopeError(f"non_nfc:{field}")
    return text


def canonicalize_nfc(text: str) -> str:
    """Require already-canonical NFC input; return unchanged (no repair)."""

    return require_already_nfc(text, field="nfc")


def _reject_floats(value: Any, *, path: str = "$") -> None:
    if isinstance(value, float):
        raise BoundScopeError(f"float_forbidden:{path}")
    if isinstance(value, dict):
        for key, child in value.items():
            _reject_floats(child, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _reject_floats(child, path=f"{path}[{index}]")


def _strict_canonical_bytes(value: Any) -> bytes:
    def _validate(obj: Any) -> None:
        _reject_floats(obj)

    return canonical_json_bytes(value, validate=_validate, error_type=BoundScopeError)


def sha256_digest(data: bytes | str) -> str:
    if isinstance(data, str):
        require_already_nfc(data, field="sha256_input")
        raw = data.encode("utf-8")
    else:
        if not isinstance(data, (bytes, bytearray)):
            raise BoundScopeError("sha256_input_type")
        raw = bytes(data)
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def parse_strict_domain(raw: Any) -> str:
    text = require_already_nfc(raw, field="domain")
    if not text or text != text.lower() or not _DOMAIN_RE.fullmatch(text):
        raise BoundScopeError("domain_invalid")
    if text == "general":
        raise BoundScopeError("domain_general_widening")
    return text


def domain_matches(requested_or_row: str, bound_or_effective: str) -> bool:
    """Containment: child-or-equal of the second argument (Architecture §6.3/6.4)."""

    require_already_nfc(requested_or_row, field="domain_child")
    require_already_nfc(bound_or_effective, field="domain_parent")
    return _domain_matches_child(requested_or_row, bound_or_effective)


def normalize_authority_site(raw: Any) -> str:
    """UTS #46 non-transitional / IDNA2008 / STD3 bare-hostname normalizer.

    Rejects whitespace, non-NFC, schemes, ports, user-info, paths, empty labels,
    and underscores. Removes at most one terminal DNS dot. Does not strip or
    otherwise repair noncanonical input.
    """

    text = require_already_nfc(raw, field="site")
    if not text:
        raise BoundScopeError("site_invalid")
    if text != text.strip():
        raise BoundScopeError("site_whitespace")
    if any(ch.isspace() for ch in text):
        raise BoundScopeError("site_whitespace")
    if "://" in text or "/" in text or "?" in text or "#" in text:
        raise BoundScopeError("site_invalid")
    if "@" in text or ":" in text:
        raise BoundScopeError("site_invalid")
    if "_" in text:
        raise BoundScopeError("site_invalid")
    lowered = text
    if lowered.endswith("."):
        lowered = lowered[:-1]
        if lowered.endswith("."):
            raise BoundScopeError("site_invalid")
    if not lowered or lowered.startswith(".") or ".." in lowered:
        raise BoundScopeError("site_invalid")
    labels = lowered.split(".")
    if any(not label for label in labels):
        raise BoundScopeError("site_invalid")
    try:
        encoded = idna.encode(lowered, uts46=True, std3_rules=True, transitional=False)
    except idna.IDNAError as exc:
        raise BoundScopeError("site_invalid") from exc
    ascii_host = encoded.decode("ascii")
    if not ascii_host or ascii_host != ascii_host.lower():
        raise BoundScopeError("site_invalid")
    if "_" in ascii_host or ascii_host.endswith(".") or ".." in ascii_host:
        raise BoundScopeError("site_invalid")
    return ascii_host


def _open_immutable_json(path: Path) -> dict[str, Any]:
    if not path.is_absolute():
        raise BoundScopeError("path_must_be_absolute")
    if path.is_symlink() or not path.is_file():
        raise BoundScopeError("path_not_regular_file")
    st = path.stat()
    if st.st_mode & 0o222:
        raise BoundScopeError("path_writable")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BoundScopeError("path_not_utf8") from exc
    try:
        obj = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise BoundScopeError("path_json_invalid") from exc
    if not isinstance(obj, dict):
        raise BoundScopeError("path_json_object_required")
    _reject_floats(obj)
    return obj


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise BoundScopeError(f"duplicate_key:{key}")
        out[key] = value
    return out


def _require_closed_keys(raw: Mapping[str, Any], required: set[str], *, label: str) -> None:
    if set(raw) != required:
        raise BoundScopeError(f"{label}_keys")


@dataclass(frozen=True, slots=True)
class SourceRegistration:
    id: str
    source_class: str
    source_identity: str
    identity_match: str
    authorization_domain: str
    site: str | None
    event_id_resolver: str


@dataclass(frozen=True, slots=True)
class CaptureIssuer:
    issuer_id: str
    capture_class: str
    enrollment_sha256: str
    receipt_root: str
    source_registration_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VerificationProducer:
    source_registration_id: str
    producer: str
    transformer_identity: str
    transformer_version: str
    transformer_artifact_sha256: str
    recipe_sha256: str
    capture_class: str


@dataclass(frozen=True, slots=True)
class ProjectBinding:  # pylint: disable=R0902  # attributes mirror project-binding schema fields
    id: str
    public_ref: str
    project: str
    domain_root: str
    site_mode: str
    site: str | None
    non_expanding_roots: tuple[str, ...]
    source_registrations: tuple[SourceRegistration, ...]
    lineage_id: str
    capture_issuers: tuple[CaptureIssuer, ...]
    verification_producers: tuple[VerificationProducer, ...]


@dataclass(frozen=True, slots=True)
class BoundReadScope:  # pylint: disable=R0902  # attributes mirror bound-read-scope schema fields
    project: str
    allowed_project_bindings: tuple[str, ...]
    domain: str
    site_mode: str
    site: str | None
    authority_snapshot: str
    serving_projection: str
    max_snapshot_age_seconds: int
    scope_sha256: str


@dataclass(frozen=True, slots=True)
class ProjectBindingRegistry:
    bindings: tuple[ProjectBinding, ...]
    revision: str
    registry_sha256: str

    def binding(self, binding_id: str) -> ProjectBinding:
        require_already_nfc(binding_id, field="binding_id")
        for item in self.bindings:
            if item.id == binding_id:
                return item
        raise BoundScopeError("binding_unknown")

    def by_public_ref(self, public_ref: str) -> ProjectBinding | None:
        require_already_nfc(public_ref, field="public_ref")
        matches = [b for b in self.bindings if b.public_ref == public_ref]
        if len(matches) > 1:
            raise BoundScopeError("public_ref_ambiguous")
        return matches[0] if matches else None


@dataclass(frozen=True, slots=True)
class EffectiveSelectors:
    project: str
    site: str | None
    site_mode: str
    domain: str
    binding_id: str


@dataclass(frozen=True, slots=True)
class ResolvedScope:
    scope: BoundReadScope
    registry: ProjectBindingRegistry
    binding: ProjectBinding
    owner_digest: str


def load_bound_read_scope(path: str | Path) -> BoundReadScope:
    obj = _open_immutable_json(Path(path))
    required = {
        "schema",
        "project",
        "allowed_project_bindings",
        "domain",
        "site_mode",
        "site",
        "authority_snapshot",
        "serving_projection",
        "max_snapshot_age_seconds",
    }
    _require_closed_keys(obj, required, label="scope")
    if obj["schema"] != "convmem.bound-read-scope.v2":
        raise BoundScopeError("scope_schema")
    project = require_already_nfc(obj["project"], field="scope.project")
    if not project:
        raise BoundScopeError("scope_project")
    bindings = obj["allowed_project_bindings"]
    if not isinstance(bindings, list) or len(bindings) != 1:
        raise BoundScopeError("scope_bindings_cardinality")
    binding_id = require_already_nfc(bindings[0], field="scope.binding_id")
    if not _BINDING_ID_RE.fullmatch(binding_id):
        raise BoundScopeError("scope_binding_id")
    domain = parse_strict_domain(obj["domain"])
    site_mode = obj["site_mode"]
    if site_mode not in SITE_MODES:
        raise BoundScopeError("scope_site_mode")
    site_raw = obj["site"]
    if site_mode == "exact":
        site = normalize_authority_site(site_raw)
    else:
        if site_raw is not None:
            raise BoundScopeError("scope_site_must_be_null")
        site = None
    for field in ("authority_snapshot", "serving_projection"):
        value = require_already_nfc(obj[field], field=f"scope.{field}")
        if not value:
            raise BoundScopeError(f"scope_{field}")
    age = obj["max_snapshot_age_seconds"]
    if not isinstance(age, int) or isinstance(age, bool) or not 60 <= age <= 86400:
        raise BoundScopeError("scope_age")
    digest = sha256_digest(_strict_canonical_bytes(obj))
    return BoundReadScope(
        project=project,
        allowed_project_bindings=(binding_id,),
        domain=domain,
        site_mode=site_mode,
        site=site,
        authority_snapshot=obj["authority_snapshot"],
        serving_projection=obj["serving_projection"],
        max_snapshot_age_seconds=age,
        scope_sha256=digest,
    )


def _parse_source_registration(raw: Mapping[str, Any]) -> SourceRegistration:
    required = {
        "id",
        "source_class",
        "source_identity",
        "identity_match",
        "authorization_domain",
        "site",
        "event_id_resolver",
    }
    _require_closed_keys(raw, required, label="source_registration")
    source_id = require_already_nfc(raw["id"], field="source_registration.id")
    if not _SOURCE_ID_RE.fullmatch(source_id):
        raise BoundScopeError("source_registration_id")
    source_class = require_already_nfc(raw["source_class"], field="source_class")
    if not _SOURCE_CLASS_RE.fullmatch(source_class):
        raise BoundScopeError("source_class")
    source_identity = require_already_nfc(raw["source_identity"], field="source_identity")
    if not 1 <= len(source_identity) <= 512:
        raise BoundScopeError("source_identity")
    identity_match = raw["identity_match"]
    if identity_match != IDENTITY_MATCH_EXACT:
        raise BoundScopeError("identity_match")
    event_resolver = raw["event_id_resolver"]
    if event_resolver != EVENT_ID_RESOLVER_FIXTURE:
        raise BoundScopeError("event_id_resolver")
    auth_domain = parse_strict_domain(raw["authorization_domain"])
    site_raw = raw["site"]
    if site_raw is None:
        site = None
    else:
        site = normalize_authority_site(site_raw)
    return SourceRegistration(
        id=source_id,
        source_class=source_class,
        source_identity=source_identity,
        identity_match=identity_match,
        authorization_domain=auth_domain,
        site=site,
        event_id_resolver=event_resolver,
    )


def _parse_capture_issuer(raw: Mapping[str, Any]) -> CaptureIssuer:
    required = {
        "issuer_id",
        "capture_class",
        "enrollment_sha256",
        "receipt_root",
        "source_registration_ids",
    }
    _require_closed_keys(raw, required, label="capture_issuer")
    issuer_id = require_already_nfc(raw["issuer_id"], field="issuer_id")
    if not _ISSUER_ID_RE.fullmatch(issuer_id):
        raise BoundScopeError("capture_issuer_id")
    capture_class = raw["capture_class"]
    if capture_class not in CAPTURE_CLASSES:
        raise BoundScopeError("capture_class")
    enrollment = require_already_nfc(raw["enrollment_sha256"], field="enrollment_sha256")
    if not _SHA_RE.fullmatch(enrollment):
        raise BoundScopeError("capture_enrollment_sha")
    receipt_root = require_already_nfc(raw["receipt_root"], field="receipt_root")
    if not receipt_root.startswith("/"):
        raise BoundScopeError("receipt_root")
    src_ids = raw["source_registration_ids"]
    if not isinstance(src_ids, list):
        raise BoundScopeError("capture_source_ids")
    parsed_ids: list[str] = []
    for item in src_ids:
        parsed_ids.append(require_already_nfc(item, field="capture_source_id"))
    if parsed_ids != sorted(set(parsed_ids)):
        raise BoundScopeError("capture_source_ids_order")
    return CaptureIssuer(
        issuer_id=issuer_id,
        capture_class=capture_class,
        enrollment_sha256=enrollment,
        receipt_root=receipt_root,
        source_registration_ids=tuple(parsed_ids),
    )


def _parse_verification_producer(raw: Mapping[str, Any]) -> VerificationProducer:
    required = {
        "source_registration_id",
        "producer",
        "transformer_identity",
        "transformer_version",
        "transformer_artifact_sha256",
        "recipe_sha256",
        "capture_class",
    }
    _require_closed_keys(raw, required, label="verification_producer")
    source_registration_id = require_already_nfc(
        raw["source_registration_id"], field="verification_producer.source"
    )
    producer = require_already_nfc(raw["producer"], field="producer")
    if not _PRODUCER_RE.fullmatch(producer):
        raise BoundScopeError("verification_producer")
    transformer_identity = require_already_nfc(
        raw["transformer_identity"], field="transformer_identity"
    )
    transformer_version = require_already_nfc(
        raw["transformer_version"], field="transformer_version"
    )
    if not transformer_identity or not transformer_version:
        raise BoundScopeError("transformer_fields")
    artifact = require_already_nfc(
        raw["transformer_artifact_sha256"], field="transformer_artifact_sha256"
    )
    recipe = require_already_nfc(raw["recipe_sha256"], field="recipe_sha256")
    if not _SHA_RE.fullmatch(artifact) or not _SHA_RE.fullmatch(recipe):
        raise BoundScopeError("verification_sha")
    capture_class = raw["capture_class"]
    if capture_class not in CAPTURE_CLASSES:
        raise BoundScopeError("verification_capture_class")
    return VerificationProducer(
        source_registration_id=source_registration_id,
        producer=producer,
        transformer_identity=transformer_identity,
        transformer_version=transformer_version,
        transformer_artifact_sha256=artifact,
        recipe_sha256=recipe,
        capture_class=capture_class,
    )



def _parse_project_binding(
    raw: Any, *, seen_public_refs: set[str]
) -> ProjectBinding:
    """Parse one registry binding object into a ProjectBinding."""

    if not isinstance(raw, dict):
        raise BoundScopeError("binding_type")
    required = {
        "id",
        "public_ref",
        "project",
        "domain_root",
        "site_mode",
        "site",
        "non_expanding_roots",
        "source_registrations",
        "lineage_id",
        "capture_issuers",
        "verification_producers",
    }
    _require_closed_keys(raw, required, label="binding")
    binding_id = require_already_nfc(raw["id"], field="binding.id")
    if not _BINDING_ID_RE.fullmatch(binding_id):
        raise BoundScopeError("binding_id")
    public_ref = require_already_nfc(raw["public_ref"], field="public_ref")
    if not _PUBLIC_REF_RE.fullmatch(public_ref):
        raise BoundScopeError("public_ref")
    if public_ref in seen_public_refs:
        raise BoundScopeError("public_ref_duplicate")
    project = require_already_nfc(raw["project"], field="binding.project")
    if not project:
        raise BoundScopeError("binding_project")
    domain_root = parse_strict_domain(raw["domain_root"])
    site_mode = raw["site_mode"]
    if site_mode not in SITE_MODES:
        raise BoundScopeError("binding_site_mode")
    site_raw = raw["site"]
    if site_mode == "exact":
        site = normalize_authority_site(site_raw)
    else:
        if site_raw is not None:
            raise BoundScopeError("binding_site_must_be_null")
        site = None
    lineage_id = require_already_nfc(raw["lineage_id"], field="lineage_id")
    if not _LINEAGE_RE.fullmatch(lineage_id):
        raise BoundScopeError("binding_lineage")
    roots = raw["non_expanding_roots"]
    if not isinstance(roots, list):
        raise BoundScopeError("non_expanding_roots")
    parsed_roots = [require_already_nfc(x, field="non_expanding_root") for x in roots]
    if parsed_roots != sorted(set(parsed_roots)):
        raise BoundScopeError("non_expanding_roots_order")
    regs_raw = raw["source_registrations"]
    if not isinstance(regs_raw, list) or not regs_raw:
        raise BoundScopeError("source_registrations")
    registrations = tuple(_parse_source_registration(r) for r in regs_raw)
    reg_ids = [r.id for r in registrations]
    if reg_ids != sorted(reg_ids) or len(reg_ids) != len(set(reg_ids)):
        raise BoundScopeError("source_registrations_order")
    for reg in registrations:
        if not domain_matches(reg.authorization_domain, domain_root):
            raise BoundScopeError("source_domain_outside_binding")
        if site_mode == "exact":
            if reg.site != site:
                raise BoundScopeError("source_site_mismatch")
        elif reg.site is not None:
            if reg.site != normalize_authority_site(reg.site):
                raise BoundScopeError("source_site_noncanonical")
    issuers_raw = raw["capture_issuers"]
    if not isinstance(issuers_raw, list):
        raise BoundScopeError("capture_issuers")
    issuers = tuple(_parse_capture_issuer(i) for i in issuers_raw)
    issuer_ids = [i.issuer_id for i in issuers]
    if issuer_ids != sorted(issuer_ids) or len(issuer_ids) != len(set(issuer_ids)):
        raise BoundScopeError("capture_issuers_order")
    for issuer in issuers:
        if issuer.capture_class != "synthetic_fixture":
            raise BoundScopeError("fixture_issuer_only")
        for src_id in issuer.source_registration_ids:
            if src_id not in reg_ids:
                raise BoundScopeError("issuer_source_unknown")
    producers_raw = raw["verification_producers"]
    if not isinstance(producers_raw, list):
        raise BoundScopeError("verification_producers")
    producers = tuple(_parse_verification_producer(prod) for prod in producers_raw)
    producer_keys = [
        (
            prod.source_registration_id,
            prod.producer,
            prod.transformer_identity,
            prod.transformer_version,
            prod.transformer_artifact_sha256,
            prod.recipe_sha256,
            prod.capture_class,
        )
        for prod in producers
    ]
    if producer_keys != sorted(set(producer_keys)):
        raise BoundScopeError("verification_producers_order")
    for producer in producers:
        if producer.source_registration_id not in reg_ids:
            raise BoundScopeError("verification_producer_source")
    return ProjectBinding(
        id=binding_id,
        public_ref=public_ref,
        project=project,
        domain_root=domain_root,
        site_mode=site_mode,
        site=site,
        non_expanding_roots=tuple(parsed_roots),
        source_registrations=registrations,
        lineage_id=lineage_id,
        capture_issuers=issuers,
        verification_producers=producers,
    )


def load_project_binding_registry(path: str | Path) -> ProjectBindingRegistry:
    obj = _open_immutable_json(Path(path))
    _require_closed_keys(obj, {"schema", "revision", "bindings"}, label="registry")
    if obj["schema"] != "convmem.project-binding-registry.v3":
        raise BoundScopeError("registry_schema")
    bindings_raw = obj["bindings"]
    if not isinstance(bindings_raw, list) or not bindings_raw:
        raise BoundScopeError("registry_bindings")
    parsed: list[ProjectBinding] = []
    public_refs: set[str] = set()
    binding_ids: list[str] = []
    for raw in bindings_raw:
        binding = _parse_project_binding(raw, seen_public_refs=public_refs)
        public_refs.add(binding.public_ref)
        binding_ids.append(binding.id)
        parsed.append(binding)
    if binding_ids != sorted(binding_ids):
        raise BoundScopeError("registry_bindings_order")
    if len(binding_ids) != len(set(binding_ids)):
        raise BoundScopeError("registry_binding_duplicate")
    without_revision = {k: v for k, v in obj.items() if k != "revision"}
    expected = sha256_digest(_strict_canonical_bytes(without_revision))
    revision = require_already_nfc(obj["revision"], field="revision")
    if revision != expected:
        raise BoundScopeError("registry_revision_mismatch")
    return ProjectBindingRegistry(
        bindings=tuple(parsed),
        revision=revision,
        registry_sha256=revision,
    )


def owner_digest(*, scope_sha256: str, registry_sha256: str, project_binding_id: str) -> str:
    require_already_nfc(scope_sha256, field="scope_sha256")
    require_already_nfc(registry_sha256, field="registry_sha256")
    require_already_nfc(project_binding_id, field="project_binding_id")
    if not _SHA_RE.fullmatch(scope_sha256) or not _SHA_RE.fullmatch(registry_sha256):
        raise BoundScopeError("owner_digest_sha")
    if not _BINDING_ID_RE.fullmatch(project_binding_id):
        raise BoundScopeError("owner_digest_binding")
    payload = {
        "schema": "convmem.strict-owner.v1",
        "scope_sha256": scope_sha256,
        "registry_sha256": registry_sha256,
        "project_binding_id": project_binding_id,
    }
    return sha256_digest(_strict_canonical_bytes(payload))


def resolve_scope(
    *,
    scope_path: str | Path,
    registry_path: str | Path,
) -> ResolvedScope:
    """Load and cross-validate scope + registry; return immutable resolved view."""

    scope = load_bound_read_scope(scope_path)
    registry = load_project_binding_registry(registry_path)
    binding_id = scope.allowed_project_bindings[0]
    binding = registry.binding(binding_id)
    if binding.project != scope.project:
        raise BoundScopeError("binding_project_mismatch")
    if binding.domain_root != scope.domain:
        raise BoundScopeError("binding_domain_root_mismatch")
    if binding.site_mode != scope.site_mode:
        raise BoundScopeError("binding_site_mode_mismatch")
    if scope.site_mode == "exact" and binding.site != scope.site:
        raise BoundScopeError("binding_site_mismatch")
    if scope.site_mode == "not_applicable" and binding.site_mode != "not_applicable":
        raise BoundScopeError("binding_site_mode_mismatch")
    digest = owner_digest(
        scope_sha256=scope.scope_sha256,
        registry_sha256=registry.registry_sha256,
        project_binding_id=binding_id,
    )
    return ResolvedScope(
        scope=scope,
        registry=registry,
        binding=binding,
        owner_digest=digest,
    )


def resolve_selectors(
    scope: BoundReadScope,
    *,
    project: Any = OMITTED,
    site: Any = OMITTED,
    domain: Any = OMITTED,
    cross_domain: Any = OMITTED,
) -> EffectiveSelectors:
    """Architecture §6.3 selector resolution. Explicit null/blank denies."""

    def _reject_blank(value: Any, name: str) -> None:
        if value is None:
            raise BoundScopeError(f"{name}_null")
        if not isinstance(value, str):
            raise BoundScopeError(f"{name}_type")
        if value != value.strip() or value.strip() == "" or any(ch.isspace() for ch in value):
            raise BoundScopeError(f"{name}_blank")

    if cross_domain is not OMITTED:
        if cross_domain is True:
            raise BoundScopeError("cross_domain_denied")
        if cross_domain is not False:
            raise BoundScopeError("cross_domain_invalid")

    if project is OMITTED:
        effective_project = scope.project
    else:
        _reject_blank(project, "project")
        require_already_nfc(project, field="project")
        if project != scope.project:
            raise BoundScopeError("project_denied")
        effective_project = scope.project

    if site is OMITTED:
        effective_site = scope.site
    else:
        _reject_blank(site, "site")
        if scope.site_mode == "not_applicable":
            raise BoundScopeError("site_denied")
        if normalize_authority_site(site) != scope.site:
            raise BoundScopeError("site_denied")
        effective_site = scope.site

    if domain is OMITTED:
        effective_domain = scope.domain
    else:
        _reject_blank(domain, "domain")
        requested = parse_strict_domain(domain)
        if not domain_matches(requested, scope.domain):
            raise BoundScopeError("domain_denied")
        effective_domain = requested

    return EffectiveSelectors(
        project=effective_project,
        site=effective_site,
        site_mode=scope.site_mode,
        domain=effective_domain,
        binding_id=scope.allowed_project_bindings[0],
    )


def reject_hostile_source_keys(obj: Any, *, path: str = "$") -> None:
    """Reject forged authority-shaped keys before trusted construction."""

    if isinstance(obj, dict):
        for key, value in obj.items():
            if not isinstance(key, str):
                raise BoundScopeError("source_key_type")
            if key in FORBIDDEN_SOURCE_KEYS or key.startswith(FORBIDDEN_SOURCE_PREFIXES):
                raise BoundScopeError(f"hostile_source_key:{path}.{key}")
            if key in AUTHORITY_LIKE_KEYS:
                raise BoundScopeError(f"hostile_authority_field:{path}.{key}")
            reject_hostile_source_keys(value, path=f"{path}.{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            reject_hostile_source_keys(value, path=f"{path}[{index}]")


def authorize_row(
    *,
    scope: BoundReadScope,
    registry: ProjectBindingRegistry,
    selectors: EffectiveSelectors,
    project_binding_id: str,
    source_registration_id: str,
    authority_site: str | None,
    authority_domain: str,
) -> None:
    """Architecture §6.4 row authorization against service-owned protected fields."""

    require_already_nfc(project_binding_id, field="project_binding_id")
    require_already_nfc(source_registration_id, field="source_registration_id")
    require_already_nfc(authority_domain, field="authority_domain")
    if authority_site is not None:
        require_already_nfc(authority_site, field="authority_site")
    if project_binding_id not in scope.allowed_project_bindings:
        raise BoundScopeError("row_binding_denied")
    if project_binding_id != selectors.binding_id:
        raise BoundScopeError("row_binding_denied")
    binding = registry.binding(project_binding_id)
    if binding.project != selectors.project:
        raise BoundScopeError("row_project_denied")
    regs = {r.id: r for r in binding.source_registrations}
    if source_registration_id not in regs:
        raise BoundScopeError("row_source_denied")
    reg = regs[source_registration_id]
    if authority_domain != reg.authorization_domain:
        raise BoundScopeError("row_domain_mismatch")
    if not domain_matches(authority_domain, binding.domain_root):
        raise BoundScopeError("row_domain_outside_binding")
    if not domain_matches(authority_domain, selectors.domain):
        raise BoundScopeError("row_domain_outside_effective")
    if binding.site_mode == "exact":
        if authority_site != binding.site or authority_site != reg.site:
            raise BoundScopeError("row_site_mismatch")
        if selectors.site_mode == "exact" and authority_site != selectors.site:
            raise BoundScopeError("row_site_denied")
    else:
        if selectors.site_mode != "not_applicable":
            raise BoundScopeError("row_site_mode")
        if authority_site is None:
            raise BoundScopeError("row_site_missing")
        if authority_site == "not_applicable":
            pass
        else:
            if authority_site != normalize_authority_site(authority_site):
                raise BoundScopeError("row_site_noncanonical")
            if reg.site is not None and authority_site != reg.site:
                raise BoundScopeError("row_site_mismatch")


def freeze_mapping(obj: Mapping[str, Any]) -> MappingProxyType:
    return MappingProxyType(dict(obj))


__all__ = [
    "OMITTED",
    "BoundScopeError",
    "BoundReadScope",
    "CaptureIssuer",
    "EffectiveSelectors",
    "ProjectBinding",
    "ProjectBindingRegistry",
    "ResolvedScope",
    "SourceRegistration",
    "VerificationProducer",
    "authorize_row",
    "canonicalize_nfc",
    "domain_matches",
    "load_bound_read_scope",
    "load_project_binding_registry",
    "normalize_authority_site",
    "owner_digest",
    "parse_strict_domain",
    "reject_hostile_source_keys",
    "require_already_nfc",
    "resolve_scope",
    "resolve_selectors",
    "sha256_digest",
]
