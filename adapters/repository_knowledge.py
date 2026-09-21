"""Deterministic repository-knowledge chunkers. Never execute input or call an LLM."""

# Chunk is an explicit immutable transport record; similarity with the existing
# documentary indexer is intentional because both implement the same boundary.
# pylint: disable=duplicate-code

from __future__ import annotations

import ast
import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from repository_knowledge_scope import (
    ADAPTER_CONTRACT_VERSION,
    FALLBACK_WINDOW_LINES,
    MAX_CHUNK_CHARS,
    MAX_CHUNKS_PER_FILE,
    MAX_FILE_BYTES,
    OVERLAP_LINES,
    SOURCE_TYPE,
    decide_path,
    source_identity,
)

ADAPTER_VERSION = ADAPTER_CONTRACT_VERSION


class RepositoryKnowledgeParseError(ValueError):
    """A repository-knowledge file could not be parsed as documentary chunks."""


@dataclass(frozen=True)
class Chunk:  # pylint: disable=too-many-instance-attributes
    label: str
    locator: str
    content: str
    start_line: int
    end_line: int
    original_source_text: str | None = None
    byte_start: int | None = None
    byte_end: int | None = None


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_JS_LABEL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\b|^\s*(?:import|export)\b"
)
_TOML_TABLE_RE = re.compile(r"(?m)^\[")


def _refuse(code: str, detail: str) -> None:
    raise RepositoryKnowledgeParseError(f"{code}: {detail}")


def _utf8(data: bytes, *, relpath: str) -> str:
    if b"\x00" in data:
        _refuse("binary", f"{relpath} contains NUL bytes")
    if len(data) > MAX_FILE_BYTES:
        _refuse("resource_limit", f"{relpath} exceeds max_file_bytes")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        _refuse("invalid_utf8", f"{relpath} is not UTF-8: {exc}")
        raise


def _line_windows(text: str, *, label: str, start_line: int = 1) -> list[Chunk]:
    lines = text.splitlines()
    if not lines:
        return []
    if any(len(line) > MAX_CHUNK_CHARS for line in lines):
        _refuse("resource_limit", "source line exceeds max_chunk_chars")
    chunks: list[Chunk] = []
    idx = 0
    while idx < len(lines):
        end = min(len(lines), idx + FALLBACK_WINDOW_LINES)
        while end > idx and len("\n".join(lines[idx:end])) > MAX_CHUNK_CHARS:
            end -= 1
        if end == idx:
            _refuse("resource_limit", "source line exceeds max_chunk_chars")
        body = "\n".join(lines[idx:end])
        first = start_line + idx
        last = start_line + end - 1
        chunks.append(
            Chunk(
                label=f"{label} lines {first}-{last}",
                locator=f"lines:{first}-{last}",
                content=body,
                start_line=first,
                end_line=last,
            )
        )
        if end >= len(lines):
            break
        idx = max(idx + 1, end - OVERLAP_LINES)
    if len(chunks) > MAX_CHUNKS_PER_FILE:
        _refuse("resource_limit", "file exceeds max_chunks_per_file")
    return chunks


def _bounded(chunks: list[Chunk], *, label: str) -> list[Chunk]:
    out: list[Chunk] = []
    for chunk in chunks:
        if len(chunk.content) <= MAX_CHUNK_CHARS:
            out.append(chunk)
            continue
        out.extend(
            _line_windows(
                chunk.content,
                label=f"{label} {chunk.label}",
                start_line=chunk.start_line,
            )
        )
    if len(out) > MAX_CHUNKS_PER_FILE:
        _refuse("resource_limit", "file exceeds max_chunks_per_file")
    if not out:
        _refuse("empty", "no documentary chunks")
    return out


