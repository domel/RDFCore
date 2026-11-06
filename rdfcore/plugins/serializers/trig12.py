"""RDF 1.2 TriG serializer."""

from ...serializer import Serializer, text_output, write_output
from ...term import URIRef
from .turtle12 import _term
from .turtle import _safe_iris


class TriG12Serializer(Serializer):
    def serialize(self, stream=None, base=None, encoding=None, canonical=False, rdf_version="auto", mode="pretty", **kwargs):
        dataset = hasattr(self.store, "quads")
        default = getattr(getattr(self.store, "default_graph", None), "identifier", None)
        safe = _safe_iris(kwargs, True)
        if base is None:
            base = self.store.base
        if base is None:
            base = getattr(getattr(self.store, 'default_graph', None), 'base', None)
        if mode == "stream":
            from ...streaming import TriGStreamingWriter
            from ...rdf_version import required_rdf_version
            stream_version = required_rdf_version(self.store) if rdf_version == 'auto' else rdf_version
            if stream is None:
                from io import BytesIO, StringIO
                stream = BytesIO() if encoding else StringIO()
                capture = True
            else:
                capture = False
            use_text = text_output(stream, encoding, kwargs.get('text_output'))
            writer = TriGStreamingWriter(stream, encoding=encoding or "utf-8", rdf_version=stream_version,
                                         base=base, safe_iris=safe, text_output=use_text, canonical=canonical, default_graph_id=None)
            contexts = self.store.store.contexts() if dataset else (self.store.identifier,)
            for context in contexts:
                if context != getattr(getattr(self.store, "default_graph", None), "identifier", None) and not self.store.store.__len__(context):
                    writer._write(_term(context, None, canonical, base, safe) + ' {}\n')
            quads = self.store.quads() if dataset else ((*triple, self.store.identifier) for triple in self.store)
            for quad in quads:
                subject, predicate, obj, graph = quad
                graph = getattr(graph, 'identifier', graph)
                quad = subject, predicate, obj, None if graph == default else graph
                writer.add(quad)
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
        if base:
            lines.append(f'@base {URIRef(base).n3()} .\n')
        for prefix, namespace in manager.namespaces():
            lines.append(f"@prefix {prefix}: <{namespace}> .\n")
        if manager._prefixes:
            lines.append("\n")
        groups = {}
        contexts = self.store.store.contexts() if dataset else (self.store.identifier,)
        for context in contexts:
            if context != getattr(getattr(self.store, "default_graph", None), "identifier", None):
                groups.setdefault(context, [])
        quads = self.store.quads((None, None, None, None)) if dataset else ((*triple, self.store.identifier) for triple in self.store)
        for subject, predicate, obj, graph in quads:
            graph = getattr(graph, 'identifier', graph)
            graph = None if graph == default else graph
            groups.setdefault(graph, []).append((subject, predicate, obj))
        for graph in sorted(groups, key=lambda item: str(item)):
            triples = sorted(groups[graph], key=lambda triple: tuple(str(item) for item in triple))
            body = "".join(
                f"  {_term(subject, manager, canonical, base, safe)} {_term(predicate, manager, canonical, base, safe)} "
                f"{_term(obj, manager, canonical, base, safe)} .\n"
                for subject, predicate, obj in triples
            )
            if graph is None:
                lines.append("{\n" + body + "}\n")
            else:
                lines.append(f"{_term(graph, manager, canonical, base, safe)} {{\n" + body + "}\n")
        value = "".join(lines)
        if stream is None:
            return value.encode(encoding) if encoding else value
        write_output(stream, value, encoding, kwargs.get('text_output'))
        return stream


__all__ = ["TriG12Serializer"]
