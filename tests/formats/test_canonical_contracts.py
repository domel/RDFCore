"""NT/NQ WD 2026-10-23 §3; lexical layout is separate from RDFC-1.0."""
from itertools import permutations

import pytest
import rdflib

import rdfcore
from rdfcore import BNode, Dataset, Graph, Literal, RDF, RDFS, TripleTerm, URIRef, XSD
from rdfcore.compare import isomorphic


@pytest.mark.parametrize('format,cls', [('nt12', Graph), ('nq12', Dataset)])
def test_canonical_nested_statement_has_exact_utf8_bytes(format, cls):
    value = Literal('é\t\n\x00\x7f\ufffe', lang='EN', direction='rtl')
    term = TripleTerm(BNode('kept'), URIRef('urn:p'), value)
    graph = cls().add((URIRef('urn:s'), RDF.reifies, term))
    expected = ('<urn:s> <' + str(RDF.reifies) + '> <<( _:kept <urn:p> '
                '"é\\t\\n\\u0000\\u007F\\uFFFE"@en--rtl )>> .\n').encode('utf-8')
    assert graph.serialize(format=format, canonical=True, encoding='utf-8') == expected


@pytest.mark.parametrize('format,cls', [('nt12', Graph), ('nq12', Dataset)])
def test_canonical_string_datatype_is_omitted(format, cls):
    graph = cls().add((URIRef('urn:s'), URIRef('urn:p'), Literal('v', datatype=XSD.string)))
    assert graph.serialize(format=format, canonical=True, encoding='utf-8') == b'<urn:s> <urn:p> "v" .\n'


def test_nq12_canonical_order_is_deterministic_for_fixed_labels():
    triples = [(BNode('kept'), URIRef('urn:p'), Literal(value, lang='EN')) for value in ('a', 'b', 'c')]
    expected = b''.join(f'_:kept <urn:p> "{value}"@en .\n'.encode() for value in ('a', 'b', 'c'))
    for order in permutations(triples):
        graph = Dataset()
        for triple in order:
            graph.add(triple)
        assert graph.serialize(format='nq12', canonical=True, encoding='utf-8') == expected


def test_nt12_canonical_layout_does_not_sort_an_input_iterator():
    rows = [(URIRef('urn:s'), URIRef('urn:p'), Literal(value)) for value in ('b', 'a')]

    class OrderedGraph(Graph):
        def __iter__(self):
            return iter(rows)

    assert OrderedGraph().serialize(format='nt12', canonical=True) == (
        '<urn:s> <urn:p> "b" .\n<urn:s> <urn:p> "a" .\n')


@pytest.mark.parametrize('format,cls', [('nt12', Graph), ('nq12', Dataset),
                                     ('turtle12', Graph), ('trig12', Dataset)])
def test_canonical_flag_does_not_rename_blank_nodes(format, cls):
    a, b = cls(), cls()
    a.add((BNode('first'), RDFS.label, Literal('v', lang='EN')))
    b.add((BNode('second'), RDFS.label, Literal('v', lang='EN')))
    assert isomorphic(a, b)
    assert a.serialize(format=format, canonical=True) != b.serialize(format=format, canonical=True)


@pytest.mark.parametrize('format', ['turtle', 'ttl', 'turtle11', 'trig', 'trig11', 'xml', 'rdfxml'])
def test_legacy_non_line_formats_ignore_canonical_like_reference(format):
    reference_format = {'turtle11': 'turtle', 'trig11': 'trig', 'rdfxml': 'xml'}.get(format, format)
    for module in (rdflib, rdfcore):
        graph = module.Graph(identifier=module.URIRef('urn:g'))
        graph.add((module.URIRef('urn:s'), module.RDFS.label, module.Literal('v', lang='EN')))
        selected = reference_format if module is rdflib else format
        assert graph.serialize(format=selected, canonical=True) == graph.serialize(format=selected, canonical=False)


def test_xml12_canonical_flag_does_not_apply_xml_canonicalization():
    graph = Graph().add((URIRef('urn:s'), RDFS.label, Literal('v', lang='EN')))
    assert graph.serialize(format='xml12', canonical=True) == graph.serialize(format='xml12', canonical=False)


@pytest.mark.parametrize('format', ['nt', 'nt11', 'ntriples', 'nquads', 'nq', 'nq11'])
def test_legacy_line_format_normalization_is_an_explicit_extension(format):
    graph = Dataset() if format in ('nquads', 'nq', 'nq11') else Graph()
    graph.add((URIRef('urn:s'), URIRef('urn:p'), Literal('v', lang='EN')))
    graph.add((URIRef('urn:s'), URIRef('urn:p'), Literal('text', datatype=XSD.string)))
    actual = graph.serialize(format=format, canonical=True, encoding='utf-8')
    assert set(actual.splitlines(keepends=True)) == {
        b'<urn:s> <urn:p> "v"@en .\n', b'<urn:s> <urn:p> "text" .\n'}
