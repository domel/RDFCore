"""Regression scenarios from the 2026-10-17 review, RDFLib 7.6.0 oracle."""
from io import BytesIO
from unittest.mock import patch

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('fmt', ['nt', 'turtle', 'xml'])
@pytest.mark.parametrize('union', [False, True])
@pytest.mark.parametrize('empty', [False, True])
def test_dataset_graph_formats_match_reference(fmt, union, empty):
    observations = []
    for module in (rdflib, rdfcore):
        graph = module.Dataset(default_union=union)
        if not empty:
            s, p = module.URIRef('urn:s'), module.URIRef('urn:p')
            graph.add((s, p, module.Literal('default')))
            graph.graph(module.URIRef('urn:g')).add((s, p, module.Literal('named')))
        output = graph.serialize(format=fmt)
        observations.append(set(rdflib.Graph().parse(data=output, format=fmt)))
        target = BytesIO()
        assert graph.serialize(target, format=fmt) is graph
        assert not target.closed
        assert set(rdflib.Graph().parse(data=target.getvalue(), format=fmt)) == observations[-1]
    assert observations[0] == observations[1]


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
@pytest.mark.parametrize('other_graph', [False, True])
def test_remove_graph_removes_last_union_copy(tmp_path, backend, other_graph):
    def exercise(module, store=None):
        dataset = module.Dataset(**({'store': store} if store is not None else {}))
        triple = module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x')
        dataset.add((*triple, None))
        dataset.graph(module.URIRef('urn:g')).add(triple)
        if other_graph:
            dataset.graph(module.URIRef('urn:h')).add(triple)
        dataset.remove_graph(module.URIRef('urn:g'))
        dataset.remove_graph(module.URIRef('urn:g'))
        return len(dataset), sorted(str(g.identifier) for g in dataset.graphs())
    store = rdfcore.SQLiteStore(tmp_path/'store.sqlite') if backend == 'sqlite' else rdfcore.Memory()
    try:
        assert exercise(rdfcore, store) == exercise(rdflib)
    finally:
        store.close()


@pytest.mark.parametrize('fragment', ['<![CDATA[a & b]]>', '<!--x--><br/>', '<?p x?><br/>',
                                     '<x xmlns:z="urn:z"><z:y/></x>', '<a>before<![CDATA[&]]>after</a>'])
def test_xml_literal_events_match_reference(fragment):
    data = f'<rdf:RDF xmlns:rdf="{rdflib.RDF}" xmlns:e="urn:e:"><rdf:Description rdf:about="urn:s"><e:p rdf:parseType="Literal">{fragment}</e:p></rdf:Description></rdf:RDF>'
    observations = []
    for module in (rdflib, rdfcore):
        graph = module.Graph().parse(data=data, format='xml')
        observations.append(str(graph.value(module.URIRef('urn:s'), module.URIRef('urn:e:p'))))
    assert observations[0] == observations[1]


@pytest.mark.parametrize('language', ['EN', 'en', 'en-US'])
def test_sqlite_retains_language_spelling_and_deduplicates(tmp_path, language):
    oracle = rdflib.Graph()
    oracle.add((rdflib.URIRef('urn:s'), rdflib.URIRef('urn:p'), rdflib.Literal('v', lang=language)))
    oracle.add((rdflib.URIRef('urn:s'), rdflib.URIRef('urn:p'), rdflib.Literal('v', lang=language.swapcase())))
    expected = next(oracle.objects()).language
    path = tmp_path/'language.sqlite'
    store = rdfcore.SQLiteStore(path)
    s, p = rdfcore.URIRef('urn:s'), rdfcore.URIRef('urn:p')
    graph = rdfcore.Graph(store=store, identifier=rdfcore.URIRef('urn:g'))
    graph.add((s, p, rdfcore.Literal('v', lang=language)))
    graph.add((s, p, rdfcore.Literal('v', lang=language.swapcase())))
    assert len(graph) == 1
    assert next(graph.objects()).language == expected
    store.close()
    store = rdfcore.SQLiteStore(path)
    try:
        graph = rdfcore.Graph(store=store, identifier=rdfcore.URIRef('urn:g'))
        assert next(graph.objects()).language == expected
    finally:
        store.close()


@pytest.mark.parametrize('failure', ['lookup', 'constructor'])
def test_graph_parse_closes_owned_source_on_plugin_failure(failure):
    source = rdfcore.InputSource(file=BytesIO(), auto_close=True)
    class BrokenParser:
        def __init__(self, *args):
            raise RuntimeError('constructor failed')
    class Plugin:
        def getClass(self):
            return BrokenParser
    with patch('rdfcore.graph.create_input_source', return_value=source):
        with patch('rdfcore.graph.get_plugin', side_effect=RuntimeError('lookup failed') if failure == 'lookup' else None,
                   return_value=Plugin()):
            with pytest.raises(RuntimeError):
                rdfcore.Graph().parse(data='', format='xml')
    assert source.file.closed
