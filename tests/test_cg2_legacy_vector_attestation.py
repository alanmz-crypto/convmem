"""Hermetic D0 exact-vector authority oracles."""

# pylint: disable=redefined-outer-name

from __future__ import annotations

import hashlib
import inspect
import json
import math
from pathlib import Path
from unittest.mock import patch

import pytest

from cg2_legacy_vector_attestation import (
    CG2_D0_CANDIDATE_V1,
    CG2_D0_RATIFICATION_V1,
    CG2_D0_VALIDATION_RESULT_V1,
    CONTEXT_KEYS,
    KNOWN_MODEL_AND_VECTOR_V1,
    LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
    PIPELINE_KEYS,
    QUERY_EMBEDDING_CONTEXT_V1,
    QUERY_EMBEDDING_PIPELINE_V1,
    CandidateReference,
    D0AttestationError,
    capture_d0_legacy_vector_candidate,
    derive_query_embedding_context,
    load_ratified_d0_chain,
    validate_d0_legacy_vector_candidate,
    validate_d0_ratification_record,
    vector_encoding_sha256,
    verify_d0_chain_for_grb_conversion,
)
from chroma_store import ChromaStore
from complete_data_restore import (
    EXIT_BLOCKED,
    OUTCOME_BLOCKED,
    OUTCOME_VALID,
    closed_state_spec_paths,
    inventory_restored_state,
)
from file_generation_contract import (
    canonical_bytes,
    canonical_hash,
    canonical_source_path,
    ownership_key,
)
from serving_authority import generation_root_for_cfg


DIGEST = "a" * 64
MODEL = "nomic-embed-text"


def _source_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cfg(tmp_path: Path, chroma: Path) -> dict:
    return {
        "models": {
            "embed_model": MODEL,
            "ollama_host": "http://127.0.0.1:9",
        },
        "index": {
            "chroma_dir": str(chroma),
            "generation_root": str(tmp_path / "file_generations"),
            "processed_log": str(tmp_path / "processed.json"),
        },
    }


def _write_processed(cfg: dict, source: Path) -> str:
    canonical = canonical_source_path(source)
    digest = _source_hash(source)
    Path(cfg["index"]["processed_log"]).write_text(
        json.dumps({digest: {"path": canonical, "units": 1}}),
        encoding="utf-8",
    )
    return digest


def _add_rows(chroma: Path, source: Path, *, order: str = "ab") -> None:
    canonical = canonical_source_path(source)
    store = ChromaStore(str(chroma))
    rows = [
        (
            "phys-a",
            "doc-a",
            [0.25, 0.5, 0.75],
            {
                "source_path": canonical,
                "logical_id": "log-a",
                "content_hash": "ca",
            },
        ),
        (
            "phys-b",
            "doc-b",
            [0.1, 0.2, 0.3],
            {
                "source_path": canonical,
                "logical_id": "log-b",
                "content_hash": "cb",
            },
        ),
    ]
    if order == "ba":
        rows = list(reversed(rows))
    for physical_id, document, embedding, meta in rows:
        store.add_unit(physical_id, document, embedding, meta)
    store.add_summary(
        "sum-1",
        "summary",
        [0.9, 0.8, 0.7],
        {"source_path": canonical, "logical_id": "sum-1"},
    )
    store.close()


def _mock_ollama(monkeypatch, *, digest=f"sha256:{DIGEST}", quant="Q4_0", version="0.11.4", dim=3):
    def fake_embed(text, model, _host):
        assert model == MODEL
        assert text == "a"
        return [0.01] * dim

    class _Resp:
        def __init__(self, url: str):
            self.url = url

        def raise_for_status(self) -> None:
            return None

        def json(self):
            if self.url.endswith("/api/tags"):
                entry = {"name": MODEL, "model": MODEL, "details": {}}
                if digest is not None:
                    entry["digest"] = digest
                if quant is not None:
                    entry["details"]["quantization_level"] = quant
                return {"models": [entry]}
            if self.url.endswith("/api/version"):
                payload = {}
                if version is not None:
                    payload["version"] = version
                return payload
            raise AssertionError(self.url)

    monkeypatch.setattr("cg2_legacy_vector_attestation.ollama_embed", fake_embed)
    monkeypatch.setattr(
        "cg2_legacy_vector_attestation.requests.get",
        lambda url, timeout=5: _Resp(url),
    )


