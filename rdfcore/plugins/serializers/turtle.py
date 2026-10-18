"""RDF 1.1 Turtle serializer."""

from __future__ import annotations

from ...serializer import Serializer
from ...term import BNode, Literal, URIRef


class TurtleSerializer(Serializer):
    def serialize(self, stream=None, base=None, encoding=None, mode="pretty", **kwargs):
        if base is None:
            base = self.store.base
        if mode == "stream":
            from ...streaming import TurtleStreamingWriter
            if stream is None:
                from io import BytesIO, StringIO
                stream = BytesIO() if encoding else StringIO()
                capture = True
            else:
                capture = False
            writer = TurtleStreamingWriter(stream, encoding=encoding or "utf-8", rdf_version="1.1", base=base)
            for triple in self.store.triples((None, None, None)):
                writer.add(triple)
            writer.close()
            return stream.getvalue() if capture else stream
        if mode != "pretty":
            raise ValueError("mode must be 'pretty' or 'stream'")
        manager = self.store.namespace_manager
        prefixes = list(manager.namespaces())
        lines = [f"@prefix {prefix}: <{namespace}> .\n" for prefix, namespace in prefixes]
        if base:
            lines.insert(0, f'@base {URIRef(base).n3()} .\n')
        if prefixes:
            lines.append("\n")
        triples = sorted(self.store.triples((None, None, None)), key=lambda triple: tuple(str(item) for item in triple))
        lines.extend(
            f"{_term(subject, manager, base)} {_term(predicate, manager, base)} {_term(obj, manager, base)} .\n"
            for subject, predicate, obj in triples
        )
        value = "".join(lines)
        if stream is None:
            return value.encode("utf-8") if encoding else value
        payload = value.encode("utf-8") if encoding else value
        try:
            stream.write(payload)
        except TypeError:
            stream.write(value if isinstance(payload, bytes) else value.encode("utf-8"))
        return stream


def _relativize(term, base):
    if (base is not None and term.startswith(base)
            and '#' not in term.replace(base, '') and '/' not in term.replace(base, '')):
        return URIRef(term.replace(base, '', 1))
    return term


def _term(term, manager, base=None):
    if isinstance(term, URIRef):
        relative = _relativize(term, base)
        if relative != term:
            return relative.n3()
        return manager.normalizeUri(term)
    if isinstance(term, BNode):
        return term.n3()
    if isinstance(term, Literal):
        return term.n3(manager)
    raise TypeError(f"unsupported RDF term: {term!r}")
