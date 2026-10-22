"""XML12 selects text/bytes before writing; a sink failure is never retried."""
from io import BytesIO, StringIO, TextIOWrapper
from xml.etree import ElementTree

import pytest

from rdfcore import Graph, Literal, URIRef
from rdfcore.plugins.serializers.rdfxml import XML12Serializer


def graph():
    return Graph().add((URIRef('urn:s'), URIRef('urn:p'), Literal('é😀')))


@pytest.mark.parametrize('direct', [False, True])
@pytest.mark.parametrize('text', [None, False, True])
@pytest.mark.parametrize('error_type', [TypeError, OSError])
def test_partial_sink_error_is_propagated_once_with_original_identity(direct, text, error_type):
    original = error_type('sink failed after accepting a prefix')
    class Sink:
        calls = 0
        accepted = None
        def write(self, data):
            self.calls += 1
            assert isinstance(data, str if text else bytes)
            self.accepted = data[:10]
            raise original
    sink = Sink()
    with pytest.raises(error_type) as caught:
        if direct:
            XML12Serializer(graph()).serialize(sink, text_output=text)
        else:
            graph().serialize(sink, format='xml12', text_output=text)
    assert caught.value is original
    assert sink.calls == 1
    assert sink.accepted == ('<?xml vers' if text else b'<?xml vers')


@pytest.mark.parametrize('factory', [BytesIO, StringIO])
@pytest.mark.parametrize('encoding', [None, 'utf-8', 'utf-16'])
def test_standard_streams_are_selected_without_a_probe_and_stay_open(factory, encoding):
    class Sink(factory):
        calls = 0
        def write(self, data):
            self.calls += 1
            return super().write(data)
    sink = Sink()
    value = graph()
    assert value.serialize(sink, format='xml12', encoding=encoding) is value
    assert sink.calls == 1 and not sink.closed
    assert ElementTree.fromstring(sink.getvalue()).find('.//{urn:}p').text == 'é😀'


def test_text_io_wrapper_is_detected_and_not_closed():
    raw = BytesIO()
    sink = TextIOWrapper(raw, encoding='utf-8')
    try:
        graph().serialize(sink, format='xml12')
        sink.flush()
        assert ElementTree.fromstring(raw.getvalue()).find('.//{urn:}p').text == 'é😀'
        assert not sink.closed and not raw.closed
    finally:
        sink.detach()


def test_custom_text_sink_has_an_explicit_protocol():
    class Sink:
        data = ''
        calls = 0
        def write(self, value):
            assert isinstance(value, str)
            self.calls += 1
            self.data += value
    sink = Sink()
    assert XML12Serializer(graph()).serialize(sink, text_output=True) is None
    assert sink.calls == 1
    assert ElementTree.fromstring(sink.data).find('.//{urn:}p').text == 'é😀'


@pytest.mark.parametrize('value', ['text', 1, 0])
def test_text_output_requires_boolean_or_none_before_writing(value):
    sink = BytesIO()
    with pytest.raises(ValueError, match='text_output'):
        graph().serialize(sink, format='xml12', text_output=value)
    assert sink.getvalue() == b'' and not sink.closed


def test_text_stream_still_checks_requested_codec_before_writing():
    sink = StringIO()
    with pytest.raises(LookupError):
        graph().serialize(sink, format='xml12', encoding='not-a-codec')
    assert sink.getvalue() == ''
