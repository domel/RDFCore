"""Executable RDFLib 7.6.0 observations for legacy XML parsing."""
import pytest
import rdflib
import rdfcore
from rdflib.compare import isomorphic

RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'


def document(body, attrs=''):
    return f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:e:" {attrs}>{body}</rdf:RDF>'


@pytest.mark.parametrize('body,attrs', [
    ('<rdf:Description foo="v"/>', ''),
    ('<rdf:Description nodeID="b"/>', ''),
    ('<rdf:Description version="v"/>', ''),
    ('<rdf:Description rdf:about="urn:s"><e:p rdf:resource="urn:o">ignored</e:p></rdf:Description>', ''),
    ('<rdf:Description rdf:about="urn:s"><e:p e:q="v">ignored</e:p></rdf:Description>', ''),
    ('<rdf:Description rdf:about="urn:s"><e:p rdf:type="relative"/></rdf:Description>', ''),
    ('<rdf:Description rdf:about="urn:s" rdf:type="relative"/>', ''),
    ('', 'foo="ignored" rdf:about="urn:ignored"'),
    ('<rdf:Description rdf:about="urn:s"><e:p datatype="relative">ignored</e:p></rdf:Description>', ''),
    ('<Thing foo="v"><p>v</p></Thing>', ''),
    ('<rdf:Description rdf:about="urn:s"><e:p rdf:datatype="relative">v</e:p></rdf:Description>', ''),
    ('<rdf:Description rdf:about="urn:s"><e:p rdf:ID="x">v</e:p><e:q rdf:ID="x">w</e:q></rdf:Description>', ''),
])
def test_legacy_parser_matches_oracle(body, attrs):
    source = document(body, attrs)
    expected = rdflib.Graph().parse(data=source, format='xml', publicID='https://example/base/')
    actual = rdfcore.Graph().parse(data=source, format='xml', publicID='https://example/base/')
    # RDFLib permits relative objects here, which N-Triples cannot represent.
    def convert(term):
        if isinstance(term, rdfcore.Literal):
            return rdflib.Literal(str(term), lang=term.language,
                                  datatype=rdflib.URIRef(str(term.datatype)) if term.datatype else None,
                                  normalize=False)
        return (rdflib.BNode if isinstance(term, rdfcore.BNode) else rdflib.URIRef)(str(term))
    converted = rdflib.Graph()
    for triple in actual:
        converted.add(tuple(convert(term) for term in triple))
    assert isomorphic(expected, converted)


@pytest.mark.parametrize('options', [{'format': 'xml', 'strict': True}, {'format': 'xml12'}])
def test_normative_modes_reject_text_on_resource(options):
    from xml.sax import SAXParseException
    source = document('<rdf:Description><e:p rdf:resource="urn:o">text</e:p></rdf:Description>')
    with pytest.raises(SAXParseException, match='must be empty'):
        rdfcore.Graph().parse(data=source, **options)


def test_node_id_uniqueness_uses_resolved_iri_in_both_libraries():
    from rdfcore.exceptions import ParserError as CoreParserError
    from rdflib.exceptions import ParserError as ReferenceParserError
    source = document('<rdf:Description rdf:ID="x"/>'
                      '<rdf:Description xml:base="#other" rdf:ID="x"/>')
    for module, error in ((rdflib, ReferenceParserError), (rdfcore, CoreParserError)):
        with pytest.raises(error, match='same ID'):
            module.Graph().parse(data=source, format='xml', publicID='https://example/doc#old')
