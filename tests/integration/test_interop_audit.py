"""Interop DNOTE 2026-07-23 §§3.1–3.3; ED reviewed 2026-11-04.

These are transformation tests, not entailment or normative conformance claims.
"""
from itertools import chain, count
from types import SimpleNamespace

import pytest

from rdfcore import BNode, Dataset, Graph, Literal, RDF, SQLiteStore, TripleTerm, URIRef
from rdfcore.compare import isomorphic
from rdfcore.interop import (basic_decode, basic_encode, decode_direction_i18n,
                             encode_direction_i18n, interop_downgrade)

S, P, O = map(URIRef, ('urn:s', 'urn:p', 'urn:o'))
FIELDS = (RDF.propositionFormSubject, RDF.propositionFormPredicate, RDF.propositionFormObject)


def form(graph, node, components=(S, P, O)):
    graph.add((node, RDF.type, RDF.PropositionForm))
    for predicate, value in zip(FIELDS, components):
        graph.add((node, predicate, value))


@pytest.mark.parametrize('operation', [basic_encode, basic_decode,
                                     lambda value: interop_downgrade(value, '1.1')])
@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
def test_transform_does_not_reset_input_graph_metadata(operation, backend):
    store = SQLiteStore(':memory:') if backend == 'sqlite' else 'default'
    source = Dataset(store=store, default_graph_base='https://example/default/')
    named = source.graph(URIRef('urn:g'), base='https://example/named/')
    named.add((S, P, O))
    source.graph(BNode('empty'), base='https://example/empty/')
    cache = dict(source._graphs)
    bases = {key: graph.base for key, graph in cache.items()}
    try:
        result = operation(source)
        assert {key: graph.base for key, graph in source._graphs.items()} == bases
        assert source._graphs == cache
        assert isomorphic(source, result)
    finally:
        source.close()


def test_fresh_form_nodes_avoid_nested_and_graph_name_collisions(monkeypatch):
    source = Dataset()
    source.graph(BNode('Ngraph'))
    term = TripleTerm(BNode('Nnested'), P, O)
    source.add((S, RDF.reifies, term))
    names = chain(('result', 'nested', 'graph'), (f'fresh{i}' for i in count()))
    monkeypatch.setattr('rdfcore.term.uuid4', lambda: SimpleNamespace(hex=next(names)))
    encoded = basic_encode(source)
    node = encoded.default_graph.value(S, RDF.reifies)
    assert node not in {BNode('Nnested'), BNode('Ngraph')}
    assert set(encoded.default_graph) == {
        (S, RDF.reifies, node), (node, RDF.type, RDF.PropositionForm),
        (node, FIELDS[0], BNode('Nnested')), (node, FIELDS[1], P), (node, FIELDS[2], O),
    }
    assert isomorphic(source, basic_decode(encoded))


@pytest.mark.parametrize('missing', FIELDS)
def test_incomplete_typed_form_is_rejected(missing):
    graph, node = Graph(), BNode('form')
    form(graph, node)
    graph.remove((node, missing, None))
    before = set(graph)
    with pytest.raises(ValueError, match='incomplete'):
        basic_decode(graph)
    assert set(graph) == before


def test_untyped_form_properties_are_ordinary_data():
    graph, node = Graph(), BNode('ordinary')
    graph.add((node, FIELDS[2], S)).add((node, FIELDS[2], O))
    assert set(basic_decode(graph)) == set(graph)


@pytest.mark.parametrize('used', [False, True])
def test_cycles_are_rejected_even_without_an_external_reference(used):
    graph, a, b = Graph(), BNode('a'), BNode('b')
    form(graph, a, (S, P, b))
    form(graph, b, (S, P, a))
    if used:
        graph.add((S, RDF.reifies, a))
    with pytest.raises(ValueError, match='cyclic'):
        basic_decode(graph)


def test_hybrid_full_and_basic_input_is_rejected_by_both_transforms():
    graph, node = Graph(), BNode('form')
    form(graph, node)
    graph.add((S, RDF.reifies, TripleTerm(S, P, O)))
    for operation in (basic_encode, basic_decode):
        with pytest.raises(ValueError, match='PropositionForm'):
            operation(graph)


def test_invalid_form_subject_usage_is_rejected_without_losing_its_metadata():
    graph, node = Graph(), BNode('form')
    form(graph, node)
    graph.add((node, URIRef('urn:extra'), Literal('keep')))
    before = set(graph)
    with pytest.raises(ValueError, match='subject'):
        basic_decode(graph)
    assert set(graph) == before


def test_multiple_reifiers_and_nested_forms_have_exact_round_trip():
    inner = TripleTerm(BNode('shared'), P, Literal('v', lang='EN', direction='rtl'))
    outer = TripleTerm(S, P, inner)
    source = Graph().add((S, RDF.reifies, outer)).add((O, RDF.reifies, outer))
    encoded = basic_encode(source)
    assert encoded.value(S, RDF.reifies) == encoded.value(O, RDF.reifies)
    assert len(list(encoded.subjects(RDF.type, RDF.PropositionForm))) == 2
    assert set(basic_decode(encoded)) == set(source)
    assert isomorphic(basic_encode(encoded), encoded)
    assert set(basic_decode(source)) == set(source)


def test_graph_local_forms_are_fresh_dataset_wide_and_preserve_sharing():
    source = Dataset()
    shared = BNode('shared')
    term = TripleTerm(shared, P, O)
    for name in (None, BNode('named'), URIRef('urn:g')):
        target = source.default_graph if name is None else source.graph(name)
        target.add((S, RDF.reifies, term)).add((O, RDF.reifies, term))
    encoded = basic_encode(source)
    nodes = set()
    for graph in encoded.graphs():
        node = graph.value(S, RDF.reifies)
        assert graph.value(O, RDF.reifies) == node
        assert graph.value(node, FIELDS[0]) == shared
        nodes.add(node)
    assert len(nodes) == 3
    assert set(basic_decode(encoded).quads()) == set(source.quads())


def test_iri_proposition_type_is_not_a_decodable_blank_form():
    graph = Graph()
    form(graph, S)
    graph.add((S, FIELDS[2], Literal('another value')))
    assert set(basic_decode(graph)) == set(graph)


def test_form_used_as_graph_name_is_rejected_explicitly():
    source, node = Dataset(), BNode('form-name')
    source.graph(node)
    form(source.default_graph, node)
    source.add((S, RDF.reifies, node))
    with pytest.raises(ValueError, match='graph name'):
        basic_decode(source)


@pytest.mark.parametrize('components', [(Literal('invalid'), P, O), (S, BNode('p'), O)])
def test_invalid_components_raise_explicit_errors(components):
    graph = Graph()
    form(graph, BNode('form'), components)
    with pytest.raises(ValueError, match='invalid proposition form components'):
        basic_decode(graph)


@pytest.mark.parametrize('direction', ['ltr', 'rtl'])
@pytest.mark.parametrize('language', ['EN', 'zh-Hant', 'en-001'])
def test_i18n_mapping_preserves_term_identity(direction, language):
    literal = Literal('text', lang=language, direction=direction)
    encoded = encode_direction_i18n(literal)
    assert str(encoded.datatype) == 'https://www.w3.org/ns/i18n#' + language.lower() + '_' + direction
    assert decode_direction_i18n(encoded) == literal
    assert literal.language == language
