"""RDFCore aliases use RDFLib 7.6.0's nquads as the executable oracle."""
from io import BytesIO

import pytest
import rdflib

from rdfcore import Dataset, Graph, Literal, URIRef, convert, plugin
from rdfcore.parser import Parser
from rdfcore.serializer import Serializer
from rdfcore.exceptions import ParserError
from tests.w3c.runner import _parse

DATA = '<urn:s> <urn:p> "named"@EN <urn:g> .\n<urn:t> <urn:p> "default" .\n'


def records(dataset):
    return {tuple((type(term).__name__, str(term), getattr(term, 'language', None),
                   str(getattr(term, 'datatype', None))) for term in quad)
            for quad in dataset.quads()}


@pytest.mark.parametrize('alias', ['nq', 'nq11'])
@pytest.mark.parametrize('kind', [Parser, Serializer])
def test_nquads_aliases_resolve_to_existing_classes(alias, kind):
    assert plugin.get(alias, kind).getClass() is plugin.get('nquads', kind).getClass()


@pytest.mark.parametrize('alias', ['nq', 'nq11'])
@pytest.mark.parametrize('data', ['', DATA, DATA + DATA])
def test_nquads_aliases_round_trip_like_reference(alias, data):
    expected = rdflib.Dataset().parse(data=data, format='nquads')
    actual = Dataset()
    for _ in range(2):
        assert actual.parse(data=data, format=alias) is actual
        assert records(actual) == records(expected)
        encoded = actual.serialize(format=alias, encoding='utf-8')
        assert isinstance(encoded, bytes)
        restored = rdflib.Dataset().parse(data=encoded, format='nquads')
        assert records(restored) == records(expected)


@pytest.mark.parametrize('source', ['nq', 'nq11'])
@pytest.mark.parametrize('target', ['nq', 'nq11', 'nq12'])
def test_convert_accepts_new_aliases_in_both_directions(source, target):
    output = BytesIO()
    convert(BytesIO(DATA.encode()), output, input_format=source, output_format=target)
    expected = Dataset().parse(data=DATA, format='nquads')
    assert records(Dataset().parse(data=output.getvalue(), format=target)) == records(expected)


@pytest.mark.parametrize('alias', ['nq', 'nq11'])
@pytest.mark.parametrize('policy,expected', [('strict', None), ('default', 1), ('union', 2)])
def test_new_aliases_preserve_dataset_policy(alias, policy, expected):
    output = BytesIO()
    if expected is None:
        with pytest.raises(Exception) as caught:
            convert(BytesIO(DATA.encode()), output, input_format=alias, output_format='nt', dataset_policy=policy)
        assert isinstance(caught.value.__cause__, ValueError)
    else:
        convert(BytesIO(DATA.encode()), output, input_format=alias, output_format='nt', dataset_policy=policy)
        assert len(Graph().parse(data=output.getvalue(), format='nt')) == expected


@pytest.mark.parametrize('alias', ['nq', 'nq11'])
def test_new_aliases_do_not_enable_rdf12(alias):
    errors = []
    for format in ('nquads', alias):
        with pytest.raises(Exception) as caught:
            Dataset().parse(data='<urn:s> <urn:p> "text"@en--rtl .\n', format=format)
        errors.append(type(caught.value))
    assert errors[0] is errors[1]
    graph = Dataset().add((URIRef('urn:s'), URIRef('urn:p'), Literal('text', lang='en', direction='rtl')))
    with pytest.raises(ValueError):
        graph.serialize(format=alias)
    with pytest.raises(ParserError) as caught:
        convert(BytesIO(b'VERSION "1.2"\n<urn:s> <urn:p> "text"@en--rtl .\n'),
                BytesIO(), input_format='nq12', output_format=alias)
    assert isinstance(caught.value.__cause__, ValueError)


@pytest.mark.parametrize('alias', ['nq', 'nq11'])
def test_w3c_runner_accepts_new_aliases(tmp_path, alias):
    path = tmp_path / 'input.nq'
    path.write_text(DATA, encoding='utf-8')
    assert records(_parse(path, alias)) == records(_parse(path, 'nquads'))
