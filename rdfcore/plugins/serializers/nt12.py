"""RDF 1.2 N-Triples serializer."""

from ...serializer import Serializer
from ...term import BNode, Literal, TripleTerm, URIRef


class NT12Serializer(Serializer):
    def serialize(self, stream=None, base=None, encoding=None, canonical=False, rdf_version="auto", **kwargs):
        from ...rdf_version import required_rdf_version, validate_rdf_version

        requested = validate_rdf_version(rdf_version)
        required = required_rdf_version(self.store)
        if (requested == "1.1" and required != "1.1") or (requested == "1.2-basic" and required == "1.2"):
            raise ValueError(f"RDF {required} data cannot be serialized as {requested}")
        version = required if requested == "auto" else requested
        lines = []
        if not canonical and version != "1.1":
            lines.append(f'VERSION "{version}"\n')
        for subject, predicate, obj in self.store:
            lines.append(
                f"{_term(subject, canonical=canonical)} {_term(predicate, canonical=canonical)} "
                f"{_term(obj, canonical=canonical)} .\n"
            )
        value = "".join(lines)
        if stream is None:
            return value.encode(encoding) if encoding else value
        payload = value.encode(encoding) if encoding else value
        try:
            stream.write(payload)
        except TypeError:
            stream.write(value)
        return stream


def _term(term, canonical=False):
    if isinstance(term, URIRef):
        return "<" + _escape_iri(str(term)) + ">"
    if isinstance(term, BNode):
        return "_:" + str(term)
    if isinstance(term, TripleTerm):
        return "<<( " + " ".join(_term(item, canonical=canonical) for item in term) + " )>>"
    if isinstance(term, Literal):
        value = '"' + _escape_literal(str(term)) + '"'
        if term.language is not None:
            language = term.language.lower() if canonical else term.language
            if term.direction is not None:
                return value + "@" + language + "--" + term.direction
            return value + "@" + language
        if term.datatype is not None and (not canonical or str(term.datatype) != "http://www.w3.org/2001/XMLSchema#string"):
            return value + "^^<" + _escape_iri(str(term.datatype)) + ">"
        return value
    raise TypeError(f"unsupported RDF term: {term!r}")


def _escape_literal(value):
    simple = {"\\": "\\\\", '"': '\\"', "\t": "\\t", "\b": "\\b", "\n": "\\n", "\r": "\\r", "\f": "\\f"}
    return "".join(simple.get(char, _unicode_escape(char) if ord(char) < 0x20 else char) for char in value)


def _escape_iri(value):
    return "".join(_unicode_escape(char) if ord(char) <= 0x20 or char in '<>"{}|^`\\' else char for char in value)


def _unicode_escape(char):
    return f"\\u{ord(char):04X}" if ord(char) <= 0xFFFF else f"\\U{ord(char):08X}"

__all__ = ["NT12Serializer"]
