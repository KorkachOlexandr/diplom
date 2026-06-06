"""Source-code tokenization with normalization for similarity detection.

The normalization step is what lets the cohort signal survive trivial
evasions like variable renaming and literal substitution. Every
identifier collapses to a single `IDENT` token, every numeric and string
literal to `NUM`/`STR`, while keywords, operators, and structural
punctuation keep their lexical identity.

Python is the first-class language. The Tokenizer interface is small on
purpose so a C/C++/Java tokenizer drops in as future work without
touching the rest of the cohort pipeline.
"""
from __future__ import annotations

import io
import tokenize
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Token:
    kind: str          # normalized symbolic name: "IDENT", "NUM", "STR", or the literal symbol
    start: int         # original character offset (start of the token)
    end: int           # original character offset (one past the end)
    raw: str           # the original source text for this token


class Tokenizer(Protocol):
    language: str

    def tokenize(self, source: str) -> list[Token]:
        ...


# ---------- Python ----------

# tokens we drop entirely — they carry no similarity signal and add noise
_PY_DROP = {
    tokenize.NEWLINE,
    tokenize.NL,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.COMMENT,
    tokenize.ENCODING,
    tokenize.ENDMARKER,
}

# Python 3.12 introduced FSTRING_START/MIDDLE/END as distinct token types;
# on 3.11 they don't exist. Build the set conditionally so the tokenizer
# works across both versions.
_PY_FSTRING_TYPES: set[int] = set()
for _name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
    if hasattr(tokenize, _name):
        _PY_FSTRING_TYPES.add(getattr(tokenize, _name))


class PythonTokenizer:
    language = "python"

    def tokenize(self, source: str) -> list[Token]:
        tokens: list[Token] = []
        try:
            raw_tokens = list(tokenize.tokenize(io.BytesIO(source.encode("utf-8")).readline))
        except (tokenize.TokenizeError, IndentationError, SyntaxError):
            return self._fallback_tokenize(source)

        for tok in raw_tokens:
            if tok.type in _PY_DROP:
                continue
            start_off = _offset(source, tok.start)
            end_off = _offset(source, tok.end)
            if start_off is None or end_off is None:
                continue
            tokens.append(
                Token(
                    kind=_normalize_python(tok),
                    start=start_off,
                    end=end_off,
                    raw=tok.string,
                )
            )
        return tokens

    @staticmethod
    def _fallback_tokenize(source: str) -> list[Token]:
        """If a submission won't parse, fall back to a simple word/symbol scan
        so we still produce a similarity signal instead of silently dropping
        the file. The thesis discusses this tradeoff: broken code is common
        in student submissions and we'd rather over-detect than skip them."""
        import re

        tokens: list[Token] = []
        for m in re.finditer(r"\w+|[^\s\w]", source):
            text = m.group(0)
            if text.isidentifier():
                kind = "IDENT"
            elif text.replace(".", "", 1).isdigit():
                kind = "NUM"
            else:
                kind = text
            tokens.append(Token(kind=kind, start=m.start(), end=m.end(), raw=text))
        return tokens


_PY_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield", "match", "case",
}


def _normalize_python(tok: tokenize.TokenInfo) -> str:
    if tok.type == tokenize.NAME:
        return tok.string if tok.string in _PY_KEYWORDS else "IDENT"
    if tok.type == tokenize.NUMBER:
        return "NUM"
    if tok.type == tokenize.STRING:
        return "STR"
    if tok.type in _PY_FSTRING_TYPES:
        return "STR"
    if tok.type == tokenize.OP:
        return tok.string
    return tok.string


def _offset(source: str, position: tuple[int, int]) -> int | None:
    """Convert (1-based line, 0-based column) to absolute character offset."""
    line, col = position
    if line <= 0:
        return None
    # find start of line (line index is 1-based)
    pos = 0
    current_line = 1
    for ch in source:
        if current_line == line:
            return pos + col
        if ch == "\n":
            current_line += 1
        pos += 1
    if current_line == line:
        return pos + col
    return None


# Registry — language → tokenizer instance. Phase 1: Python only.
TOKENIZERS: dict[str, Tokenizer] = {"python": PythonTokenizer()}


def detect_language(filename: str) -> str | None:
    """Map a filename to a tokenizer language. Conservative: only what we support."""
    name = filename.lower()
    if name.endswith((".py", ".pyw")):
        return "python"
    return None


def tokenize_source(source: str, language: str = "python") -> list[Token]:
    tok = TOKENIZERS.get(language)
    if tok is None:
        raise ValueError(f"No tokenizer registered for language: {language}")
    return tok.tokenize(source)
