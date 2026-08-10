"""Hermetic JudgeBench safety-package tests.

The corpus in these tests is synthetic and contains explicit calibration and
holdout sentinels.  No locked JudgeBench JSONL is read or executed here.
"""

# Independent locked-contract fixtures intentionally repeat schema-shaped data.
# pylint: disable=duplicate-code

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import requests

import eval_model_identity
from eval_judgebench.calibration import (
    CalibrationBoundaryError,
    CalibrationPackage,
    ExpectedCorpusHashesError,
    ExpectedPromptHashesError,
    ExpectedPromptWrapperHashError,
    ExpectedRubricHashesError,
    HoldoutAccessError,
    full_sha256,
    invoke_calibration_callbacks,
    load_calibration_package,
    run_calibration,
    serialize_prompt_case,
    serialize_report_case,
)
from eval_judgebench.contracts import (
    IndependenceClass,
    InvocationStatus,
    JudgeInvocationV1,
    SelectionRole,
)
from eval_judgebench.prompt_wrappers import (
    build_semantic_prompt,
    prompt_hash,
    prompt_wrapper_hash,
    semantic_output_schema,
)
from eval_judgebench.provider_requests import (
    ProviderPreflightError,
    ProviderResponseError,
    build_deepseek_request,
    build_llama_request,
    deepseek_decoding_signature,
    llama_decoding_signature,
    parse_provider_response,
    validate_deepseek_request,
    validate_llama_request,
)
from eval_judgebench.rubric import load_rubric
from eval_judgebench.runner import (
    _bind_candidate_provenance,
    _contract_hashes,
    _origin_key,
)
from eval_model_identity import (
    CanonicalPreflightError,
    load_registry,
    preflight_registry_v2_origins,
    resolve_identity,
)
from eval_provenance import build_comparison_signature

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_V2 = ROOT / "eval_corpus/fixtures/judgebench/identity-registry-v2.json"


def _valid_semantic_output() -> dict[str, str]:
    return {
        "support": "full",
        "coverage": "complete",
        "contradiction": "none",
        "verdict": "pass",
    }


def _write_synthetic_package(
    root: Path,
    *,
    calibration_count: int = 20,
    holdout_count: int = 10,
    candidate_origin: dict | None = None,
) -> dict[str, str]:
    rubric_dir = root / "rubrics"
    rubric_dir.mkdir()
    rubric = {
        "id": "synthesis-grounded-v1",
        "version": 1,
        "task": "synthesis",
        "rules": {},
    }
    (rubric_dir / "synthesis-grounded-v1.json").write_text(
        json.dumps(rubric, sort_keys=True), encoding="utf-8"
    )
    rows = []
    gold = []
    origin = candidate_origin or {
        "kind": "human_curated",
        "author": "Ryan",
        "version": "test",
    }
    for index in range(calibration_count + holdout_count):
        split = "calibration" if index < calibration_count else "holdout"
        case_id = f"synthetic-{split}-{index + 1:02d}"
        sentinel = f"{split.upper()}_SENTINEL_{index + 1:02d}"
        rows.append(
            {
                "case_id": case_id,
                "task_kind": "synthesis",
                "rubric_id": "synthesis-grounded-v1",
                "instruction": "Answer from supplied evidence only.",
                "evidence": [{"id": 1, "text": sentinel}],
                "candidate": f"{sentinel} [1].",
                "candidate_mode": "answer",
                "candidate_origin": origin,
                "tags": ["synthetic"],
                "split": split,
            }
        )
        gold.append(
            {
                "case_id": case_id,
                "j0": {
                    "expected_pass": True,
                    "expected_candidate_mode": "answer",
                    "required_tokens": ["[1]"],
                },
                "j1": {
                    "support": "full",
                    "coverage": "complete",
                    "contradiction": "none",
                    "verdict": "pass",
                },
                "rationale": "Synthetic fixture only.",
                "lock": {"status": "locked", "owner": "Ryan", "locked_at": "test"},
            }
        )
    cases_text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    gold_text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in gold)
    (root / "cases.jsonl").write_text(cases_text, encoding="utf-8")
    (root / "gold.jsonl").write_text(gold_text, encoding="utf-8")
    manifest = {
        "manifest_version": "synthetic-judgebench-v1",
        "corpus": "judgebench",
        "bucket": "semantic-v1",
        "schema": "JudgeBenchCorpusV1",
        "rubric_dir": "rubrics/",
        "case_count": len(rows),
        "case_rows": [row["case_id"] for row in rows],
        "split_policy": {
            "calibration_count": calibration_count,
            "holdout_count": holdout_count,
            "minimum_holdout": holdout_count,
        },
        "gold_lock": {"status": "locked", "owner": "Ryan"},
        "hashes": {
            "cases.jsonl": hashlib.sha256(cases_text.encode()).hexdigest(),
            "gold.jsonl": hashlib.sha256(gold_text.encode()).hexdigest(),
        },
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )
    return {
        "cases.jsonl": full_sha256(root / "cases.jsonl"),
        "gold.jsonl": full_sha256(root / "gold.jsonl"),
        "synthesis-grounded-v1": full_sha256(
            root / "rubrics" / "synthesis-grounded-v1.json"
        ),
    }


