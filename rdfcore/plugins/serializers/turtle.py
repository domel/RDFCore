"""RDF 1.1 Turtle serializer."""

from __future__ import annotations

from ...serializer import Serializer
from ...term import BNode, Literal, URIRef


class TurtleSerializer(Serializer):
    def serialize(self, stream=None, base=None, encoding=None, mode="pretty", **kwargs):
        if mode == "stream":
            from ...streaming import TurtleStreamingWriter
            if stream is None:
                from io import BytesIO, StringIO
                stream = BytesIO() if encoding else StringIO()
                capture = True
            else:
                capture = False
            writer = TurtleStreamingWriter(stream, encoding=encoding or "utf-8", rdf_version="1.1")
            for triple in self.store:
                writer.add(triple)
            writer.close()
            return stream.getvalue() if capture else stream
        if mode != "pretty":
            raise ValueError("mode must be 'pretty' or 'stream'")
        manager = self.store.namespace_manager
        prefixes = list(manager.namespaces())
        lines = [f"@prefix {prefix}: <{namespace}> .\n" for prefix, namespace in prefixes]
        if prefixes:
            lines.append("\n")
        triples = sorted(self.store, key=lambda triple: tuple(str(item) for item in triple))
        lines.extend(
            f"{_term(subject, manager)} {_term(predicate, manager)} {_term(obj, manager)} .\n"
            for subject, predicate, obj in triples
        )
        value = "".join(lines)
        if stream is None:
            return value.encode(encoding) if encoding else value
        payload = value.encode(encoding) if encoding else value
        try:
            stream.write(payload)
        except TypeError:
            stream.write(value if isinstance(payload, bytes) else value.encode("utf-8"))
        return stream


def _term(term, manager):
    if isinstance(term, URIRef):
        return manager.normalizeUri(term)
    if isinstance(term, BNode):
        return term.n3()
    if isinstance(term, Literal):
        return term.n3(manager)
    raise TypeError(f"unsupported RDF term: {term!r}")
