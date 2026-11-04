"""Explicit projection/downgrade extensions preserve legacy RDFLib dispatch."""
from io import BytesIO

import pytest

from rdfcore import Dataset, Graph, Literal, SQLiteStore, TripleTerm, URIRef, convert
from rdfcore.interop import basic_decode, decode_direction_i18n
import rdflib

S, P, O = map(URIRef, ('urn:s', 'urn:p', 'urn:o'))


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
@pytest.mark.parametrize('format', ['nt12', 'turtle12', 'xml12'])
@pytest.mark.parametrize('policy', ['strict', 'default', 'union'])
@pytest.mark.parametrize('empty', [False, True])
def test_rdf12_dataset_projection_requires_an_explicit_loss_policy(backend, format, policy, empty):
    source = Dataset(store=SQLiteStore(':memory:') if backend == 'sqlite' else 'default',
                     default_union=True)
    source.add((S, P, Literal('default')))
    named = source.graph(URIRef('urn:g'), base='https://example/named/')
    term = TripleTerm(S, P, O)
    if not empty:
        named.add((S, P, term))
    output = BytesIO()
    try:
        if policy == 'strict':
            for options in ({}, {'dataset_policy': 'strict'}):
                with pytest.raises(ValueError, match='named graph'):
                    source.serialize(output, format=format, encoding='utf-8', **options)
                assert output.getvalue() == b''
        else:
            assert source.serialize(output, format=format, encoding='utf-8', dataset_policy=policy) is source
            actual = Graph().parse(data=output.getvalue(), format=format)
            expected = {(S, P, Literal('default'))}
            if policy == 'union' and not empty:
                expected.add((S, P, term))
            assert set(actual) == expected
        assert named.base == 'https://example/named/'
        assert not output.closed
    finally:
        source.close()


@pytest.mark.parametrize('format', ['nt12', 'turtle12', 'xml12'])
@pytest.mark.parametrize('policy', ['bad', False])
def test_invalid_projection_policy_preserves_existing_file(tmp_path, format, policy):
    path = tmp_path / 'out.rdf'
    path.write_bytes(b'keep')
    with pytest.raises(ValueError, match='dataset_policy'):
        Dataset().serialize(path, format=format, dataset_policy=policy)
    assert path.read_bytes() == b'keep'


@pytest.mark.parametrize('format', ['nt', 'turtle', 'xml'])
def test_explicit_interop_downgrade_does_not_implicitly_discard_graph_names(format):
    source = Dataset()
    source.graph(URIRef('urn:g')).add((S, P, TripleTerm(S, P, O)))
    with pytest.raises(ValueError, match='named graph'):
        source.serialize(format=format, rdf_version='1.1', downgrade='interop')
    text = source.serialize(format=format, rdf_version='1.1', downgrade='interop', dataset_policy='union')
    decoded = basic_decode(Graph().parse(data=text, format=format))
    assert set(decoded) == {(S, P, TripleTerm(S, P, O))}


def test_directional_downgrade_is_explicit_and_reversible_per_literal():
    original = Literal('text', lang='EN', direction='rtl')
    source = Graph().add((S, P, original))
    with pytest.raises(ValueError):
        source.serialize(format='nt')
    text = source.serialize(format='nt', rdf_version='1.1', downgrade='interop')
    restored = Graph().parse(data=text, format='nt')
    assert decode_direction_i18n(restored.value(S, P)) == original


@pytest.mark.parametrize('downgrade', ['interop', 'drop'])
def test_streaming_convert_rejects_unavailable_downgrade_before_output(tmp_path, downgrade):
    path = tmp_path / 'out.nt'
    path.write_bytes(b'keep')
    with pytest.raises(ValueError, match='downgrade'):
        convert(BytesIO(b''), path, input_format='nt12', output_format='nt', downgrade=downgrade)
    assert path.read_bytes() == b'keep'


@pytest.mark.parametrize('format', ['nt', 'turtle', 'xml'])
@pytest.mark.parametrize('policy', ['default', 'union'])
@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
def test_explicit_projection_matches_the_corresponding_reference_graph(format, policy, backend):
    source = Dataset(store=SQLiteStore(':memory:') if backend == 'sqlite' else 'default')
    source.add((S, P, Literal('default')))
    source.graph(URIRef('urn:g')).add((S, P, Literal('named')))
    reference = rdflib.Dataset(default_union=policy == 'union')
    rs, rp = rdflib.URIRef(str(S)), rdflib.URIRef(str(P))
    reference.add((rs, rp, rdflib.Literal('default')))
    reference.graph(rdflib.URIRef('urn:g')).add((rs, rp, rdflib.Literal('named')))
    try:
        expected = rdflib.Graph()
        for triple in reference.triples((None, None, None)):
            expected.add(triple)
        actual = rdflib.Graph().parse(data=source.serialize(format=format, dataset_policy=policy), format=format)
        assert set(actual) == set(expected)
    finally:
        source.close()
