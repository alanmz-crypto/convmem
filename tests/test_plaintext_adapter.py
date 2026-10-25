from pathlib import Path

from adapters.detect import TOOL_BY_FORMAT, detect_format, get_parser
from adapters.plaintext import parse


def test_watchable_document_types_use_plaintext_adapter(tmp_path: Path) -> None:
    for name in (
        "notes.md",
        "notes.txt",
        "notes.rst",
        "README",
        "notes.adoc",
        "config.yaml",
    ):
        path = tmp_path / name
        path.write_text("Readable project notes\n", encoding="utf-8")
        assert detect_format(path) == "plaintext_document"
        assert get_parser(path) is parse
        assert TOOL_BY_FORMAT["plaintext_document"] == "document"


def test_binary_and_invalid_utf8_files_are_not_watchable(tmp_path: Path) -> None:
    binary = tmp_path / "image.bin"
    binary.write_bytes(b"\x89PNG\x00binary")
    invalid = tmp_path / "notes.md"
    invalid.write_bytes(b"not utf-8: \xff")

    assert detect_format(binary) is None
    assert detect_format(invalid) is None


def test_plaintext_parser_returns_document_message(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("First line\nSecond line\n", encoding="utf-8")

    assert parse(str(path)) == [
        {
            "role": "document",
            "content": "First line\nSecond line\n",
            "source_type": "plaintext_document",
            "title": "notes.txt",
        }
    ]
