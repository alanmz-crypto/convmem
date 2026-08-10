"""Offline entry-path tests for the zero-call-ready JudgeBench live driver."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
import requests

from eval_judgebench.contracts import InvocationStatus
from eval_judgebench.calibration import CalibrationBoundaryError
from eval_judgebench.live_driver import (
    LlamaRuntimeError,
    LiveDriverConfigurationError,
    RequestsHttpClient,
    RemoteCostConfigurationError,
    run_live_calibration,
)
from eval_judgebench.provider_requests import LLAMA_MODEL, llama_decoding_signature
from eval_judgebench.prompt_wrappers import prompt_wrapper_hash
from eval_provenance import comparison_signature_digest
from tests.test_judgebench_safety import (
    REGISTRY_V2,
    _expected_signature,
    _valid_semantic_output,
    _write_synthetic_package,
)


@pytest.fixture(autouse=True)
def _block_real_http(monkeypatch: pytest.MonkeyPatch):
    """A live-driver test must fail if it reaches a real HTTP client."""

    def fail(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("real HTTP is forbidden in live-driver tests")

    monkeypatch.setattr(requests.Session, "get", fail)
    monkeypatch.setattr(requests.Session, "post", fail)


class _Response:
    def __init__(self, payload: dict, *, status: int = 200):
        self.payload = payload
        self.status = status

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    def json(self) -> dict:
        return self.payload


class _FakeHttp:  # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        provider: str,
        *,
        response_model: str | None = None,
        response_provider: str | None = None,
        wrong_envelope: bool = False,
        provider_error_calls: set[int] | None = None,
    ):
        self.provider = provider
        self.response_model = response_model
        self.response_provider = response_provider
        self.wrong_envelope = wrong_envelope
        self.metadata_drift_after_posts = False
        self.provider_error_calls = provider_error_calls or set()
        self.get_calls: list[tuple[str, dict]] = []
        self.post_calls: list[tuple[str, dict]] = []

    def get(self, url: str, **kwargs):
        self.get_calls.append((url, kwargs))
        if url.endswith("/api/tags"):
            digest = "sha256:drifted" if self.metadata_drift_after_posts and self.post_calls else "sha256:model"
            return _Response({"models": [{"name": LLAMA_MODEL, "digest": digest}]})
        if url.endswith("/api/version"):
            version = "ollama-test-drift" if self.metadata_drift_after_posts and self.post_calls else "ollama-test-1"
            return _Response({"version": version})
        raise AssertionError(f"unexpected metadata URL: {url}")

    def post(self, url: str, **kwargs):
        self.post_calls.append((url, kwargs))
        if len(self.post_calls) in self.provider_error_calls:
            raise RuntimeError("synthetic provider outage")
        request = kwargs["json"]
        model = self.response_model or request["model"]
        if self.provider == "deepseek":
            if self.wrong_envelope:
                return _Response({"response": json.dumps(_valid_semantic_output())})
            payload = {
                "model": model,
                "choices": [
                    {"message": {"content": json.dumps(_valid_semantic_output())}}
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            if self.response_provider is not None:
                payload["provider"] = self.response_provider
            return _Response(
                payload
            )
        return _Response(
            {
                "model": model,
                "response": json.dumps(_valid_semantic_output()),
                "prompt_eval_count": 10,
                "eval_count": 5,
                "done": True,
            }
        )


def _deepseek_kwargs(
    root: Path,
    hashes: dict[str, str],
    client: _FakeHttp,
    *,
    candidate_model: str = "deepseek-v4-pro",
) -> dict:
    return {
        "cfg": {"models": {}},
        "candidate_model": candidate_model,
        "under_test_model": "human_curated",
        "registry_path": str(REGISTRY_V2),
        "expected_full_hashes": hashes,
        "expected_rubric_hashes": {
            "synthesis-grounded-v1": hashes["synthesis-grounded-v1"]
        },
        "expected_prompt_wrapper_hash": prompt_wrapper_hash("deepseek"),
        "expected_comparison_signature": _expected_signature(
            root, hashes, judge_model=candidate_model
        ),
        "http_client": client,
        "deepseek_api_key": "test-only-not-a-real-key",
        "remote_cost_ceiling_usd": Decimal("0.20"),
        "remote_price_basis": {
            "cache_miss_input_usd_per_million_tokens": "1",
            "output_usd_per_million_tokens": "1",
            "source": "test-pinned-price",
            "effective_at": "test",
        },
        "max_input_tokens": 100000,
    }


@pytest.mark.parametrize("candidate_model", ("deepseek-v4-pro", "deepseek-v4-flash"))
def test_remote_entry_attempts_exactly_20_and_records_only_calibration(
    tmp_path: Path, candidate_model: str
):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("deepseek")
    result = run_live_calibration(
        tmp_path,
        **_deepseek_kwargs(
            tmp_path, hashes, client, candidate_model=candidate_model
        ),
    )

    assert len(client.post_calls) == 20
    assert len(result.transport_evidence) == 20
    serialized = (
        json.dumps(result.report)
        + json.dumps(result.transport_evidence)
        + json.dumps([call[1]["json"] for call in client.post_calls])
    )
    assert "synthetic-holdout" not in serialized
    assert "HOLDOUT_SENTINEL" not in serialized
    assert result.report["transport"]["attempted_calls"] == 20
    assert "judge_recommendation" not in serialized
    assert all(
        set(call[1]["json"]) == {
            "model", "messages", "thinking", "reasoning_effort",
            "response_format", "max_tokens", "stream",
        }
        for call in client.post_calls
    )
    assert all(
        call[1]["json"]["model"] == candidate_model for call in client.post_calls
    )
    assert all(call[1]["json"]["stream"] is False for call in client.post_calls)
    assert all(case.invocation.status == InvocationStatus.OK for case in result.run.cases)
    assert all(case.invocation.response_hash for case in result.run.cases)
    assert all(case.invocation.tokens_in == 10 for case in result.run.cases)
    assert all(case.invocation.tokens_out == 5 for case in result.run.cases)
    remote_cost = result.report["transport"]["remote_cost"]
    assert remote_cost["input_token_bound"] <= remote_cost["caller_input_token_ceiling"]
    assert "UTF-8 serialized bytes" in remote_cost["input_token_bound_method"]
    assert remote_cost["price_basis"]["cache_miss_input_usd_per_million_tokens"] == "1"


def test_local_entry_resolves_digest_and_runtime_before_20_posts(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("llama")
    signature = _expected_signature(
        tmp_path,
        hashes,
        judge_model=LLAMA_MODEL,
        family="llama",
        decoding=llama_decoding_signature("sha256:model"),
    )
    signature["model_serving_version"] = "ollama-test-1"
    result = run_live_calibration(
        tmp_path,
        cfg={"models": {}},
        candidate_model=LLAMA_MODEL,
        under_test_model="human_curated",
        registry_path=str(REGISTRY_V2),
        expected_full_hashes=hashes,
        expected_rubric_hashes={
            "synthesis-grounded-v1": hashes["synthesis-grounded-v1"]
        },
        expected_prompt_wrapper_hash=prompt_wrapper_hash("llama"),
        expected_comparison_signature=signature,
        http_client=client,
        ollama_host="http://ollama.test",
        expected_llama_model_digest="sha256:model",
        expected_llama_runtime_version="ollama-test-1",
    )

    assert len(client.get_calls) == 4
    assert len(client.post_calls) == 20
    assert client.get_calls[0][0].endswith("/api/tags")
    assert client.get_calls[1][0].endswith("/api/version")
    assert result.llama_runtime is not None
    assert result.llama_runtime.model_digest == "sha256:model"
    assert result.llama_runtime.serving_runtime_version == "ollama-test-1"
    assert result.report["transport"]["llama_runtime"]["model_digest"] == "sha256:model"
    assert all(
        set(call[1]["json"]) == {"model", "prompt", "stream", "format", "options"}
        for call in client.post_calls
    )
    assert all(case.invocation.status == InvocationStatus.OK for case in result.run.cases)


def test_retry_and_fallback_configuration_is_rejected_before_http(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("deepseek")
    kwargs = _deepseek_kwargs(tmp_path, hashes, client)
    kwargs["cfg"] = {"judgebench": {"retries": 1}}
    with pytest.raises(LiveDriverConfigurationError):
        run_live_calibration(tmp_path, **kwargs)
    assert not client.post_calls


def test_public_requests_client_is_explicitly_available_without_calling_it():
    client = RequestsHttpClient()
    assert client.__class__.__name__ == "RequestsHttpClient"


def test_partial_provider_failure_is_incomplete_without_retry(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("deepseek", provider_error_calls={1})
    result = run_live_calibration(tmp_path, **_deepseek_kwargs(tmp_path, hashes, client))

    assert len(client.post_calls) == 20
    statuses = [case.invocation.status for case in result.run.cases]
    assert statuses[0] == InvocationStatus.PROVIDER_ERROR
    assert all(status == InvocationStatus.OK for status in statuses[1:])
    assert result.report["counts"]["scored_cases"] == 19
    assert result.report["counts"]["unscored_cases"] == 1
    assert result.report["run_state"] == {
        "status": "incomplete",
        "complete": False,
        "incomplete_statuses": {"provider_error": 1},
    }


def test_low_caller_input_ceiling_is_rejected_against_exact_wire_bound(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("deepseek")
    kwargs = _deepseek_kwargs(tmp_path, hashes, client)
    kwargs["max_input_tokens"] = 1
    with pytest.raises(RemoteCostConfigurationError, match="input bound"):
        run_live_calibration(tmp_path, **kwargs)
    assert not client.post_calls

    kwargs["cfg"] = {"judgebench": {"fallback_model": "llama3.1:8b"}}
    with pytest.raises(LiveDriverConfigurationError):
        run_live_calibration(tmp_path, **kwargs)
    assert not client.post_calls


def test_wrong_response_model_is_operational_failure_not_semantic_fail(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("deepseek", response_model="deepseek-v4-flash")
    result = run_live_calibration(tmp_path, **_deepseek_kwargs(tmp_path, hashes, client))
    assert len(client.post_calls) == 20
    assert all(case.invocation.status == InvocationStatus.PROVIDER_ERROR for case in result.run.cases)
    assert all(case.agrees_with_gold is None for case in result.run.cases)
    assert result.report["counts"]["scored_cases"] == 0


def test_wrong_provider_and_response_envelope_are_rejected_on_entry_path(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("deepseek", response_provider="llama")
    result = run_live_calibration(tmp_path, **_deepseek_kwargs(tmp_path, hashes, client))
    assert len(client.post_calls) == 20
    assert all(case.invocation.status == InvocationStatus.PROVIDER_ERROR for case in result.run.cases)

    client = _FakeHttp("deepseek", wrong_envelope=True)
    result = run_live_calibration(tmp_path, **_deepseek_kwargs(tmp_path, hashes, client))
    assert len(client.post_calls) == 20
    assert all(case.invocation.status == InvocationStatus.PROVIDER_ERROR for case in result.run.cases)


def test_wrong_provider_settings_in_config_are_rejected_before_http(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("deepseek")
    kwargs = _deepseek_kwargs(tmp_path, hashes, client)
    kwargs["cfg"] = {"judgebench": {"provider": "llama"}}
    with pytest.raises(LiveDriverConfigurationError):
        run_live_calibration(tmp_path, **kwargs)
    kwargs["cfg"] = {
        "judgebench": {
            "provider_settings": {
                **{
                    "thinking": "enabled",
                    "reasoning_effort": "low",
                    "response_mode": "json_object",
                    "max_tokens": 4096,
                    "stream": False,
                    "attempts": 1,
                    "temperature": {"status": "unsupported", "behavior": "ignored"},
                }
            }
        }
    }
    with pytest.raises(LiveDriverConfigurationError):
        run_live_calibration(tmp_path, **kwargs)
    assert not client.post_calls


def test_wrong_configured_candidate_model_is_rejected_before_http(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("deepseek")
    kwargs = _deepseek_kwargs(tmp_path, hashes, client)
    kwargs["cfg"] = {"models": {"distill_model": "deepseek-v4-flash"}}
    with pytest.raises(LiveDriverConfigurationError):
        run_live_calibration(tmp_path, **kwargs)
    assert not client.post_calls


def test_remote_cost_and_price_inputs_fail_closed_before_http(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("deepseek")
    kwargs = _deepseek_kwargs(tmp_path, hashes, client)
    kwargs["remote_price_basis"] = None
    with pytest.raises(RemoteCostConfigurationError):
        run_live_calibration(tmp_path, **kwargs)
    assert not client.post_calls

    kwargs = _deepseek_kwargs(tmp_path, hashes, client)
    kwargs["remote_cost_ceiling_usd"] = Decimal("0.001")
    with pytest.raises(RemoteCostConfigurationError):
        run_live_calibration(tmp_path, **kwargs)
    assert not client.post_calls


def test_llama_digest_drift_refuses_before_generation(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("llama")
    with pytest.raises(LlamaRuntimeError):
        run_live_calibration(
            tmp_path,
            cfg={"models": {}},
            candidate_model=LLAMA_MODEL,
            under_test_model="human_curated",
            registry_path=str(REGISTRY_V2),
            expected_full_hashes=hashes,
            expected_rubric_hashes={
                "synthesis-grounded-v1": hashes["synthesis-grounded-v1"]
            },
            expected_prompt_wrapper_hash=prompt_wrapper_hash("llama"),
            expected_comparison_signature={},
            http_client=client,
            expected_llama_model_digest="sha256:other-model",
            expected_llama_runtime_version="ollama-test-1",
        )
    assert len(client.get_calls) == 2
    assert not client.post_calls


def test_llama_requires_both_expected_runtime_pins_before_metadata(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("llama")
    with pytest.raises(LlamaRuntimeError, match="runtime version"):
        run_live_calibration(
            tmp_path,
            cfg={"models": {}},
            candidate_model=LLAMA_MODEL,
            under_test_model="human_curated",
            registry_path=str(REGISTRY_V2),
            expected_full_hashes=hashes,
            expected_rubric_hashes={
                "synthesis-grounded-v1": hashes["synthesis-grounded-v1"]
            },
            expected_prompt_wrapper_hash=prompt_wrapper_hash("llama"),
            expected_comparison_signature={},
            http_client=client,
            expected_llama_model_digest="sha256:model",
        )
    assert not client.get_calls
    assert not client.post_calls


def test_llama_post_run_metadata_drift_fails_closed(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("llama")
    client.metadata_drift_after_posts = True
    signature = _expected_signature(
        tmp_path,
        hashes,
        judge_model=LLAMA_MODEL,
        family="llama",
        decoding=llama_decoding_signature("sha256:model"),
    )
    signature["model_serving_version"] = "ollama-test-1"
    with pytest.raises(LlamaRuntimeError, match="changed during calibration"):
        run_live_calibration(
            tmp_path,
            cfg={"models": {}},
            candidate_model=LLAMA_MODEL,
            under_test_model="human_curated",
            registry_path=str(REGISTRY_V2),
            expected_full_hashes=hashes,
            expected_rubric_hashes={
                "synthesis-grounded-v1": hashes["synthesis-grounded-v1"]
            },
            expected_prompt_wrapper_hash=prompt_wrapper_hash("llama"),
            expected_comparison_signature=signature,
            http_client=client,
            expected_llama_model_digest="sha256:model",
            expected_llama_runtime_version="ollama-test-1",
        )
    assert len(client.post_calls) == 20
    assert len(client.get_calls) == 4


def test_comparison_signature_drift_refuses_before_transport(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("deepseek")
    kwargs = _deepseek_kwargs(tmp_path, hashes, client)
    signature = dict(kwargs["expected_comparison_signature"])
    signature["metric_policy_version"] = "drifted"
    kwargs["expected_comparison_signature"] = signature
    with pytest.raises(CalibrationBoundaryError):
        run_live_calibration(tmp_path, **kwargs)
    assert not client.post_calls


def test_live_result_signature_stays_the_phase_a_signature(tmp_path: Path):
    hashes = _write_synthetic_package(tmp_path)
    client = _FakeHttp("deepseek")
    kwargs = _deepseek_kwargs(tmp_path, hashes, client)
    result = run_live_calibration(tmp_path, **kwargs)
    assert comparison_signature_digest(result.run.comparison_signature) == comparison_signature_digest(
        kwargs["expected_comparison_signature"]
    )