def chunk_markdown(text: str) -> list[Chunk]:
    lines = text.splitlines()
    title = Path("document").stem
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip() or title
    sections: list[tuple[str, int, list[str]]] = []
    current = title
    start = 1
    buf: list[str] = []
    for i, line in enumerate(lines, start=1):
        match = _HEADING_RE.match(line)
        if match:
            if buf or not sections:
                sections.append((current, start, buf))
            current = match.group(2).strip()
            start = i
            buf = [line]
        else:
            buf.append(line)
    sections.append((current, start, buf))
    chunks: list[Chunk] = []
    for label, start_line, body_lines in sections:
        body = "\n".join(body_lines).strip()
        if not body:
            continue
        end_line = start_line + len(body_lines) - 1
        chunks.append(
            Chunk(
                label=label,
                locator=f"lines:{start_line}-{end_line}",
                content=body,
                start_line=start_line,
                end_line=end_line,
            )
        )
    return _bounded(chunks or _line_windows(text, label=title), label="markdown")


def chunk_python(text: str) -> list[Chunk]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        _refuse("parse_error", f"python ast failed: {exc}")
    lines = text.splitlines()
    spans: list[Chunk] = []
    first_def = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first_def = node.lineno if first_def is None else first_def
            end = int(getattr(node, "end_lineno", node.lineno) or node.lineno)
            body = "\n".join(lines[node.lineno - 1 : end])
            spans.append(
                Chunk(
                    label=getattr(node, "name", "definition"),
                    locator=f"lines:{node.lineno}-{end}",
                    content=body,
                    start_line=node.lineno,
                    end_line=end,
                )
            )
    if first_def and first_def > 1:
        preamble = "\n".join(lines[: first_def - 1]).strip()
        if preamble:
            spans.insert(
                0,
                Chunk(
                    label="module preamble",
                    locator=f"lines:1-{first_def - 1}",
                    content=preamble,
                    start_line=1,
                    end_line=first_def - 1,
                ),
            )
    used: set[int] = set()
    for chunk in spans:
        used.update(range(chunk.start_line, chunk.end_line + 1))
    residual_lines = [
        line for idx, line in enumerate(lines, start=1) if idx not in used
    ]
    residual = "\n".join(residual_lines).strip()
    if residual and not spans:
        return _line_windows(text, label="python")
    if residual:
        spans.extend(_line_windows(residual, label="python residual"))
    return _bounded(spans or _line_windows(text, label="python"), label="python")


def chunk_javascript(text: str) -> list[Chunk]:
    lines = text.splitlines()
    labeled = next(
        (i for i, line in enumerate(lines, start=1) if _JS_LABEL_RE.search(line)),
        1,
    )
    windows = _line_windows(text, label="javascript")
    if labeled:
        windows = [
            Chunk(
                label=chunk.label,
                locator=chunk.locator,
                content=chunk.content,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
            )
            for chunk in windows
        ]
    return _bounded(windows, label="javascript")


def _escape_pointer(key: str) -> str:
    return key.replace("~", "~0").replace("/", "~1")


def chunk_json(text: str) -> list[Chunk]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        _refuse("parse_error", f"json failed: {exc}")
    decoder = json.JSONDecoder()
    chunks: list[Chunk] = []

    def add_chunk(pointer: str, value: object, start: int, end: int) -> None:
        dumped = json.dumps(value, ensure_ascii=False, indent=2)
        original = text[start:end]
        if max(len(dumped), len(original)) > MAX_CHUNK_CHARS:
            _refuse("resource_limit", f"json {pointer or '/'} exceeds max_chunk_chars")
        start_line = text.count("\n", 0, start) + 1
        end_line = start_line + original.count("\n")
        chunks.append(
            Chunk(
                label=f"json {pointer}" if pointer else "json document",
                locator=f"pointer:{pointer}",
                content=dumped,
                start_line=start_line,
                end_line=end_line,
                original_source_text=original,
                byte_start=len(text[:start].encode("utf-8")),
                byte_end=len(text[:end].encode("utf-8")),
            )
        )

    def skip_ws(offset: int) -> int:
        while offset < len(text) and text[offset].isspace():
            offset += 1
        return offset

    if isinstance(data, dict) and data:
        offset = skip_ws(0)
        if text[offset : offset + 1] != "{":
            _refuse("parse_error", "json object boundary missing")
        offset += 1
        for expected_key, value in data.items():
            offset = skip_ws(offset)
            key, offset = decoder.raw_decode(text, offset)
            if key != expected_key:
                _refuse("parse_error", "json key decode mismatch")
            offset = skip_ws(offset)
            if text[offset : offset + 1] != ":":
                _refuse("parse_error", "json object colon missing")
            start = skip_ws(offset + 1)
            _decoded, end = decoder.raw_decode(text, start)
            pointer = "/" + _escape_pointer(str(key))
            add_chunk(pointer, value, start, end)
            offset = skip_ws(end)
            if text[offset : offset + 1] == ",":
                offset += 1
    elif isinstance(data, list) and data:
        offset = skip_ws(0)
        if text[offset : offset + 1] != "[":
            _refuse("parse_error", "json array boundary missing")
        offset += 1
        for idx, value in enumerate(data):
            start = skip_ws(offset)
            _decoded, end = decoder.raw_decode(text, start)
            pointer = f"/{idx}"
            add_chunk(pointer, value, start, end)
            offset = skip_ws(end)
            if text[offset : offset + 1] == ",":
                offset += 1
    else:
        start = skip_ws(0)
        _decoded, end = decoder.raw_decode(text, start)
        add_chunk("", data, start, end)
    return _bounded(chunks, label="json")


