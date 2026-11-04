"""RDF 1.2 extensions preserve ConjunctiveGraph context boundaries.

Concepts CR 2026-04-07 §4; TriG/N-Quads WD 2026-10-23 §2.
Editors' Drafts checked 2026-11-04: same default/named graph distinction.
"""

import io

import pytest

from rdfcore import BNode, ConjunctiveGraph, Dataset, Literal, SQLiteStore, TripleTerm, URIRef
from rdfcore.compare import isomorphic
from rdfcore.external_sort import external_sort, statement_key
from rdfcore.interop import basic_decode, basic_encode
from rdfcore.pipeline import convert
from rdfcore.semantics import merge_datasets
from rdfcore.streaming import DatasetSink, NQStreamingWriter, TriGStreamingWriter, parse_stream


S, P, O = map(URIRef, ('urn:s', 'urn:p', 'urn:o'))


@pytest.mark.parametrize('format,mode', [('nq12', 'pretty'), ('trig12', 'pretty'), ('trig12', 'stream')])
@pytest.mark.parametrize('identifier', [URIRef('urn:default'), BNode('default')])
def test_rdf12_roundtrip(format, mode, identifier):
    source = ConjunctiveGraph(identifier=identifier)
    source.add((S, P, TripleTerm(S, P, O)))
    source.get_context(URIRef('urn:named')).add((S, P, Literal('v', lang='en', direction='rtl')))
    text = source.serialize(format=format, mode=mode)
    target = ConjunctiveGraph(identifier=URIRef('urn:new-default'))
    assert target.parse(data=text, format=format) is target
    assert isomorphic(source, target)
    assert len(target.default_context) == 1
    assert len(target.get_context(URIRef('urn:named'))) == 1
    assert isomorphic(source, basic_decode(basic_encode(source)))


@pytest.mark.parametrize('format', ['trig11', 'trig12'])
@pytest.mark.parametrize('mode', ['pretty', 'stream'])
def test_sentinel_is_a_named_graph_when_default_is_custom(format, mode):
    source = ConjunctiveGraph(identifier=URIRef('urn:default'))
    source.add((S, P, O))
    sentinel = URIRef('urn:x-rdflib:default')
    source.get_context(sentinel).add((O, P, S))
    target = ConjunctiveGraph(identifier=URIRef('urn:target'))
    target.parse(data=source.serialize(format=format, mode=mode), format=format)
    assert isomorphic(source, target)
    assert set(target.default_context) == {(S, P, O)}
    assert set(target.get_context(sentinel)) == {(O, P, S)}


@pytest.mark.parametrize('sqlite', [False, True])
def test_pipeline_writers_and_external_sort(sqlite, tmp_path):
    source = ConjunctiveGraph(**({'store': SQLiteStore(tmp_path / 'pipeline.sqlite')} if sqlite else {}),
                              identifier=URIRef('urn:default'))
    try:
        sink = DatasetSink(source)
        assert parse_stream(io.StringIO('<urn:s> <urn:p> <urn:o> <urn:g> .\n'), 'nq11', sink) is sink
        convert(io.StringIO('<urn:s> <urn:p> <urn:o> .\n'), input_format='nt11', output_format='nt11', sink=sink)
        quads = list(source.quads())
        for row in quads:
            assert statement_key(row) == statement_key((*row[:3], row[3].identifier))
        sorted_rows = list(external_sort(quads, memory_budget=1, temp_dir=tmp_path))
        assert all(isinstance(row[3], URIRef) for row in sorted_rows)
        assert len(sorted_rows) == 2
        for factory, format in [(NQStreamingWriter, 'nq11'), (TriGStreamingWriter, 'trig11')]:
            output = io.StringIO()
            writer = factory(output, default_graph_id=source.default_context.identifier)
            for row in quads:
                writer.add(row)
            writer.close()
            target = ConjunctiveGraph(identifier=URIRef('urn:target'))
            target.parse(data=output.getvalue(), format=format)
            assert isomorphic(source, target)
        assert not list(tmp_path.glob('rdfcore-run-*'))
    finally:
        source.close()


def test_comparison_is_read_only_and_dataset_ids_stay_distinct():
    source = ConjunctiveGraph(identifier=URIRef('urn:default'))
    source.default_context.base = 'urn:base'
    source.add((S, P, O))
    source.graph(URIRef('urn:empty'), base='urn:named-base')
    target = Dataset().add((S, P, O))
    target.graph(URIRef('urn:empty'))
    before = list(source.store.contexts()), dict(source._graphs)
    assert isomorphic(source, target)
    assert (list(source.store.contexts()), source._graphs) == before
    assert source.default_context.base == 'urn:base'
    assert source._graphs[URIRef('urn:empty')].base == 'urn:named-base'
    merged = merge_datasets([source])
    assert set(merged.default_graph) == {(S, P, O)}
