"""The pinned XML11 serializer uses its encoding attribute, not the argument."""
from io import BytesIO
from xml.etree import ElementTree

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('encoding', [None, 'ascii', 'utf-8', 'utf-16', 'not-a-codec'])
@pytest.mark.parametrize('destination', [False, True])
@pytest.mark.parametrize('empty', [False, True])
def test_xml11_encoding_and_return_contract(encoding, destination, empty):
    observations = []
    for module in (rdflib, rdfcore):
        graph = module.Graph()
        if not empty:
            graph.add((module.URIRef('urn:s'), module.URIRef('urn:p'),
                       module.Literal('é😀\r\n\t')))
        stream = BytesIO() if destination else None
        result = graph.serialize(destination=stream, format='xml', encoding=encoding)
        output = stream.getvalue() if destination else result
        assert isinstance(output, bytes if destination or encoding else str)
        assert result is graph if destination else result is output
        assert output.startswith(b'<?xml version="1.0" encoding="utf-8"?>'
                                 if isinstance(output, bytes)
                                 else '<?xml version="1.0" encoding="utf-8"?>')
        root = ElementTree.fromstring(output)
        observations.append([node.text for node in root.iter('{urn:}p')])
        assert not destination or not stream.closed
    assert observations[0] == observations[1]


@pytest.mark.parametrize('xml_base', ['', 'https://example.org/override/'])
def test_xml_base_keyword_overrides_base(xml_base):
    roots = []
    for module in (rdflib, rdfcore):
        output = module.Graph().serialize(format='xml', base='https://example.org/base/',
                                          xml_base=xml_base)
        roots.append(ElementTree.fromstring(output).attrib)
    assert roots[0] == roots[1]
