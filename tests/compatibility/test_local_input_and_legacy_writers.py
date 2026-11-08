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