@pytest.fixture
def d0_env(tmp_path, monkeypatch):
    chroma = tmp_path / "chroma"
    source = tmp_path / "owner.txt"
    source.write_text("legacy-source", encoding="utf-8")
    cfg = _cfg(tmp_path, chroma)
    accepted = _write_processed(cfg, source)
    _add_rows(chroma, source)
    _mock_ollama(monkeypatch)
    monkeypatch.setattr(
        "cg2_legacy_vector_attestation._resolve_live_production_paths",
        lambda: (tmp_path / "live-chroma", tmp_path / "live-generations"),
    )
    return {
        "cfg": cfg,
        "source": source,
        "owner_key": ownership_key(source),
        "accepted": accepted,
        "tmp_path": tmp_path,
        "chroma": chroma,
    }


def _capture(env) -> CandidateReference:
    return capture_d0_legacy_vector_candidate(
        env["cfg"],
        owner_key=env["owner_key"],
        source_path=env["source"],
        accepted_source_hash=env["accepted"],
    )


def _validate(env, candidate_sha: str):
    return validate_d0_legacy_vector_candidate(
        env["cfg"],
        owner_key=env["owner_key"],
        source_path=env["source"],
        accepted_source_hash=env["accepted"],
        candidate_sha256=candidate_sha,
        validator_identity="hermetic-validator-v1",
    )


def test_schema_constants_exist():
    assert LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1.endswith("UNKNOWN_MODEL_V1")
    assert KNOWN_MODEL_AND_VECTOR_V1.endswith("VECTOR_V1")
    assert QUERY_EMBEDDING_CONTEXT_V1 == "QUERY_EMBEDDING_CONTEXT_V1"
    assert QUERY_EMBEDDING_PIPELINE_V1 == "QUERY_EMBEDDING_PIPELINE_V1"
    assert CG2_D0_CANDIDATE_V1 == "CG2_D0_CANDIDATE_V1"
    assert CG2_D0_VALIDATION_RESULT_V1 == "CG2_D0_VALIDATION_RESULT_V1"
    assert CG2_D0_RATIFICATION_V1 == "CG2_D0_RATIFICATION_V1"
    assert PIPELINE_KEYS == tuple(sorted(PIPELINE_KEYS))
    assert CONTEXT_KEYS == tuple(sorted(CONTEXT_KEYS))


def test_canonical_json_key_order_and_nonfinite_refusal():
    pipeline = {
        "schema_version": QUERY_EMBEDDING_PIPELINE_V1,
        "query_vector_transform": "IDENTITY_FLOAT_VECTOR_V1",
        "request_operation": "OLLAMA_POST_API_EMBEDDINGS_PROMPT_V1",
        "output_selector": "embedding",
        "input_text_transform": "IDENTITY_UNICODE_STRING_V1",
        "query_vector_normalization": "NONE",
    }
    encoded = canonical_bytes(pipeline)
    assert encoded == canonical_bytes({key: pipeline[key] for key in PIPELINE_KEYS})
    with pytest.raises(Exception):
        canonical_bytes({"n": math.nan})


def test_vector_float32_encoding_and_nonfinite_refusal():
    first = vector_encoding_sha256([1.0, -2.5, 0.0])
    second = vector_encoding_sha256([1.0, -2.5, 0.0])
    assert first == second
    assert len(first) == 64
    with pytest.raises(D0AttestationError, match="non-finite"):
        vector_encoding_sha256([1.0, math.inf])
    with pytest.raises(D0AttestationError, match="non-finite"):
        vector_encoding_sha256([math.nan])


def test_insertion_order_independent_leaf_roots(d0_env, tmp_path):
    other = tmp_path / "chroma-ba"
    _add_rows(other, d0_env["source"], order="ba")
    cfg_ba = dict(d0_env["cfg"])
    cfg_ba["index"] = dict(d0_env["cfg"]["index"])
    cfg_ba["index"]["chroma_dir"] = str(other)
    cfg_ba["index"]["generation_root"] = str(tmp_path / "file_generations-ba")
    first = _capture(d0_env)
    second = capture_d0_legacy_vector_candidate(
        cfg_ba,
        owner_key=d0_env["owner_key"],
        source_path=d0_env["source"],
        accepted_source_hash=d0_env["accepted"],
    )
    left = json.loads(first.path.read_text(encoding="utf-8"))
    right = json.loads(second.path.read_text(encoding="utf-8"))

    def _leaf_identities(payload):
        leaves = []
        for collection in payload["collections"]:
            for leaf in collection["leaves"]:
                leaves.append(
                    (
                        leaf["collection_name"],
                        leaf["conversion_logical_id"],
                        leaf["physical_id"],
                        leaf["document_hash"],
                        leaf["vector_encoding_sha256"],
                    )
                )
        return leaves

    assert _leaf_identities(left) == _leaf_identities(right)
    assert _leaf_identities(left) == sorted(
        _leaf_identities(left),
        key=lambda item: tuple(part.encode("utf-8") for part in item[0:3]),
    )


