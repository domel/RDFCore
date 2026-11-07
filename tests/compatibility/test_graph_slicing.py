import itertools

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize("bound", list(itertools.product([False, True], repeat=3)))
def test_graph_slice_matches_reference(bound):
    def observe(module):
        graph = module.Graph()
        triple = (module.URIRef("urn:s"), module.URIRef("urn:p"), module.Literal("x"))
        graph.add(triple)
        pattern = [value if flag else None for value, flag in zip(triple, bound)]
        result = graph[slice(*pattern)]
        if isinstance(result, bool):
            return result
        return [
            (
                type(item).__name__,
                tuple(str(v) for v in item) if isinstance(item, tuple) else str(item),
            )
            for item in result
        ]

    assert observe(rdfcore) == observe(rdflib)
