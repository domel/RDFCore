"""RDF 1.1 N-Triples parser."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from ...exceptions import ParserError
from ...parser import Parser
from ...term import BNode, Literal, TripleTerm, URIRef


_IRI = re.compile(r"<((?:[^<>]|\\.)*)>")
_BNODE = re.compile(r"_:([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9_-])?)")
_LANG = re.compile(r"@[A-Za-z]+(?:-[A-Za-z0-9]+)*(?:--(?:ltr|rtl))?")


class NTParser(Parser):
    rdf_version = "1.1"

    def parse(self, source, sink, **kwargs):
        stream = source.getCharacterStream()
        if stream is None:
            stream = source.getByteStream()
        if stream is None:
            raise ParserError("N-Triples source has no readable stream")
        bnode_map = {}
        for line_number, raw_line in enumerate(stream, 1):
            try:
                if isinstance(raw_line, bytes):
                    raw_line = raw_line.decode("utf-8")
                self._parse_line(raw_line, sink, line_number, bnode_map)
            except ParserError:
                raise
            except (UnicodeDecodeError, ValueError) as error:
                raise ParserError(f"line {line_number}: {error}") from error
        return sink

    def _parse_line(self, line, sink, line_number, bnode_map):
        text = line.strip()
        if not text or text.startswith("#"):
            return
        position = 0
        subject, position = _term(text, position, line_number, "subject", bnode_map)
        position = _spaces(text, position)
        predicate, position = _term(text, position, line_number, "predicate", bnode_map)
        position = _spaces(text, position)
        obj, position = _term(text, position, line_number, "object", bnode_map)
        position = _spaces(text, position)
        if position >= len(text) or text[position] != ".":
            raise ParserError(f"line {line_number}: expected final '.'")
        position = _spaces(text, position + 1)
        if position < len(text) and text[position] == "#":
            position = len(text)
        if position != len(text):
            raise ParserError(f"line {line_number}: expected final '.'")
        if not isinstance(subject, (URIRef, BNode)) or not isinstance(predicate, URIRef):
            raise ParserError(f"line {line_number}: invalid subject or predicate")
        sink.add((subject, predicate, obj))


class NT12Parser(NTParser):
    """RDF 1.2 N-Triples parser, retaining the RDF 1.1 line-oriented core."""

    rdf_version = "1.2"

    def parse(self, source, sink, **kwargs):
        from ...rdf_version import validate_rdf_version

        self._requested_version = validate_rdf_version(kwargs.get("rdf_version", "auto"))
        return super().parse(source, sink, **kwargs)

    def _parse_line(self, line, sink, line_number, bnode_map):
        text = line.strip()
        if not text or text.startswith("#"):
            return
        if text.startswith("VERSION"):
            self._parse_version(text, line_number)
            return
        position = 0
        subject, position = _term(text, position, line_number, "subject", bnode_map, allow_rdf12=True)
        position = _spaces(text, position)
        predicate, position = _term(text, position, line_number, "predicate", bnode_map, allow_rdf12=True)
        position = _spaces(text, position)
        obj, position = _term(text, position, line_number, "object", bnode_map, allow_rdf12=True)
        position = _spaces(text, position)
        if position >= len(text) or text[position] != ".":
            raise ParserError(f"line {line_number}: expected final '.'")
        position = _spaces(text, position + 1)
        if position < len(text) and text[position] == "#":
            position = len(text)
        if position != len(text):
            raise ParserError(f"line {line_number}: expected final '.'")
        if not isinstance(subject, (URIRef, BNode)) or not isinstance(predicate, URIRef):
            raise ParserError(f"line {line_number}: invalid subject or predicate")
        self._validate_rdf_version(obj, line_number)
        sink.add((subject, predicate, obj))

    def _parse_version(self, text, line_number):
        match = re.fullmatch(r'VERSION\s+"(1\.1|1\.2-basic|1\.2)"(?:\s+#.*)?', text)
        if match is None:
            raise ParserError(f"line {line_number}: invalid VERSION declaration")

    def _validate_rdf_version(self, term, line_number):
        from ...rdf_version import version_allows

        def required(value):
            if isinstance(value, TripleTerm):
                return "1.2"
            if isinstance(value, Literal) and value.direction is not None:
                return "1.2-basic"
            return "1.1"

        needed = required(term)
        if not version_allows(self._requested_version, needed):
            raise ParserError(f"line {line_number}: {needed} term exceeds rdf_version={self._requested_version!r}")


W3CNTriplesParser = NTParser
ParseError = ParserError


def _spaces(text, position):
    while position < len(text) and text[position].isspace():
        position += 1
    return position


def _required_spaces(text, position, line_number):
    end = _spaces(text, position)
    if end == position:
        raise ParserError(f"line {line_number}: expected whitespace")
    return end


def _term(text, position, line_number, role, bnode_map, allow_rdf12=False):
    position = _spaces(text, position)
    if position >= len(text):
        raise ParserError(f"line {line_number}: missing {role}")
    if allow_rdf12 and text.startswith("<<(", position):
        subject, position = _term(text, position + 3, line_number, "triple subject", bnode_map, allow_rdf12=True)
        position = _required_spaces(text, position, line_number)
        predicate, position = _term(text, position, line_number, "triple predicate", bnode_map, allow_rdf12=True)
        position = _required_spaces(text, position, line_number)
        obj, position = _term(text, position, line_number, "triple object", bnode_map, allow_rdf12=True)
        position = _spaces(text, position)
        if not text.startswith(")>>", position):
            raise ParserError(f"line {line_number}: unterminated triple term")
        position += 3
        if not isinstance(subject, (URIRef, BNode)) or not isinstance(predicate, URIRef):
            raise ParserError(f"line {line_number}: invalid triple term subject or predicate")
        return TripleTerm(subject, predicate, obj), position
    if text[position] == "<":
        match = _IRI.match(text, position)
        if not match:
            raise ParserError(f"line {line_number}: invalid IRI")
        raw_value = match.group(1)
        if any(ord(char) <= 0x20 or char in '<>"{}|^`' for char in raw_value if char != "\\"):
            raise ParserError(f"line {line_number}: invalid IRI")
        value = _unescape(raw_value, line_number)
        if not urlparse(value).scheme:
            raise ParserError(f"line {line_number}: IRI must be absolute")
        if any(ord(char) <= 0x20 or char in '<>"{}|^`\\' for char in value):
            raise ParserError(f"line {line_number}: invalid IRI")
        return URIRef(value), match.end()
    if text.startswith("_:", position):
        match = _BNODE.match(text, position)
        if not match:
            raise ParserError(f"line {line_number}: invalid blank node")
        label = match.group(1)
        return bnode_map.setdefault(label, BNode()), match.end()
    if text[position] == '"':
        lexical, end = _literal(text, position, line_number)
        lang = None
        datatype = None
        if end < len(text) and text[end] == "@":
            match = _LANG.match(text, end)
            if not match:
                raise ParserError(f"line {line_number}: invalid language tag")
            lang = match.group(0)[1:]
            end = match.end()
        elif text.startswith("^^", end):
            datatype, end = _term(text, end + 2, line_number, "datatype", bnode_map, allow_rdf12=allow_rdf12)
            if not isinstance(datatype, URIRef):
                raise ParserError(f"line {line_number}: datatype must be an IRI")
        direction = None
        if lang is not None and "--" in lang:
            lang, direction = lang.split("--", 1)
        if direction is not None and not allow_rdf12:
            raise ParserError(f"line {line_number}: directional literal requires RDF 1.2")
        return Literal(lexical, lang=lang, datatype=datatype, normalize=False, direction=direction), end
    raise ParserError(f"line {line_number}: invalid {role}")


def _literal(text, position, line_number):
    index = position + 1
    output = []
    while index < len(text):
        char = text[index]
        if char == '"':
            return "".join(output), index + 1
        if char == "\\":
            if index + 1 >= len(text):
                break
            size = 6 if text[index + 1] == "u" else 10 if text[index + 1] == "U" else 2
            output.append(_unescape(text[index:index + size], line_number))
            index += size
        else:
            if char in "\r\n":
                raise ParserError(f"line {line_number}: newline in literal")
            output.append(char)
            index += 1
    raise ParserError(f"line {line_number}: unterminated literal")


def _unescape(value, line_number):
    result = []
    index = 0
    while index < len(value):
        if value[index] != "\\":
            result.append(value[index])
            index += 1
            continue
        if index + 1 >= len(value):
            raise ParserError(f"line {line_number}: incomplete escape")
        code = value[index + 1]
        simple = {"t": "\t", "b": "\b", "n": "\n", "r": "\r", "f": "\f", '"': '"', "\\": "\\"}
        if code in simple:
            result.append(simple[code])
            index += 2
        elif code in "uU":
            size = 4 if code == "u" else 8
            digits = value[index + 2:index + 2 + size]
            if len(digits) != size:
                raise ParserError(f"line {line_number}: incomplete Unicode escape")
            try:
                character = chr(int(digits, 16))
                if 0xD800 <= ord(character) <= 0xDFFF:
                    raise ValueError
                result.append(character)
            except (ValueError, OverflowError):
                raise ParserError(f"line {line_number}: invalid Unicode escape")
            index += 2 + size
        else:
            raise ParserError(f"line {line_number}: invalid escape")
    return "".join(result)
