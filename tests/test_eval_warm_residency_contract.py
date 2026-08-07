"""Timed-worker residency checks are fail-closed for real latency."""

from __future__ import annotations

import subprocess

import pytest

from eval_corpus.subprocess_compare import WorkerFailure, WorkerHandle, worker_query


class _Input:
    def write(self, _value):
        return None

    def flush(self):
        return None


class _Output:
    def __init__(self, payload):
        self.payload = payload

    def readline(self):
        import json

        return json.dumps(self.payload) + "\n"


def _handle(payload):
    proc = subprocess.Popen(
        ["/bin/sh", "-c", "sleep 10"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    proc.stdin.close()
    proc.stdin = _Input()
    proc.stdout = _Output(payload)
    return proc


def _valid_payload(load_duration=0):
    return {
        "type": "result",
        "error": None,
        "hits": [{"id": "unit-1", "metadata": {}, "distance": 0.1}],
        "retrieval_mode": "vector",
        "vector_query_attempted": True,
        "fallback_used": False,
        "query_vector_fingerprint": "a" * 64,
        "query_vector_dimension": 2,
        "query_vector_finite": True,
        "query_vector_norm": 1.0,
        "embedding_request_diagnostics": {"load_duration": load_duration},
        "warm_residency_verified": True,
        "eval_view": "embedding_influenced",
    }


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({**_valid_payload(), "warm_residency_verified": False}, "residency"),
        (_valid_payload(load_duration=1), "loaded or reloaded"),
    ],
)
def test_real_timed_worker_rejects_unverified_residency(payload, message):
    proc = _handle(payload)
    try:
        handle = WorkerHandle(
            arm="baseline",
            proc=proc,
            config_path=None,
            startup={},
            startup_ms=0.0,
            expected_identity={"embed_model_digest": "sha256:" + ("a" * 64)},
            require_warm_residency=True,
        )
        with pytest.raises(WorkerFailure, match=message):
            worker_query(
                handle,
                "q",
                top_k=5,
                eval_view="embedding_influenced",
                enforce_warm_residency=True,
            )
    finally:
        proc.kill()
        proc.wait()
