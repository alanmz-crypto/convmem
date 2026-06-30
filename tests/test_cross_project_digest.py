"""Tests for cross_project_digest (no LLM)."""

from cross_project_digest import (
    is_coordination_unresolved,
    load_link_queue,
    load_recent_decisions,
    render_digest_markdown,
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
