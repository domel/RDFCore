"""RDFLib 7.6.0 legacy behavior is distinct from safe_iris extensions."""
from xml.etree import ElementTree

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('base,iri', [
    ('https://example.org/a', 'https://example.org/abc'),
    ('https://example.org/', 'https://example.org/urn:x'),
    ('https://example.org/', 'https://example.org/name'),
])
@pytest.mark.parametrize('format', ['turtle', 'trig'])
def test_legacy_relative_iri_observations_match_reference(base, iri, format):
    observations = []
    for module in (rdflib, rdfcore):
        graph = module.Graph(base=base, bind_namespaces='none')
        graph.add((module.URIRef(iri), module.URIRef('urn:p'), module.Literal('v')))
        output = graph.serialize(format=format)
        target = rdflib.Graph() if format == 'turtle' else rdflib.Dataset()
        target.parse(data=output, format=format)
        observations.append({str(row[0]) for row in target.quads()} if format == 'trig'
                            else {str(s) for s in target.subjects()})
    assert observations[0] == observations[1]


def test_legacy_xmlns_output_conflict_is_shared_with_reference():
    for module in (rdflib, rdfcore):
        graph = module.Graph().add((module.URIRef('urn:s'),
            module.URIRef('http://www.w3.org/2000/xmlns/name'), module.Literal('v')))
        with pytest.raises(ElementTree.ParseError, match='reserved namespace'):
            ElementTree.fromstring(graph.serialize(format='xml'))


@pytest.mark.parametrize('local', ['version', 'annotation', 'annotationNodeID'])
def test_xml12_explicit_11_profile_has_reference_11_vocabulary(local):
    observations = []
    for module, format, options in [(rdflib, 'xml', {}),
                                    (rdfcore, 'xml12', {'rdf_version': '1.1'})]:
        predicate = str(module.RDF)+local
        graph = module.Graph().add((module.URIRef('urn:s'), module.URIRef(predicate), module.Literal('v')))
        output = graph.serialize(format=format, **options)
        assert '{'+str(module.RDF)+'}version' not in ElementTree.fromstring(output).attrib
        actual = rdflib.Graph().parse(data=output, format='xml')
        observations.append(set(actual))
        if module is rdfcore:
            assert set(rdfcore.Graph().parse(data=output, format='xml12')) == set(graph)
    assert observations[0] == observations[1]
