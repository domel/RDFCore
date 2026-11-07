"""Direct plugin tests; registration belongs to integration.

RDF 1.2 expectations target WD-rdf12-xml-20261009, sections 3.1,
5.1.2, 6.2.19 and 6.2.22 (Editor's Draft inspected 2026-10-17).
"""

import pytest

from rdfcore import Graph, URIRef, TripleTerm
from rdfcore.parser import create_input_source
from rdfcore.plugins.parsers.rdfxml import RDFXMLParser, RDFXML12Parser
from rdfcore.plugins.serializers.rdfxml import XMLSerializer, XML12Serializer

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
EX = "http://example.org/"


def document(body, attrs=""):
    return f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:ex="{EX}" {attrs}>{body}</rdf:RDF>'


def parse(data, cls=RDFXMLParser, **kwargs):
    graph = Graph()
    cls().parse(create_input_source(data=data, publicID=EX), graph, **kwargs)
    return graph


def test_rdf12_nested_terms_annotations_direction():
    data = document(
        """<rdf:Description rdf:about="s">
      <ex:p rdf:annotationNodeID="r" xml:lang="ar" its:dir="rtl">text</ex:p>
      <ex:q rdf:parseType="Triple"><rdf:Description rdf:about="inner">
        <ex:p rdf:parseType="Triple"><rdf:Description rdf:about="deep"><ex:q>v</ex:q></rdf:Description></ex:p>
      </rdf:Description></ex:q>
    </rdf:Description>""",
        'rdf:version="1.2" xmlns:its="http://www.w3.org/2005/11/its" its:version="2.0"',
    )
    graph = parse(data, RDFXML12Parser)
    assert len(graph) == 3
    literal = graph.value(URIRef(EX + "s"), URIRef(EX + "p"))
    assert literal.direction == "rtl" and literal.language == "ar"
    term = graph.value(URIRef(EX + "s"), URIRef(EX + "q"))
    assert isinstance(term, TripleTerm) and isinstance(term.object, TripleTerm)
    assert (term.subject, term.predicate, term.object) not in graph
    result = parse(
        XML12Serializer(graph).serialize(), RDFXML12Parser, preserve_bnode_ids=True
    )
    assert len(result) == len(graph)
    assert result.value(URIRef(EX + "s"), URIRef(EX + "q")) == term
    with pytest.raises(ValueError):
        XMLSerializer(graph).serialize()
