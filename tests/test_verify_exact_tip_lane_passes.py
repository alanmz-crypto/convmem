"""Unit tests for exact-tip lane PASS and closeout readiness helpers."""

# pylint: disable=duplicate-code,wrong-import-position

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify_exact_tip_lane_passes import (
    EvidenceItem,
    EvidenceMeta,
    classify_lane,
    is_edited,
    latest_lane_verdict,
    verdict_of,
    verify_exact_tip_lane_passes,
    whole_token_sha_present,
)
from verify_pr_closeout_readiness import (
    CloseoutFlags,
    CloseoutHooks,
    CloseoutInputs,
    PR52_CLOSEOUT_ALLOWLIST,
    check_body,
    verify_closeout_readiness,
)

SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
BASE = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
OTHER = "cccccccccccccccccccccccccccccccccccccccc"


def _item(
    *,
    body: str,
    author: str = "alanmz-crypto",
    kind: str = "issue_comment",
    item_id: int = 1,
    created_at: str = "2026-07-20T10:00:00Z",
    updated_at: str | None = None,
    url: str = "https://example.test/1",
    review_state: str = "",
) -> EvidenceItem:
    return EvidenceItem(
        kind=kind,
        item_id=item_id,
        author=author,
        body=body,
        meta=EvidenceMeta(
            created_at=created_at,
            updated_at=created_at if updated_at is None else updated_at,
            url=url,
            review_state=review_state,
        ),
    )


def _canonical(lane: str, verdict: str, sha: str = SHA, base: str = BASE) -> str:
    return (
        f"Lane: {lane}\n"
        f"Verdict: {verdict}\n"
        f"Reviewed head: {sha}\n"
        f"Reviewed base: {base}\n"
    )


class ExactTipHelpersTests(unittest.TestCase):
    def test_whole_token_rejects_longer_hash_substring(self):
        longer = SHA + "dead"
        self.assertFalse(whole_token_sha_present(longer, SHA))
        self.assertTrue(whole_token_sha_present(f"head {SHA} ok", SHA))

    def test_classify_lane_requires_lane_line(self):
        self.assertEqual(
            classify_lane("Lane: GitHub Copilot audit lane\n"), "copilot"
        )
        self.assertEqual(classify_lane("Lane: Kiro\n"), "kiro")
        self.assertIsNone(classify_lane("Thanks Kiro for the review\n"))
        self.assertIsNone(
            classify_lane("Lane: GitHub Copilot audit lane\nLane: Kiro\n")
        )

    def test_verdict_rejects_bare_pass_prose(self):
        self.assertIsNone(verdict_of("This is a PASS for the tip\n"))
        self.assertEqual(verdict_of("Verdict: PASS\n"), "PASS")
        self.assertIsNone(verdict_of("Verdict: PASS\nVerdict: FAIL\n"))

    def test_edited_comment_rejected(self):
        item = _item(
            body=_canonical("Kiro", "PASS"),
            updated_at="2026-07-20T11:00:00Z",
        )
        self.assertTrue(is_edited(item))
        ok, msgs = verify_exact_tip_lane_passes([item], sha=SHA, base=BASE)
        self.assertFalse(ok)
        self.assertTrue(any("no qualifying" in m for m in msgs))

    def test_pending_review_rejected(self):
        items = [
            _item(
                body=_canonical("Kiro", "PASS"),
                kind="review",
                review_state="PENDING",
            ),
            _item(
                body=_canonical("GitHub Copilot audit lane", "PASS"),
                item_id=2,
            ),
        ]
        ok, _ = verify_exact_tip_lane_passes(items, sha=SHA, base=BASE)
        self.assertFalse(ok)

    def test_incidental_prose_does_not_qualify(self):
        prose = (
            f"GitHub Copilot audit lane thinks this is a PASS for {SHA} "
            f"on base {BASE}\n"
        )
        items = [
            _item(body=prose, item_id=1),
            _item(body=_canonical("Kiro", "PASS"), item_id=2),
        ]
        ok, msgs = verify_exact_tip_lane_passes(items, sha=SHA, base=BASE)
        self.assertFalse(ok)
        self.assertTrue(any("Copilot" in m and "no qualifying" in m for m in msgs))

    def test_missing_reviewed_base_rejected(self):
        body = (
            "Lane: Kiro\n"
            f"Verdict: PASS\n"
            f"Reviewed head: {SHA}\n"
        )
        items = [
            _item(body=body),
            _item(
                body=_canonical("GitHub Copilot audit lane", "PASS"),
                item_id=2,
            ),
        ]
        ok, _ = verify_exact_tip_lane_passes(items, sha=SHA, base=BASE)
        self.assertFalse(ok)

    def test_latest_pass_wins_then_later_fail_blocks(self):
        items = [
            _item(
                body=_canonical("Kiro", "PASS"),
                item_id=1,
                created_at="2026-07-20T10:00:00Z",
            ),
            _item(
                body=_canonical("Kiro", "FAIL"),
                item_id=2,
                created_at="2026-07-20T11:00:00Z",
            ),
            _item(
                body=_canonical("GitHub Copilot audit lane", "PASS"),
                item_id=3,
                created_at="2026-07-20T10:30:00Z",
            ),
        ]
        latest = latest_lane_verdict(items, sha=SHA, base=BASE, lane="kiro")
        assert latest is not None
        self.assertEqual(latest[1], "FAIL")
        ok, _ = verify_exact_tip_lane_passes(items, sha=SHA, base=BASE)
        self.assertFalse(ok)

    def test_both_lanes_pass(self):
        items = [
            _item(
                body=_canonical("GitHub Copilot audit lane", "PASS"),
                item_id=10,
            ),
            _item(
                body=_canonical("Kiro", "PASS"),
                item_id=11,
                created_at="2026-07-20T10:01:00Z",
            ),
        ]
        ok, msgs = verify_exact_tip_lane_passes(items, sha=SHA, base=BASE)
        self.assertTrue(ok, msgs)
        self.assertEqual(sum(1 for m in msgs if m.startswith("PASS ")), 2)


