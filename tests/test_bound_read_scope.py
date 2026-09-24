"""M3/T1 adversarial coverage for bound read scope, IDNA2008 site, and selectors."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

from bound_read_scope import (
    BoundScopeError,
    OMITTED,
    canonicalize_nfc,
    normalize_authority_site,
    parse_strict_domain,
    reject_hostile_source_keys,
    require_already_nfc,
    resolve_selectors,
    sha256_digest,
)
from tests.fixtures.openclaw_strict.protocol_fixture.pinned_vectors import IDNA2008_VECTORS


def test_bound_read_scope_capability_present():
    spec = importlib.util.find_spec("bound_read_scope")
    assert spec is not None, "[T1] module bound_read_scope absent"
    module = importlib.import_module("bound_read_scope")
    assert hasattr(module, "resolve_scope"), "[T1] bound_read_scope.resolve_scope capability absent"


def test_require_already_nfc_rejects_decomposed_and_non_string():
    with pytest.raises(BoundScopeError, match="non_nfc"):
        require_already_nfc("cafe\u0301", field="x")
    with pytest.raises(BoundScopeError, match="not_string"):
        require_already_nfc(12, field="x")  # type: ignore[arg-type]
    assert canonicalize_nfc("caf\u00e9") == "caf\u00e9"


def test_normalize_authority_site_idna2008_vectors():
    for vector in IDNA2008_VECTORS:
        if vector["expect_accept"]:
            assert normalize_authority_site(vector["input"]) == vector["expected_ascii"], vector[
                "name"
            ]
        else:
            with pytest.raises(BoundScopeError):
                normalize_authority_site(vector["input"])


def test_normalize_authority_site_rejects_whitespace_repair_and_non_nfc():
    with pytest.raises(BoundScopeError, match="site_whitespace|site_invalid"):
        normalize_authority_site(" example.com")
    with pytest.raises(BoundScopeError, match="site_whitespace|site_invalid"):
        normalize_authority_site("example.com ")
    with pytest.raises(BoundScopeError, match="non_nfc"):
        normalize_authority_site("e\u0301xample.com")
    # Terminal DNS dot is the only allowed transformation before IDNA.
    assert normalize_authority_site("example.com.") == "example.com"
    with pytest.raises(BoundScopeError):
        normalize_authority_site("example.com..")


def test_normalize_authority_site_rejects_scheme_port_userinfo_underscore():
    for bad in (
        "https://example.com",
        "example.com:443",
        "user@example.com",
        "bad_host.example",
        "example.com/path",
    ):
        with pytest.raises(BoundScopeError):
            normalize_authority_site(bad)


def test_parse_strict_domain_no_coercion_or_case_repair():
    assert parse_strict_domain("coding.backend") == "coding.backend"
    with pytest.raises(BoundScopeError):
        parse_strict_domain("Coding.backend")
    with pytest.raises(BoundScopeError):
        parse_strict_domain(12)  # type: ignore[arg-type]
    with pytest.raises(BoundScopeError):
        parse_strict_domain("general")
    with pytest.raises(BoundScopeError):
        parse_strict_domain(" coding")


def test_resolve_selectors_omission_vs_null_blank_and_no_str_coerce():
    scope = _mini_scope(site_mode="exact", site="example.com", domain="coding")
    ok = resolve_selectors(scope)
    assert ok.project == "convmem"
    assert ok.site == "example.com"
    assert ok.domain == "coding"

    with pytest.raises(BoundScopeError, match="project_null"):
        resolve_selectors(scope, project=None)
    with pytest.raises(BoundScopeError, match="project_blank"):
        resolve_selectors(scope, project="  ")
    with pytest.raises(BoundScopeError, match="project_type"):
        resolve_selectors(scope, project=1)  # type: ignore[arg-type]
    with pytest.raises(BoundScopeError, match="site_denied"):
        resolve_selectors(scope, site="other.example")
    with pytest.raises(BoundScopeError, match="domain_denied"):
        resolve_selectors(scope, domain="other")
    with pytest.raises(BoundScopeError, match="cross_domain_denied"):
        resolve_selectors(scope, cross_domain=True)
    # Explicit equal site through IDNA path.
    narrowed = resolve_selectors(scope, domain="coding.backend", site="example.com.")
    assert narrowed.domain == "coding.backend"
    assert narrowed.site == "example.com"
    assert resolve_selectors(scope, cross_domain=False, project=OMITTED).project == "convmem"


def test_resolve_selectors_not_applicable_rejects_explicit_site():
    scope = _mini_scope(site_mode="not_applicable", site=None, domain="coding")
    assert resolve_selectors(scope).site is None
    with pytest.raises(BoundScopeError, match="site_denied"):
        resolve_selectors(scope, site="example.com")


def test_reject_hostile_source_keys_closed():
    with pytest.raises(BoundScopeError, match="hostile"):
        reject_hostile_source_keys({"_convmem_auth": {}})
    with pytest.raises(BoundScopeError, match="hostile"):
        reject_hostile_source_keys({"assertion_id": "x"})
    reject_hostile_source_keys({"title": "ok", "nested": [{"document": "x"}]})


def test_sha256_digest_rejects_non_string_coercion():
    assert sha256_digest(b"abc").startswith("sha256:")
    with pytest.raises(BoundScopeError):
        sha256_digest(123)  # type: ignore[arg-type]


def test_load_scope_and_registry_trusted_assignment(tmp_path: Path):
    from bound_read_scope import resolve_scope

    scope_path, registry_path = _write_scope_registry(tmp_path)
    resolved = resolve_scope(scope_path=scope_path, registry_path=registry_path)
    assert resolved.binding.id == "project:convmem:v1"
    assert resolved.binding.project == resolved.scope.project
    assert resolved.owner_digest.startswith("sha256:")


def test_registry_rejects_optional_field_omission_and_str_coerce(tmp_path: Path):
    from bound_read_scope import load_project_binding_registry

    _, registry_path = _write_scope_registry(tmp_path)
    obj = json.loads(registry_path.read_text())
    del obj["bindings"][0]["lineage_id"]
    bad = tmp_path / "bad-registry.json"
    _write_immutable(bad, obj)
    with pytest.raises(BoundScopeError, match="binding_keys"):
        load_project_binding_registry(bad)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MiniScope:
    def __init__(self, *, site_mode: str, site: str | None, domain: str):
        self.project = "convmem"
        self.allowed_project_bindings = ("project:convmem:v1",)
        self.domain = domain
        self.site_mode = site_mode
        self.site = site


def _mini_scope(*, site_mode: str, site: str | None, domain: str) -> _MiniScope:
    return _MiniScope(site_mode=site_mode, site=site, domain=domain)


def _write_immutable(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
    os.chmod(path, 0o444)


def _write_scope_registry(tmp_path: Path) -> tuple[Path, Path]:
    from canonical_json import canonical_json_bytes

    scope = {
        "schema": "convmem.bound-read-scope.v2",
        "project": "convmem",
        "allowed_project_bindings": ["project:convmem:v1"],
        "domain": "coding",
        "site_mode": "exact",
        "site": "example.com",
        "authority_snapshot": "/fixture/authority",
        "serving_projection": "/fixture/serving",
        "max_snapshot_age_seconds": 3600,
    }
    binding = {
        "id": "project:convmem:v1",
        "public_ref": "a" * 32,
        "project": "convmem",
        "domain_root": "coding",
        "site_mode": "exact",
        "site": "example.com",
        "non_expanding_roots": [],
        "source_registrations": [
            {
                "id": "src-reg-1",
                "source_class": "fixture_scan",
                "source_identity": "fixture/source-a",
                "identity_match": "exact",
                "authorization_domain": "coding",
                "site": "example.com",
                "event_id_resolver": "fixture_scan_event_v1",
            }
        ],
        "lineage_id": "b" * 32,
        "capture_issuers": [
            {
                "issuer_id": "fixture-issuer",
                "capture_class": "synthetic_fixture",
                "enrollment_sha256": "sha256:" + ("c" * 64),
                "receipt_root": "/fixture/receipts",
                "source_registration_ids": ["src-reg-1"],
            }
        ],
        "verification_producers": [],
    }
    without_revision = {
        "schema": "convmem.project-binding-registry.v3",
        "bindings": [binding],
    }
    revision = sha256_digest(
        canonical_json_bytes(
            without_revision,
            validate=lambda _obj: None,
            error_type=BoundScopeError,
        )
    )
    registry = {**without_revision, "revision": revision}
    scope_path = tmp_path / "scope.json"
    registry_path = tmp_path / "registry.json"
    _write_immutable(scope_path, scope)
    _write_immutable(registry_path, registry)
    return scope_path, registry_path
