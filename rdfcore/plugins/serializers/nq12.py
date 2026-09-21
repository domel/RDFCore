"""RDF 1.2 N-Quads serializer."""

from ...dataset import DATASET_DEFAULT_GRAPH_ID
from ...serializer import Serializer
from ..serializers.nt12 import _term


class NQuads12Serializer(Serializer):
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
        for subject, predicate, obj, graph in self.store.quads((None, None, None, None)):
            parts = [_term(subject, canonical), _term(predicate, canonical), _term(obj, canonical)]
            if graph is not None and graph != DATASET_DEFAULT_GRAPH_ID:
                parts.append(_term(graph, canonical))
            lines.append(" ".join(parts) + " .\n")
        value = "".join(sorted(lines[1:]) if lines and lines[0].startswith("VERSION") else sorted(lines))
        if lines and lines[0].startswith("VERSION"):
            value = lines[0] + value
        if stream is None:
            return value.encode(encoding) if encoding else value
        payload = value.encode(encoding) if encoding else value
        try:
            stream.write(payload)
        except TypeError:
            stream.write(value)
        return stream


__all__ = ["NQuads12Serializer"]
