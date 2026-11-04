import pytest
from rdfcore import BNode, ConjunctiveGraph, Dataset, Graph, Literal, URIRef, TripleTerm
from rdfcore.interop import basic_encode, interop_downgrade
from rdfcore.compare import isomorphic

S, P, O = map(URIRef, ('urn:s', 'urn:p', 'urn:o'))

def test_direction_collision():
    a = Literal('x', lang='en', direction='rtl')
    b = Literal('x', datatype=URIRef('https://www.w3.org/ns/i18n#en_rtl'))
    source = Graph().add((S,P,a)).add((S,P,b))
    with pytest.raises(ValueError, match='collides'):
        interop_downgrade(source, '1.1')
    assert len(source) == 2

def test_custom_default():
    source = ConjunctiveGraph(identifier=URIRef('urn:default'))
    source.add((S,P,O))
    assert isomorphic(source, basic_encode(source))
    source.graph(URIRef('urn:x-rdflib:default'))
    with pytest.raises(ValueError, match='collides'):
        basic_encode(source)

@pytest.mark.parametrize('mode', ['pretty', 'stream'])
@pytest.mark.parametrize('name', [URIRef('urn:empty'), BNode('empty')])
def test_empty_trig(mode, name):
    source = Dataset(); source.graph(name)
    text = source.serialize(format='trig12', mode=mode)
    assert isomorphic(source, Dataset().parse(data=text, format='trig12'))

def test_default_projection_excludes_other_terms():
    source = Dataset(); source.add((S,P,O))
    source.graph(URIRef('urn:other')).add((S,P,TripleTerm(S,P,O)))
    assert set(Graph().parse(data=source.serialize(format='nt', dataset_policy='default'), format='nt')) == {(S,P,O)}

def test_custom_plugin_options(monkeypatch):
    import rdfcore
    from rdfcore.serializer import Serializer
    class Custom(Serializer):
        def serialize(self, stream=None, **options):
            assert isinstance(self.store, Dataset)
            return options['dataset_policy']
    monkeypatch.setitem(rdfcore.plugin._registry, ('nt', Serializer), rdfcore.plugin.Plugin('nt', Serializer, implementation=Custom))
    assert Dataset().serialize(format='nt', dataset_policy='custom') == 'custom'
