"""Baseline provenance + regression triage for the eval harnesses.

A baseline score is only meaningful relative to the model that produced it. If
Ollama is upgraded, a quant level changes, or the model file is swapped, a lower
score can mean "quality actually dropped" OR "the fixture was tuned for a model
that no longer exists." Those need different responses, so we record the model
context alongside the scores and classify regressions mechanically.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import requests

# Distinct exit codes so callers/CI can branch on the triage outcome.
EXIT_OK = 0
EXIT_REGRESSION = 1  # same model, worse scores -> genuine quality regression
EXIT_NEEDS_REBASELINE = 3  # model context changed -> baseline is stale, not a regression


def _ollama_host(cfg: dict) -> str:
    return (cfg.get("models") or {}).get(
        "ollama_host", "http://localhost:11434"
    ).rstrip("/")


def ollama_version(cfg: dict) -> str:
    try:
        resp = requests.get(f"{_ollama_host(cfg)}/api/version", timeout=5)
        resp.raise_for_status()
        return str(resp.json().get("version") or "")
    except requests.RequestException:
        return ""


def model_digest_and_quant(cfg: dict, model_name: str) -> tuple[str, str]:
    """Return (digest, quantization_level) for ``model_name`` from /api/tags.

    DeepSeek (remote) models are not in the local registry — return ("remote", "").
    Any failure degrades to ("", "") so provenance never breaks an eval run.
    """
    if not model_name or "deepseek" in model_name:
        return ("remote", "") if model_name else ("", "")
    try:
        resp = requests.get(f"{_ollama_host(cfg)}/api/tags", timeout=5)
        resp.raise_for_status()
        for m in resp.json().get("models") or []:
            if m.get("name") == model_name or m.get("model") == model_name:
                digest = str(m.get("digest") or "")
                quant = str((m.get("details") or {}).get("quantization_level") or "")
                return digest, quant
    except requests.RequestException:
        pass
    return "", ""


def fixture_hash(path: Path | str) -> str:
    p = Path(path)
    if not p.is_file():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def model_context(cfg: dict, model_name: str, fixture_path: Path | str | None = None) -> dict:
    """Capture the model/version/quant/fixture context for a baseline record."""
    digest, quant = model_digest_and_quant(cfg, model_name)
    ctx = {
        "model_name": model_name,
        "model_digest": digest,
        "quant": quant,
        "ollama_version": ollama_version(cfg),
    }
    if fixture_path is not None:
        ctx["fixture_hash"] = fixture_hash(fixture_path)
    return ctx


def context_changed(current: dict, baseline: dict) -> tuple[bool, list[str]]:
    """Return (changed, reasons). Empty/absent baseline fields are ignored so
    older baselines without provenance don't spuriously trip NEEDS REBASELINE."""
    reasons: list[str] = []
    for key in ("model_name", "model_digest", "quant", "ollama_version", "fixture_hash"):
        base_val = baseline.get(key)
        cur_val = current.get(key)
        if not base_val:  # baseline didn't record it — can't compare
            continue
        if cur_val and cur_val != base_val:
            reasons.append(f"{key}: {base_val!r} -> {cur_val!r}")
    return (bool(reasons), reasons)


def classify(
    *,
    regressed: bool,
    current_ctx: dict,
    baseline_ctx: dict,
) -> tuple[int, str]:
    """Map (regressed?, model-context delta) to an exit code + human message.

    - no regression                          -> EXIT_OK
    - regression + same model context        -> EXIT_REGRESSION (genuine)
    - regression + changed model context     -> EXIT_NEEDS_REBASELINE (stale)
    - comparison signature mismatch            -> EXIT_NEEDS_REBASELINE (incomparable)
    """
    sig_changed, sig_reasons = comparison_signature_changed(current_ctx, baseline_ctx)
    changed, reasons = context_changed(current_ctx, baseline_ctx)
    all_reasons = sig_reasons + reasons
    if sig_changed or changed:
        changed = True
        reasons = all_reasons
    if not regressed:
        note = " (model context changed — consider --update-baseline)" if changed else ""
        return EXIT_OK, f"No regression vs baseline.{note}"
    if changed:
        return (
            EXIT_NEEDS_REBASELINE,
            "NEEDS REBASELINE: scores dropped but model context changed ("
            + "; ".join(reasons)
            + "). Not treated as a quality regression — re-run with --update-baseline "
            "once the new model is intended.",
        )
    return (
        EXIT_REGRESSION,
        "REGRESSION: scores dropped with the SAME model context — genuine quality "
        "regression, investigate model/infra.",
    )


