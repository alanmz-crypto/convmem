"""Calibration-only JudgeBench boundary.

This module is the narrow gate between the locked corpus and a provider adapter.
It validates the complete package first, checks caller-supplied full hashes,
and then exposes only manifest-selected calibration rows.  Holdout rows are
never transport inputs.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval_judgebench.corpus_validate import assert_corpus_valid
from eval_judgebench.provider_requests import ProviderTransport
from eval_judgebench.runner_types import CallbackCase

MAX_CALIBRATION_CALLS = 20
# Compatibility name for the standalone projection helper below. Canonical
# run_calibration uses the transport-oriented limit above.
MAX_CALIBRATION_CALLBACKS = MAX_CALIBRATION_CALLS
_SAFE_CASE_FIELDS = {
    "case_id",
    "task_kind",
    "rubric_id",
    "instruction",
    "evidence",
    "candidate",
    "candidate_mode",
}


class CalibrationBoundaryError(ValueError):
    """Raised before transport when calibration preflight is not exact."""


class ExpectedCorpusHashesError(CalibrationBoundaryError):
    """Configured full corpus hashes are missing or do not match."""


class ExpectedRubricHashesError(CalibrationBoundaryError):
    """Configured rubric hashes are missing, extra, or do not match."""


class ExpectedPromptWrapperHashError(CalibrationBoundaryError):
    """The configured prompt wrapper hash is missing or drifted."""


class ExpectedPromptHashesError(CalibrationBoundaryError):
    """The expected complete per-case prompt-hash map is missing or drifted."""


class HoldoutAccessError(CalibrationBoundaryError):
    """A prompt/report serializer was asked to process a holdout row."""


def full_sha256(path: Path | str) -> str:
    """Return the complete SHA-256 digest for a corpus artifact."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _expected_hash(expected: Mapping[str, str], filename: str) -> str | None:
    aliases = {
        "cases.jsonl": ("cases.jsonl", "cases_sha256", "cases_hash"),
        "gold.jsonl": ("gold.jsonl", "gold_sha256", "gold_hash"),
        "manifest.json": ("manifest.json", "manifest_sha256", "manifest_hash"),
    }
    for key in aliases[filename]:
        value = expected.get(key)
        if value:
            return str(value).lower()
    return None


def verify_expected_full_hashes(
    root: Path,
    expected_full_hashes: Mapping[str, str] | None,
) -> dict[str, str]:
    """Verify configured complete hashes after structural corpus validation."""
    if not expected_full_hashes:
        raise ExpectedCorpusHashesError(
            "calibration preflight requires configured full cases and gold hashes"
        )
    actual: dict[str, str] = {}
    for filename in ("cases.jsonl", "gold.jsonl"):
        configured = _expected_hash(expected_full_hashes, filename)
        if configured is None or len(configured) != 64:
            raise ExpectedCorpusHashesError(
                f"missing complete configured hash for {filename}"
            )
        if any(char not in "0123456789abcdef" for char in configured):
            raise ExpectedCorpusHashesError(f"invalid configured hash for {filename}")
        digest = full_sha256(root / filename)
        actual[filename] = digest
        if digest != configured:
            raise ExpectedCorpusHashesError(f"configured hash mismatch for {filename}")
    configured_manifest = _expected_hash(expected_full_hashes, "manifest.json")
    manifest_digest = full_sha256(root / "manifest.json")
    actual["manifest.json"] = manifest_digest
    if configured_manifest is not None:
        if len(configured_manifest) != 64:
            raise ExpectedCorpusHashesError("invalid configured hash for manifest.json")
        if manifest_digest != configured_manifest:
            raise ExpectedCorpusHashesError(
                "configured hash mismatch for manifest.json"
            )
    return actual


