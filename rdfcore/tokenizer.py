"""Incremental UTF-8 chunks and lightweight RDF concrete-syntax tokens.

This module deliberately does not assign Turtle or TriG meaning to tokens;
the format parsers introduced in later stages own that responsibility.
"""

from __future__ import annotations

import codecs
from dataclasses import dataclass


class ChunkReader:
    def __init__(self, stream, chunk_size=64 * 1024, encoding="utf-8"):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.stream = stream
        self.chunk_size = chunk_size
        self.encoding = encoding

    def __iter__(self):
        decoder = codecs.getincrementaldecoder(self.encoding)()
        while True:
            chunk = self.stream.read(self.chunk_size)
            if chunk == b"" or chunk == "":
                tail = decoder.decode(b"", final=True)
                if tail:
                    yield tail
                return
            if isinstance(chunk, bytes):
                text = decoder.decode(chunk, final=False)
            else:
                text = chunk
            if text:
                yield text


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int


class TokenReader:
    """Tokenize across arbitrary chunk boundaries while retaining positions."""

    _PUNCTUATION = set(";,.[](){}")

    def __init__(self, stream, chunk_size=64 * 1024, encoding="utf-8"):
        self.chunks = ChunkReader(stream, chunk_size, encoding)

    def __iter__(self):
        text = ""
        line, column = 1, 1
        for chunk in self.chunks:
            text += chunk
            while text:
                token, consumed = self._next(text, line, column, final=False)
                if token is None:
                    break
                text = text[consumed:]
                line, column = _advance(text[:0], token.value, line, column)
                yield token
        while text:
            token, consumed = self._next(text, line, column, final=True)
            if token is None:
                raise ValueError("unterminated token")
            text = text[consumed:]
            line, column = _advance(text[:0], token.value, line, column)
            yield token

    def _next(self, text, line, column, final):
        if not final and len(text) == 1 and text[0] in "<>{|^":
            return None, 0
        if text[0].isspace():
            index = 1
            while index < len(text) and text[index].isspace():
                index += 1
            return Token("whitespace", text[:index], line, column), index
        if text[0] == "#":
            end = text.find("\n")
            if end < 0 and not final:
                return None, 0
            end = len(text) if end < 0 else end
            return Token("comment", text[:end], line, column), end
        for marker in ("^^", "<<", ">>", "{|", "|}"):
            if text.startswith(marker):
                return Token("punctuation", marker, line, column), len(marker)
        if text[0] == "<":
            end = _closing(text, ">", 1)
            if end < 0:
                return (None, 0) if not final else (_error("unterminated IRI"), 0)
            return Token("iri", text[:end + 1], line, column), end + 1
        if text[0] in ('"', "'"):
            quote = text[0]
            closing = quote * 3 if text.startswith(quote * 3) else quote
            start = len(closing)
            end = _string_end(text, closing, start)
            if end < 0:
                return (None, 0) if not final else (_error("unterminated literal"), 0)
            return Token("literal", text[:end + len(closing)], line, column), end + len(closing)
        if text[0] in self._PUNCTUATION:
            return Token("punctuation", text[0], line, column), 1
        index = 1
        delimiters = (self._PUNCTUATION - {"."}) | set("<>")
        while index < len(text) and not text[index].isspace() and text[index] not in delimiters:
            index += 1
        if index == len(text) and not final:
            return None, 0
        if index > 1 and text[index - 1] == ".":
            index -= 1
        return Token("word", text[:index], line, column), index


def _closing(text, marker, start):
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if char == marker and not escaped:
            return index
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    return -1


def _string_end(text, marker, start):
    index = start
    escaped = False
    while index < len(text):
        if text.startswith(marker, index) and not escaped:
            return index
        char = text[index]
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
        index += 1
    return -1


def _advance(_unused, value, line, column):
    parts = value.split("\n")
    if len(parts) == 1:
        return line, column + len(value)
    return line + len(parts) - 1, len(parts[-1]) + 1


def _error(message):
    raise ValueError(message)
