"""Acceptance tests for Crush-only verbatim evidence retrieval (#263).

Fixtures only — no live Crush DB, no Chroma writes, no config mutation.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unicodedata
import unittest
from pathlib import Path
from unittest import mock

from ask import _attach_verbatim_source_context
from verbatim_evidence import (
    LABEL_SUMMARY,
    LABEL_UNAVAILABLE,
    LABEL_VERBATIM_SOURCE,
    EvidenceLocator,
    EvidenceStatus,
    digest_excerpt,
    format_labeled_context,
    normalize_evidence_text,
    retrieve_verbatim_evidence,
)
from verbatim_evidence.crush import TRUNCATION_MARKER


SID_HEADING = "Social Infrastructure Density (SID)"
SID_BODY = (
    f"The most scientifically advanced metrics include "
    f"**{SID_HEADING}** as a peer-reviewed quality-of-life measure."
)
SESSION_ID = "d82521a1-4535-4ef2-b920-b819f548c25a"
MESSAGE_ID = "49631113-ab85-4c1b-9a6c-36524b15e914"


def _write_crush_fixture(
    path: Path,
    *,
    include_sid: bool = True,
    include_hidden_parts: bool = True,
    long_sid: bool = False,
) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE goose_db_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id INTEGER NOT NULL,
            is_applied INTEGER NOT NULL,
            tstamp TIMESTAMP DEFAULT (datetime('now'))
        );
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            cost REAL NOT NULL DEFAULT 0.0,
            updated_at INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            parts TEXT NOT NULL DEFAULT '[]',
            model TEXT,
            provider TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            finished_at INTEGER
        );
        """
    )
    con.execute(
        "INSERT INTO sessions VALUES (?, ?, 2, 0, 0, 0.0, ?, ?)",
        (SESSION_ID, "SID fixture", 1_700_000_000_000, 1_700_000_000_000),
    )
    user_parts = json.dumps(
        [{"type": "text", "data": {"text": "What are top quality-of-life metrics?"}}]
    )
    text_body = ("X" * 2500 + "\n" + SID_BODY) if long_sid else SID_BODY
    assistant_parts_list: list[dict] = []
    if include_hidden_parts:
        assistant_parts_list.append(
            {
                "type": "reasoning",
                "data": {"thinking": "SECRET_REASONING_SHOULD_NOT_LEAK"},
            }
        )
        assistant_parts_list.append(
            {
                "type": "tool",
                "data": {"name": "bash", "output": "SECRET_TOOL_PAYLOAD"},
            }
        )
    if include_sid:
        assistant_parts_list.append({"type": "text", "data": {"text": text_body}})
    else:
        assistant_parts_list.append(
            {"type": "text", "data": {"text": "No metrics discussed."}}
        )
    assistant_parts_list.append(
        {"type": "finish", "data": {"reason": "stop", "time": 1}}
    )
    assistant_parts = json.dumps(assistant_parts_list)
    con.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, NULL)",
        ("m-user", SESSION_ID, "user", user_parts, 1_700_000_001_000, 1_700_000_001_000),
    )
    con.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        (
            MESSAGE_ID,
            SESSION_ID,
            "assistant",
            assistant_parts,
            "qwen-fixture",
            "ollama",
            1_700_000_002_000,
            1_700_000_002_000,
        ),
    )
    # Negative-control session: related topic, no SID heading.
    other_session = "negative-control-session"
    con.execute(
        "INSERT INTO sessions VALUES (?, ?, 1, 0, 0, 0.0, ?, ?)",
        (other_session, "Nearby summary", 1_700_000_010_000, 1_700_000_010_000),
    )
    con.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        (
            "m-near",
            other_session,
            "assistant",
            json.dumps(
                [
                    {
                        "type": "text",
                        "data": {
                            "text": (
                                "Urban amenity density is sometimes discussed "
                                "near infrastructure topics, but this message "
                                "never names the SID heading."
                            )
                        },
                    }
                ]
            ),
            "qwen-fixture",
            "ollama",
            1_700_000_011_000,
            1_700_000_011_000,
        ),
    )
    con.commit()
    con.close()


def _write_unsupported_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE chat_message (id INTEGER PRIMARY KEY, content TEXT)")
    con.execute("INSERT INTO chat_message VALUES (1, 'hello')")
    con.commit()
    con.close()