def verify_expected_rubric_hashes(
    root: Path,
    cases: list[dict[str, Any]],
    expected_rubric_hashes: Mapping[str, str] | None,
) -> dict[str, str]:
    """Require an exact full hash for every rubric referenced by the corpus."""
    if not expected_rubric_hashes:
        raise ExpectedRubricHashesError(
            "calibration preflight requires exact expected rubric hashes"
        )
    rubric_ids = {str(case.get("rubric_id")) for case in cases if case.get("rubric_id")}
    configured: dict[str, str] = {}
    for raw_key, raw_value in expected_rubric_hashes.items():
        key = str(raw_key)
        if key.startswith("rubric:"):
            key = key.removeprefix("rubric:")
        if key in configured:
            raise ExpectedRubricHashesError(f"duplicate expected rubric hash for {key}")
        value = str(raw_value).lower()
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ExpectedRubricHashesError(f"invalid expected rubric hash for {key}")
        configured[key] = value
    if set(configured) != rubric_ids:
        raise ExpectedRubricHashesError(
            "expected rubric hashes must exactly match corpus rubric ids"
        )
    actual = {
        rubric_id: full_sha256(root / "rubrics" / f"{rubric_id}.json")
        for rubric_id in sorted(rubric_ids)
    }
    for rubric_id, digest in actual.items():
        if configured[rubric_id] != digest:
            raise ExpectedRubricHashesError(
                f"configured rubric hash mismatch for {rubric_id}"
            )
    return actual


