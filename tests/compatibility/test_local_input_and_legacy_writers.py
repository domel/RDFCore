"""Behavioral regressions for parsing, graph algebra and literal storage."""
from io import StringIO

import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('writer', [rdfcore.NTStreamingWriter, rdfcore.NQStreamingWriter])
def test_legacy_writer_rejects_direction(writer):
    output = StringIO()
    with pytest.raises(ValueError):
        writer(output).add((rdfcore.URIRef('urn:s'), rdfcore.URIRef('urn:p'),
                            rdfcore.Literal('hello', lang='en', direction='rtl')))
    assert output.getvalue() == ''


@pytest.mark.parametrize('mode', ['path', 'source', 'file', 'data'])
def test_relative_input_base(tmp_path, mode):
    path = tmp_path / 'input.ttl'
    path.write_text('<s> <p> <o> .')
    results = []
    for module in (rdflib, rdfcore):
        with path.open('rb') as handle:
            args = {'path': {'source': path}, 'source': {'source': handle},
                    'file': {'file': handle}, 'data': {'data': path.read_text()}}[mode]
            results.append(tuple(map(str, next(iter(module.Graph().parse(format='turtle', **args))))))
    assert results[0] == results[1]


@pytest.mark.parametrize('mode', ['path', 'source', 'file'])
@pytest.mark.parametrize('suffix,data', [
    ('nq', '<urn:s> <urn:p> <urn:o> <urn:g> .'),
    ('trig', '<urn:g> { <urn:s> <urn:p> <urn:o> . }'),
])
def test_dataset_format_from_path_or_named_stream(tmp_path, mode, suffix, data):
    path = tmp_path / ('input.' + suffix)
    path.write_text(data)
    results = []
    for module in (rdflib, rdfcore):
        with path.open('rb') as handle:
            args = {'source': path} if mode == 'path' else {mode: handle}
            if mode == 'source':
                args['format'] = 'nquads' if suffix == 'nq' else 'trig'
            dataset = module.Dataset().parse(**args)
            results.append(sorted(tuple((type(t).__name__, str(t)) for t in q)
                                  for q in dataset.quads()))
    assert results[0] == results[1]


def test_explicit_format_overrides_stream_name(tmp_path):
    path = tmp_path / 'input.nq'
    path.write_text('<urn:g> { <urn:s> <urn:p> <urn:o> . }')
    for module in (rdflib, rdfcore):
        with path.open('rb') as handle:
            dataset = module.Dataset().parse(file=handle, format='trig')
            assert list(dataset.quads()) == [(module.URIRef('urn:s'), module.URIRef('urn:p'),
                                             module.URIRef('urn:o'), module.URIRef('urn:g'))]
