"""RDF12 October 2026 published grammars; EDs checked 2026-10-22."""
from io import BytesIO

import pytest

from rdfcore import Dataset, Graph, Literal, URIRef, parse_stream
from rdfcore.exceptions import BadSyntax, ParserError
from rdfcore.streaming import BoundedReadStream


@pytest.mark.parametrize('format,cls', [('turtle12', Graph), ('trig12', Dataset)])
@pytest.mark.parametrize('term', [
    '<<( [ <urn:q> <urn:r> ] <urn:a> <urn:b> )>>',
    '<<( << <urn:a> <urn:b> <urn:c> >> <urn:p> <urn:o> )>>',
    '<<( <urn:a> <urn:b> << <urn:c> <urn:d> <urn:e> >> )>>',
])
def test_triple_term_does_not_accept_reified_triples_or_property_lists(format, cls, term):
    with pytest.raises(BadSyntax):
        cls().parse(data=f'<urn:s> <urn:p> {term} .', format=format)


@pytest.mark.parametrize('format,cls', [('nt12', Graph), ('nq12', Dataset)])
@pytest.mark.parametrize('label', ['é', '漢字', '_label', 'a\u0300', '\U00010000'])
def test_line_formats_accept_normative_unicode_blank_node_labels(format, cls, label):
    graph = cls().parse(data=f'_:{label} <urn:p> _:{label} .', format=format)
    subject, _, obj = next(iter(graph.default_graph if cls is Dataset else graph))
    assert subject == obj


@pytest.mark.parametrize('format', ['nt12', 'nq12'])
@pytest.mark.parametrize('separator', ['\x0b', '\x0c', '\u00a0', '\u2003'])
def test_line_formats_reject_non_grammar_whitespace(format, separator):
    with pytest.raises(ParserError):
        list(parse_stream(BytesIO(f'<urn:s>{separator}<urn:p> <urn:o> .'.encode()), format))


@pytest.mark.parametrize('format', ['nt12', 'nq12', 'turtle12', 'trig12'])
@pytest.mark.parametrize('chunk_size', [1, 7, 65536])
def test_unicode_escapes_and_long_records_across_chunks(format, chunk_size):
    lexical = 'é漢' * 100
    source = f'<urn:s> <urn:p> "{lexical}\\n\\u0041" .\n'.encode()
    rows = list(parse_stream(BoundedReadStream(BytesIO(source), chunk_size=chunk_size), format))
    assert rows == [(URIRef('urn:s'), URIRef('urn:p'), Literal(lexical+'\nA'), None)]


@pytest.mark.parametrize('format', ['nt12', 'nq12'])
@pytest.mark.parametrize('eol', ['\r', '\n', '\r\n'])
def test_line_endings_are_record_boundaries(format, eol):
    data = eol.join(['<urn:s> <urn:p> <urn:o> .', '<urn:a> <urn:p> <urn:o> .']).encode()
    rows = list(parse_stream(BoundedReadStream(BytesIO(data), chunk_size=1), format))
    assert len(rows) == 2
    with pytest.raises(ParserError):
        list(parse_stream(BytesIO(f'<urn:s>{eol}<urn:p> <urn:o> .'.encode()), format))


@pytest.mark.parametrize('format,cls', [('turtle12', Graph), ('trig12', Dataset)])
@pytest.mark.parametrize('obj', ['"v"^^_:b', '"v"^^1',
                                '<< ( <urn:a> <urn:b> <urn:c> )>>',
                                '<<( <urn:a> <urn:b> <urn:c> ) >>'])
def test_rdf12_datatype_and_triple_delimiters_follow_grammar(format, cls, obj):
    with pytest.raises(BadSyntax):
        cls().parse(data=f'<urn:s> <urn:p> {obj} .', format=format)


@pytest.mark.parametrize('format,cls', [('turtle12', Graph), ('trig12', Dataset)])
@pytest.mark.parametrize('source', [
    'PREFIX 1bad: <urn:> 1bad:s 1bad:p 1bad:o .',
    'PREFIX _: <urn:> _:s <urn:p> <urn:o> .',
    'PREFIX : <urn:bad space> :s :p :o .',
    'BASE <https://example/bad space> <s> <p> <o> .',
    '<urn:s> <urn:p> <urn:bad"quote> .',
    '<urn:s>\u00a0<urn:p> <urn:o> .',
])
def test_rdf12_prefix_iri_and_whitespace_constraints(format, cls, source):
    with pytest.raises((BadSyntax, ParserError)):
        cls().parse(data=source, format=format)


@pytest.mark.parametrize('format', ['nt12', 'nq12'])
@pytest.mark.parametrize('declaration', ['VERSION"1.2"', r'VERSION "\u0031.2"', 'VERSION "1.2"#comment'])
def test_line_version_specifier_uses_string_grammar(format, declaration):
    source = declaration+'\n<urn:s> <urn:p> <urn:o> .'
    assert len(list(parse_stream(BytesIO(source.encode()), format))) == 1