def _load_manifest(root: Path) -> dict[str, Any]:
    try:
        value = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CalibrationBoundaryError(f"invalid calibration manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise CalibrationBoundaryError("calibration manifest must be an object")
    return value


def _require_calibration(row: Mapping[str, Any]) -> None:
    if row.get("split") == "calibration":
        return
    # Adapter-safe projections intentionally omit split and all corpus-only
    # metadata.  They may be re-serialized for provider prompts/reports.
    if "split" not in row and not set(row) - _SAFE_CASE_FIELDS:
        return
    if row.get("split") != "calibration":
        raise HoldoutAccessError(
            "only calibration rows may reach a serializer or transport"
        )


def safe_case(row: Mapping[str, Any]) -> dict[str, Any]:
    """Project a validated calibration row to the adapter-safe case shape."""
    _require_calibration(row)
    return {
        "case_id": row["case_id"],
        "task_kind": row["task_kind"],
        "rubric_id": row["rubric_id"],
        "instruction": row["instruction"],
        "evidence": [
            {"id": item["id"], "text": item["text"]} for item in row["evidence"]
        ],
        "candidate": row["candidate"],
        "candidate_mode": row["candidate_mode"],
    }


def serialize_prompt_case(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return the only case fields permitted in a prompt input envelope."""
    return safe_case(row)


def serialize_report_case(
    row: Mapping[str, Any],
    *,
    status: str,
    judgment: Mapping[str, Any] | None = None,
    failure_code: str | None = None,
) -> dict[str, Any]:
    """Serialize calibration diagnostics without gold or corpus metadata."""
    safe = safe_case(row)
    output: dict[str, Any] = {
        "case_id": safe["case_id"],
        "task_kind": safe["task_kind"],
        "rubric_id": safe["rubric_id"],
        "status": status,
    }
    if judgment is not None:
        allowed_judgment_fields = {
            "support",
            "coverage",
            "contradiction",
            "verdict",
            "model_reported_confidence",
            "reason",
        }
        output["judgment"] = {
            key: judgment[key] for key in allowed_judgment_fields if key in judgment
        }
    if failure_code is not None:
        output["failure_code"] = failure_code
    return output


@dataclass(frozen=True)
class CalibrationPackage:
    root: Path
    manifest: dict[str, Any]
    cases: tuple[dict[str, Any], ...]
    gold_by_id: dict[str, dict[str, Any]]
    full_hashes: dict[str, str]
    rubric_hashes: dict[str, str]

    @property
    def calibration_cases(self) -> tuple[dict[str, Any], ...]:
        return tuple(safe_case(row) for row in self.cases)


def load_calibration_package(
    corpus_dir: Path | str,
    *,
    expected_full_hashes: Mapping[str, str] | None,
    expected_rubric_hashes: Mapping[str, str] | None = None,
) -> CalibrationPackage:
    """Validate the full locked corpus, then select manifest calibration rows."""
    root = Path(corpus_dir)
    # Importing the existing loader here is safe: it is only used after the
    # complete locked-corpus validator has run and before any transport exists.
    from eval_judgebench.runner import load_corpus  # local cycle break

    assert_corpus_valid(root, require_locked=True)
    full_hashes = verify_expected_full_hashes(root, expected_full_hashes)
    manifest = _load_manifest(root)
    if not isinstance(manifest.get("case_count"), int):
        raise CalibrationBoundaryError("manifest.case_count must be an integer")
    split_policy = manifest.get("split_policy") or {}
    declared_count = split_policy.get("calibration_count")
    if not isinstance(declared_count, int) or declared_count > MAX_CALIBRATION_CALLS:
        raise CalibrationBoundaryError(
            "manifest calibration count must be an integer no greater than 20"
        )
    _, all_cases, all_gold_by_id = load_corpus(root)
    rubric_hashes = verify_expected_rubric_hashes(
        root, all_cases, expected_rubric_hashes
    )
    calibration = [row for row in all_cases if row.get("split") == "calibration"]
    if len(calibration) != declared_count:
        raise CalibrationBoundaryError(
            "manifest calibration count does not match selected calibration rows"
        )
    if len(calibration) > MAX_CALIBRATION_CALLS:
        raise CalibrationBoundaryError("calibration transport limit exceeded")
    calibration_ids = {str(row["case_id"]) for row in calibration}
    # Keep the package's gold view calibration-only.  This is deliberately
    # done after complete corpus validation, so a report cannot accidentally
    # traverse holdout gold or use a partial/unvalidated package.
    gold_by_id = {
        case_id: all_gold_by_id[case_id] for case_id in sorted(calibration_ids)
    }
    return CalibrationPackage(
        root=root,
        manifest=manifest,
        cases=tuple(calibration),
        gold_by_id=gold_by_id,
        full_hashes=full_hashes,
        rubric_hashes=rubric_hashes,
    )


def invoke_calibration_callbacks(
    package: CalibrationPackage,
    callback: Callable[[CallbackCase], Any],
) -> list[Any]:
    """Invoke one callback per selected calibration row, never holdout."""
    if len(package.cases) > MAX_CALIBRATION_CALLBACKS:
        raise CalibrationBoundaryError("calibration callback limit exceeded")
    results: list[Any] = []
    for index, row in enumerate(package.cases):
        if index >= MAX_CALIBRATION_CALLBACKS:
            raise CalibrationBoundaryError("calibration callback limit exceeded")
        results.append(callback(safe_case(row)))
    return results


def _expected_prompt_hash(
    expected: str | Mapping[str, str] | None,
    *,
    family: str,
    expected_signature: Mapping[str, Any] | None,
) -> str:
    if isinstance(expected, Mapping):
        value = (
            expected.get("prompt_wrapper")
            or expected.get(f"{family}:wrapper")
            or expected.get(family)
        )
    else:
        value = expected
    if value is None and expected_signature is not None:
        contract_hashes = expected_signature.get("contract_hashes") or {}
        value = contract_hashes.get("prompt_wrapper")
    if not isinstance(value, str) or len(value) != 64:
        raise ExpectedPromptWrapperHashError(
            "calibration preflight requires an exact prompt wrapper hash"
        )
    return value


def _calibration_prompt_hashes(
    package: CalibrationPackage,
    *,
    family: str,
) -> dict[str, str]:
    """Hash each safe calibration case with its exact versioned rubric prompt."""
    from eval_judgebench.prompt_wrappers import prompt_hash
    from eval_judgebench.rubric import load_rubric

    prompt_hashes: dict[str, str] = {}
    for row in package.cases:
        safe = safe_case(row)
        case_id = str(safe["case_id"])
        rubric = load_rubric(package.root / "rubrics", str(safe["rubric_id"]))
        prompt_hashes[case_id] = prompt_hash(safe, rubric, family=family)
    if len(prompt_hashes) != len(package.cases):
        raise ExpectedPromptHashesError(
            "calibration prompt hashes must contain one entry per unique case"
        )
    return prompt_hashes


def _verify_expected_prompt_hashes(
    expected_signature: Mapping[str, Any],
    actual: Mapping[str, str],
) -> None:
    expected = expected_signature.get("prompt_hashes")
    if not isinstance(expected, Mapping):
        raise ExpectedPromptHashesError(
            "comparison signature requires a complete calibration prompt-hash map"
        )
    normalized = {str(key): str(value) for key, value in expected.items()}
    if dict(normalized) != dict(actual):
        raise ExpectedPromptHashesError("calibration prompt hashes drifted")


def _validate_provider_configuration(
    *,
    provider: str | None,
    request: Mapping[str, Any] | None,
    settings: Mapping[str, Any] | None,
    judge_model: str,
) -> tuple[str, dict[str, Any]]:
    """Validate a complete provider envelope without contacting a provider."""
    from eval_judgebench.provider_requests import (
        deepseek_decoding_signature,
        llama_decoding_signature,
        validate_provider_request,
    )

    if not provider or not request or not settings:
        raise CalibrationBoundaryError(
            "calibration preflight requires provider, request, and settings"
        )
    normalized = provider.strip().lower()
    if normalized == "deepseek":
        if request.get("model") != judge_model.strip():
            raise CalibrationBoundaryError(
                "provider request model is not the pinned judge"
            )
        validate_provider_request(normalized, request)
        expected = deepseek_decoding_signature()
        if dict(settings) != expected:
            raise CalibrationBoundaryError("DeepSeek provider settings drifted")
        return normalized, expected
    if normalized in {"llama", "ollama"}:
        from eval_judgebench.provider_requests import LLAMA_MODEL

        if judge_model.strip() != LLAMA_MODEL:
            raise CalibrationBoundaryError(
                "Llama judge model must be exactly llama3.1:8b"
            )

        runtime_digest = str(
            settings.get("runtime_digest") or request.get("runtime_digest") or ""
        )
        expected = llama_decoding_signature(runtime_digest)
        validate_provider_request(
            normalized,
            request,
            runtime_digest=runtime_digest,
        )
        if request.get("model") != LLAMA_MODEL or dict(settings) != expected:
            raise CalibrationBoundaryError("Llama model or provider settings drifted")
        return "llama", expected
    raise CalibrationBoundaryError(f"unsupported provider family: {provider!r}")


def _build_exact_provider_request(
    *,
    family: str,
    prompt: str,
    judge_model: str,
    decoding: Mapping[str, Any],
) -> dict[str, Any]:
    """Build and revalidate the one request permitted for this case."""
    from eval_judgebench.prompt_wrappers import semantic_output_schema
    from eval_judgebench.provider_requests import (
        build_deepseek_request,
        build_llama_request,
        validate_llama_request,
    )

    if family == "deepseek":
        return build_deepseek_request(prompt, model=judge_model.strip())
    schema = semantic_output_schema()
    request = build_llama_request(
        prompt,
        runtime_digest=str(decoding["runtime_digest"]),
        json_schema=schema,
    )
    validate_llama_request(
        request,
        runtime_digest=str(decoding["runtime_digest"]),
        expected_schema=schema,
    )
    return request


def _provider_invocation(
    *,
    family: str,
    request: Mapping[str, Any],
    transport: ProviderTransport,
    rubric_id: str,
    rubric_dir: Path,
    judge_identity: str,
    under_test_identity: str,
    independence: Any,
) -> Any:
    """Invoke one adapter request and classify transport/output failures."""
    from eval_judgebench.contracts import InvocationStatus, JudgeInvocationV1
    from eval_judgebench.provider_requests import (
        ProviderResponseError,
        parse_provider_response,
    )
    from eval_judgebench.runner import _validate_judgment_output

    try:
        response = transport(request)
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        return JudgeInvocationV1(
            status=InvocationStatus.PROVIDER_ERROR,
            judge_identity=judge_identity,
            under_test_identity=under_test_identity,
            independence_class=independence,
            failure_code=f"{type(exc).__name__}: {exc}",
        )
    try:
        raw = parse_provider_response(family, response)
        judgment, status, failure = _validate_judgment_output(
            raw, rubric_id, rubric_dir
        )
    except (ProviderResponseError, TypeError, ValueError) as exc:
        return JudgeInvocationV1(
            status=InvocationStatus.INVALID_OUTPUT,
            judge_identity=judge_identity,
            under_test_identity=under_test_identity,
            independence_class=independence,
            failure_code=f"{type(exc).__name__}: {exc}",
        )
    return JudgeInvocationV1(
        status=status,
        judge_identity=judge_identity,
        under_test_identity=under_test_identity,
        independence_class=independence,
        failure_code=failure,
        semantic_judgment=judgment,
    )


def _calibration_case_result(
    *,
    case: dict[str, Any],
    gold: dict[str, Any] | None,
    invocation: Any,
) -> Any:
    from eval_judgebench.contracts import InvocationStatus
    from eval_judgebench.runner import CaseResult, grade_mechanical

    mechanical = grade_mechanical(case, gold)
    expected = ((gold or {}).get("j1") or {}).get("verdict")
    agrees = None
    if (
        expected is not None
        and invocation.status == InvocationStatus.OK
        and invocation.semantic_judgment is not None
    ):
        agrees = invocation.semantic_judgment.verdict.value == expected
    return CaseResult(
        case_id=str(case.get("case_id") or case.get("id") or ""),
        mechanical=mechanical,
        invocation=invocation,
        gold_verdict=expected,
        agrees_with_gold=agrees,
    )


def run_calibration(  # pylint: disable=too-many-arguments,too-many-locals
    corpus_dir: Path | str,
    *,
    cfg: dict,
    judge_model: str,
    under_test_model: str,
    registry_path: Path | str,
    transport: ProviderTransport | None = None,
    callback: Callable[[dict[str, Any]], Any] | None = None,
    semantic_judge: Callable[[dict[str, Any]], Any] | None = None,
    canonical: bool = True,
    metric_policy_version: str = "judgebench-v1",
    expected_full_hashes: Mapping[str, str] | None = None,
    expected_rubric_hashes: Mapping[str, str] | None = None,
    expected_prompt_wrapper_hash: str | Mapping[str, str] | None = None,
    expected_comparison_signature: dict[str, Any] | None = None,
    prompt_family: str | None = None,
    provider: str | None = None,
    provider_request: Mapping[str, Any] | None = None,
    provider_settings: Mapping[str, Any] | None = None,
) -> Any:
    """Run a preflighted calibration experiment over selected rows only.

    This is intentionally separate from :func:`runner.run_judgebench`, whose
    historical API remains the general JudgeBench runner contract.
    """
    from eval_judgebench.contracts import SelectionRole
    from eval_judgebench.prompt_wrappers import prompt_wrapper_hash
    from eval_judgebench.runner import (
        _bind_candidate_provenance,
        _case_candidate_binding,
        _contract_hashes,
        _origin_key,
    )
    from eval_model_identity import load_registry, resolve_identity
    from eval_provenance import (
        attach_comparison_signature,
        build_comparison_signature,
        comparison_signature_digest,
    )

    if callback is not None or semantic_judge is not None:
        raise CalibrationBoundaryError(
            "canonical calibration accepts an injected provider transport, "
            "not an arbitrary semantic callback"
        )
    if transport is None:
        raise CalibrationBoundaryError(
            "calibration execution requires an injected provider transport"
        )
    judgebench_cfg = cfg.get("judgebench") or {}
    configured_full_hashes = expected_full_hashes or judgebench_cfg.get(
        "expected_full_hashes"
    )
    configured_rubric_hashes = expected_rubric_hashes or judgebench_cfg.get(
        "expected_rubric_hashes"
    )
    package = load_calibration_package(
        corpus_dir,
        expected_full_hashes=configured_full_hashes,
        expected_rubric_hashes=configured_rubric_hashes,
    )
    if not canonical:
        raise CalibrationBoundaryError(
            "calibration entry point requires canonical mode"
        )

    registry = load_registry(registry_path)
    if not registry.version.endswith("v2"):
        raise CalibrationBoundaryError("calibration requires identity registry v2")
    judge_identity = resolve_identity(judge_model, registry, cfg, offline=True)
    binding = _bind_candidate_provenance(
        cases=list(package.cases),
        judge_identity=judge_identity,
        caller_under_test_model=under_test_model,
        registry=registry,
        cfg=cfg,
        canonical=True,
        offline=True,
    )

    provider_name, decoding = _validate_provider_configuration(
        provider=(provider if provider is not None else judgebench_cfg.get("provider")),
        request=(
            provider_request
            if provider_request is not None
            else judgebench_cfg.get("provider_request")
        ),
        settings=(
            provider_settings
            if provider_settings is not None
            else judgebench_cfg.get("provider_settings")
        ),
        judge_model=judge_model,
    )
    family = (
        (prompt_family if prompt_family is not None else provider_name).strip().lower()
    )
    if family != provider_name:
        raise CalibrationBoundaryError(
            "prompt family must equal the validated provider family"
        )
    wrapper_hash = prompt_wrapper_hash(family)
    expected_wrapper = _expected_prompt_hash(
        expected_prompt_wrapper_hash,
        family=family,
        expected_signature=expected_comparison_signature,
    )
    if wrapper_hash != expected_wrapper:
        raise ExpectedPromptWrapperHashError("prompt wrapper hash drifted")
    if expected_comparison_signature is None:
        raise CalibrationBoundaryError(
            "calibration preflight requires an expected comparison signature"
        )

    manifest = package.manifest
    contract_hashes = _contract_hashes(package.root, list(package.cases))
    contract_hashes["prompt_wrapper"] = wrapper_hash
    prompt_hashes = _calibration_prompt_hashes(package, family=family)
    resolved_identities = {"judge": judge_identity.to_record_dict()}
    for index, origin in enumerate(binding.origins):
        identity = binding.identities[_origin_key(origin)]
        resolved_identities[f"candidate_origin:{index}"] = {
            **identity.to_record_dict(),
            "frozen_model": origin["model"],
            "frozen_provider": origin["provider"],
            "frozen_version": origin["version"],
        }
    signature = build_comparison_signature(
        evaluation_surface=str(manifest.get("manifest_version") or "judgebench"),
        case_hash=package.full_hashes["cases.jsonl"],
        fixture_hash_value=package.full_hashes["manifest.json"],
        gold_hash=package.full_hashes["gold.jsonl"],
        contract_hashes=contract_hashes,
        identity_policy_version=registry.version,
        resolved_identities=resolved_identities,
        judge_pin={
            "model": judge_model.strip(),
            "lineage": judge_identity.base_lineage,
            "digest": judge_identity.revision_digest,
            "quant": judge_identity.quantization,
            "role": SelectionRole.PRIMARY.value,
        },
        under_test_provenance={
            "source": "frozen_candidate_origin",
            "origins": binding.origins,
        },
        independence_class=binding.aggregate.value,
        decoding_params=decoding,
        model_serving_version=str(judgebench_cfg.get("runtime_version") or ""),
        metric_policy_version=metric_policy_version,
        prompt_hashes=prompt_hashes,
        prompt_family=family,
        rubric_hashes=package.rubric_hashes,
        full_corpus_hashes=package.full_hashes,
    )
    _verify_expected_prompt_hashes(expected_comparison_signature, prompt_hashes)
    if comparison_signature_digest(signature) != comparison_signature_digest(
        expected_comparison_signature
    ):
        raise CalibrationBoundaryError(
            "comparison signature drifted; aborting before calibration transport"
        )

    results = []
    for case in package.cases:
        case_id = str(case.get("case_id") or case.get("id") or "")
        candidate_identity, independence = _case_candidate_binding(case, binding)
        safe = safe_case(case)
        from eval_judgebench.prompt_wrappers import build_semantic_prompt, prompt_hash
        from eval_judgebench.rubric import load_rubric

        rubric = load_rubric(package.root / "rubrics", str(safe["rubric_id"]))
        prompt = build_semantic_prompt(safe, rubric, family=family)
        if prompt_hash(safe, rubric, family=family) != prompt_hashes[case_id]:
            raise ExpectedPromptHashesError(
                "calibration prompt changed after preflight"
            )
        request = _build_exact_provider_request(
            family=family,
            prompt=prompt,
            judge_model=judge_model,
            decoding=decoding,
        )
        invocation = _provider_invocation(
            family=family,
            request=request,
            transport=transport,
            rubric_id=str(safe["rubric_id"]),
            rubric_dir=package.root / "rubrics",
            judge_identity=judge_identity.normalized_name,
            under_test_identity=candidate_identity,
            independence=independence,
        )
        results.append(
            _calibration_case_result(
                case=safe,
                gold=package.gold_by_id.get(case_id),
                invocation=invocation,
            )
        )

    gold_hash_after = full_sha256(Path(package.root) / "gold.jsonl")
    if gold_hash_after != package.full_hashes["gold.jsonl"]:
        raise CalibrationBoundaryError("gold hash changed during calibration transport")
    from eval_judgebench.runner import RunResult

    frozen_model_label = (
        ",".join(origin["model"] for origin in binding.origins) or "human_curated"
    )
    provenance = attach_comparison_signature(
        {
            "model_name": frozen_model_label,
            "model_digest": "",
            "quant": "",
            "ollama_version": str(judgebench_cfg.get("runtime_version") or ""),
            "fixture_hash": package.full_hashes["cases.jsonl"],
        },
        signature,
    )
    return RunResult(
        cases=results,
        independence_class=binding.aggregate,
        comparison_signature=signature,
        provenance=provenance,
        gold_hash_before=package.full_hashes["gold.jsonl"],
        gold_hash_after=gold_hash_after,
        pinned_judge_model=judge_model.strip(),
    )


run_judgebench_calibration = run_calibration
