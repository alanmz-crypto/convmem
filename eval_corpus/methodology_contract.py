"""Frozen methodology-v1 contract for the first embedding evaluation.

This module deliberately owns only the experiment contract.  It does not open
Ollama, Chroma, or a corpus; callers bind its validated bytes to later
authorization manifests.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "embedding_eval_methodology_v1"
CONTRACT_ID = "embedding-eval-production-swap-v1"
_SHA256_EMPTY = hashlib.sha256(b"").hexdigest()
_BUILD_SCHEDULE = (
    "baseline-0",
    "challenger-0",
    "challenger-1",
    "baseline-1",
    "baseline-2",
    "challenger-2",
)


class MethodologyError(ValueError):
    """A methodology is absent, malformed, or changes a frozen rule."""


def canonical_methodology_bytes(methodology: Mapping[str, Any]) -> bytes:
    """Canonical JSON used for C0a identity binding."""
    return json.dumps(
        methodology, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def methodology_sha256(methodology: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_methodology_bytes(methodology)).hexdigest()


def _require_object(container: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = container.get(key)
    if not isinstance(value, Mapping):
        raise MethodologyError(f"{key} must be an object")
    return value


def _require_string(container: Mapping[str, Any], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value:
        raise MethodologyError(f"{key} must be a nonempty string")
    return value


def _require_int(container: Mapping[str, Any], key: str, *, minimum: int = 1) -> int:
    value = container.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise MethodologyError(f"{key} must be an integer >= {minimum}")
    return value


def _require_number(container: Mapping[str, Any], key: str, *, minimum: float = 0.0) -> float:
    value = container.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MethodologyError(f"{key} must be a finite number")
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        raise MethodologyError(f"{key} must be a finite number >= {minimum}")
    return number


def _require_transform(name: str, transform: Mapping[str, Any]) -> None:
    _require_string(transform, "id")
    bytes_utf8 = transform.get("bytes_utf8")
    if not isinstance(bytes_utf8, str):
        raise MethodologyError(f"transforms.{name}.bytes_utf8 must be a string")
    claimed = _require_string(transform, "sha256")
    actual = hashlib.sha256(bytes_utf8.encode("utf-8")).hexdigest()
    if claimed != actual:
        raise MethodologyError(f"transforms.{name}.sha256 does not match bytes_utf8")


def validate_methodology_v1(methodology: Mapping[str, Any]) -> None:
    """Fail closed unless every pre-C0a methodology choice is explicit.

    The future C0a packet supplies this exact object.  Values that could be
    silently chosen after a probe—dimensions, transforms, endpoint semantics,
    statistics, ANN stability rules, or latency rules—are all validated here.
    """
    if not isinstance(methodology, Mapping):
        raise MethodologyError("methodology must be an object")
    if methodology.get("schema_version") != SCHEMA_VERSION:
        raise MethodologyError(f"schema_version must be {SCHEMA_VERSION!r}")
    if methodology.get("contract_id") != CONTRACT_ID:
        raise MethodologyError(f"contract_id must be {CONTRACT_ID!r}")
    if methodology.get("evaluation_objective") != "production_swap":
        raise MethodologyError("evaluation_objective must be production_swap")

    dimension = _require_int(methodology, "production_output_dimension", minimum=1)
    if dimension > 4096:
        raise MethodologyError("production_output_dimension must be <= 4096")

    transforms = _require_object(methodology, "transforms")
    _require_transform("document", _require_object(transforms, "document"))
    _require_transform("query", _require_object(transforms, "query"))

    request = _require_object(methodology, "request_contract")
    if request.get("endpoint_path") != "/api/embed":
        raise MethodologyError("request_contract.endpoint_path must be /api/embed")
    if request.get("http_method") != "POST":
        raise MethodologyError("request_contract.http_method must be POST")
    if request.get("schema_version") != "ollama.embed.v1":
        raise MethodologyError(
            "request_contract.schema_version must be ollama.embed.v1"
        )
    if request.get("truncate") is not False:
        raise MethodologyError("request_contract.truncate must be false")
    if request.get("requested_dimensions") != dimension:
        raise MethodologyError(
            "request_contract.requested_dimensions must equal production_output_dimension"
        )
    if request.get("batching_policy") != "serial_per_document":
        raise MethodologyError(
            "request_contract.batching_policy must be serial_per_document"
        )
    if request.get("normalization_policy") != "production_passthrough_v1":
        raise MethodologyError(
            "request_contract.normalization_policy must be production_passthrough_v1"
        )
    if request.get("retry_count") != 0:
        raise MethodologyError("request_contract.retry_count must be zero")
    _require_int(request, "timeout_seconds", minimum=1)
    _require_string(request, "keep_alive")
    if not isinstance(request.get("options"), Mapping):
        raise MethodologyError("request_contract.options must be an object")

    retrieval = _require_object(methodology, "retrieval")
    _require_int(retrieval, "candidate_depth", minimum=5)
    if retrieval.get("distance_metric") != "cosine":
        raise MethodologyError("retrieval.distance_metric must be cosine")
    _require_string(retrieval, "filter_policy")
    _require_number(retrieval, "keyword_boost", minimum=0.0)
    _require_number(retrieval, "source_trust_weight", minimum=0.0)
    _require_number(retrieval, "recency_weight", minimum=0.0)
    _require_string(retrieval, "reranking_policy")
    _require_string(retrieval, "as_of")

    stats = _require_object(methodology, "statistics")
    if stats.get("primary_metric") != "hit_at_5":
        raise MethodologyError("statistics.primary_metric must be hit_at_5")
    if stats.get("primary_view") != "embedding_influenced":
        raise MethodologyError(
            "statistics.primary_view must be embedding_influenced"
        )
    if stats.get("domain_weighting") != "equal_domain_query_equal_within_domain":
        raise MethodologyError("statistics.domain_weighting is not the approved estimand")
    if stats.get("source_group_policy") != "within_domain_clusters_only":
        raise MethodologyError("statistics.source_group_policy must be within-domain")
    if stats.get("tie_epsilon") != 0.0:
        raise MethodologyError("statistics.tie_epsilon must be exactly 0.0")
    if stats.get("confidence_level") != 0.95:
        raise MethodologyError("statistics.confidence_level must be 0.95")
    if stats.get("significance_alpha") != 0.05:
        raise MethodologyError("statistics.significance_alpha must be 0.05")
    if stats.get("bootstrap") != {
        "algorithm": "domain_stratified_cluster_percentile_v1",
        "seed": 20260804,
        "resamples": 100000,
    }:
        raise MethodologyError("statistics.bootstrap is not the frozen bootstrap contract")
    if stats.get("permutation") != {
        "algorithm": "domain_stratified_cluster_sign_flip_v1",
        "seed": 20260805,
        "draws": 100000,
        "alternative": "one_sided_symmetric",
    }:
        raise MethodologyError("statistics.permutation is not the frozen test contract")
    if stats.get("minimum_non_tied_groups") != 20:
        raise MethodologyError("statistics.minimum_non_tied_groups must be 20")

    exact = _require_object(methodology, "exact_vector")
    if exact != {
        "algorithm": "exact_vector_rank_v1",
        "accumulator": "float64",
        "stored_vector_type": "float32",
        "tie_break": "utf8_unit_id_ascending",
        "same_query_and_document_vectors_as_ann": True,
    }:
        raise MethodologyError("exact_vector is not the frozen diagnostic contract")

    ann = _require_object(methodology, "ann")
    if ann.get("hnsw_space") != "cosine":
        raise MethodologyError("ann.hnsw_space must be cosine")
    if ann.get("seed_control") != "not_exposed" or ann.get("seed_list") != []:
        raise MethodologyError("ann seed policy must declare no exposed seed")
    if ann.get("realization_count") != 3:
        raise MethodologyError("ann.realization_count must be 3")
    if tuple(ann.get("build_schedule") or ()) != _BUILD_SCHEDULE:
        raise MethodologyError("ann.build_schedule differs from the approved schedule")
    if ann.get("top1_change_pair_limit") != 1:
        raise MethodologyError("ann.top1_change_pair_limit must be 1")
    if ann.get("mean_pairwise_top5_jaccard_minimum") != 0.98:
        raise MethodologyError(
            "ann.mean_pairwise_top5_jaccard_minimum must be 0.98"
        )
    if ann.get("verdict_consistency") != "matched_realizations_identical":
        raise MethodologyError("ann.verdict_consistency is not frozen")

    latency = _require_object(methodology, "latency")
    if latency != {
        "query_selection": "first_query_id_utf8_ascending",
        "warmups_per_view": 5,
        "timed_repetitions_per_view": 20,
        "order_schedule": "four_cycle_latin_v1",
        "percentile_algorithm": "nearest_rank_v1",
        "warm_residency_required": True,
        "reload_or_eviction_outcome": "incomplete",
    }:
        raise MethodologyError("latency is not the frozen warm-latency contract")

    ceilings = _require_object(methodology, "safety_ceilings")
    for key in (
        "minimum_free_disk_bytes",
        "maximum_request_seconds",
        "maximum_build_seconds_per_unit",
    ):
        _require_number(ceilings, key, minimum=1.0)
    if ceilings.get("maximum_worker_errors") != 0:
        raise MethodologyError("safety_ceilings.maximum_worker_errors must be zero")


def load_methodology_v1(path: Path | str) -> dict[str, Any]:
    """Read, parse, and validate one immutable methodology document."""
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MethodologyError(f"cannot load methodology {source}: {exc}") from exc
    if not isinstance(data, dict):
        raise MethodologyError("methodology JSON root must be an object")
    validate_methodology_v1(data)
    return data


def assert_c0b_contract_unchanged(
    c0a_methodology: Mapping[str, Any], c0b_methodology_sha256: str
) -> None:
    """C0b may attest compatibility but cannot alter a C0a methodology byte."""
    validate_methodology_v1(c0a_methodology)
    expected = methodology_sha256(c0a_methodology)
    if c0b_methodology_sha256 != expected:
        raise MethodologyError(
            "C0b methodology identity differs from the frozen C0a methodology"
        )


__all__ = [
    "CONTRACT_ID",
    "SCHEMA_VERSION",
    "MethodologyError",
    "assert_c0b_contract_unchanged",
    "canonical_methodology_bytes",
    "load_methodology_v1",
    "methodology_sha256",
    "validate_methodology_v1",
]
