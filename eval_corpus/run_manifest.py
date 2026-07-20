"""Approved run-manifest guards (mechanical auth, not identity proof).

Operation-specific binders reject missing, extra, or mismatched runtime fields.
Real mode requires an external sidecar approval digest.
"""
# pylint: disable=too-many-lines

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from eval_corpus.io_atomic import sha256_file

REQUIRED_REAL_FIELDS = (
    "execution_mode",
    "status",
    "operations",
    "model_tag",
    "merged_harness_sha256",
    "paths",
    "corpus_package_sha256",
    "unit_corpus_fingerprint",
    "query_set_sha256",
    "enrichment_sha256",
    "config_identity_sha256",
    "primary_metric",
    "primary_view",
    "tie_epsilon",
    "significance_alpha",
    "confidence_level",
    "bootstrap_seed",
    "bootstrap_resamples",
    "minimum_non_tied_pairs",
    "resource_ceiling",
    "service_policy",
    "prohibited_actions",
)

DEFAULT_UNCERTAINTY = {
    "primary_metric": "hit_at_k",
    "primary_view": "embedding_influenced",
    "tie_epsilon": 0.0,
    "significance_alpha": 0.05,
    "confidence_level": 0.95,
    "bootstrap_seed": 20260719,
    "bootstrap_resamples": 1999,
    "minimum_non_tied_pairs": 20,
}

# Operation → exact required runtime field names (no extras, no omissions).
CAPTURE_FIELDS = frozenset({"export", "processed", "capture_dir", "chroma_dir"})
ADJUDICATE_FIELDS = frozenset({"capture_dir", "adjudications", "acceptance_out"})
CONFIG_GENERATION_FIELDS = frozenset(
    {"live_config", "out_dir", "chroma_dir", "embed_model", "embed_host"}
)
BASELINE_BUILD_FIELDS = frozenset(
    {
        "package",
        "manifest",
        "chroma_dir",
        "result",
        "journal",
        "capture_dir",
        "model_tag",
        "embed_host",
        "corpus_package_sha256",
        "unit_corpus_fingerprint",
        "config_identity_sha256",
        "enrichment_sha256",
        "build_identity",
    }
)
CHALLENGER_BUILD_FIELDS = frozenset(BASELINE_BUILD_FIELDS)
COMPARE_FIELDS = frozenset(
    {
        "compare_mode",
        "golden",
        "package",
        "out",
        "baseline_chroma",
        "challenger_chroma",
        "baseline_config",
        "challenger_config",
        "baseline_model_tag",
        "challenger_model_tag",
        "baseline_config_sha256",
        "challenger_config_sha256",
        "embed_host",
        "query_set_sha256",
        "corpus_package_sha256",
        "enrichment_sha256",
    }
)
MODEL_EXECUTION_FIELDS = frozenset({"model_tag", "embed_host", "chroma_dir"})

PATH_FIELD_NAMES = frozenset(
    {
        "export",
        "processed",
        "capture_dir",
        "chroma_dir",
        "adjudications",
        "acceptance_out",
        "live_config",
        "out_dir",
        "package",
        "manifest",
        "result",
        "journal",
        "golden",
        "out",
        "baseline_chroma",
        "challenger_chroma",
        "baseline_config",
        "challenger_config",
    }
)

APPROVAL_EXCLUDED_KEYS = frozenset({"ryan_approved_manifest_sha256"})

# Immutable Gate 1 harness (PR #44 squash). R2a manifests must pin this SHA.
GATE_1_HARNESS_SHA256 = "3b2790f50414f0445c35748e52f849c6276839f7"

REQUIRED_R2A_FIELDS = (
    "authorization_phase",
    "execution_mode",
    "status",
    "operations",
    "merged_harness_sha256",
    "paths",
    "service_policy",
    "prohibited_actions",
)

R2A_ONLY_OPERATIONS = frozenset({"config_generation"})
R2A_FORBIDDEN_OPERATIONS = frozenset(
    {
        "capture",
        "adjudicate",
        "baseline_build",
        "challenger_build",
        "compare",
        "model_execution",
        "model_exec",
    }
)

_EVAL_ROOT_MARKER = "/.local/share/convmem/eval"
_CONFIG_ROOT_MARKER = "/.config/convmem"


@dataclass(frozen=True)
class R2aBindings:
    """Bindings re-derived from an approved R2a manifest (never from grant fields)."""

    live_config: Path
    out_dir: Path
    chroma_dir: Path
    embed_model: str
    embed_host: str
    merged_harness_sha256: str
    manifest_path: Path