def _expected_signature(
    root: Path,
    hashes: dict[str, str],
    *,
    judge_model: str = "deepseek-v4-pro",
    family: str = "deepseek",
    decoding: dict | None = None,
    candidate_origin: dict | None = None,
    under_test_model: str = "human_curated",
) -> dict:
    rubric_hashes = {"synthesis-grounded-v1": hashes["synthesis-grounded-v1"]}
    package = load_calibration_package(
        root,
        expected_full_hashes={
            key: hashes[key] for key in ("cases.jsonl", "gold.jsonl")
        },
        expected_rubric_hashes=rubric_hashes,
    )
    registry = load_registry(REGISTRY_V2)
    judge = resolve_identity(judge_model, registry, {}, offline=True)
    binding = None
    if candidate_origin is not None:
        binding = _bind_candidate_provenance(
            cases=list(package.cases),
            judge_identity=judge,
            caller_under_test_model=under_test_model,
            registry=registry,
            cfg={},
            canonical=True,
            offline=True,
        )
    contract_hashes = _contract_hashes(root, list(package.cases))
    wrapper_hash = prompt_wrapper_hash(family)
    contract_hashes["prompt_wrapper"] = wrapper_hash
    rubric = load_rubric(root / "rubrics", "synthesis-grounded-v1")
    prompt_hashes = {
        case["case_id"]: prompt_hash(case, rubric, family=family)
        for case in package.calibration_cases
    }
    resolved_identities = {"judge": judge.to_record_dict()}
    origins = []
    independence = IndependenceClass.NOT_APPLICABLE.value
    if binding is not None:
        origins = binding.origins
        independence = binding.aggregate.value
        for index, origin in enumerate(binding.origins):
            identity = binding.identities[_origin_key(origin)]
            resolved_identities[f"candidate_origin:{index}"] = {
                **identity.to_record_dict(),
                "frozen_model": origin["model"],
                "frozen_provider": origin["provider"],
                "frozen_version": origin["version"],
            }
    return build_comparison_signature(
        evaluation_surface=package.manifest["manifest_version"],
        case_hash=package.full_hashes["cases.jsonl"],
        fixture_hash_value=package.full_hashes["manifest.json"],
        gold_hash=package.full_hashes["gold.jsonl"],
        contract_hashes=contract_hashes,
        identity_policy_version=registry.version,
        resolved_identities=resolved_identities,
        judge_pin={
            "model": judge_model,
            "lineage": judge.base_lineage,
            "digest": judge.revision_digest,
            "quant": judge.quantization,
            "role": SelectionRole.PRIMARY.value,
        },
        under_test_provenance={
            "source": "frozen_candidate_origin",
            "origins": origins,
        },
        independence_class=independence,
        decoding_params=decoding or deepseek_decoding_signature(),
        model_serving_version="",
        metric_policy_version="judgebench-v1",
        prompt_hashes=prompt_hashes,
        prompt_family=family,
        rubric_hashes=rubric_hashes,
        full_corpus_hashes=package.full_hashes,
    )


