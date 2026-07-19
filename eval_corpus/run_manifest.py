"""Approved run-manifest guards (mechanical auth, not identity proof)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


def load_run_manifest(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def manifest_sha256(path: Path | str) -> str:
    return sha256_file(path)


def validate_run_manifest_schema(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    mode = str(manifest.get("execution_mode") or "")
    if mode not in ("fixture", "real"):
        errors.append(f"execution_mode must be fixture|real, got {mode!r}")
    if str(manifest.get("status") or "") != "approved":
        errors.append("status must be approved")
    if mode == "real":
        for key in REQUIRED_REAL_FIELDS:
            if key not in manifest:
                errors.append(f"missing required field {key}")
        if str(manifest.get("primary_view") or "") != "embedding_influenced":
            errors.append("primary_view must be embedding_influenced")
        approved_sha = str(manifest.get("ryan_approved_manifest_sha256") or "")
        if not approved_sha:
            errors.append("real manifest requires ryan_approved_manifest_sha256")
    else:
        # Fixture: must not authorize real/external path prefixes
        paths = manifest.get("paths") or {}
        if isinstance(paths, dict):
            for k, v in paths.items():
                s = str(v)
                if "/.local/share/convmem/eval" in s or "/.config/convmem" in s:
                    errors.append(f"fixture manifest must not authorize external path {k}={s}")
    return errors


def assert_manifest_file_matches_approval(path: Path, manifest: dict[str, Any]) -> None:
    if str(manifest.get("execution_mode")) != "real":
        return
    want = str(manifest.get("ryan_approved_manifest_sha256") or "")
    # Approval binds the exact file bytes excluding the approval field itself is
    # awkward; Gate 1 convention: ryan_approved_manifest_sha256 equals sha of the
    # file as stored (self-binding for fixtures that precompute it), or a sidecar.
    # For real mode, require equality with current file hash of a companion
    # `.approved.sha256` OR match when field equals sha256 of body without that key.
    body = dict(manifest)
    body.pop("ryan_approved_manifest_sha256", None)
    import hashlib

    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    got = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if want != got and want != sha256_file(path):
        raise PermissionError(
            "ryan_approved_manifest_sha256 does not match manifest content hash"
        )


def assert_operation_allowed(manifest: dict[str, Any], operation: str) -> None:
    ops = set(manifest.get("operations") or [])
    prohibited = set(manifest.get("prohibited_actions") or [])
    if operation in prohibited:
        raise PermissionError(f"operation prohibited by run-manifest: {operation}")
    if ops and operation not in ops:
        raise PermissionError(f"operation not listed in run-manifest.operations: {operation}")


def _path_is_tempish(path: Path) -> bool:
    s = str(path.resolve())
    return "/tmp/" in s or s.startswith("/tmp") or "/pytest-" in s or "/tmp." in s


def assert_capture_authorized(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    export: Path,
    processed: Path,
    capture_dir: Path,
    chroma_dir: Path,
) -> None:
    if authorize_fixture:
        for p in (export, processed, capture_dir, chroma_dir):
            if not _path_is_tempish(Path(p)):
                raise PermissionError(
                    f"--authorize-fixture forbids non-temp path: {p}"
                )
        return
    if run_manifest_path is None:
        raise PermissionError(
            "pass --authorize-fixture (Gate 1 hermetic) or --run-manifest (approved)"
        )
    manifest = load_run_manifest(run_manifest_path)
    errs = validate_run_manifest_schema(manifest)
    if errs:
        raise PermissionError("; ".join(errs))
    assert_manifest_file_matches_approval(run_manifest_path, manifest)
    assert_operation_allowed(manifest, "capture")
    if str(manifest.get("execution_mode")) == "fixture":
        for p in (export, processed, capture_dir, chroma_dir):
            if not _path_is_tempish(Path(p)):
                raise PermissionError(
                    f"fixture run-manifest forbids non-temp path: {p}"
                )


def assert_build_authorized(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
    chroma_dir: Path,
    package_path: Path,
) -> dict[str, Any]:
    if authorize_fixture:
        for p in (chroma_dir, package_path):
            if not _path_is_tempish(Path(p)):
                raise PermissionError(f"--authorize-fixture forbids non-temp path: {p}")
        return {"execution_mode": "fixture", "status": "approved", **DEFAULT_UNCERTAINTY}
    if run_manifest_path is None:
        raise PermissionError("pass --authorize-fixture or --run-manifest")
    manifest = load_run_manifest(run_manifest_path)
    errs = validate_run_manifest_schema(manifest)
    if errs:
        raise PermissionError("; ".join(errs))
    assert_manifest_file_matches_approval(run_manifest_path, manifest)
    assert_operation_allowed(manifest, "shadow_build")
    if str(manifest.get("execution_mode")) == "fixture" and not _path_is_tempish(chroma_dir):
        raise PermissionError("fixture run-manifest forbids non-temp chroma_dir")
    if str(manifest.get("execution_mode")) == "real":
        # Model exec still requires explicit operation; Gate 1 tests never set this live.
        pass
    return manifest


def assert_compare_authorized(
    *,
    authorize_fixture: bool,
    run_manifest_path: Path | None,
) -> dict[str, Any]:
    if authorize_fixture:
        return {"execution_mode": "fixture", "status": "approved", **DEFAULT_UNCERTAINTY}
    if run_manifest_path is None:
        raise PermissionError("pass --authorize-fixture or --run-manifest")
    manifest = load_run_manifest(run_manifest_path)
    errs = validate_run_manifest_schema(manifest)
    if errs:
        raise PermissionError("; ".join(errs))
    assert_manifest_file_matches_approval(run_manifest_path, manifest)
    assert_operation_allowed(manifest, "compare")
    return manifest


def make_fixture_run_manifest(**overrides: Any) -> dict[str, Any]:
    base = {
        "execution_mode": "fixture",
        "status": "approved",
        "operations": ["capture", "shadow_build", "compare", "adjudicate"],
        "prohibited_actions": ["promote", "service_stop", "cleanup_external"],
        "paths": {},
        **DEFAULT_UNCERTAINTY,
    }
    base.update(overrides)
    return base