def _build_r2a_capability_api() -> tuple[Any, Any, type]:
    """Closure-held MAC key: capability is immutable and binder-authenticated."""
    mac_key = secrets.token_bytes(32)

    class _R2aCapability:
        """Opaque authenticated capability. Construct only via binder issue()."""

        __slots__ = ("_manifest_path", "_mac", "_frozen")

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise TypeError("R2aCapability is binder-issued only")

        def __setattr__(self, name: str, value: Any) -> None:
            if getattr(self, "_frozen", False):
                raise AttributeError("R2aCapability is immutable")
            object.__setattr__(self, name, value)

    def issue(manifest_path: Path) -> _R2aCapability:
        path = Path(manifest_path).expanduser().resolve(strict=False)
        mac = hmac.new(mac_key, str(path).encode("utf-8"), "sha256").digest()
        obj = object.__new__(_R2aCapability)
        object.__setattr__(obj, "_manifest_path", path)
        object.__setattr__(obj, "_mac", mac)
        object.__setattr__(obj, "_frozen", True)
        return obj

    def authenticate(obj: Any) -> Path:
        # Exact type — reject subclasses that could forge __dict__/slots layouts.
        if type(obj) is not _R2aCapability:  # pylint: disable=unidiomatic-typecheck
            raise PermissionError("eval-root write requires a binder-issued R2a capability")
        path = object.__getattribute__(obj, "_manifest_path")
        mac = object.__getattribute__(obj, "_mac")
        expected = hmac.new(mac_key, str(path).encode("utf-8"), "sha256").digest()
        if not hmac.compare_digest(mac, expected):
            raise PermissionError("forged or corrupted R2a capability")
        return Path(path)

    return issue, authenticate, _R2aCapability


_issue_r2a_capability, _authenticate_r2a_capability, _ = _build_r2a_capability_api()


def is_r2a_eval_root_grant(obj: Any) -> bool:
    """True only for binder-issued authenticated R2a capabilities."""
    try:
        _authenticate_r2a_capability(obj)
    except PermissionError:
        return False
    return True


def path_is_eval_root(path: Path | str) -> bool:
    return _EVAL_ROOT_MARKER in str(Path(path).expanduser().resolve(strict=False))


def path_is_live_config_root(path: Path | str) -> bool:
    return _CONFIG_ROOT_MARKER in str(Path(path).expanduser().resolve(strict=False))


def derive_r2a_bindings_from_manifest(
    manifest: Mapping[str, Any], *, manifest_path: Path
) -> R2aBindings:
    """Derive every R2a binding from the approved manifest body (not from a grant)."""
    if str(manifest.get("authorization_phase") or "") != "r2a":
        raise PermissionError('manifest authorization_phase must be "r2a"')
    errs = validate_r2a_manifest_schema(dict(manifest))
    if errs:
        raise PermissionError("; ".join(errs))
    paths = manifest.get("paths") or {}
    if not isinstance(paths, dict):
        raise PermissionError("manifest.paths must be an object")
    live_config = Path(str(paths["live_config"])).expanduser().resolve(strict=False)
    out_dir = Path(str(paths["out_dir"])).expanduser().resolve(strict=False)
    chroma_dir = Path(str(paths["chroma_dir"])).expanduser().resolve(strict=False)
    embed_model = str(manifest.get("embed_model") or manifest.get("model_tag") or "")
    embed_host = str(paths.get("embed_host") or manifest.get("embed_host") or "")
    if not embed_model or not embed_host:
        raise PermissionError("R2a manifest missing embed_model/embed_host")
    if path_is_live_config_root(out_dir) or path_is_live_config_root(chroma_dir):
        raise PermissionError("R2a forbids writing under ~/.config/convmem")
    if not path_is_eval_root(out_dir) or not path_is_eval_root(chroma_dir):
        raise PermissionError(
            "R2a requires out_dir and chroma_dir under "
            "~/.local/share/convmem/eval (or hermetic path containing that marker)"
        )
    return R2aBindings(
        live_config=live_config,
        out_dir=out_dir,
        chroma_dir=chroma_dir,
        embed_model=embed_model,
        embed_host=embed_host,
        merged_harness_sha256=str(manifest.get("merged_harness_sha256")),
        manifest_path=Path(manifest_path).expanduser().resolve(strict=False),
    )


def materialize_r2a_capability(capability: Any) -> R2aBindings:
    """Authenticate capability, re-verify sidecar, re-derive all bindings from manifest."""
    manifest_path = _authenticate_r2a_capability(capability)
    manifest = load_run_manifest(manifest_path)
    assert_manifest_file_matches_approval(manifest_path, manifest)
    # Re-check operation allow/prohibit after sidecar re-verify (write-time).
    assert_operation_allowed(manifest, "config_generation")
    return derive_r2a_bindings_from_manifest(manifest, manifest_path=manifest_path)