def test_canonical_calibration_resolves_frozen_origin_offline_before_20_transports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    origin = {
        "kind": "model_generated",
        "model": "gpt-5-codex-sol",
        "provider": "openai",
        "version": "test",
    }
    hashes = _write_synthetic_package(tmp_path, candidate_origin=origin)
    transport_calls = 0

    def fail_network(*args, **kwargs):
        raise AssertionError("identity resolution must remain offline")

    monkeypatch.setattr(requests, "get", fail_network)
    monkeypatch.setattr(eval_model_identity, "model_digest_and_quant", fail_network)

    def transport(request: dict):
        nonlocal transport_calls
        transport_calls += 1
        assert request["model"] == "deepseek-v4-pro"
        return {
            "choices": [{"message": {"content": json.dumps(_valid_semantic_output())}}]
        }

    result = run_calibration(
        tmp_path,
        cfg={"models": {}},
        judge_model="deepseek-v4-pro",
        under_test_model="gpt-5-codex-sol",
        registry_path=REGISTRY_V2,
        transport=transport,
        expected_full_hashes=hashes,
        expected_rubric_hashes={
            "synthesis-grounded-v1": hashes["synthesis-grounded-v1"]
        },
        expected_prompt_wrapper_hash=prompt_wrapper_hash("deepseek"),
        expected_comparison_signature=_expected_signature(
            tmp_path,
            hashes,
            candidate_origin=origin,
            under_test_model="gpt-5-codex-sol",
        ),
        provider="deepseek",
        provider_request=build_deepseek_request("safe prompt", model="deepseek-v4-pro"),
        provider_settings=deepseek_decoding_signature(),
    )

    assert transport_calls == 20
    assert len(result.cases) == 20
    assert all(case.invocation.status == InvocationStatus.OK for case in result.cases)
    assert result.independence_class == IndependenceClass.CROSS_FAMILY


def test_registry_v2_preserves_alias_provenance_and_cross_family_matrix():
    from eval_judgebench.identity_registry import load_identity_registry

    registry = load_identity_registry(REGISTRY_V2)
    assert registry.resolve_alias("gpt-5.6") == "gpt-5.6-sol"
    assert registry.alias_provenance("gpt-5.6") == "public"
    assert registry.alias_provenance("gpt-5-codex-sol") == "historical_local"
    assert registry.alias_metadata("gpt-5-codex-sol")["public"] is False
    assert registry.records["gpt-5.6-sol"].revision_digest is None
    result = preflight_registry_v2_origins(
        ["deepseek-v4-pro", "deepseek-v4-flash", "llama3.1:8b"],
        registry=registry,
    )
    assert set(result.values()) == {IndependenceClass.CROSS_FAMILY}