class TestVerbatimEvidenceAcceptance(unittest.TestCase):
    """Eight architecture acceptance checks for the Crush-only slice."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.db_path = root / "project" / ".crush" / "crush.db"
        cls.db_path.parent.mkdir(parents=True)
        _write_crush_fixture(cls.db_path)

        cls.long_db = root / "long" / ".crush" / "crush.db"
        cls.long_db.parent.mkdir(parents=True)
        _write_crush_fixture(cls.long_db, long_sid=True)

        cls.unsupported = root / "other.db"
        _write_unsupported_db(cls.unsupported)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _sid_locator(self, **overrides) -> EvidenceLocator:
        base = dict(
            source_path=str(self.db_path),
            session_id=SESSION_ID,
            start_offset=0,
            end_offset=1,
        )
        base.update(overrides)
        return EvidenceLocator(**base)

    def test_01_exact_sid_fixture_returns_provenance(self):
        result = retrieve_verbatim_evidence(
            self._sid_locator(), SID_HEADING
        )
        self.assertEqual(result.status, EvidenceStatus.AVAILABLE)
        self.assertEqual(len(result.excerpts), 1)
        excerpt = result.excerpts[0]
        self.assertIn(SID_HEADING, excerpt.excerpt)
        self.assertEqual(excerpt.session_id, SESSION_ID)
        self.assertEqual(excerpt.message_id, MESSAGE_ID)
        self.assertEqual(excerpt.role, "assistant")
        self.assertEqual(excerpt.source_path, str(self.db_path))
        self.assertEqual(excerpt.adapter_kind, "sqlite_crush")
        self.assertFalse(excerpt.truncated)
        self.assertEqual(
            excerpt.content_digest_sha256, digest_excerpt(excerpt.excerpt)
        )

    def test_02_near_match_returns_unavailable_match(self):
        result = retrieve_verbatim_evidence(
            self._sid_locator(session_id="negative-control-session", start_offset=0, end_offset=0),
            SID_HEADING,
        )
        self.assertEqual(result.status, EvidenceStatus.UNAVAILABLE_MATCH)
        self.assertEqual(result.excerpts, ())

    def test_03_missing_and_unsupported_source(self):
        missing = retrieve_verbatim_evidence(
            EvidenceLocator(
                source_path=str(Path(self.tmp.name) / "nope.db"),
                session_id=SESSION_ID,
            ),
            SID_HEADING,
        )
        self.assertEqual(missing.status, EvidenceStatus.UNAVAILABLE_SOURCE)
        self.assertEqual(missing.reason, "source_missing")

        unsupported = retrieve_verbatim_evidence(
            EvidenceLocator(
                source_path=str(self.unsupported),
                session_id="any",
            ),
            SID_HEADING,
        )
        self.assertEqual(unsupported.status, EvidenceStatus.UNAVAILABLE_SOURCE)
        self.assertEqual(unsupported.reason, "unsupported_source")

    def test_04_reasoning_and_tool_parts_excluded(self):
        result = retrieve_verbatim_evidence(self._sid_locator(), SID_HEADING)
        self.assertEqual(result.status, EvidenceStatus.AVAILABLE)
        text = result.excerpts[0].excerpt
        self.assertNotIn("SECRET_REASONING_SHOULD_NOT_LEAK", text)
        self.assertNotIn("SECRET_TOOL_PAYLOAD", text)
        self.assertIn(SID_HEADING, text)

    def test_05_oversized_excerpt_truncates_deterministically(self):
        result = retrieve_verbatim_evidence(
            EvidenceLocator(
                source_path=str(self.long_db),
                session_id=SESSION_ID,
            ),
            SID_HEADING,
            max_excerpt_chars=80,
        )
        self.assertEqual(result.status, EvidenceStatus.AVAILABLE)
        excerpt = result.excerpts[0]
        self.assertTrue(excerpt.truncated)
        self.assertTrue(excerpt.excerpt.endswith(TRUNCATION_MARKER))
        self.assertLessEqual(len(excerpt.excerpt), 80)
        # Digest is over post-truncation excerpt after NFC+LF.
        expected = hashlib.sha256(
            normalize_evidence_text(excerpt.excerpt).encode("utf-8")
        ).hexdigest()
        self.assertEqual(excerpt.content_digest_sha256, expected)
        # Pre-truncation body is longer; digest must not equal full-text digest.
        full = normalize_evidence_text(("X" * 2500 + "\n" + SID_BODY))
        full_digest = hashlib.sha256(full.encode("utf-8")).hexdigest()
        self.assertNotEqual(excerpt.content_digest_sha256, full_digest)

    def test_06_ask_context_labels_summary_and_verbatim_separately(self):
        evidence = retrieve_verbatim_evidence(self._sid_locator(), SID_HEADING)
        context, citations, items = format_labeled_context(
            summary_text="Generated summary mentioning SID vaguely.",
            summary_meta={
                "tool": "crush",
                "source_path": str(self.db_path),
                "session_id": SESSION_ID,
                "start_offset": 0,
                "end_offset": 1,
            },
            evidence=evidence,
        )
        labels = [item["label"] for item in items]
        self.assertEqual(labels[0], LABEL_SUMMARY)
        self.assertIn(LABEL_VERBATIM_SOURCE, labels)
        self.assertIn("label=summary", context)
        self.assertIn("label=verbatim_source", context)
        self.assertEqual(citations[0]["context_label"], LABEL_SUMMARY)
        self.assertEqual(citations[1]["context_label"], LABEL_VERBATIM_SOURCE)

    def test_07_summary_similarity_alone_cannot_create_verbatim_source(self):
        # Summary-like hit points at the negative-control session: related
        # topic language in a generated summary must not invent verbatim_source.
        summary_hit = {
            "document": (
                "Conversation summary: discussed infrastructure density and "
                f"quality-of-life metrics including {SID_HEADING}."
            ),
            "metadata": {
                "tool": "crush",
                "source_path": str(self.db_path),
                "session_id": "negative-control-session",
                "start_offset": 0,
                "end_offset": 0,
            },
        }
        context, citations, _blocks = _attach_verbatim_source_context(
            [summary_hit], query_text=SID_HEADING
        )
        self.assertIn(f"label={LABEL_SUMMARY}", context)
        self.assertIn(f"label={LABEL_UNAVAILABLE}", context)
        self.assertNotIn(f"label={LABEL_VERBATIM_SOURCE}", context)
        self.assertEqual(citations[1]["context_label"], LABEL_UNAVAILABLE)
        self.assertEqual(
            citations[1]["evidence_status"], EvidenceStatus.UNAVAILABLE_MATCH.value
        )

    def test_08_hermetic_no_live_corpus_or_chroma_writes(self):
        real_home_crush = (Path.home() / ".crush" / "crush.db").resolve()
        opened: list[Path] = []
        real_connect = sqlite3.connect

        def guarded_connect(database, *args, **kwargs):
            raw = str(database)
            if raw.startswith("file:"):
                file_part = raw.split("file:", 1)[-1].split("?", 1)[0]
                resolved = Path(file_part).resolve()
            else:
                resolved = Path(raw).expanduser().resolve()
            opened.append(resolved)
            if resolved == real_home_crush:
                raise AssertionError("test opened real Crush DB")
            if "chroma" in resolved.name.lower() or "chroma" in str(resolved.parent).lower():
                raise AssertionError("test opened Chroma")
            return real_connect(database, *args, **kwargs)

        with mock.patch(
            "verbatim_evidence.crush.sqlite3.connect",
            side_effect=guarded_connect,
        ):
            result = retrieve_verbatim_evidence(self._sid_locator(), SID_HEADING)
            self.assertEqual(result.status, EvidenceStatus.AVAILABLE)

        self.assertTrue(opened)
        for path in opened:
            self.assertNotEqual(path, real_home_crush)

        # NFC consistency: matching and digesting share the same normalize.
        nfc = unicodedata.normalize("NFC", "cafe\u0301")
        self.assertEqual(normalize_evidence_text("cafe\u0301"), nfc)
        self.assertEqual(
            digest_excerpt("a\r\nb"),
            hashlib.sha256(b"a\nb").hexdigest(),
        )
        mixed = retrieve_verbatim_evidence(
            self._sid_locator(),
            unicodedata.normalize("NFD", SID_HEADING),
        )
        self.assertEqual(mixed.status, EvidenceStatus.AVAILABLE)

    def test_invalid_locator_without_identity(self):
        result = retrieve_verbatim_evidence(
            EvidenceLocator(source_path=str(self.db_path)),
            SID_HEADING,
        )
        self.assertEqual(result.status, EvidenceStatus.INVALID_LOCATOR)


if __name__ == "__main__":
    unittest.main()
