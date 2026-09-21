"""RDF 1.1 N-Quads serializer."""

from __future__ import annotations

from ...serializer import Serializer
from ...dataset import DATASET_DEFAULT_GRAPH_ID
from .nt import _term


class NQuadsSerializer(Serializer):
    def serialize(self, stream=None, base=None, encoding=None, canonical=False, **kwargs):
        if hasattr(self.store, "quads"):
            quads = self.store.quads((None, None, None, None))
        else:
            quads = ((*triple, DATASET_DEFAULT_GRAPH_ID) for triple in self.store)
        lines = []
        for subject, predicate, obj, graph in quads:
            parts = [_term(subject, canonical=canonical), _term(predicate, canonical=canonical), _term(obj, canonical=canonical)]
            if graph is not None and graph != DATASET_DEFAULT_GRAPH_ID:
                parts.append(_term(graph, canonical=canonical))
            lines.append(" ".join(parts) + " .\n")
        value = "".join(sorted(lines))
        if stream is None:
            return value.encode(encoding) if encoding else value
        payload = value.encode(encoding) if encoding else value
        try:
            stream.write(payload)
        except TypeError:
            stream.write(value if isinstance(payload, bytes) else value.encode("utf-8"))
        return stream