class CloseoutReadinessTests(unittest.TestCase):
    def _clean_view(self, **overrides) -> dict:
        view = {
            "state": "OPEN",
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "headRefOid": SHA,
            "baseRefOid": BASE,
            "body": (
                f"Reviewed head `{SHA}` on base `{BASE}`.\n"
                "- **Kiro:** sign-off\n"
                "- **Not authorized:** R2a execution\n"
            ),
            "files": [{"path": p} for p in sorted(PR52_CLOSEOUT_ALLOWLIST)],
        }
        view.update(overrides)
        return view

    def _pass_items(self) -> list[EvidenceItem]:
        return [
            _item(
                body=_canonical("GitHub Copilot audit lane", "PASS"),
                item_id=1,
            ),
            _item(
                body=_canonical("Kiro", "PASS"),
                item_id=2,
                created_at="2026-07-20T10:01:00Z",
            ),
        ]

    def _inputs(self, **kwargs) -> CloseoutInputs:
        hooks_kwargs = {
            "fetch_pr_view": self._clean_view,
            "count_threads": lambda: 0,
            "fetch_evidence": lambda *_a: self._pass_items(),
        }
        for key in ("fetch_pr_view", "count_threads", "fetch_evidence"):
            if key in kwargs:
                hooks_kwargs[key] = kwargs.pop(key)
        flag_keys = ("require_mutex_acquired", "check_allowlist")
        flags = CloseoutFlags(
            **{k: kwargs.pop(k) for k in flag_keys if k in kwargs}
        )
        return CloseoutInputs(
            owner="alanmz-crypto",
            repo="convmem",
            pr=52,
            sha=SHA,
            base=BASE,
            flags=flags,
            hooks=CloseoutHooks(**hooks_kwargs),
            **kwargs,
        )

    def test_check_body_flags_codex_and_missing_sha(self):
        bad = check_body(
            "- **Codex:** audit\nhead missing\n",
            sha=SHA,
            base=BASE,
        )
        self.assertTrue(any("Codex" in e for e in bad))
        self.assertTrue(any("head" in e for e in bad))

    def test_readiness_ok(self):
        ok, msgs = verify_closeout_readiness(
            self._inputs(check_allowlist=True)
        )
        self.assertTrue(ok, msgs)

    def test_mutex_rejects_foreign_author(self):
        items = self._pass_items() + [
            _item(
                body="MAIN-MERGE-MUTEX ACQUIRED for PR #52 closeout",
                author="attacker",
                item_id=99,
                created_at="2026-07-20T12:00:00Z",
            )
        ]
        ok, msgs = verify_closeout_readiness(
            self._inputs(
                require_mutex_acquired=True,
                fetch_evidence=lambda *_a: items,
            )
        )
        self.assertFalse(ok)
        self.assertTrue(any("mutex" in m.lower() for m in msgs))

    def test_mutex_rejects_edited_comment(self):
        items = self._pass_items() + [
            _item(
                body="MAIN-MERGE-MUTEX ACQUIRED for PR #52 closeout",
                item_id=99,
                created_at="2026-07-20T12:00:00Z",
                updated_at="2026-07-20T12:05:00Z",
            )
        ]
        ok, _msgs = verify_closeout_readiness(
            self._inputs(
                require_mutex_acquired=True,
                fetch_evidence=lambda *_a: items,
            )
        )
        self.assertFalse(ok)

    def test_mutex_required_ok(self):
        items = self._pass_items() + [
            _item(
                body="MAIN-MERGE-MUTEX ACQUIRED for PR #52 closeout",
                item_id=99,
                created_at="2026-07-20T12:00:00Z",
            )
        ]
        ok, msgs = verify_closeout_readiness(
            self._inputs(
                require_mutex_acquired=True,
                fetch_evidence=lambda *_a: items,
            )
        )
        self.assertTrue(ok, msgs)

    def test_allowlist_constant_has_twelve_paths(self):
        self.assertEqual(len(PR52_CLOSEOUT_ALLOWLIST), 12)
        for name in (
            "verify_exact_tip_lane_passes",
            "verify_pr_closeout_readiness",
        ):
            path = SCRIPTS / f"{name}.py"
            spec = importlib.util.spec_from_file_location(name, path)
            assert spec and spec.loader
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)


if __name__ == "__main__":
    unittest.main()