def test_duplicate_identity_refusal(d0_env, monkeypatch):
    original = capture_d0_legacy_vector_candidate.__globals__["_read_admitted_rows"]

    def duplicated(*args, **kwargs):
        rows = original(*args, **kwargs)
        return rows + [dict(rows[0])]

    monkeypatch.setattr(
        "cg2_legacy_vector_attestation._read_admitted_rows", duplicated
    )
    with pytest.raises(D0AttestationError, match="duplicate"):
        _capture(d0_env)


def test_capture_and_end_of_capture_authority_recheck(d0_env):
    ref = _capture(d0_env)
    payload = json.loads(ref.path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == CG2_D0_CANDIDATE_V1
    assert payload["proof_profile"] == LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1
    assert payload["historical_embedding_model"] == {"identifier": None, "status": "UNKNOWN"}
    assert payload["authority_mode"] == "LEGACY"
    assert ref.path.name == f"{ref.candidate_sha256}.json"
    calls = {"n": 0}
    real = capture_d0_legacy_vector_candidate.__globals__["_require_legacy_owner"]

    def drifting(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise D0AttestationError("owner has fence; D0 requires LEGACY")
        return real(*args, **kwargs)

    with patch("cg2_legacy_vector_attestation._require_legacy_owner", drifting):
        with pytest.raises(D0AttestationError, match="fence"):
            _capture(d0_env)


def test_capture_churn_refuses_publication(d0_env, monkeypatch):
    calls = {"n": 0}
    real = capture_d0_legacy_vector_candidate.__globals__["_observe_locked_state"]

    def churn(*args, **kwargs):
        state = real(*args, **kwargs)
        calls["n"] += 1
        if calls["n"] == 2:
            mutated = dict(state)
            mutated["accepted_legacy_snapshot_root"] = "b" * 64
            return mutated
        return state

    monkeypatch.setattr("cg2_legacy_vector_attestation._observe_locked_state", churn)
    generation_root = generation_root_for_cfg(d0_env["cfg"])
    with pytest.raises(D0AttestationError, match="churn"):
        _capture(d0_env)
    attest = Path(generation_root) / "legacy_vector_attestation"
    if attest.exists():
        assert not list(attest.rglob("candidates/*.json"))


def test_independent_validation_and_single_lock(d0_env):
    candidate = _capture(d0_env)
    flocks = {"n": 0}
    real = capture_d0_legacy_vector_candidate.__globals__["source_flock"]

    def counting(cfg, canonical):
        flocks["n"] += 1
        return real(cfg, canonical)

    with patch("cg2_legacy_vector_attestation.source_flock", counting):
        validation = _validate(d0_env, candidate.candidate_sha256)
    assert flocks["n"] == 1
    payload = json.loads(validation.path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == CG2_D0_VALIDATION_RESULT_V1
    assert payload["candidate_artifact_sha256"] == candidate.candidate_sha256
    assert validation.path.parent.name == "validations"


def test_tampered_candidate_with_recomputed_hash_still_refuses(d0_env):
    candidate = _capture(d0_env)
    payload = json.loads(candidate.path.read_text(encoding="utf-8"))
    payload["accepted_legacy_snapshot_root"] = "c" * 64
    body = {k: v for k, v in payload.items() if k != "artifact_sha256"}
    sha = canonical_hash(body)
    path = candidate.path.parent / f"{sha}.json"
    path.write_bytes(canonical_bytes(body))
    with pytest.raises(D0AttestationError, match="independent reproduction"):
        _validate(d0_env, sha)


def test_validation_authority_source_root_and_query_context_drift(d0_env, monkeypatch):
    candidate = _capture(d0_env)
    real = capture_d0_legacy_vector_candidate.__globals__["_observe_locked_state"]

    def _drift(field, value):
        calls = {"n": 0}

        def wrapped(*args, **kwargs):
            state = real(*args, **kwargs)
            calls["n"] += 1
            if calls["n"] == 2:
                mutated = dict(state)
                mutated[field] = value
                return mutated
            return state

        return wrapped

    monkeypatch.setattr(
        "cg2_legacy_vector_attestation._observe_locked_state",
        _drift("authority_mode", "FENCED_NO_POINTER"),
    )
    with pytest.raises(D0AttestationError, match="churn"):
        _validate(d0_env, candidate.candidate_sha256)

    monkeypatch.setattr(
        "cg2_legacy_vector_attestation._observe_locked_state",
        _drift("accepted_source_hash", "d" * 64),
    )
    with pytest.raises(D0AttestationError, match="churn"):
        _validate(d0_env, candidate.candidate_sha256)

    monkeypatch.setattr(
        "cg2_legacy_vector_attestation._observe_locked_state",
        _drift("accepted_legacy_vector_root", "e" * 64),
    )
    with pytest.raises(D0AttestationError, match="churn"):
        _validate(d0_env, candidate.candidate_sha256)

    monkeypatch.setattr(
        "cg2_legacy_vector_attestation._observe_locked_state",
        _drift("query_embedding_context_sha256", "f" * 64),
    )
    with pytest.raises(D0AttestationError, match="churn"):
        _validate(d0_env, candidate.candidate_sha256)


def test_candidate_cannot_emit_validation(d0_env):
    source = inspect.getsource(capture_d0_legacy_vector_candidate)
    assert "validate_d0_legacy_vector_candidate" not in source
    assert "validations" not in source
    candidate = _capture(d0_env)
    with patch("cg2_legacy_vector_attestation._D0_ROLE") as role:
        role.get.return_value = "capture"
        with pytest.raises(D0AttestationError, match="cannot emit validation"):
            _validate(d0_env, candidate.candidate_sha256)


def test_ratification_missing_mismatch_invalidated(d0_env):
    candidate = _capture(d0_env)
    validation = _validate(d0_env, candidate.candidate_sha256)
    cand = json.loads(candidate.path.read_text(encoding="utf-8"))
    base = {
        "schema_version": CG2_D0_RATIFICATION_V1,
        "ratification_id": "ryan-d0-fixture-1",
        "candidate_artifact_sha256": candidate.candidate_sha256,
        "validation_result_sha256": validation.validation_result_sha256,
        "owner_key": d0_env["owner_key"],
        "owner_digest": candidate.owner_digest,
        "accepted_legacy_snapshot_root": cand["accepted_legacy_snapshot_root"],
        "accepted_legacy_vector_root": cand["accepted_legacy_vector_root"],
        "producer_repository_sha": cand["producer_repository_sha"],
        "capture_identity": cand["capture_module_identity"],
        "capture_time": cand["capture_start_time"],
        "query_embedding_context_sha256": cand["query_embedding_context_sha256"],
    }
    view = validate_d0_ratification_record(base)
    assert view.candidate_artifact_sha256 == candidate.candidate_sha256
    missing = dict(base)
    missing.pop("capture_time")
    with pytest.raises(D0AttestationError, match="missing"):
        validate_d0_ratification_record(missing)
    mismatched = dict(base)
    mismatched["candidate_artifact_sha256"] = "1" * 64
    # record itself still structurally valid, but chain load must refuse
    generation_root = generation_root_for_cfg(d0_env["cfg"])
    from cg2_legacy_vector_attestation import ratification_path, _publish_immutable

    path = ratification_path(generation_root, candidate.owner_digest, "ryan-d0-fixture-1")
    _publish_immutable(path, canonical_bytes(base))
    chain = load_ratified_d0_chain(
        generation_root,
        owner_digest=candidate.owner_digest,
        ratification_id="ryan-d0-fixture-1",
    )
    verify_d0_chain_for_grb_conversion(
        chain, live_query_context_sha256=cand["query_embedding_context_sha256"]
    )
    with pytest.raises(D0AttestationError):
        verify_d0_chain_for_grb_conversion(chain, live_query_context_sha256="2" * 64)
    bad = dict(base)
    bad["candidate_artifact_sha256"] = "3" * 64
    _publish_immutable(
        ratification_path(generation_root, candidate.owner_digest, "bad-digest"),
        canonical_bytes(bad),
    )
    with pytest.raises(D0AttestationError):
        load_ratified_d0_chain(
            generation_root,
            owner_digest=candidate.owner_digest,
            ratification_id="bad-digest",
        )
    invalidated = dict(base)
    invalidated["invalidated"] = True
    with pytest.raises(D0AttestationError, match="invalidated"):
        validate_d0_ratification_record(invalidated)
    with pytest.raises(D0AttestationError, match="missing D0 artifact"):
        load_ratified_d0_chain(
            generation_root,
            owner_digest=candidate.owner_digest,
            ratification_id="does-not-exist",
        )


def test_query_context_missing_digest_quant_version(d0_env, monkeypatch):
    _mock_ollama(monkeypatch, digest=None)
    with pytest.raises(D0AttestationError, match="digest"):
        derive_query_embedding_context(d0_env["cfg"], admitted_dimension=3)
    _mock_ollama(monkeypatch, quant=None)
    with pytest.raises(D0AttestationError, match="quantization"):
        derive_query_embedding_context(d0_env["cfg"], admitted_dimension=3)
    _mock_ollama(monkeypatch, version=None)
    with pytest.raises(D0AttestationError, match="runtime version"):
        derive_query_embedding_context(d0_env["cfg"], admitted_dimension=3)


def test_production_boundary_refusal(d0_env, tmp_path, monkeypatch):
    live_chroma = tmp_path / "live-chroma"
    live_chroma.mkdir()
    monkeypatch.setattr(
        "cg2_legacy_vector_attestation._resolve_live_production_paths",
        lambda: (live_chroma.resolve(), tmp_path / "live-generations"),
    )
    cfg = dict(d0_env["cfg"])
    cfg["index"] = dict(d0_env["cfg"]["index"])
    cfg["index"]["chroma_dir"] = str(live_chroma)
    with pytest.raises(D0AttestationError, match="production Chroma"):
        capture_d0_legacy_vector_candidate(
            cfg,
            owner_key=d0_env["owner_key"],
            source_path=d0_env["source"],
            accepted_source_hash=d0_env["accepted"],
        )


def test_no_writes_to_configured_live_generation_root(d0_env, tmp_path):
    live = tmp_path / "live-generations"
    live.mkdir()
    before = {path.relative_to(live): path.stat().st_mtime_ns for path in live.rglob("*")}
    _capture(d0_env)
    after = {path.relative_to(live): path.stat().st_mtime_ns for path in live.rglob("*")}
    assert before == after
    generation_root = Path(generation_root_for_cfg(d0_env["cfg"]))
    assert generation_root.resolve() != live.resolve()


def test_restore_preserves_d0_and_keeps_backup_evidence_non_authoritative(d0_env, tmp_path):
    candidate = _capture(d0_env)
    validation = _validate(d0_env, candidate.candidate_sha256)
    cand = json.loads(candidate.path.read_text(encoding="utf-8"))
    record = {
        "schema_version": CG2_D0_RATIFICATION_V1,
        "ratification_id": "ryan-d0-fixture-restore",
        "candidate_artifact_sha256": candidate.candidate_sha256,
        "validation_result_sha256": validation.validation_result_sha256,
        "owner_key": d0_env["owner_key"],
        "owner_digest": candidate.owner_digest,
        "accepted_legacy_snapshot_root": cand["accepted_legacy_snapshot_root"],
        "accepted_legacy_vector_root": cand["accepted_legacy_vector_root"],
        "producer_repository_sha": cand["producer_repository_sha"],
        "capture_identity": cand["capture_module_identity"],
        "capture_time": cand["capture_start_time"],
        "query_embedding_context_sha256": cand["query_embedding_context_sha256"],
    }
    from cg2_legacy_vector_attestation import _publish_immutable, ratification_path

    generation_root = Path(generation_root_for_cfg(d0_env["cfg"]))
    _publish_immutable(
        ratification_path(generation_root, candidate.owner_digest, "ryan-d0-fixture-restore"),
        canonical_bytes(record),
    )
    root = tmp_path / "restore-root"
    root.mkdir()
    (root / "chroma").mkdir()
    (root / "decisions-approved.jsonl").write_text("{}\n", encoding="utf-8")
    # Move generation root into the restore data root.
    dest = root / "file_generations"
    dest.symlink_to(generation_root)
    assert "file_generations" in closed_state_spec_paths()
    result = inventory_restored_state(root, root)
    d0_rows = [row for row in result.classifications if row.path == "file_generations"]
    assert d0_rows
    assert d0_rows[0].outcome == OUTCOME_VALID
    assert d0_rows[0].authority == "retained_d0_and_generation_evidence"
    evidence_rows = [
        row
        for row in result.classifications
        if row.authority == "capture_evidence_non_authority"
    ]
    assert all(row.authority == "capture_evidence_non_authority" for row in evidence_rows)

    # Divergent candidate filename must fail closed.
    bad = tmp_path / "restore-bad"
    bad.mkdir()
    (bad / "chroma").mkdir()
    (bad / "decisions-approved.jsonl").write_text("{}\n", encoding="utf-8")
    bad_gen = bad / "file_generations" / "legacy_vector_attestation" / candidate.owner_digest / "candidates"
    bad_gen.mkdir(parents=True)
    (bad_gen / f"{'0'*64}.json").write_bytes(candidate.path.read_bytes())
    blocked = inventory_restored_state(bad, bad)
    blocked_rows = [row for row in blocked.classifications if row.path == "file_generations"]
    assert blocked_rows
    assert blocked_rows[0].outcome == OUTCOME_BLOCKED
    assert blocked.exit_code == EXIT_BLOCKED
