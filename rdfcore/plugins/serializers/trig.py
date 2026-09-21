"""RDF 1.1 TriG serializer."""

from __future__ import annotations

from ...dataset import DATASET_DEFAULT_GRAPH_ID
from ...serializer import Serializer
from ..serializers.turtle import _term


class TriGSerializer(Serializer):
    def serialize(self, stream=None, base=None, encoding=None, canonical=False, mode="pretty", **kwargs):
        if mode == "stream":
            from ...streaming import TriGStreamingWriter
            if stream is None:
                from io import BytesIO, StringIO
                stream = BytesIO() if encoding else StringIO()
                capture = True
            else:
                capture = False
            writer = TriGStreamingWriter(stream, encoding=encoding or "utf-8", rdf_version="1.1")
            statements = self.store.quads() if hasattr(self.store, "quads") else self.store
            for statement in statements:
                writer.add(statement)
            writer.close()
            return stream.getvalue() if capture else stream
        if mode != "pretty":
            raise ValueError("mode must be 'pretty' or 'stream'")
        manager = self.store.namespace_manager
        lines = [f"@prefix {prefix}: <{namespace}> .\n" for prefix, namespace in manager.namespaces()]
        if lines:
            lines.append("\n")
        groups = {}
        if hasattr(self.store, "quads"):
            for subject, predicate, obj, graph in self.store.quads((None, None, None, None)):
                groups.setdefault(graph, []).append((subject, predicate, obj))
        else:
            groups[DATASET_DEFAULT_GRAPH_ID] = list(self.store)
        for graph in sorted(groups, key=lambda item: str(item)):
            triples = sorted(groups[graph], key=lambda triple: tuple(str(item) for item in triple))
            body = "".join(f"  {_term(s, manager)} {_term(p, manager)} {_term(o, manager)} .\n" for s, p, o in triples)
            if graph == DATASET_DEFAULT_GRAPH_ID or graph is None:
                lines.append("{\n" + body + "}\n")
            else:
                lines.append(f"{_term(graph, manager)} {{\n" + body + "}\n")
        value = "".join(lines)
        if stream is None:
            return value.encode(encoding) if encoding else value
        payload = value.encode(encoding) if encoding else value
        try:
            stream.write(payload)
        except TypeError:
            stream.write(value if isinstance(payload, bytes) else value.encode("utf-8"))
        return stream
