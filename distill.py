"""Distillation layer — extract reusable knowledge units from conversation chunks.

NOTE: DISTILL_PROMPT was previously locked per an earlier handoff ("do not
edit without escalation"). This revision adds a `domain` field to the
extraction schema as part of the multi-domain / multi-model memory upgrade.
It is a deliberate, flagged exception to that lock, not an oversight —
the original four required fields (type/title/summary/keywords) and the
confidence field are unchanged, so old parsing/validation logic still
applies; only one new optional-with-fallback field was added.
"""

import hashlib
import json
import re

from domains import normalize_domain
from llm import generate

DISTILL_PROMPT = """Extract reusable knowledge from this AI conversation.

Return a JSON array. Each item must have:
- type: "solution" | "decision" | "explanation" | "pattern"
- title: short and specific, under 10 words
- summary: 1-2 sentences, self-contained and reusable outside this conversation
- keywords: 5-8 technical terms, tool names, concepts, or error messages
- confidence: 0.0 to 1.0
- domain: a dotted path classifying the subject area, e.g. "coding.backend",
  "web_stack.wordpress.plugins", "web_stack.security", "web_stack.hosting".
  Use "general" if nothing more specific fits.

Rules:
- Only extract items useful in a future session
- Ignore pleasantries, dead ends, repetition, vague discussion
- Be specific: include tool names, file paths, model names, error messages
- If nothing reusable exists, return []
- Return valid JSON only, no commentary

Conversation:
{chunk}"""

_MAX_CHUNK_CHARS = 8000
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def safe_json_parse(text: str) -> list:
    """Parse a JSON array from LLM output; strip fences, retry once, else []."""
    for attempt in range(2):
        cleaned = text.strip()
        cleaned = _FENCE_RE.sub("", cleaned).strip()
        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError:
            if attempt == 0:
                # Retry on substring between first [ and last ]
                start = cleaned.find("[")
                end = cleaned.rfind("]")
                if start != -1 and end != -1 and end > start:
                    text = cleaned[start : end + 1]
                    continue
            return []
    return []


def _resolve_model(model: str) -> str:
    import os

    if "deepseek-v4" in model and not os.environ.get("DEEPSEEK_API_KEY"):
        return "llama3.1:8b"
    return model


def distill(
    chunk_text: str,
    model: str,
    ollama_host: str,
    deepseek_base_url: str = "https://api.deepseek.com",
) -> list[dict]:
    """Extract knowledge units from a conversation chunk."""
    if len(chunk_text) > _MAX_CHUNK_CHARS:
        chunk_text = chunk_text[:_MAX_CHUNK_CHARS]
    prompt = DISTILL_PROMPT.format(chunk=chunk_text)
    model = _resolve_model(model)
    raw = generate(prompt, model, ollama_host, deepseek_base_url)
    return safe_json_parse(raw)


UNIT_TYPES = ("solution", "decision", "explanation", "pattern", "observation")


def make_unit_id(source_path: str, start_offset: int | None, title: str, unit_index: int = 0) -> str:
    """Stable id for a unit within a source file (survives watch re-index).

    Uses source_path + start_offset + unit_index only — title is excluded because LLM
    distillation produces slightly different titles on each run, which would
    defeat deduplication.
    """
    offset = "" if start_offset is None else str(start_offset)
    key = f"{source_path}\0{offset}\0{unit_index}"
    return hashlib.sha256(key.encode()).hexdigest()


def normalize_unit(
    raw: dict,
    *,
    source_path: str,
    tool: str,
    date: str,
    min_confidence: float,
    author_model: str = "unknown",
    start_offset: int | None = None,
    unit_index: int = 0,
) -> dict | None:
    """Validate and enrich a single distilled unit, or return None if rejected."""
    if not isinstance(raw, dict):
        return None

    unit_type = raw.get("type")
    if unit_type not in UNIT_TYPES:
        return None

    title = raw.get("title")
    summary = raw.get("summary")
    if not isinstance(title, str) or not isinstance(summary, str):
        return None
    title, summary = title.strip(), summary.strip()
    if not title or not summary:
        return None

    keywords = raw.get("keywords")
    if not isinstance(keywords, list):
        return None
    keywords = [str(k).strip() for k in keywords if str(k).strip()]
    if len(keywords) < 3:
        return None

    try:
        confidence = float(raw.get("confidence", 0))
    except (TypeError, ValueError):
        return None
    if confidence < min_confidence:
        return None

    domain = normalize_domain(raw.get("domain"))

    return {
        "id": make_unit_id(source_path, start_offset, title, unit_index),
        "type": unit_type,
        "title": title,
        "summary": summary,
        "keywords": keywords,
        "source_path": source_path,
        "confidence": confidence,
        "timestamp": date or None,
        "tool": tool,
        "domain": domain,
        "author_model": author_model,
        "verifier_model": None,
    }
