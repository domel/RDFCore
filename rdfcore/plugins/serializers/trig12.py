"""RDF 1.2 TriG serializer."""

from ...dataset import DATASET_DEFAULT_GRAPH_ID
from ...serializer import Serializer
from .turtle12 import _term


class TriG12Serializer(Serializer):
    def serialize(self, stream=None, base=None, encoding=None, canonical=False, rdf_version="auto", mode="pretty", **kwargs):
        if mode == "stream":
            from ...streaming import TriGStreamingWriter
            if stream is None:
                from io import BytesIO, StringIO
                stream = BytesIO() if encoding else StringIO()
                capture = True
            else:
                capture = False
            writer = TriGStreamingWriter(stream, encoding=encoding or "utf-8", rdf_version=rdf_version)
            for quad in self.store.quads():
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
        for prefix, namespace in manager.namespaces():
            lines.append(f"@prefix {prefix}: <{namespace}> .\n")
        if manager._prefixes:
            lines.append("\n")
        groups = {}
        for subject, predicate, obj, graph in self.store.quads((None, None, None, None)):
            groups.setdefault(graph, []).append((subject, predicate, obj))
        for graph in sorted(groups, key=lambda item: str(item)):
            triples = sorted(groups[graph], key=lambda triple: tuple(str(item) for item in triple))
            body = "".join(
                f"  {_term(subject, manager, canonical)} {_term(predicate, manager, canonical)} "
                f"{_term(obj, manager, canonical)} .\n"
                for subject, predicate, obj in triples
            )
            if graph == DATASET_DEFAULT_GRAPH_ID or graph is None:
                lines.append("{\n" + body + "}\n")
            else:
                lines.append(f"{_term(graph, manager, canonical)} {{\n" + body + "}\n")
        value = "".join(lines)
        if stream is None:
            return value.encode(encoding) if encoding else value
        payload = value.encode(encoding) if encoding else value
        try:
            stream.write(payload)
        except TypeError:
            stream.write(value)
        return stream


__all__ = ["TriG12Serializer"]
