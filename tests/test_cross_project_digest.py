"""Tests for cross_project_digest (no LLM)."""

from cross_project_digest import (
    digest_ask_question,
    is_coordination_unresolved,
    load_attempts,
    load_link_queue,
    load_recent_decisions,
    recency_check,
    render_digest_markdown,
    render_recency_check_section,
    _pick_relates_to,
)


def test_coordination_unresolved_filters_client_site():
    assert is_coordination_unresolved(
        {"domain": "tooling.kiro", "site": "", "title": "Kiro MCP"}
    )
    assert not is_coordination_unresolved(
        {"domain": "web_stack.security", "site": "staging2.willowyhollow.com", "title": "CSP"}
    )
    assert not is_coordination_unresolved(
        {"domain": "tooling.kiro", "site": "staging2.willowyhollow.com", "title": "x"}
    )


def test_load_recent_decisions_filters_by_age(tmp_path):
    path = tmp_path / "decisions-approved.jsonl"
    path.write_text(
        '{"id":"dec_prop_old","timestamp":"2020-01-01T00:00:00Z","summary":"old"}\n'
        '{"id":"dec_prop_new","timestamp":"2099-06-01T12:00:00Z","summary":"new","relates_to":"dec_prop_x"}\n',
        encoding="utf-8",
    )
    rows = load_recent_decisions(path, days=7, limit=10)
    assert len(rows) == 1
    assert rows[0]["id"] == "dec_prop_new"


def test_load_link_queue_tail(tmp_path):
    path = tmp_path / "link_queue.jsonl"
    lines = [
        '{"ledger_id_a":"a1","ledger_id_b":"b1"}',
        '{"ledger_id_a":"a2","ledger_id_b":"b2"}',
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rows = load_link_queue(path, limit=1)
    assert len(rows) == 1
    assert rows[0]["ledger_id_a"] == "a2"


def test_render_digest_includes_stale_handoff():
    md = render_digest_markdown(
        brief={
            "units": 100,
            "unresolved_count": 13,
            "handoff_staleness": {"stale": True, "newest_file": "SOAK-REPORT.md", "newest_age_label": "5m ago"},
            "projects": [{"slug": "ComfyUI", "knowledge_units": 99, "newest_source_age": "1h ago"}],
        },
        coordination_unresolved=[{"ledger_id": "obs_abc", "domain": "tooling.kiro", "title": "Kiro gap"}],
        recent_decisions=[],
        link_queue=[],
        ask_result=None,
    )
    assert "STALE" in md
    assert "ComfyUI" not in md
    assert "obs_abc" in md


def test_pick_relates_to_from_ask_citation():
    brief = {"recent_decisions": [{"id": "dec_prop_20260601_120000_abcd"}]}
    answer = "Theme [4] cites dec_prop_20260629_005903_51b4 for protocol."
    assert _pick_relates_to(brief, answer) == "dec_prop_20260629_005903_51b4"


def test_digest_ask_question_injects_recent_ids():
    recent = [
        {"id": "dec_prop_20260701_211650_5a62", "summary": "dedupe"},
        {"id": "dec_prop_20260701_182803_987b", "summary": "builder"},
    ]
    q = digest_ask_question(recent)
    assert "dec_prop_20260701_211650_5a62" in q
    assert "Prioritize these recent approved decisions" in q


def test_recency_check_overlap_pass():
    recent = [{"id": "dec_prop_a"}, {"id": "dec_prop_b"}]
    ask = {
        "answer": "Theme dec_prop_a and dec_prop_c.",
        "citations": [{"ledger_id": "dec_prop_a", "n": 1}],
    }
    check = recency_check(recent, ask)
    assert check["pass"] is True
    assert "dec_prop_a" in check["overlap"]


def test_recency_check_warn_when_no_overlap():
    recent = [{"id": "dec_prop_new"}]
    ask = {"answer": "Old theme.", "citations": [{"ledger_id": "dec_prop_old", "n": 1}]}
    check = recency_check(recent, ask)
    assert check["pass"] is False
    md = "\n".join(render_recency_check_section(check))
    assert "WARN" in md


def test_load_attempts_tail(tmp_path):
    path = tmp_path / "attempts.jsonl"
    path.write_text(
        '{"obs_id":"obs_001","outcome":"failed","path":"a.py","summary":"fail"}\n'
        '{"obs_id":"obs_002","outcome":"partial","path":"b.py","summary":"partial"}\n',
        encoding="utf-8",
    )
    rows = load_attempts(path, limit=1)
    assert len(rows) == 1
    assert rows[0]["obs_id"] == "obs_002"


def test_render_digest_do_not_retry():
    attempts = [
        {"obs_id": "obs_001", "outcome": "failed", "path": "a.py", "summary": "fail"},
        {"obs_id": "obs_002", "outcome": "partial", "path": "b.py", "summary": "partial"},
    ]
    md = render_digest_markdown(
        brief={"units": 100, "unresolved_count": 0, "handoff_staleness": {}, "projects": []},
        coordination_unresolved=[],
        recent_decisions=[],
        link_queue=[],
        ask_result=None,
        attempts=attempts,
    )
    assert "## Do not retry" in md
    assert "FAILED" in md
    assert "PARTIAL" in md
