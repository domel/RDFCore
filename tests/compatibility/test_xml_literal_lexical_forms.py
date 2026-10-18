"""Keep the executable RDFLib baseline separate from old XML C14N fixtures."""

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('fragment', [
    '<br/>', '<br></br>', '<b>text &amp; value</b>',
    'text&#13;more', '<b>&#13;</b>', '<b a="&#13;&#10;&#9;"/>',
    '<a xmlns="urn:a"><b xmlns=""/></a>',
    '<a xmlns="urn:a"><b xmlns=""><c/></b></a>',
    '<a xmlns="urn:a"><b xmlns=""/><c/></a>',
    '<!--comment--><![CDATA[text & more]]><?target data?>',
])
@pytest.mark.parametrize('reified', [False, True])
def test_xml_literal_lexical_form_matches_reference(fragment, reified):
    annotation = 'rdf:ID="statement"' if reified else ''
    data = f'''<rdf:RDF xmlns:rdf="{rdflib.RDF}" xmlns:e="urn:e:">
      <rdf:Description rdf:about="urn:s"><e:p rdf:parseType="Literal" {annotation}>
      {fragment}</e:p></rdf:Description></rdf:RDF>'''
    def observe(module):
        graph = module.Graph().parse(data=data, format='xml', publicID='https://example.org/doc')
        value = graph.value(module.URIRef('urn:s'), module.URIRef('urn:e:p'))
        return len(graph), str(value), str(value.datatype), value.language
    assert observe(rdfcore) == observe(rdflib)