def test_calibration_boundary_hashes_and_transport_exclude_holdout(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    package = load_calibration_package(
        tmp_path,
        expected_full_hashes={
            key: hashes[key] for key in ("cases.jsonl", "gold.jsonl")
        },
        expected_rubric_hashes={
            "synthesis-grounded-v1": hashes["synthesis-grounded-v1"]
        },
    )
    assert set(package.gold_by_id) == {
        f"synthetic-calibration-{index:02d}" for index in range(1, 21)
    }
    seen: list[dict] = []

    def transport(request: dict):
        seen.append(request)
        prompts.append(request["messages"][0]["content"])
        reports.append({"status": "ok"})
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "support": "full",
                                "coverage": "complete",
                                "contradiction": "none",
                                "verdict": "pass",
                            }
                        )
                    }
                }
            ]
        }

    prompts: list[str] = []
    reports: list[dict] = []
    result = run_calibration(
        tmp_path,
        cfg={"models": {}},
        judge_model="deepseek-v4-pro",
        under_test_model="human_curated",
        registry_path=REGISTRY_V2,
        transport=transport,
        expected_full_hashes=hashes,
        expected_rubric_hashes={
            "synthesis-grounded-v1": hashes["synthesis-grounded-v1"]
        },
        expected_prompt_wrapper_hash=prompt_wrapper_hash("deepseek"),
        expected_comparison_signature=_expected_signature(tmp_path, hashes),
        provider="deepseek",
        provider_request=build_deepseek_request("safe prompt", model="deepseek-v4-pro"),
        provider_settings=deepseek_decoding_signature(),
    )
    assert len(result.cases) == 20
    assert len(seen) == 20
    assert len(prompts) == len(reports) == 20
    assert "CALIBRATION_SENTINEL" in json.dumps(seen)
    assert all("synthetic-calibration-" in prompt for prompt in prompts)
    assert "synthetic-holdout-" not in json.dumps(seen + reports + prompts)
    assert "HOLDOUT_SENTINEL" not in json.dumps(seen + reports + prompts)
    assert all("HOLDOUT_SENTINEL" not in repr(case) for case in result.cases)
    assert len(result.comparison_signature["case_hash"]) == 64
    assert len(result.comparison_signature["gold_hash"]) == 64
    assert "prompt_wrapper" in result.comparison_signature["contract_hashes"]
    assert len(result.comparison_signature["prompt_hashes"]) == 20
    assert set(result.comparison_signature["prompt_hashes"]) == {
        f"synthetic-calibration-{index:02d}" for index in range(1, 21)
    }
    assert all(request["model"] == "deepseek-v4-pro" for request in seen)
    assert all(request["attempts"] == 1 for request in seen)
    assert all(request["stream"] is False for request in seen)
    assert "judge_recommendation" not in result.provenance


def test_missing_or_drifted_hashes_abort_before_transport(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    with pytest.raises(ExpectedCorpusHashesError):
        run_calibration(
            tmp_path,
            cfg={"models": {}},
            judge_model="deepseek-v4-pro",
            under_test_model="human_curated",
            registry_path=REGISTRY_V2,
            transport=lambda _: pytest.fail("transport must not run"),
            expected_full_hashes={"cases.jsonl": hashes["cases.jsonl"]},
        )


def test_arbitrary_semantic_callback_substitution_is_rejected(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    kwargs = _valid_calibration_kwargs(tmp_path, hashes, lambda _: None)
    kwargs["callback"] = lambda _: JudgeInvocationV1(
        status=InvocationStatus.OK,
        judge_identity="wrong",
        under_test_identity="wrong",
    )
    with pytest.raises(
        CalibrationBoundaryError, match="not an arbitrary semantic callback"
    ):
        run_calibration(tmp_path, **kwargs)


def test_transport_errors_and_invalid_outputs_have_no_retry_or_semantic_fail(
    tmp_path: Path,
):
    hashes = _write_synthetic_package(tmp_path)
    calls = 0

    def transport(_: dict):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("synthetic provider outage")
        if calls == 2:
            return []
        if calls == 3:
            return {"choices": [{"message": {"content": "not-json"}}]}
        if calls == 4:
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    **_valid_semantic_output(),
                                    "verdict": "not-a-verdict",
                                }
                            )
                        }
                    }
                ]
            }
        return {
            "choices": [{"message": {"content": json.dumps(_valid_semantic_output())}}]
        }

    result = run_calibration(
        tmp_path,
        **_valid_calibration_kwargs(tmp_path, hashes, transport),
    )
    assert calls == 20
    statuses = [case.invocation.status for case in result.cases]
    assert statuses[0] == InvocationStatus.PROVIDER_ERROR
    assert statuses[1:4] == [
        InvocationStatus.INVALID_OUTPUT,
        InvocationStatus.INVALID_OUTPUT,
        InvocationStatus.INVALID_OUTPUT,
    ]
    assert all(
        case.invocation.status != InvocationStatus.OK for case in result.cases[:4]
    )
    assert all(case.agrees_with_gold is None for case in result.cases[:4])


