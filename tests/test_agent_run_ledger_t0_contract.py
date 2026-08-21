"""T0 — Kiro hook contract fixtures for Arc Runway Ledger.

Locks stdin/env/exit/idempotency/stop-fallback expectations before T1–T4
capture code is written. No live hooks; fixtures only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "agent_run_ledger"
CONTRACT_PATH = FIXTURE_ROOT / "kiro_hook_contract.json"
STDIN_DIR = FIXTURE_ROOT / "stdin"
GIT_DIR = FIXTURE_ROOT / "git"


@pytest.fixture(scope="module")
def contract() -> dict:
    raw = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
    assert raw["slice"] == "T0"
    assert raw["client"] == "kiro"
    return raw


def test_t0_contract_documents_fail_open_and_forbidden_fields(contract: dict) -> None:
    exit_policy = contract["exit_policy"]
    assert exit_policy["fail_open_exit_code"] == 0
    assert exit_policy["stdout"] == "empty"
    assert exit_policy["never_emit_stop_block_decision"] is True

    forbidden = set(contract["stdin_fields"]["forbidden_to_persist"])
    assert "assistant_response" in forbidden
    assert "USER_PROMPT" in forbidden

    assert contract["native_session_id"]["normalize_sess_prefix"] is False
    assert contract["stop_fallback"]["never_close_newest_by_recency"] is True
    assert contract["stop_cadence"]["docs_conflict"] is True
    assert contract["stop_cadence"]["soak_required_before_enable"] is True
    assert contract["hook_files"]["default_enabled_for_landing"] is False


@pytest.mark.parametrize(
    "name",
    [
        "session_start_ok.json",
        "session_start_missing_id.json",
        "stop_ok.json",
        "stop_missing_id.json",
        "stop_with_assistant_response.json",
    ],
)
def test_t0_stdin_fixtures_are_valid_json_objects(name: str) -> None:
    payload = json.loads((STDIN_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert "hook_event_name" in payload
    assert "cwd" in payload


def test_t0_session_start_ok_has_native_id() -> None:
    payload = json.loads((STDIN_DIR / "session_start_ok.json").read_text(encoding="utf-8"))
    assert isinstance(payload["session_id"], str) and payload["session_id"]
    assert "assistant_response" not in payload


def test_t0_session_start_missing_id_is_explicit() -> None:
    payload = json.loads(
        (STDIN_DIR / "session_start_missing_id.json").read_text(encoding="utf-8")
    )
    assert "session_id" not in payload


def test_t0_stop_with_assistant_response_marks_content_for_redaction(
    contract: dict,
) -> None:
    payload = json.loads(
        (STDIN_DIR / "stop_with_assistant_response.json").read_text(encoding="utf-8")
    )
    assert "assistant_response" in payload
    assert payload["assistant_response"]
    assert "assistant_response" in contract["stdin_fields"]["forbidden_to_persist"]


def test_t0_event_name_aliases_cover_legacy_and_pascal(contract: dict) -> None:
    aliases = contract["stdin_fields"]["event_name_aliases"]
    assert "agentSpawn" in aliases["SessionStart"]
    assert "SessionStart" in aliases["SessionStart"]
    assert "stop" in aliases["Stop"]
    assert "Stop" in aliases["Stop"]
    assert "agentStop" in aliases["Stop"]


def test_t0_git_command_fixture_is_bounded() -> None:
    commands = json.loads((GIT_DIR / "commands.json").read_text(encoding="utf-8"))
    assert commands["schema_version"] == 1
    ids = {row["id"] for row in commands["commands"]}
    assert {"toplevel", "head_sha", "branch", "dirty", "name_only_diff"} <= ids
    for row in commands["commands"]:
        assert row["argv"][0] == "git"
        assert "maps_to" in row

    samples = json.loads((GIT_DIR / "sample_outputs.json").read_text(encoding="utf-8"))
    case_ids = {c["id"] for c in samples["cases"]}
    assert {"clean_branch", "detached_dirty", "non_git_cwd"} <= case_ids

    non_git = next(c for c in samples["cases"] if c["id"] == "non_git_cwd")
    assert non_git["expected"]["repository"] is None
    assert non_git["expected"]["head_revision"] is None

    detached = next(c for c in samples["cases"] if c["id"] == "detached_dirty")
    assert detached["expected"]["branch"] == "detached"
    assert detached["expected"]["dirty_tree"] is True


def test_t0_contract_lists_all_fixture_files(contract: dict) -> None:
    for rel in contract["fixtures"]["stdin"] + contract["fixtures"]["git"]:
        path = FIXTURE_ROOT / rel
        assert path.is_file(), f"missing fixture {rel}"


def test_t0_contract_markdown_exists() -> None:
    assert (FIXTURE_ROOT / "CONTRACT.md").is_file()
