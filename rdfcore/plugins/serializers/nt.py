"""RDF 1.1 N-Triples serializer."""

from __future__ import annotations

from ...serializer import Serializer
from ...term import BNode, Literal, URIRef


class NTSerializer(Serializer):
    def serialize(self, stream=None, base=None, encoding=None, canonical=False, **kwargs):
        lines = []
        for subject, predicate, obj in self.store:
            lines.append(
                f"{_term(subject, canonical=canonical)} {_term(predicate, canonical=canonical)} {_term(obj, canonical=canonical)} .\n"
            )
        value = "".join(lines)
        if stream is None:
            return value.encode(encoding) if encoding else value
        if encoding:
            stream.write(value.encode(encoding))
        else:
            stream.write(value)
        return stream


class NT11Serializer(NTSerializer):
    pass


def _term(term, canonical=False):
    if isinstance(term, URIRef):
        return "<" + _escape_iri(str(term)) + ">"
    if isinstance(term, BNode):
        return "_:" + str(term)
    if isinstance(term, Literal):
        value = '"' + _escape_literal(str(term)) + '"'
        if term.language is not None:
            language = term.language.lower() if canonical else term.language
            return value + "@" + language
        if term.datatype is not None and (not canonical or str(term.datatype) != "http://www.w3.org/2001/XMLSchema#string"):
            return value + "^^<" + _escape_iri(str(term.datatype)) + ">"
        return value
    raise TypeError(f"unsupported RDF term: {term!r}")


def _escape_literal(value):
    simple = {"\\": "\\\\", '"': '\\"', "\t": "\\t", "\b": "\\b", "\n": "\\n", "\r": "\\r", "\f": "\\f"}
    return "".join(simple.get(char, _unicode_escape(char) if ord(char) < 0x20 else char) for char in value)


def _escape_iri(value):
    return "".join(
        _unicode_escape(char) if ord(char) <= 0x20 or char in '<>"{}|^`\\' else char
        for char in value
    )


def _unicode_escape(char):
    return f"\\u{ord(char):04X}" if ord(char) <= 0xFFFF else f"\\U{ord(char):08X}"