@pytest.mark.parametrize(
    ("provider", "response"),
    [
        ("deepseek", _valid_semantic_output()),
        ("llama", _valid_semantic_output()),
        ("deepseek", {"response": json.dumps(_valid_semantic_output())}),
        (
            "llama",
            {
                "choices": [
                    {"message": {"content": json.dumps(_valid_semantic_output())}}
                ]
            },
        ),
        (
            "deepseek",
            {
                "choices": [
                    {"message": {"content": json.dumps(_valid_semantic_output())}}
                ],
                "response": json.dumps(_valid_semantic_output()),
            },
        ),
        (
            "llama",
            {
                "choices": [
                    {"message": {"content": json.dumps(_valid_semantic_output())}}
                ],
                "response": json.dumps(_valid_semantic_output()),
            },
        ),
        ("unsupported", {"response": json.dumps(_valid_semantic_output())}),
    ],
)
def test_provider_response_requires_exact_supported_envelope(
    provider: str,
    response: dict,
):
    with pytest.raises(ProviderResponseError):
        parse_provider_response(provider, response)


@pytest.mark.parametrize(
    ("judge_model", "family"),
    [
        ("deepseek-v4-pro", "deepseek"),
        ("deepseek-v4-flash", "deepseek"),
        ("llama3.1:8b", "llama"),
    ],
)
def test_all_provider_paths_build_internal_exact_requests(
    tmp_path: Path, judge_model: str, family: str
):
    hashes = _write_synthetic_package(tmp_path)
    if family == "deepseek":
        settings = deepseek_decoding_signature()
        provider_request = build_deepseek_request(
            "caller prompt is ignored", model=judge_model
        )
    else:
        settings = llama_decoding_signature("sha256:synthetic-runtime")
        provider_request = build_llama_request(
            "caller prompt is ignored",
            runtime_digest="sha256:synthetic-runtime",
            json_schema={"type": "object"},
        )
    provider_requests_seen: list[dict] = []

    def transport(request: dict):
        provider_requests_seen.append(request)
        if family == "deepseek":
            content = json.dumps(_valid_semantic_output())
            return {"choices": [{"message": {"content": content}}]}
        return {"response": json.dumps(_valid_semantic_output())}

    result = run_calibration(
        tmp_path,
        cfg={"models": {}},
        judge_model=judge_model,
        under_test_model="human_curated",
        registry_path=REGISTRY_V2,
        transport=transport,
        expected_full_hashes=hashes,
        expected_rubric_hashes={
            "synthesis-grounded-v1": hashes["synthesis-grounded-v1"]
        },
        expected_prompt_wrapper_hash=prompt_wrapper_hash(family),
        expected_comparison_signature=_expected_signature(
            tmp_path,
            hashes,
            judge_model=judge_model,
            family=family,
            decoding=settings,
        ),
        provider=family,
        provider_request=provider_request,
        provider_settings=settings,
    )
    assert len(provider_requests_seen) == 20
    assert all(request["attempts"] == 1 for request in provider_requests_seen)
    assert all(request["stream"] is False for request in provider_requests_seen)
    prompt_digests = {
        hashlib.sha256(
            (
                request["messages"][0]["content"]
                if family == "deepseek"
                else request["prompt"]
            ).encode()
        ).hexdigest()
        for request in provider_requests_seen
    }
    assert prompt_digests == set(result.comparison_signature["prompt_hashes"].values())
    if family == "deepseek":
        assert all(
            request["model"] == judge_model for request in provider_requests_seen
        )
        assert all(
            request["reasoning_effort"] == "high" for request in provider_requests_seen
        )
    else:
        assert all(
            request["model"] == "llama3.1:8b" for request in provider_requests_seen
        )
        assert all(
            request["runtime_digest"] == "sha256:synthetic-runtime"
            for request in provider_requests_seen
        )
        assert all(
            request["format"] == semantic_output_schema()
            for request in provider_requests_seen
        )


