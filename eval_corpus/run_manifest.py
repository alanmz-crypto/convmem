"""Approved run-manifest guards (mechanical auth, not identity proof).

Operation-specific binders reject missing, extra, or mismatched runtime fields.
Real mode requires an external sidecar approval digest.
"""

from __future__ import annotations

import hashlib
import json
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
        "golden",
        "package",
        "out",
        "baseline_chroma",
        "challenger_chroma",
        "baseline_config",
        "challenger_config",
        "embed_host",
        "query_set_sha256",
        "corpus_package_sha256",
        "config_identity_sha256",
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


@dataclass(frozen=True)
class AuthContext:
    """Validated authorization context for an operation."""

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
    if mode == "real":
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
                if "/.local/share/convmem/eval" in s or "/.config/convmem" in s:
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
            expected = manifest.get("model_tag")
        else:
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
    # Accept either model_execution or legacy model_exec operation name
    ops = set(manifest.get("operations") or [])
    if "model_execution" not in ops and "model_exec" not in ops:
        raise PermissionError(
            "model_execution requires model_execution (or model_exec) in operations"
        )
    if "model_execution" in ops:
        assert_operation_allowed(manifest, "model_execution")
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
        "embed_host": paths.get("embed_host", "http://127.0.0.1:0"),
        **DEFAULT_UNCERTAINTY,
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
    "MODEL_EXECUTION_FIELDS",
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
    "canonical_manifest_body_sha256",
    "load_run_manifest",
    "make_fixture_run_manifest",
    "make_real_run_manifest_for_tests",
    "manifest_sha256",
    "path_is_temp_contained",
    "validate_run_manifest_schema",
    "write_approval_sidecar",
    "_path_is_tempish",
]
