"""Executable RDFLib 7.6.0 observations for legacy XML parsing."""

import pytest
import rdflib
import rdfcore

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"


@pytest.mark.parametrize("content", ["", "<!--x-->", "<?p x?>", "<!--x--><?p x?>"])
def test_default_xml_empty_literal_and_reification_match_reference(content):
    source = document(
        '<rdf:Description rdf:about="urn:s">'
        '<e:p rdf:ID="r" rdf:parseType="Literal">'
        "<br>" + content + "</br></e:p></rdf:Description>"
    )
    for module in (rdflib, rdfcore):
        graph = module.Graph().parse(
            data=source, format="xml", publicID="https://example/doc"
        )
        literal = module.Literal("<br/>", datatype=module.URIRef(RDF + "XMLLiteral"))
        assert graph.value(module.URIRef("urn:s"), module.URIRef("urn:e:p")) == literal
        assert (
            graph.value(
                module.URIRef("https://example/doc#r"), module.URIRef(RDF + "object")
            )
            == literal
        )
        assert len(graph) == 5


def document(body, attrs=""):
    return f'<rdf:RDF xmlns:rdf="{RDF}" xmlns:e="urn:e:" {attrs}>{body}</rdf:RDF>'


@pytest.mark.parametrize(
    "options", [{"format": "xml", "strict": True}, {"format": "xml12"}]
)
def test_normative_modes_reject_text_on_resource(options):
    from xml.sax import SAXParseException

    source = document(
        '<rdf:Description><e:p rdf:resource="urn:o">text</e:p></rdf:Description>'
    )
    with pytest.raises(SAXParseException, match="must be empty"):
        rdfcore.Graph().parse(data=source, **options)


def test_node_id_uniqueness_uses_resolved_iri_in_both_libraries():
    from rdfcore.exceptions import ParserError as CoreParserError
    from rdflib.exceptions import ParserError as ReferenceParserError

    source = document(
        '<rdf:Description rdf:ID="x"/><rdf:Description xml:base="#other" rdf:ID="x"/>'
    )
    for module, error in ((rdflib, ReferenceParserError), (rdfcore, CoreParserError)):
        with pytest.raises(error, match="same ID"):
            module.Graph().parse(
                data=source, format="xml", publicID="https://example/doc#old"
            )
