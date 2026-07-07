"""Pure, deterministic grading helpers for the summary + synthesis evals.

Kept model-free and importable so the offline unit tests exercise the exact
same logic the live scripts use (the scripts themselves are hyphenated and not
importable). These are the HARD GATE; judge scores (eval_judge) are advisory.
"""

from __future__ import annotations

import re

BANNED_SUMMARY_PHRASES = ("various topics", "several issues")

# Abstention markers matching the ASK_PROMPT contract ("say so clearly",
# "the index has related material but not this specific answer").
_ABSTAIN_MARKERS = (
    "do not contain",
    "does not contain",
    "contain no information",
    "no information about",
    "not enough information",
    "not contain enough",
    "related material but not",
    "not in the index",
    "no relevant excerpts",
    "cannot answer",
    "can't answer",
    "cannot be answered",
    "can't be answered",
    "question cannot be answered",
    "not have enough",
    "don't have enough",
    "do not mention",
    "does not mention",
)

# Sentence terminator followed by whitespace or end of string. A period inside a
# version/decimal ("llama3.1:8b", "3.1") is followed by a digit, not whitespace,
# so it is naturally excluded — while a real sentence end after a number
# ("...localhost:11434.") is still counted.
_SENTENCE_RE = re.compile(r"[.!?]+(?=\s|$)")
_CITE_RE = re.compile(r"\[(\d+)\]")


def split_summary(text: str) -> tuple[str, str | None]:
    """Return (body, keywords_line) splitting on the 'Keywords:' marker."""
    for line in text.splitlines():
        if re.match(r"\s*keywords\s*:", line, re.IGNORECASE):
            idx = text.lower().index(line.lower())
            return text[:idx].strip(), line.strip()
    return text.strip(), None


def count_sentences(body: str) -> int:
    return len(_SENTENCE_RE.findall(body))


def parse_keywords(keywords_line: str | None) -> list[str]:
    if not keywords_line:
        return []
    _, _, rest = keywords_line.partition(":")
    return [k.strip() for k in rest.split(",") if k.strip()]


def has_banned_phrase(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in BANNED_SUMMARY_PHRASES)


def keyword_recall(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    low = text.lower()
    hits = sum(1 for k in keywords if k.lower() in low)
    return hits / len(keywords)


def grade_summary(text: str, *, must_mention: list[str] | None = None) -> dict:
    """Deterministic structural grade of a summary (the hard gate)."""
    must_mention = must_mention or []
    body, kw_line = split_summary(text)
    n_sentences = count_sentences(body)
    keywords = parse_keywords(kw_line)
    low = text.lower()
    missing_mentions = [m for m in must_mention if m.lower() not in low]

    sentences_ok = n_sentences == 3
    # Prompt asks for 5-8 keywords, but a healthy local model varies run-to-run
    # (temp>0). Gate on "at least 5, not runaway" so normal sampling variance
    # (e.g. 9 keywords) isn't misread as a quality regression; a generous upper
    # bound still catches degenerate/empty output.
    keywords_ok = 5 <= len(keywords) <= 15
    banned = has_banned_phrase(text)
    mentions_ok = not missing_mentions

    return {
        "structural_pass": sentences_ok and keywords_ok and not banned and mentions_ok,
        "n_sentences": n_sentences,
        "n_keywords": len(keywords),
        "banned_phrase": banned,
        "missing_mentions": missing_mentions,
        "sentences_ok": sentences_ok,
        "keywords_ok": keywords_ok,
    }


def cited_indices(answer: str) -> list[int]:
    return [int(m) for m in _CITE_RE.findall(answer)]


def is_abstention(answer: str) -> bool:
    low = answer.lower()
    return any(m in low for m in _ABSTAIN_MARKERS)


def grade_answer(
    answer: str,
    *,
    n_citations: int,
    must_include: list[str] | None = None,
    must_cite: bool = False,
    should_abstain: bool = False,
) -> dict:
    """Deterministic grade of a synthesized answer (the hard gate).

    n_citations is the number of excerpts returned to the answer (upper bound
    for valid citation indices).
    """
    must_include = must_include or []
    low = answer.lower()
    cites = cited_indices(answer)
    invalid_cites = [c for c in cites if c < 1 or c > n_citations]

    if should_abstain:
        abstained = is_abstention(answer)
        return {
            "pass": abstained,
            "mode": "abstain",
            "abstained": abstained,
            "cites": cites,
            "invalid_cites": invalid_cites,
        }

    missing = [t for t in must_include if t.lower() not in low]
    include_ok = not missing
    cite_ok = (not must_cite) or bool(cites)
    cites_valid = not invalid_cites

    return {
        "pass": include_ok and cite_ok and cites_valid,
        "mode": "answer",
        "missing_include": missing,
        "cite_ok": cite_ok,
        "cites": cites,
        "invalid_cites": invalid_cites,
    }
