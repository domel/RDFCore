"""Explicit recovery for the locked pre-October W3C XML fixtures."""
import pytest
import rdflib
from rdfcore import Graph, URIRef, TripleTerm

RDF = str(rdflib.RDF)


def document(body, attrs=''):
    return f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:e:" {attrs}><rdf:Description rdf:about="urn:s">{body}</rdf:Description></rdf:RDF>'


def test_legacy_recovers_unannounced_terms_without_changing_default():
    data = document('<e:p rdf:parseType="Triple"><rdf:Description rdf:about="urn:a"><e:q rdf:resource="urn:b"/></rdf:Description></e:p>')
    with pytest.raises(Exception, match='require rdf:version'):
        Graph().parse(data=data, format='xml12')
    graph = Graph().parse(data=data, format='xml12', legacy_w3c=True)
    assert len(graph) == 1
    assert isinstance(graph.value(URIRef('urn:s'), URIRef('urn:e:p')), TripleTerm)
    with pytest.raises(Exception, match='require rdf:version'):
        Graph().parse(data=data.replace('<rdf:RDF ', '<rdf:RDF rdf:version="1.1" '), format='xml12', legacy_w3c=True)


@pytest.mark.parametrize('format', ['xml', 'xml12'])
def test_legacy_empty_elements_are_expanded_only_when_requested(format):
    data = document('<e:p rdf:parseType="Literal"><b><br/></b></e:p>')
    default = Graph().parse(data=data, format=format).value(URIRef('urn:s'), URIRef('urn:e:p'))
    reference = rdflib.Graph().parse(data=data, format='xml').value(rdflib.URIRef('urn:s'), rdflib.URIRef('urn:e:p'))
    assert str(default) == str(reference) == '<b><br/></b>'
    legacy = Graph().parse(data=data, format=format, legacy_w3c=True)
    assert str(legacy.value(URIRef('urn:s'), URIRef('urn:e:p'))) == '<b><br></br></b>'


@pytest.mark.parametrize('value', ['true', 1, None])
def test_legacy_option_requires_boolean(value):
    with pytest.raises(ValueError, match='legacy_w3c'):
        Graph().parse(data=document(''), format='xml12', legacy_w3c=value)


def test_legacy_keeps_security_checks():
    with pytest.raises(Exception, match='DTD'):
        Graph().parse(data='<!DOCTYPE x []>'+document(''), format='xml12', legacy_w3c=True)


def test_legacy_does_not_discard_direction_to_match_old_expected_graph():
    data = document('<e:p>bar</e:p>', 'xmlns:its="http://www.w3.org/2005/11/its" its:dir="ltr" xml:lang="en"')
    graph = Graph().parse(data=data, format='xml12', legacy_w3c=True)
    value = graph.value(URIRef('urn:s'), URIRef('urn:e:p'))
    assert value.language == 'en'
    assert value.direction == 'ltr'