def canonical_signature_dict(sig: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with sorted nested dicts for stable hashing."""
    out: dict[str, Any] = {}
    for key in sorted(sig):
        value = sig[key]
        if isinstance(value, dict):
            out[key] = {k: value[k] for k in sorted(value)}
        else:
            out[key] = value
    return out


def comparison_signature_digest(sig: dict[str, Any]) -> str:
    """Stable digest for a comparison signature payload."""
    payload = json.dumps(canonical_signature_dict(sig), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_comparison_signature(  # pylint: disable=too-many-arguments
    *,
    evaluation_surface: str,
    case_hash: str = "",
    fixture_hash_value: str = "",
    gold_hash: str = "",
    contract_hashes: dict[str, str] | None = None,
    identity_policy_version: str = "",
    resolved_identities: dict[str, dict[str, str]] | None = None,
    judge_pin: dict[str, str] | None = None,
    under_test_provenance: dict[str, Any] | None = None,
    independence_class: str = "",
    decoding_params: dict[str, Any] | None = None,
    model_serving_version: str = "",
    metric_policy_version: str = "",
    e2e_retrieval_fingerprint: str | None = None,
    prompt_hashes: dict[str, str] | None = None,
    prompt_family: str = "",
    rubric_hashes: dict[str, str] | None = None,
    full_corpus_hashes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the canonical comparison signature for baseline compatibility."""
    signature = {
        "evaluation_surface": evaluation_surface,
        "case_hash": case_hash,
        "fixture_hash": fixture_hash_value,
        "gold_hash": gold_hash,
        "contract_hashes": contract_hashes or {},
        "identity_policy_version": identity_policy_version,
        "resolved_identities": resolved_identities or {},
        "judge_pin": judge_pin or {},
        "under_test_provenance": under_test_provenance or {},
        "independence_class": independence_class,
        "decoding_params": decoding_params or {},
        "model_serving_version": model_serving_version,
        "metric_policy_version": metric_policy_version,
        "e2e_retrieval_fingerprint": e2e_retrieval_fingerprint or "",
        "prompt_family": prompt_family,
    }
    if prompt_hashes is not None:
        signature["prompt_hashes"] = prompt_hashes
    if rubric_hashes is not None:
        signature["rubric_hashes"] = rubric_hashes
    if full_corpus_hashes is not None:
        signature["full_corpus_hashes"] = full_corpus_hashes
    return signature


def comparison_signature_changed(current: dict, baseline: dict) -> tuple[bool, list[str]]:
    """Detect hard comparison-signature changes between baseline records."""
    cur_sig = current.get("comparison_signature")
    base_sig = baseline.get("comparison_signature")
    if not base_sig:
        return False, []
    if not cur_sig:
        return True, ["comparison_signature: absent -> present"]
    cur_digest = comparison_signature_digest(cur_sig)
    base_digest = comparison_signature_digest(base_sig)
    if cur_digest == base_digest:
        return False, []
    reasons: list[str] = []
    for key in sorted(set(cur_sig) | set(base_sig)):
        if cur_sig.get(key) != base_sig.get(key):
            reasons.append(f"comparison_signature.{key} changed")
    return True, reasons or [f"comparison_signature digest: {base_digest[:16]} -> {cur_digest[:16]}"]


def attach_comparison_signature(ctx: dict, signature: dict[str, Any]) -> dict[str, Any]:
    """Return a provenance context copy with comparison signature + digest attached."""
    out = dict(ctx)
    out["comparison_signature"] = signature
    out["comparison_signature_digest"] = comparison_signature_digest(signature)
    return out
