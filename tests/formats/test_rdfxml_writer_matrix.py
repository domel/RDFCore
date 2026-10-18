"""T31 writer acceptance: XML WD 2026-10-09 §§ 3.1, 6.2.19, 7.

The linked Editor's Draft was checked 2026-10-18. Triple construction
follows the explicit interpretation recorded by T29, not silent inference.
"""
from io import BytesIO
from xml.etree import ElementTree

import pytest

from rdfcore import BNode, Graph, Literal, RDF, TripleTerm, URIRef
from rdfcore.compare import isomorphic
from rdfcore.plugins.serializers.rdfxml import XML12Serializer


def sample(version):
    graph = Graph(base='https://example.org/base/')
    graph.bind('rdf', URIRef('urn:wrong:'))
    graph.bind('ns1', URIRef('urn:collision:'))
    s, p, q = map(URIRef, ('urn:s', 'urn:p', 'urn:q'))
    shared = BNode('shared')
    for obj in (URIRef('urn:o'), shared, Literal(''), Literal('é😀\r\n\t<&>'),
                Literal('value', lang='EN'),
                Literal('<b xmlns="urn:x" a="v">\r<!--c--><?p x?></b>', datatype=RDF.XMLLiteral)):
        graph.add((s, p, obj)).add((s, p, obj))
    graph.add((shared, q, shared))
    if version != '1.1':
        graph.add((shared, p, Literal('text', lang='ar', direction='rtl')))
    if version == '1.2':
        inner = TripleTerm(shared, q, Literal('text', lang='en', direction='ltr'))
        outer = TripleTerm(s, p, inner)
        for reifier in (URIRef('urn:r'), shared):
            graph.add((reifier, RDF.reifies, outer))
        graph.add((URIRef('urn:r'), RDF.reifies, inner))
    return graph


@pytest.mark.parametrize('version', ['1.1', '1.2-basic', '1.2'])
@pytest.mark.parametrize('encoding', [None, 'utf-8', 'utf-16'])
@pytest.mark.parametrize('empty', [False, True])
@pytest.mark.parametrize('destination', [False, True])
def test_xml12_complete_writer_roundtrip_matrix(version, encoding, empty, destination):
    graph = Graph() if empty else sample(version)
    sink = BytesIO() if destination else None
    result = graph.serialize(destination=sink, format='xml12', encoding=encoding,
                             rdf_version=version)
    output = sink.getvalue() if destination else result
    assert isinstance(output, bytes if destination or encoding is not None else str)
    if destination:
        assert result is graph and not sink.closed
    root = ElementTree.fromstring(output)
    assert root.attrib.get('{'+str(RDF)+'}version') == (None if version == '1.1' else version)
    actual = Graph().parse(data=output, format='xml12')
    assert len(actual) == len(graph)
    assert isomorphic(actual, graph)
    if version == '1.2' and not empty:
        # Nested propositions remain unasserted, even with multiple reifiers.
        assert not list(actual.triples((None, URIRef('urn:q'), Literal('text', lang='en', direction='ltr'))))


@pytest.mark.parametrize('profile', ['1.1', '1.2-basic'])
def test_lower_profiles_reject_triple_terms_before_writing_any_bytes(profile):
    sink = BytesIO()
    with pytest.raises(ValueError, match='RDF 1.2'):
        sample('1.2').serialize(sink, format='xml12', rdf_version=profile)
    assert sink.getvalue() == b'' and not sink.closed


def test_xml12_direct_serializer_reuse_resets_document_state():
    graph = sample('1.2')
    serializer = XML12Serializer(graph)
    for _ in range(2):
        sink = BytesIO()
        assert serializer.serialize(sink) is None
        assert isomorphic(Graph().parse(data=sink.getvalue(), format='xml12'), graph)


def test_utf32_writer_emits_valid_xml_with_explicit_transport_decoding():
    # Expat does not accept UTF-32 byte input. Verify the writer's codec
    # independently; direct byte-input support belongs to the parser audit.
    graph = sample('1.2')
    output = graph.serialize(format='xml12', encoding='utf-32')
    assert isinstance(output, bytes)
    text = output.decode('utf-32')
    assert text.startswith('<?xml version="1.0" encoding="utf-32"?>')
    assert ElementTree.fromstring(text).tag == '{'+str(RDF)+'}RDF'
    assert isomorphic(Graph().parse(data=text, format='xml12'), graph)


@pytest.mark.parametrize('position', [0, 1, 2])
def test_forbidden_xml_character_is_rejected_before_writing(position):
    triple = [URIRef('urn:s'), URIRef('urn:p'), Literal('text')]
    triple[position] = Literal('bad\x00') if position == 2 else URIRef('urn:bad\x00name')
    sink = BytesIO()
    with pytest.raises(ValueError, match='forbidden in XML'):
        Graph().add(tuple(triple)).serialize(sink, format='xml12')
    assert sink.getvalue() == b''
