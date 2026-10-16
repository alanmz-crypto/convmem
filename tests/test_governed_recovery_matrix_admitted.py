# pylint: disable=wrong-import-position,unused-import,redefined-outer-name
"""N8/N9 exercise real admission and effects through isolated recovery workers."""
from __future__ import annotations

import json

from tests._safe_harbor_bootstrap import require_t3_bootstrap

require_t3_bootstrap()
from tests._safe_harbor_t4_pytest import isolated_t4_child_network
from tests._safe_harbor_t4_harness import expect_probe_ok, expected_embedding_sha256
from tests.test_safe_harbor_t2 import cli, isolated, scratch, _current, _pid_events


def _assert_completion(cli, payload):
    pid = payload["pid"]
    units = cli.dump()["chroma"]["units"]
    matches = [u for u in units if u["metadata"].get("proposal_id") == pid]
    assert len(matches) == 1
    unit = matches[0]
    assert unit["embedding_sha"] == expected_embedding_sha256(unit["document"])
    exports = [json.loads(line) for line in cli.export.read_text().splitlines() if line.strip()]
    matching_exports = [e for e in exports if e.get("id") == unit["id"]]
    assert len(matching_exports) == 1
    assert matching_exports[0]["ledger_id"] == unit["metadata"]["ledger_id"]
    events = _pid_events(cli, pid)
    assert [event["event_type"] for event in events].count("APPROVED") == 1
    assert events[-1]["event_type"] == "APPROVED"


def test_n8_retry_chroma_then_approved(cli):
    payload = expect_probe_ok(cli, "matrix.create_absence", extra_env=_current(cli))
    assert payload["action"] == "retry_chroma"
    assert payload["after_units"] == payload["before_units"] + 1
    assert payload["chroma_id"] == payload["export_id"]
    _assert_completion(cli, payload)


def test_n9_marker_and_hash_append_approved(cli):
    # The existing worker independently asserts documents, metadata and vectors
    # unchanged across recovery; the parent verifies the final published effects.
    payload = expect_probe_ok(cli, "matrix.event_only", extra_env=_current(cli))
    assert payload["action"] == "approve"
    _assert_completion(cli, payload)
