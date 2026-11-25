"""How Ollama names a model, so two spellings of one model compare equal and nothing else does.

A port of Ollama's own parser (``types/model/name.go``, ``ParseNameBare`` and its part
validators) rather than a guess at its grammar. A name is ``[[scheme://]host/][namespace/]model[:tag]``
with the defaults ``registry.ollama.ai``, ``library`` and ``latest``; the scheme is ignored. The
split is positional: the tag follows the last ``:`` when that comes after the last ``/``, then
the model, then the namespace, then the host is whatever is left. Two names are the same model
when host, namespace, model and tag are equal ignoring ASCII case, after defaults.

Each part is validated as Ollama validates it: ASCII only; the first character a letter, digit
or underscore; later characters letters, digits, ``_`` and ``-`` plus ``.`` (not in a namespace)
and ``:`` (host only); at most 350 characters for a host and 80 for any other part. An empty
part, a digest (``@sha256:...``), a stray colon or more than three ``/``-separated parts is
outside the grammar. Such a name equals only an identical string, so a malformed configuration
still matches its own stamp but is never mistaken for a well-formed model, and a non-ASCII
look-alike (the Kelvin sign for ``k``) is not folded into one.
"""

from __future__ import annotations

DEFAULT_HOST = "registry.ollama.ai"
DEFAULT_NAMESPACE = "library"
DEFAULT_TAG = "latest"
_MISSING = "!MISSING!"  # Ollama's sentinel for an empty part; the "!" makes it invalid
_WORD = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_")


def _normalized(value: object) -> str | None:
    """The name stripped of surrounding blanks; None unless it is a non-blank string."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def _cut_last(text: str, sep: str) -> tuple[str, str, bool]:
    index = text.rfind(sep)
    return (text[:index], text[index + len(sep):], True) if index >= 0 else (text, "", False)


def _promised(text: str, sep: str) -> tuple[str, str, bool]:
    before, after, found = _cut_last(text, sep)
    return (before or _MISSING, after or _MISSING, True) if found else (before, after, False)


def _valid_part(kind: str, text: str) -> bool:
    """Ollama's ``isValidPart``: ``kind`` is host, namespace, model or tag."""
    if not 1 <= len(text) <= (350 if kind == "host" else 80):
        return False
    if text[0] not in _WORD:
        return False
    for char in text[1:]:
        if char in _WORD or char in "-_":
            continue
        if char == "." and kind != "namespace":
            continue
        if char == ":" and kind == "host":
            continue
        return False
    return True


def parse_embed_model(value: object) -> tuple[str, str, str, str] | None:
    """(host, namespace, model, tag) with defaults and ASCII case folded, or None if invalid."""
    text = _normalized(value)
    if text is None:
        return None
    tag = ""
    if text.rfind(":") > text.rfind("/"):
        text, tag, _ = _promised(text, ":")
    host = namespace = ""
    text, model, promised = _promised(text, "/")
    if not promised:
        model = text
    else:
        text, namespace, promised = _promised(text, "/")
        if not promised:
            namespace = text
        else:
            host = text.partition("://")[2] if "://" in text else text
    host, namespace, tag = host or DEFAULT_HOST, namespace or DEFAULT_NAMESPACE, tag or DEFAULT_TAG
    parts = (("host", host), ("namespace", namespace), ("model", model), ("tag", tag))
    if not all(_valid_part(kind, part) for kind, part in parts):
        return None
    return host.lower(), namespace.lower(), model.lower(), tag.lower()  # ASCII only by now


def same_embed_model(first: object, second: object) -> bool:
    """True when two names denote one Ollama model."""
    left, right = parse_embed_model(first), parse_embed_model(second)
    if left is None or right is None:
        # Outside the grammar: equal only to an identical string, never to a valid name.
        name = _normalized(first)
        return left is None and right is None and name is not None and name == _normalized(second)
    return left == right