@dataclass(frozen=True)
class AuthContext:
    """Validated authorization context for an operation.

    Public and caller-constructible — must never unlock eval-root writes.
    """

    execution_mode: str
    require_corpus_acceptance: bool
    manifest: dict[str, Any]
    operation: str


def load_run_manifest(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def manifest_sha256(path: Path | str) -> str:
    return sha256_file(path)


def canonical_manifest_body_sha256(manifest: Mapping[str, Any]) -> str:
    body = {k: v for k, v in manifest.items() if k not in APPROVAL_EXCLUDED_KEYS}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def approval_sidecar_path(manifest_path: Path) -> Path:
    return Path(manifest_path).with_suffix(Path(manifest_path).suffix + ".approved.sha256")


def write_approval_sidecar(manifest_path: Path, digest: str | None = None) -> Path:
    """Write external approval digest for tests/helpers (not self-attestation at runtime)."""
    path = Path(manifest_path)
    manifest = load_run_manifest(path)
    got = digest or canonical_manifest_body_sha256(manifest)
    side = approval_sidecar_path(path)
    side.write_text(got + "\n", encoding="utf-8")
    return side


def validate_r2a_manifest_schema(manifest: dict[str, Any]) -> list[str]:
    """Phase-scoped R2a schema — distinct from REQUIRED_REAL_FIELDS."""
    errors: list[str] = []
    if str(manifest.get("authorization_phase") or "") != "r2a":
        errors.append('authorization_phase must be "r2a"')
    if str(manifest.get("execution_mode") or "") != "real":
        errors.append('R2a execution_mode must be "real"')
    if str(manifest.get("status") or "") != "approved":
        errors.append("status must be approved")
    for key in REQUIRED_R2A_FIELDS:
        if key not in manifest:
            errors.append(f"missing required R2a field {key}")
    ops = manifest.get("operations")
    if not isinstance(ops, list) or not ops:
        errors.append("operations must be a nonempty list")
    else:
        ops_norm = [str(o) for o in ops]
        # Exact list identity — set equality would allow duplicates.
        if ops_norm != ["config_generation"]:
            errors.append(
                "R2a operations must be exactly ['config_generation'], "
                f"got {ops!r}"
            )
        bad = sorted(set(ops_norm) & R2A_FORBIDDEN_OPERATIONS)
        if bad:
            errors.append(f"R2a forbids operations {bad}")
    harness = str(manifest.get("merged_harness_sha256") or "")
    if harness != GATE_1_HARNESS_SHA256:
        errors.append(
            "merged_harness_sha256 must equal Gate 1 harness "
            f"{GATE_1_HARNESS_SHA256}"
        )
    if not str(manifest.get("ryan_approved_manifest_sha256") or ""):
        errors.append("R2a manifest requires ryan_approved_manifest_sha256")
    paths = manifest.get("paths")
    if not isinstance(paths, dict) or not paths:
        errors.append("R2a manifest requires nonempty paths object")
    else:
        for key in ("live_config", "out_dir", "chroma_dir"):
            if key not in paths:
                errors.append(f"R2a paths missing {key}")
        for k, v in paths.items():
            s = str(v)
            if _CONFIG_ROOT_MARKER in s and k != "live_config":
                errors.append(f"R2a must not write under live config root ({k}={s})")
    model = str(manifest.get("embed_model") or "").strip()
    tag = str(manifest.get("model_tag") or "").strip()
    if not model and not tag:
        errors.append("R2a requires embed_model or model_tag")
    paths_obj = paths if isinstance(paths, dict) else {}
    host_raw = paths_obj.get("embed_host")
    if host_raw is None:
        host_raw = manifest.get("embed_host")
    if host_raw is None or not str(host_raw).strip():
        errors.append("R2a requires embed_host (top-level or paths.embed_host)")
    return errors


def validate_run_manifest_schema(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    mode = str(manifest.get("execution_mode") or "")
    if mode not in ("fixture", "real"):
        errors.append(f"execution_mode must be fixture|real, got {mode!r}")
    if str(manifest.get("status") or "") != "approved":
        errors.append("status must be approved")
    ops = manifest.get("operations")
    if not isinstance(ops, list) or not ops:
        errors.append("operations must be a nonempty list")
    phase = str(manifest.get("authorization_phase") or "")
    if mode == "real" and phase == "r2a":
        errors.extend(validate_r2a_manifest_schema(manifest))
    elif mode == "real":
        for key in REQUIRED_REAL_FIELDS:
            if key not in manifest:
                errors.append(f"missing required field {key}")
        if str(manifest.get("primary_view") or "") != "embedding_influenced":
            errors.append("primary_view must be embedding_influenced")
        if not str(manifest.get("ryan_approved_manifest_sha256") or ""):
            errors.append("real manifest requires ryan_approved_manifest_sha256")
        paths = manifest.get("paths")
        if not isinstance(paths, dict) or not paths:
            errors.append("real manifest requires nonempty paths object")
    else:
        paths = manifest.get("paths") or {}
        if isinstance(paths, dict):
            for k, v in paths.items():
                s = str(v)
                if _EVAL_ROOT_MARKER in s or _CONFIG_ROOT_MARKER in s:
                    errors.append(f"fixture manifest must not authorize external path {k}={s}")
    return errors


def assert_manifest_file_matches_approval(path: Path, manifest: dict[str, Any]) -> None:
    """Real mode: sidecar digest is authoritative; in-file field must copy it."""
    if str(manifest.get("execution_mode")) != "real":
        return
    side = approval_sidecar_path(path)
    if not side.is_file():
        raise PermissionError(
            f"real manifest requires external approval sidecar: {side}"
        )
    sidecar_digest = side.read_text(encoding="utf-8").strip().split()[0]
    body_digest = canonical_manifest_body_sha256(manifest)
    if sidecar_digest != body_digest:
        raise PermissionError(
            "approval sidecar does not match canonical manifest body SHA-256"
        )
    want = str(manifest.get("ryan_approved_manifest_sha256") or "")
    if want != sidecar_digest:
        raise PermissionError(
            "ryan_approved_manifest_sha256 must equal external approval sidecar digest"
        )


def assert_operation_allowed(manifest: dict[str, Any], operation: str) -> None:
    ops = manifest.get("operations")
    if not isinstance(ops, list) or not ops:
        raise PermissionError("run-manifest.operations must be a nonempty list")
    prohibited = set(manifest.get("prohibited_actions") or [])
    if operation in prohibited:
        raise PermissionError(f"operation prohibited by run-manifest: {operation}")
    if operation not in ops:
        raise PermissionError(f"operation not listed in run-manifest.operations: {operation}")


def path_is_temp_contained(path: Path) -> bool:
    """True path containment under tempfile.gettempdir() (not substring /tmp/)."""
    try:
        resolved = Path(path).expanduser().resolve(strict=False)
        temp_root = Path(tempfile.gettempdir()).resolve()
    except OSError:
        return False
    try:
        return resolved == temp_root or resolved.is_relative_to(temp_root)
    except (ValueError, AttributeError):
        prefix = str(temp_root)
        s = str(resolved)
        return s == prefix or s.startswith(prefix + "/")


# Back-compat alias used by older scripts/tests
def _path_is_tempish(path: Path) -> bool:
    return path_is_temp_contained(path)


def _require_exact_fields(operation: str, required: frozenset[str], runtime: Mapping[str, Any]) -> None:
    keys = frozenset(runtime.keys())
    missing = sorted(required - keys)
    extra = sorted(keys - required)
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing={missing}")
        if extra:
            parts.append(f"extra={extra}")
        raise PermissionError(
            f"{operation} binder rejects incomplete runtime ({', '.join(parts)})"
        )


def _norm_path(value: Any) -> str:
    return str(Path(str(value)).expanduser().resolve(strict=False))


def _bind_paths_and_scalars(
    *,
    operation: str,
    required: frozenset[str],
    runtime: Mapping[str, Any],
    manifest: dict[str, Any],
    execution_mode: str,
    authorize_fixture: bool,
) -> None:
    _require_exact_fields(operation, required, runtime)
    path_keys = required & PATH_FIELD_NAMES
    if authorize_fixture or execution_mode == "fixture":
        for key in path_keys:
            p = Path(str(runtime[key]))
            if path_is_eval_root(p) or path_is_live_config_root(p):
                raise PermissionError(
                    f"{operation}: fixture forbids eval/live-config path {key}={p}"
                )
            if not path_is_temp_contained(p):
                raise PermissionError(
                    f"{operation}: fixture forbids non-temp path {key}={p}"
                )
        return

    # real mode: every runtime field must match manifest binding
    paths = manifest.get("paths") or {}
    if not isinstance(paths, dict):
        raise PermissionError("real manifest.paths must be an object")
    for key in path_keys:
        if key not in paths:
            raise PermissionError(f"{operation}: manifest.paths missing {key}")
        if _norm_path(runtime[key]) != _norm_path(paths[key]):
            raise PermissionError(
                f"{operation}: runtime {key} mismatch vs manifest.paths"
            )
    for key in required - PATH_FIELD_NAMES:
        if key == "embed_host":
            expected = (manifest.get("paths") or {}).get("embed_host") or manifest.get(
                "embed_host"
            )
        elif key == "embed_model":
            expected = manifest.get("embed_model") or manifest.get("model_tag")
        elif key == "model_tag":
            # Per-arm build tags: a single Gate 2 manifest can authorize a
            # distinct baseline and challenger model.
            if operation == "baseline_build":
                expected = manifest.get("baseline_model_tag", manifest.get("model_tag"))
            elif operation == "challenger_build":
                expected = manifest.get(
                    "challenger_model_tag", manifest.get("model_tag")
                )
            else:
                expected = manifest.get("model_tag")
        else:
            # Per-arm identities (baseline_/challenger_ model tags, config
            # hashes) and shared hashes bind by their exact manifest key.
            expected = manifest.get(key)
        if expected is None:
            raise PermissionError(f"{operation}: manifest missing binding for {key}")
        if str(runtime[key]) != str(expected):
            raise PermissionError(f"{operation}: runtime {key} mismatch vs manifest")


def _load_and_validate_manifest(run_manifest_path: Path) -> dict[str, Any]:
    manifest = load_run_manifest(run_manifest_path)
    errs = validate_run_manifest_schema(manifest)
    if errs:
        raise PermissionError("; ".join(errs))
    assert_manifest_file_matches_approval(run_manifest_path, manifest)
    return manifest


def _fixture_context(operation: str) -> AuthContext:
    return AuthContext(
        execution_mode="fixture",
        require_corpus_acceptance=False,
        manifest={"execution_mode": "fixture", "status": "approved", **DEFAULT_UNCERTAINTY},
        operation=operation,
    )


def bind_capture(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    runtime: Mapping[str, Any],
) -> AuthContext:
    _require_exact_fields("capture", CAPTURE_FIELDS, runtime)
    if authorize_fixture:
        _bind_paths_and_scalars(
            operation="capture",
            required=CAPTURE_FIELDS,
            runtime=runtime,
            manifest={},
            execution_mode="fixture",
            authorize_fixture=True,
        )
        return _fixture_context("capture")
    if run_manifest_path is None:
        raise PermissionError("pass --authorize-fixture or --run-manifest")
    manifest = _load_and_validate_manifest(run_manifest_path)
    assert_operation_allowed(manifest, "capture")
    mode = str(manifest.get("execution_mode"))
    _bind_paths_and_scalars(
        operation="capture",
        required=CAPTURE_FIELDS,
        runtime=runtime,
        manifest=manifest,
        execution_mode=mode,
        authorize_fixture=False,
    )
    return AuthContext(
        execution_mode=mode,
        require_corpus_acceptance=False,
        manifest=manifest,
        operation="capture",
    )


def bind_adjudicate(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    runtime: Mapping[str, Any],
) -> AuthContext:
    _require_exact_fields("adjudicate", ADJUDICATE_FIELDS, runtime)
    if authorize_fixture:
        _bind_paths_and_scalars(
            operation="adjudicate",
            required=ADJUDICATE_FIELDS,
            runtime=runtime,
            manifest={},
            execution_mode="fixture",
            authorize_fixture=True,
        )
        return _fixture_context("adjudicate")
    if run_manifest_path is None:
        raise PermissionError("pass --authorize-fixture or --run-manifest")
    manifest = _load_and_validate_manifest(run_manifest_path)
    assert_operation_allowed(manifest, "adjudicate")
    mode = str(manifest.get("execution_mode"))
    _bind_paths_and_scalars(
        operation="adjudicate",
        required=ADJUDICATE_FIELDS,
        runtime=runtime,
        manifest=manifest,
        execution_mode=mode,
        authorize_fixture=False,
    )
    return AuthContext(
        execution_mode=mode,
        require_corpus_acceptance=False,
        manifest=manifest,
        operation="adjudicate",
    )


def bind_config_generation(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    runtime: Mapping[str, Any],
) -> AuthContext:
    _require_exact_fields("config_generation", CONFIG_GENERATION_FIELDS, runtime)
    if authorize_fixture:
        _bind_paths_and_scalars(
            operation="config_generation",
            required=CONFIG_GENERATION_FIELDS,
            runtime=runtime,
            manifest={},
            execution_mode="fixture",
            authorize_fixture=True,
        )
        return _fixture_context("config_generation")
    if run_manifest_path is None:
        raise PermissionError("pass --authorize-fixture or --run-manifest")
    manifest = _load_and_validate_manifest(run_manifest_path)
    if str(manifest.get("authorization_phase") or "") == "r2a":
        raise PermissionError(
            "R2a manifests require bind_r2a_config_generation "
            "(plain bind_config_generation cannot grant eval-root writes)"
        )
    assert_operation_allowed(manifest, "config_generation")
    mode = str(manifest.get("execution_mode"))
    _bind_paths_and_scalars(
        operation="config_generation",
        required=CONFIG_GENERATION_FIELDS,
        runtime=runtime,
        manifest=manifest,
        execution_mode=mode,
        authorize_fixture=False,
    )
    return AuthContext(
        execution_mode=mode,
        require_corpus_acceptance=False,
        manifest=manifest,
        operation="config_generation",
    )


def bind_r2a_config_generation(
    *,
    run_manifest_path: Path,
    runtime: Mapping[str, Any],
) -> Any:
    """Authorize R2a config_generation; return an immutable authenticated capability.

    The capability stores only an authenticated manifest path. Write-time code must
    re-verify the sidecar and re-derive every binding from that manifest.
    """
    _require_exact_fields("config_generation", CONFIG_GENERATION_FIELDS, runtime)
    path = Path(run_manifest_path)
    manifest = _load_and_validate_manifest(path)
    if str(manifest.get("authorization_phase") or "") != "r2a":
        raise PermissionError('bind_r2a_config_generation requires authorization_phase="r2a"')
    assert_operation_allowed(manifest, "config_generation")
    _bind_paths_and_scalars(
        operation="config_generation",
        required=CONFIG_GENERATION_FIELDS,
        runtime=runtime,
        manifest=manifest,
        execution_mode="real",
        authorize_fixture=False,
    )
    bindings = derive_r2a_bindings_from_manifest(manifest, manifest_path=path)
    # Runtime must match bindings re-derived from the approved manifest.
    if _norm_path(runtime["live_config"]) != str(bindings.live_config):
        raise PermissionError("runtime live_config mismatch vs approved manifest")
    if _norm_path(runtime["out_dir"]) != str(bindings.out_dir):
        raise PermissionError("runtime out_dir mismatch vs approved manifest")
    if _norm_path(runtime["chroma_dir"]) != str(bindings.chroma_dir):
        raise PermissionError("runtime chroma_dir mismatch vs approved manifest")
    if str(runtime["embed_model"]) != bindings.embed_model:
        raise PermissionError("runtime embed_model mismatch vs approved manifest")
    if str(runtime["embed_host"]) != bindings.embed_host:
        raise PermissionError("runtime embed_host mismatch vs approved manifest")
    return _issue_r2a_capability(bindings.manifest_path)


def materialize_r2a_write_authorization(
    capability: Any,
    *,
    out_dir: Path | str,
    chroma_dir: Path | str,
    embed_model: str,
    embed_host: str,
    live_config: Path | str | None = None,
) -> R2aBindings:
    """Authenticate capability; re-verify sidecar; compare runtime to manifest bindings.

    Does not trust caller-mutated grant fields — every value is re-derived from the
    approved manifest after sidecar verification.
    """
    bindings = materialize_r2a_capability(capability)
    if _norm_path(out_dir) != str(bindings.out_dir):
        raise PermissionError("runtime out_dir mismatch vs approved manifest")
    if _norm_path(chroma_dir) != str(bindings.chroma_dir):
        raise PermissionError("runtime chroma_dir mismatch vs approved manifest")
    if str(embed_model) != bindings.embed_model:
        raise PermissionError("runtime embed_model mismatch vs approved manifest")
    if str(embed_host) != bindings.embed_host:
        raise PermissionError("runtime embed_host mismatch vs approved manifest")
    if live_config is not None and _norm_path(live_config) != str(bindings.live_config):
        raise PermissionError("runtime live_config mismatch vs approved manifest")
    return bindings


# Back-compat name used by earlier drafts / tests
def verify_r2a_grant_for_write(
    grant: Any,
    *,
    out_dir: Path | str,
    chroma_dir: Path | str,
    embed_model: str,
    embed_host: str,
    live_config: Path | str | None = None,
) -> R2aBindings:
    return materialize_r2a_write_authorization(
        grant,
        out_dir=out_dir,
        chroma_dir=chroma_dir,
        embed_model=embed_model,
        embed_host=embed_host,
        live_config=live_config,
    )


def _bind_build(
    *,
    operation: str,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    runtime: Mapping[str, Any],
) -> AuthContext:
    fields = BASELINE_BUILD_FIELDS if operation == "baseline_build" else CHALLENGER_BUILD_FIELDS
    _require_exact_fields(operation, fields, runtime)
    if authorize_fixture:
        _bind_paths_and_scalars(
            operation=operation,
            required=fields,
            runtime=runtime,
            manifest={},
            execution_mode="fixture",
            authorize_fixture=True,
        )
        return _fixture_context(operation)
    if run_manifest_path is None:
        raise PermissionError("pass --authorize-fixture or --run-manifest")
    manifest = _load_and_validate_manifest(run_manifest_path)
    assert_operation_allowed(manifest, operation)
    mode = str(manifest.get("execution_mode"))
    _bind_paths_and_scalars(
        operation=operation,
        required=fields,
        runtime=runtime,
        manifest=manifest,
        execution_mode=mode,
        authorize_fixture=False,
    )
    # Real builds always require corpus acceptance from auth context.
    require_acc = mode == "real"
    return AuthContext(
        execution_mode=mode,
        require_corpus_acceptance=require_acc,
        manifest=manifest,
        operation=operation,
    )


def bind_baseline_build(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    runtime: Mapping[str, Any],
) -> AuthContext:
    return _bind_build(
        operation="baseline_build",
        authorize_fixture=authorize_fixture,
        run_manifest_path=run_manifest_path,
        runtime=runtime,
    )


def bind_challenger_build(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    runtime: Mapping[str, Any],
) -> AuthContext:
    return _bind_build(
        operation="challenger_build",
        authorize_fixture=authorize_fixture,
        run_manifest_path=run_manifest_path,
        runtime=runtime,
    )


def bind_compare(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    runtime: Mapping[str, Any],
) -> AuthContext:
    _require_exact_fields("compare", COMPARE_FIELDS, runtime)
    if authorize_fixture:
        _bind_paths_and_scalars(
            operation="compare",
            required=COMPARE_FIELDS,
            runtime=runtime,
            manifest={},
            execution_mode="fixture",
            authorize_fixture=True,
        )
        return _fixture_context("compare")
    if run_manifest_path is None:
        raise PermissionError("pass --authorize-fixture or --run-manifest")
    manifest = _load_and_validate_manifest(run_manifest_path)
    assert_operation_allowed(manifest, "compare")
    mode = str(manifest.get("execution_mode"))
    _bind_paths_and_scalars(
        operation="compare",
        required=COMPARE_FIELDS,
        runtime=runtime,
        manifest=manifest,
        execution_mode=mode,
        authorize_fixture=False,
    )
    if mode == "real" and str(runtime.get("compare_mode")) != "subprocess":
        raise PermissionError(
            "compare: real mode requires compare_mode=subprocess "
            "(injectable scoring is fixture-only)"
        )
    return AuthContext(
        execution_mode=mode,
        require_corpus_acceptance=False,
        manifest=manifest,
        operation="compare",
    )


def bind_model_execution(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    runtime: Mapping[str, Any],
) -> AuthContext:
    """Authorize live model/host use. Requires model_exec in operations for real."""
    _require_exact_fields("model_execution", MODEL_EXECUTION_FIELDS, runtime)
    if authorize_fixture:
        raise PermissionError("model_execution is forbidden under --authorize-fixture")
    if run_manifest_path is None:
        raise PermissionError("model_execution requires --run-manifest")
    manifest = _load_and_validate_manifest(run_manifest_path)
    # Accept legacy model_exec alias, but both names get identical
    # allow/prohibit validation — the alias is never a prohibited-check bypass.
    ops = set(manifest.get("operations") or [])
    prohibited = set(manifest.get("prohibited_actions") or [])
    if {"model_execution", "model_exec"} & prohibited:
        raise PermissionError("operation prohibited by run-manifest: model_execution")
    if "model_execution" in ops:
        assert_operation_allowed(manifest, "model_execution")
    elif "model_exec" in ops:
        assert_operation_allowed(manifest, "model_exec")
    else:
        raise PermissionError(
            "model_execution requires model_execution (or model_exec) in operations"
        )
    mode = str(manifest.get("execution_mode"))
    _bind_paths_and_scalars(
        operation="model_execution",
        required=MODEL_EXECUTION_FIELDS,
        runtime=runtime,
        manifest=manifest,
        execution_mode=mode,
        authorize_fixture=False,
    )
    return AuthContext(
        execution_mode=mode,
        require_corpus_acceptance=False,
        manifest=manifest,
        operation="model_execution",
    )


# --- Compatibility wrappers (delegate to operation binders) -----------------


def assert_capture_authorized(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    export: Path,
    processed: Path,
    capture_dir: Path,
    chroma_dir: Path,
) -> AuthContext:
    return bind_capture(
        authorize_fixture=authorize_fixture,
        run_manifest_path=run_manifest_path,
        runtime={
            "export": export,
            "processed": processed,
            "capture_dir": capture_dir,
            "chroma_dir": chroma_dir,
        },
    )


def assert_build_authorized(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    runtime: Mapping[str, Any],
    arm: str = "baseline",
) -> AuthContext:
    binder = bind_baseline_build if arm != "challenger" else bind_challenger_build
    return binder(
        authorize_fixture=authorize_fixture,
        run_manifest_path=run_manifest_path,
        runtime=runtime,
    )


def assert_compare_authorized(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    runtime: Mapping[str, Any],
) -> AuthContext:
    return bind_compare(
        authorize_fixture=authorize_fixture,
        run_manifest_path=run_manifest_path,
        runtime=runtime,
    )


def make_fixture_run_manifest(**overrides: Any) -> dict[str, Any]:
    base = {
        "execution_mode": "fixture",
        "status": "approved",
        "operations": [
            "capture",
            "adjudicate",
            "config_generation",
            "baseline_build",
            "challenger_build",
            "compare",
        ],
        "prohibited_actions": ["promote", "service_stop", "cleanup_external", "model_execution"],
        "paths": {},
        **DEFAULT_UNCERTAINTY,
    }
    base.update(overrides)
    return base


def make_real_run_manifest_for_tests(
    *,
    paths: dict[str, Any],
    operations: list[str],
    **overrides: Any,
) -> dict[str, Any]:
    """Helper to construct a real-mode manifest body (sidecar written separately)."""
    body = {
        "execution_mode": "real",
        "status": "approved",
        "operations": operations,
        "model_tag": overrides.pop("model_tag", "fake-embed"),
        "merged_harness_sha256": "a" * 64,
        "paths": paths,
        "corpus_package_sha256": overrides.pop("corpus_package_sha256", "b" * 64),
        "unit_corpus_fingerprint": overrides.pop("unit_corpus_fingerprint", "c" * 64),
        "query_set_sha256": overrides.pop("query_set_sha256", "d" * 64),
        "enrichment_sha256": overrides.pop("enrichment_sha256", "e" * 64),
        "config_identity_sha256": overrides.pop("config_identity_sha256", "f" * 64),
        "resource_ceiling": {"max_rss_mb": 4096},
        "service_policy": "no_service_changes",
        "prohibited_actions": ["promote", "cleanup_external"],
        "build_identity": overrides.pop("build_identity", "test-build"),
        "compare_mode": overrides.pop("compare_mode", "subprocess"),
        "embed_host": paths.get("embed_host", "http://127.0.0.1:0"),
        **DEFAULT_UNCERTAINTY,
    }
    body.update(overrides)
    digest = canonical_manifest_body_sha256(body)
    body["ryan_approved_manifest_sha256"] = digest
    return body


def make_r2a_run_manifest_for_tests(
    *,
    paths: dict[str, Any],
    **overrides: Any,
) -> dict[str, Any]:
    """Construct an R2a-phase real manifest body (sidecar written separately)."""
    body: dict[str, Any] = {
        "authorization_phase": "r2a",
        "execution_mode": "real",
        "status": "approved",
        "operations": ["config_generation"],
        "merged_harness_sha256": GATE_1_HARNESS_SHA256,
        "paths": paths,
        "service_policy": "no_service_changes",
        "prohibited_actions": [
            "capture",
            "adjudicate",
            "baseline_build",
            "challenger_build",
            "compare",
            "model_execution",
            "promote",
            "cleanup_external",
        ],
        "embed_model": overrides.pop("embed_model", "fake-embed"),
        "embed_host": paths.get("embed_host", overrides.pop("embed_host", "http://127.0.0.1:0")),
    }
    body.update(overrides)
    digest = canonical_manifest_body_sha256(body)
    body["ryan_approved_manifest_sha256"] = digest
    return body


__all__ = [
    "ADJUDICATE_FIELDS",
    "AuthContext",
    "BASELINE_BUILD_FIELDS",
    "CAPTURE_FIELDS",
    "CHALLENGER_BUILD_FIELDS",
    "COMPARE_FIELDS",
    "CONFIG_GENERATION_FIELDS",
    "DEFAULT_UNCERTAINTY",
    "GATE_1_HARNESS_SHA256",
    "MODEL_EXECUTION_FIELDS",
    "REQUIRED_R2A_FIELDS",
    "REQUIRED_REAL_FIELDS",
    "R2aBindings",
    "assert_build_authorized",
    "assert_capture_authorized",
    "assert_compare_authorized",
    "assert_manifest_file_matches_approval",
    "assert_operation_allowed",
    "bind_adjudicate",
    "bind_baseline_build",
    "bind_capture",
    "bind_challenger_build",
    "bind_compare",
    "bind_config_generation",
    "bind_model_execution",
    "bind_r2a_config_generation",
    "canonical_manifest_body_sha256",
    "derive_r2a_bindings_from_manifest",
    "is_r2a_eval_root_grant",
    "load_run_manifest",
    "make_fixture_run_manifest",
    "make_r2a_run_manifest_for_tests",
    "make_real_run_manifest_for_tests",
    "manifest_sha256",
    "materialize_r2a_capability",
    "materialize_r2a_write_authorization",
    "path_is_eval_root",
    "path_is_live_config_root",
    "path_is_temp_contained",
    "validate_r2a_manifest_schema",
    "validate_run_manifest_schema",
    "verify_r2a_grant_for_write",
    "write_approval_sidecar",
    "_path_is_tempish",
]
