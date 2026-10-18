"""The new MIME parameter path preserves RDFLib 7.6.0 legacy semantics."""
import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('mime', ['text/turtle', 'application/trig', 'application/n-triples', 'application/n-quads', 'application/rdf+xml'])
def test_explicit_mime_11_matches_reference_bare_mime(mime):
    outcomes = []
    for module in (rdflib, rdfcore):
        cls = module.Dataset if mime in ('application/trig', 'application/n-quads') else module.Graph
        graph = cls()
        graph.add((module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('value', lang='EN')))
        format = mime + '; version=1.1' if module is rdfcore else mime
        result = graph.serialize(format=format, encoding='utf-8')
        assert isinstance(result, bytes)
        restored = cls().parse(data=result, format=format)
        assert len(restored) == 1
        triples = restored.default_graph if cls is module.Dataset else restored
        outcomes.append([(type(s).__name__, str(s), type(p).__name__, str(p), type(o).__name__, str(o), o.language)
                         for s, p, o in triples])
    assert outcomes[0] == outcomes[1]


def test_explicit_custom_plugin_registration_still_wins():
    from rdfcore.parser import Parser
    from rdfcore import plugin
    name = 'text/turtle; version=custom-test'
    class Custom(Parser): pass
    key = (name, Parser)
    try:
        plugin.register(name, Parser, Custom)
        assert plugin.get(name, Parser).getClass() is Custom
    finally:
        plugin._registry.pop(key, None)
