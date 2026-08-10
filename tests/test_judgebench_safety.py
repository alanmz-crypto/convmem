"""Hermetic JudgeBench safety-package tests.

The corpus in these tests is synthetic and contains explicit calibration and
holdout sentinels.  No locked JudgeBench JSONL is read or executed here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

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
)
from eval_judgebench.provider_requests import (
    ProviderPreflightError,
    build_deepseek_request,
    build_llama_request,
    deepseek_decoding_signature,
    llama_decoding_signature,
    validate_deepseek_request,
    validate_llama_request,
)
from eval_judgebench.rubric import load_rubric
from eval_judgebench.runner import _contract_hashes
from eval_model_identity import (
    CanonicalPreflightError,
    load_registry,
    preflight_registry_v2_origins,
    resolve_identity,
)
from eval_provenance import build_comparison_signature

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_V2 = ROOT / "eval_corpus/fixtures/judgebench/identity-registry-v2.json"


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


def _expected_signature(root: Path, hashes: dict[str, str]) -> dict:
    rubric_hashes = {"synthesis-grounded-v1": hashes["synthesis-grounded-v1"]}
    package = load_calibration_package(
        root,
        expected_full_hashes={
            key: hashes[key] for key in ("cases.jsonl", "gold.jsonl")
        },
        expected_rubric_hashes=rubric_hashes,
    )
    registry = load_registry(REGISTRY_V2)
    judge = resolve_identity("deepseek-v4-pro", registry, {}, offline=True)
    contract_hashes = _contract_hashes(root, list(package.cases))
    wrapper_hash = prompt_wrapper_hash("deepseek")
    contract_hashes["prompt_wrapper"] = wrapper_hash
    rubric = load_rubric(root / "rubrics", "synthesis-grounded-v1")
    prompt_hashes = {
        case["case_id"]: prompt_hash(case, rubric, family="deepseek")
        for case in package.calibration_cases
    }
    return build_comparison_signature(
        evaluation_surface=package.manifest["manifest_version"],
        case_hash=package.full_hashes["cases.jsonl"],
        fixture_hash_value=package.full_hashes["manifest.json"],
        gold_hash=package.full_hashes["gold.jsonl"],
        contract_hashes=contract_hashes,
        identity_policy_version=registry.version,
        resolved_identities={"judge": judge.to_record_dict()},
        judge_pin={
            "model": "deepseek-v4-pro",
            "lineage": judge.base_lineage,
            "digest": judge.revision_digest,
            "quant": judge.quantization,
            "role": SelectionRole.PRIMARY.value,
        },
        under_test_provenance={"source": "frozen_candidate_origin", "origins": []},
        independence_class=IndependenceClass.NOT_APPLICABLE.value,
        decoding_params=deepseek_decoding_signature(),
        model_serving_version="",
        metric_policy_version="judgebench-v1",
        prompt_hashes=prompt_hashes,
        prompt_family="deepseek",
        rubric_hashes=rubric_hashes,
        full_corpus_hashes=package.full_hashes,
    )


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


def test_calibration_boundary_hashes_and_callbacks_exclude_holdout(tmp_path: Path):
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

    def callback(case: dict):
        seen.append(case)
        rubric = load_rubric(tmp_path / "rubrics", case["rubric_id"])
        prompts.append(build_semantic_prompt(case, rubric, family="deepseek"))
        reports.append(serialize_report_case(case, status="ok"))
        return JudgeInvocationV1(
            status=InvocationStatus.NOT_RUN,
            judge_identity="deepseek-v4-pro",
            under_test_identity="human_curated",
            independence_class=IndependenceClass.NOT_APPLICABLE,
        )

    prompts: list[str] = []
    reports: list[dict] = []
    result = run_calibration(
        tmp_path,
        cfg={"models": {}},
        judge_model="deepseek-v4-pro",
        under_test_model="human_curated",
        registry_path=REGISTRY_V2,
        callback=callback,
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
    assert all(case["case_id"].startswith("synthetic-calibration-") for case in seen)
    assert "synthetic-holdout-" not in json.dumps(seen + reports + prompts)
    assert "HOLDOUT_SENTINEL" not in json.dumps(seen + reports + prompts)
    assert all("HOLDOUT_SENTINEL" not in repr(case) for case in result.cases)
    assert len(result.comparison_signature["case_hash"]) == 64
    assert len(result.comparison_signature["gold_hash"]) == 64
    assert "prompt_wrapper" in result.comparison_signature["contract_hashes"]
    assert len(result.comparison_signature["prompt_hashes"]) == 20
    assert set(result.comparison_signature["prompt_hashes"]) == {
        case["case_id"] for case in seen
    }
    assert "judge_recommendation" not in result.provenance


def test_missing_or_drifted_hashes_abort_before_callback(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    with pytest.raises(ExpectedCorpusHashesError):
        run_calibration(
            tmp_path,
            cfg={"models": {}},
            judge_model="deepseek-v4-pro",
            under_test_model="human_curated",
            registry_path=REGISTRY_V2,
            callback=lambda _: pytest.fail("callback must not run"),
            expected_full_hashes={"cases.jsonl": hashes["cases.jsonl"]},
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


def _valid_calibration_kwargs(root: Path, hashes: dict[str, str], callback):
    return {
        "cfg": {"models": {}},
        "judge_model": "deepseek-v4-pro",
        "under_test_model": "human_curated",
        "registry_path": REGISTRY_V2,
        "callback": callback,
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
def test_drift_and_identity_failures_happen_before_any_callback(
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

    def callback(_: dict) -> None:
        nonlocal calls
        calls += 1

    kwargs = _valid_calibration_kwargs(tmp_path, hashes, callback)
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


def test_calibration_execution_requires_callback(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    kwargs = _valid_calibration_kwargs(tmp_path, hashes, None)
    kwargs.pop("callback")
    with pytest.raises(CalibrationBoundaryError, match="requires an explicit callback"):
        run_calibration(tmp_path, **kwargs)
