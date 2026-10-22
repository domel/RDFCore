"""One stateful encoder per output document; no ownership transfer."""
from io import BytesIO

import pytest

from rdfcore import Dataset, Graph, Literal, URIRef
from rdfcore.compare import isomorphic
from rdfcore.streaming import TurtleStreamingWriter, TriGStreamingWriter


@pytest.mark.parametrize('format,cls', [('turtle12', Graph), ('trig12', Dataset)])
@pytest.mark.parametrize('encoding', ['utf-8-sig', 'utf-16', 'utf-32', 'iso2022_jp'])
@pytest.mark.parametrize('canonical', [False, True])
def test_streaming_uses_one_encoder_for_the_whole_document(format, cls, encoding, canonical):
    graph = cls()
    for name in ('a', 'b'):
        graph.add((URIRef('urn:'+name), URIRef('urn:p'), Literal('日本語', lang='EN')))
    output = BytesIO()
    assert graph.serialize(output, format=format, mode='stream', encoding=encoding,
                           rdf_version='1.2', canonical=canonical) is graph
    text = output.getvalue().decode(encoding)
    assert '\ufeff' not in text
    assert isomorphic(graph, cls().parse(data=text, format=format))
    assert not output.closed


@pytest.mark.parametrize('writer', [TurtleStreamingWriter, TriGStreamingWriter])
@pytest.mark.parametrize('explicit', [False, True])
def test_push_encoder_and_repeated_close_keep_caller_stream_open(writer, explicit):
    output = BytesIO()
    kwargs = {'text_output': False} if explicit else {}
    target = writer(output, encoding='utf-16', rdf_version='1.2', **kwargs)
    triple = (URIRef('urn:s'), URIRef('urn:p'), Literal('v'))
    target.add(triple)
    target.add(triple)
    target.close()
    before = output.getvalue()
    target.close()
    assert output.getvalue() == before
    assert '\ufeff' not in before.decode('utf-16')
    assert not output.closed


def test_incremental_output_finalizes_stateful_codec_without_closing_the_sink():
    from rdfcore.serializer import _IncrementalOutput
    sink = BytesIO()
    output = _IncrementalOutput(sink, 'iso2022_jp', False)
    output.write('日本語')
    assert sink.getvalue() != '日本語'.encode('iso2022_jp')
    output.finish()
    assert sink.getvalue() == '日本語'.encode('iso2022_jp')
    output.finish()
    assert sink.getvalue() == '日本語'.encode('iso2022_jp')
    assert not sink.closed