def chunk_toml(text: str) -> list[Chunk]:
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        _refuse("parse_error", f"toml failed: {exc}")
    starts = [match.start() for match in _TOML_TABLE_RE.finditer(text)]
    if not starts:
        return _bounded(_line_windows(text, label="toml"), label="toml")
    if starts[0] != 0:
        starts = [0] + starts
    chunks: list[Chunk] = []
    for idx, offset in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(text)
        body = text[offset:end].strip()
        if not body:
            continue
        start_line = text[:offset].count("\n") + 1
        end_line = start_line + body.count("\n")
        header = body.splitlines()[0].strip()
        chunks.append(
            Chunk(
                label=header if header.startswith("[") else "toml preamble",
                locator=f"lines:{start_line}-{end_line}",
                content=body,
                start_line=start_line,
                end_line=end_line,
            )
        )
    return _bounded(chunks, label="toml")


def chunk_text(text: str) -> list[Chunk]:
    return _bounded(_line_windows(text, label="text"), label="text")


_CHUNKERS = {
    "markdown": chunk_markdown,
    "python": chunk_python,
    "javascript": chunk_javascript,
    "json": chunk_json,
    "toml": chunk_toml,
    "text": chunk_text,
}


def _decision_or_refuse(path: Path):
    decision = decide_path(path)
    if decision.state != "eligible" or decision.entry is None or decision.manifest is None:
        _refuse(decision.code, decision.detail)
    return decision


def parse(filepath: str) -> list[dict]:
    """Parse an eligible repository file into documentary chunk messages."""
    path = Path(filepath)
    before = _decision_or_refuse(path)
    data = path.read_bytes()
    after = _decision_or_refuse(path)
    if (
        before.file_sha256 != after.file_sha256
        or before.git_commit != after.git_commit
        or before.manifest.identity != after.manifest.identity
    ):
        _refuse("identity_changed", "file identity changed during parse")
    relpath = after.relpath or ""
    text = _utf8(data, relpath=relpath)
    if after.file_sha256 and hashlib.sha256(data).hexdigest() != after.file_sha256:
        _refuse("hash_mismatch", f"{relpath} bytes changed")
    chunker = _CHUNKERS[after.entry.content_class]
    chunks = chunker(text)
    identity = source_identity(after)
    messages: list[dict] = []
    for chunk in chunks:
        messages.append(
            {
                "role": "document",
                "content": chunk.content,
                "chunk_label": chunk.label,
                "locator": chunk.locator,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "source_type": SOURCE_TYPE,
                "content_class": after.entry.content_class,
                "repo_relpath": relpath,
                "git_commit": after.git_commit,
                "file_sha256": after.file_sha256,
                "manifest_sha256": after.manifest.identity,
                "adapter_version": ADAPTER_VERSION,
                "source_identity": identity,
                "canonical_root": str(after.root),
                "original_source_text": (
                    chunk.original_source_text
                    if chunk.original_source_text is not None
                    else chunk.content
                ),
                "byte_start": chunk.byte_start,
                "byte_end": chunk.byte_end,
            }
        )
    return messages
