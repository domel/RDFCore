"""RDF 1.2 Turtle serializer."""

from ...serializer import Serializer
from ...term import BNode, Literal, TripleTerm, URIRef


class Turtle12Serializer(Serializer):
    def serialize(self, stream=None, base=None, encoding=None, canonical=False, rdf_version="auto", mode="pretty", **kwargs):
        if mode == "stream":
            from ...streaming import TurtleStreamingWriter
            if stream is None:
                from io import BytesIO, StringIO
                stream = BytesIO() if encoding else StringIO()
                capture = True
            else:
                capture = False
            writer = TurtleStreamingWriter(stream, encoding=encoding or "utf-8", rdf_version=rdf_version)
            for triple in self.store:
                writer.add(triple)
            writer.close()
            return stream.getvalue() if capture else stream
        if mode != "pretty":
            raise ValueError("mode must be 'pretty' or 'stream'")
        from ...rdf_version import required_rdf_version, validate_rdf_version

        requested = validate_rdf_version(rdf_version)
        required = required_rdf_version(self.store)
        if (requested == "1.1" and required != "1.1") or (requested == "1.2-basic" and required == "1.2"):
            raise ValueError(f"RDF {required} data cannot be serialized as {requested}")
        version = required if requested == "auto" else requested
        manager = self.store.namespace_manager
        lines = []
        if not canonical and version != "1.1":
            lines.append(f'VERSION "{version}"\n')
        for prefix, namespace in manager.namespaces():
            lines.append(f"@prefix {prefix}: <{namespace}> .\n")
        if manager._prefixes:
            lines.append("\n")
        triples = sorted(self.store, key=lambda triple: tuple(str(item) for item in triple))
        lines.extend(
            f"{_term(subject, manager, canonical)} {_term(predicate, manager, canonical)} "
            f"{_term(obj, manager, canonical)} .\n"
            for subject, predicate, obj in triples
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


def _term(term, manager, canonical=False):
    if isinstance(term, URIRef):
        return manager.normalizeUri(term)
    if isinstance(term, BNode):
        return term.n3()
    if isinstance(term, TripleTerm):
        return "<<( " + " ".join(_term(item, manager, canonical) for item in term) + " )>>"
    if isinstance(term, Literal):
        text = term.n3(manager)
        if term.language is not None and canonical:
            text = '"' + _escape_literal(str(term)) + '"@' + term.language.lower()
            if term.direction is not None:
                text += "--" + term.direction
        return text
    raise TypeError(f"unsupported RDF term: {term!r}")


def _escape_literal(value):
    simple = {"\\": "\\\\", '"': '\\"', "\t": "\\t", "\b": "\\b", "\n": "\\n", "\r": "\\r", "\f": "\\f"}
    return "".join(simple.get(char, char) for char in value)


__all__ = ["Turtle12Serializer"]
