"""Concepts CR 2026-04-07 §§ 3.1, 3.4, 3.6 and Appendix B.

Structural identity, many-to-many reifiers, scopes and non-assertion.
"""
import pytest

from rdfcore import BNode, Dataset, Graph, Literal, Memory, RDF, SQLiteStore, TripleTerm, URIRef, Variable
from rdfcore.compare import isomorphic
from rdfcore.rdf_version import required_rdf_version

S, P, Q = map(URIRef, ['urn:s', 'urn:p', 'urn:q'])


@pytest.mark.parametrize('position', [0, 1, 2])
@pytest.mark.parametrize('invalid', [None, 'text', Variable('v'), object()])
def test_triple_constructor_and_graph_reject_non_rdf_components(position, invalid):
    triple = [S, P, Literal('value')]
    triple[position] = invalid
    with pytest.raises(TypeError):
        TripleTerm(*triple)
    with pytest.raises(TypeError):
        Graph().add(tuple(triple))


@pytest.mark.parametrize('invalid', [Literal('value'), TripleTerm(S, P, Literal('v'))])
@pytest.mark.parametrize('position', [0, 1])
def test_terms_in_illegal_subject_or_predicate_positions(position, invalid):
    triple = [S, P, Literal('value')]
    triple[position] = invalid
    with pytest.raises(TypeError):
        TripleTerm(*triple)
    with pytest.raises(TypeError):
        Graph().add(tuple(triple))


def model():
    node = BNode('shared')
    a = TripleTerm(node, P, Literal('text', lang='ar', direction='rtl'))
    b = TripleTerm(S, Q, a)
    graph = Graph()
    for reifier in (URIRef('urn:r1'), node):
        for term in (a, b):
            graph.add((reifier, RDF.reifies, term))
    graph.add((node, Q, URIRef('urn:metadata')))
    return graph, node, a, b


@pytest.mark.parametrize('format', ['nt12', 'turtle12', 'xml12'])
def test_nested_terms_many_to_many_reifiers_roundtrip_without_assertion(format):
    graph, node, a, b = model()
    assert required_rdf_version(graph) == '1.2'
    for term in (a, b):
        assert tuple(term) not in graph
        assert len(list(graph.subjects(RDF.reifies, term))) == 2
    assert len(list(graph.objects(node, RDF.reifies))) == 2
    restored = Graph().parse(data=graph.serialize(format=format), format=format)
    assert len(restored) == 5
    assert isomorphic(restored, graph)
    for profile in ('1.1', '1.2-basic'):
        with pytest.raises(ValueError):
            graph.serialize(format=format, rdf_version=profile)


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
@pytest.mark.parametrize('format', ['nq12', 'trig12'])
def test_dataset_model_scopes_persist_and_roundtrip(tmp_path, backend, format):
    path = tmp_path / 'model.sqlite'
    dataset = Dataset(store=Memory() if backend == 'memory' else SQLiteStore(path))
    graph, node, a, b = model()
    identifiers = [dataset.default_graph.identifier, URIRef('urn:g1'), URIRef('urn:g2')]
    for identifier in identifiers:
        for triple in graph:
            dataset.graph(identifier).add(triple)
    if backend == 'sqlite':
        dataset.close()
        dataset = Dataset(store=SQLiteStore(path))
    restored = Dataset().parse(data=dataset.serialize(format=format), format=format)
    for identifier in identifiers:
        actual = dataset.graph(identifier)
        assert set(actual) == set(graph)
        assert isomorphic(restored.graph(identifier), graph)
        assert tuple(a) not in actual and tuple(b) not in actual
    # One mapping spans nested terms and ordinary occurrences in the graph.
    skolemized = dataset.graph(identifiers[1]).skolemize()
    assert isomorphic(skolemized.de_skolemize(), graph)
    selected = dataset.graph(identifiers[1]).skolemize(bnode=node)
    replacement = node.skolemize()
    assert (replacement, RDF.reifies, TripleTerm(S, Q, TripleTerm(replacement, P, a.object))) in selected
    dataset.remove_graph(identifiers[1])
    assert len(dataset.graph(identifiers[1])) == 0
    assert set(dataset.default_graph) == set(graph)
    assert set(dataset.graph(identifiers[2])) == set(graph)
    dataset.close()
