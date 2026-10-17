import itertools

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('bound', list(itertools.product([False, True], repeat=3)))
def test_query_patterns(bound):
    def observe(module):
        graph = module.Graph()
        for i in range(3):
            graph.add((module.URIRef(f'urn:s{i}'), module.URIRef('urn:p'), module.Literal('x')))
        wanted = (module.URIRef('urn:s1'), module.URIRef('urn:p'), module.Literal('x'))
        pattern = tuple(value if flag else None for value, flag in zip(wanted, bound))
        return {tuple(str(term) for term in triple) for triple in graph.triples(pattern)}
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize('selective', [False, True])
def test_iterator_survives_removal(selective):
    for module in (rdflib, rdfcore):
        graph = module.Graph()
        s, p = module.URIRef('urn:s'), module.URIRef('urn:p')
        triples = {(s, p, module.Literal(str(i))) for i in range(3)}
        for triple in triples:
            graph.add(triple)
        iterator = graph.triples((s, p, None) if selective else (None, None, None))
        first = next(iterator)
        graph.remove((None, None, None))
        assert {first, *iterator} == triples