def test_twenty_first_calibration_callback_is_rejected_before_callback(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    package = CalibrationPackage(
        root=tmp_path,
        manifest={},
        cases=tuple(
            {
                "case_id": f"case-{index}",
                "task_kind": "synthesis",
                "rubric_id": "synthesis-grounded-v1",
                "instruction": "safe",
                "evidence": [{"id": 1, "text": "safe"}],
                "candidate": "safe [1]",
                "candidate_mode": "answer",
                "split": "calibration",
            }
            for index in range(21)
        ),
        gold_by_id={},
        full_hashes={},
        rubric_hashes={},
    )
    calls = 0

    def callback(_: dict) -> None:
        nonlocal calls
        calls += 1

    with pytest.raises(CalibrationBoundaryError):
        invoke_calibration_callbacks(package, callback)
    assert calls == 0
    assert hashes["cases.jsonl"] == full_sha256(tmp_path / "cases.jsonl")


def test_serializers_and_prompt_wrapper_are_calibration_only():
    row = {
        "case_id": "cal",
        "task_kind": "synthesis",
        "rubric_id": "synthesis-grounded-v1",
        "instruction": "Use evidence.",
        "evidence": [{"id": 1, "text": "safe"}],
        "candidate": "safe [1]",
        "candidate_mode": "answer",
        "split": "calibration",
        "tags": ["hidden"],
        "candidate_origin": {"kind": "model_generated"},
        "rationale": "hidden",
        "gold": {"verdict": "fail"},
    }
    prompt = build_semantic_prompt(
        row,
        {"id": "synthesis-grounded-v1", "version": 1, "task": "synthesis", "rules": {}},
        family="deepseek",
    )
    report = serialize_report_case(row, status="ok", judgment={"verdict": "pass"})
    assert "hidden" not in prompt
    assert "hidden" not in json.dumps(report)
    assert set(report) == {"case_id", "task_kind", "rubric_id", "status", "judgment"}
    holdout = {**row, "split": "holdout", "candidate": "HOLDOUT_SENTINEL"}
    with pytest.raises(HoldoutAccessError):
        serialize_prompt_case(holdout)
    with pytest.raises(HoldoutAccessError):
        serialize_report_case(holdout, status="ok")


def test_provider_builders_pin_settings_and_reject_drift():
    prompt = "safe prompt"
    deepseek = build_deepseek_request(prompt, model="deepseek-v4-pro")
    assert validate_deepseek_request(deepseek)
    assert "temperature" not in deepseek
    assert deepseek_decoding_signature()["temperature"]["status"] == "unsupported"
    with pytest.raises(ProviderPreflightError):
        validate_deepseek_request({**deepseek, "temperature": 0})

    schema = {"type": "object", "additionalProperties": False}
    llama = build_llama_request(
        prompt, runtime_digest="sha256:test", json_schema=schema
    )
    assert validate_llama_request(
        llama, runtime_digest="sha256:test", expected_schema=schema
    )
    assert llama["model"] == "llama3.1:8b"
    assert llama_decoding_signature("sha256:test")["num_ctx"] == 8192
    with pytest.raises(ProviderPreflightError):
        validate_llama_request(
            llama, runtime_digest="sha256:drift", expected_schema=schema
        )


def _valid_calibration_kwargs(root: Path, hashes: dict[str, str], transport):
    return {
        "cfg": {"models": {}},
        "judge_model": "deepseek-v4-pro",
        "under_test_model": "human_curated",
        "registry_path": REGISTRY_V2,
        "transport": transport,
        "expected_full_hashes": hashes,
        "expected_rubric_hashes": {
            "synthesis-grounded-v1": hashes["synthesis-grounded-v1"]
        },
        "expected_prompt_wrapper_hash": prompt_wrapper_hash("deepseek"),
        "expected_comparison_signature": _expected_signature(root, hashes),
        "provider": "deepseek",
        "provider_request": build_deepseek_request(
            "safe prompt", model="deepseek-v4-pro"
        ),
        "provider_settings": deepseek_decoding_signature(),
    }


@pytest.mark.parametrize(
    ("change", "expected_error"),
    [
        ("rubric", ExpectedRubricHashesError),
        ("wrapper", ExpectedPromptWrapperHashError),
        ("prompt", ExpectedPromptHashesError),
        ("provider_settings", CalibrationBoundaryError),
        ("provider_model", CalibrationBoundaryError),
        ("signature", CalibrationBoundaryError),
        ("unresolved_identity", CanonicalPreflightError),
        ("provider_conflict", CanonicalPreflightError),
    ],
)
def test_drift_and_identity_failures_happen_before_any_transport(
    tmp_path: Path, change: str, expected_error: type[Exception]
):
    candidate_origin = None
    if change == "unresolved_identity":
        candidate_origin = {
            "kind": "model_generated",
            "model": "unknown-frozen-model",
            "provider": "unknown-provider",
            "version": "test",
        }
    elif change == "provider_conflict":
        candidate_origin = {
            "kind": "model_generated",
            "model": "gpt-5-codex-sol",
            "provider": "wrong-provider",
            "version": "test",
        }
    hashes = _write_synthetic_package(tmp_path, candidate_origin=candidate_origin)
    calls = 0

    def transport(_: dict) -> None:
        nonlocal calls
        calls += 1

    kwargs = _valid_calibration_kwargs(tmp_path, hashes, transport)
    if change == "rubric":
        kwargs["expected_rubric_hashes"] = {"synthesis-grounded-v1": "0" * 64}
    elif change == "wrapper":
        kwargs["expected_prompt_wrapper_hash"] = "0" * 64
    elif change == "prompt":
        signature = dict(kwargs["expected_comparison_signature"])
        signature["prompt_hashes"] = dict(signature["prompt_hashes"])
        first = next(iter(signature["prompt_hashes"]))
        signature["prompt_hashes"][first] = "0" * 64
        kwargs["expected_comparison_signature"] = signature
    elif change == "provider_settings":
        kwargs["provider_settings"] = {
            **deepseek_decoding_signature(),
            "reasoning_effort": "low",
        }
    elif change == "provider_model":
        kwargs["provider_request"] = build_deepseek_request(
            "safe prompt", model="deepseek-v4-flash"
        )
    elif change == "signature":
        signature = dict(kwargs["expected_comparison_signature"])
        signature["metric_policy_version"] = "drifted-policy"
        kwargs["expected_comparison_signature"] = signature
    elif change == "unresolved_identity":
        kwargs["under_test_model"] = "unknown-frozen-model"
    elif change == "provider_conflict":
        kwargs["under_test_model"] = "gpt-5-codex-sol"

    with pytest.raises(expected_error):
        run_calibration(tmp_path, **kwargs)
    assert calls == 0


def test_prompt_family_must_match_validated_provider(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    kwargs = _valid_calibration_kwargs(tmp_path, hashes, lambda _: None)
    kwargs["prompt_family"] = "llama"
    with pytest.raises(CalibrationBoundaryError):
        run_calibration(tmp_path, **kwargs)


def test_calibration_execution_requires_transport(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    kwargs = _valid_calibration_kwargs(tmp_path, hashes, None)
    kwargs.pop("transport")
    with pytest.raises(
        CalibrationBoundaryError, match="requires an injected provider transport"
    ):
        run_calibration(tmp_path, **kwargs)
