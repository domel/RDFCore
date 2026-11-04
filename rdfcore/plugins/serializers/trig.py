"""RDF 1.1 TriG serializer."""

from __future__ import annotations

from ...dataset import DATASET_DEFAULT_GRAPH_ID
from ...serializer import Serializer
from ...term import URIRef
from ..serializers.turtle import _term, _safe_iris


class TriGSerializer(Serializer):
    def serialize(self, stream=None, base=None, encoding=None, canonical=False, mode="pretty", **kwargs):
        safe = _safe_iris(kwargs, False)
        if base is None:
            base = self.store.base
        if mode == "stream":
            from ...streaming import TriGStreamingWriter
            if stream is None:
                from io import BytesIO, StringIO
                stream = BytesIO() if encoding else StringIO()
                capture = True
            else:
                capture = False
            writer = TriGStreamingWriter(stream, encoding=encoding or "utf-8", rdf_version="1.1", base=base, safe_iris=safe, default_graph_id=None)
            statements = self.store.quads() if hasattr(self.store, "quads") else self.store
            for statement in statements:
                if len(statement) == 4:
                    subject, predicate, obj, graph = statement
                    graph = getattr(graph, 'identifier', graph)
                    default = getattr(getattr(self.store, 'default_graph', None), 'identifier', DATASET_DEFAULT_GRAPH_ID)
                    statement = subject, predicate, obj, None if graph == default else graph
                writer.add(statement)
            writer.close()
            return stream.getvalue() if capture else stream
        if mode != "pretty":
            raise ValueError("mode must be 'pretty' or 'stream'")
        manager = self.store.namespace_manager
        lines = [f"@prefix {prefix}: <{namespace}> .\n" for prefix, namespace in manager.namespaces()]
        if base:
            lines.insert(0, f'@base {URIRef(base).n3()} .\n')
        if lines:
            lines.append("\n")
        groups = {}
        if hasattr(self.store, "quads"):
            for subject, predicate, obj, graph in self.store.quads((None, None, None, None)):
                graph = getattr(graph, 'identifier', graph)
                default = self.store.default_graph.identifier
                graph = None if graph == default else graph
                groups.setdefault(graph, []).append((subject, predicate, obj))
        else:
            groups[DATASET_DEFAULT_GRAPH_ID] = list(self.store)
        for graph in sorted(groups, key=lambda item: str(item)):
            triples = sorted(groups[graph], key=lambda triple: tuple(str(item) for item in triple))
            body = "".join(f"  {_term(s, manager, base, safe)} {_term(p, manager, base, safe)} {_term(o, manager, base, safe)} .\n" for s, p, o in triples)
            if graph is None or (not hasattr(self.store, 'quads') and graph == DATASET_DEFAULT_GRAPH_ID):
                lines.append("{\n" + body + "}\n")
            else:
                lines.append(f"{_term(graph, manager, base, safe)} {{\n" + body + "}\n")
        value = "".join(lines)
        if stream is None:
            return value.encode("utf-8") if encoding else value
        payload = value.encode("utf-8") if encoding else value
        try:
            stream.write(payload)
        except TypeError:
            stream.write(value if isinstance(payload, bytes) else value.encode("utf-8"))
        return stream
