from io import BytesIO
import os

import pytest

from rdfcore.io import BoundedWriteStream
from rdfcore.pipeline import convert

DATA = b'<urn:s> <urn:p> "hello" .\n'


@pytest.mark.parametrize('link', ['same', 'symlink', 'hardlink'])
def test_convert_refuses_same_file_without_modifying_it(tmp_path, link):
    source = tmp_path / 'source.nt'
    source.write_bytes(DATA)
    destination = source if link == 'same' else tmp_path / 'alias.nt'
    if link == 'symlink': destination.symlink_to(source)
    if link == 'hardlink': os.link(source, destination)
    with pytest.raises(ValueError, match='same file'):
        convert(source, destination, input_format='nt', output_format='nt')
    assert source.read_bytes() == destination.read_bytes() == DATA


@pytest.mark.parametrize('case', ['missing', 'buffer', 'policy', 'float_buffer', 'none_buffer'])
def test_preflight_failure_does_not_truncate_output(tmp_path, case):
    destination, source = tmp_path / 'out.nt', tmp_path / 'in.nq'
    destination.write_bytes(b'previous data')
    source.write_bytes(DATA)
    kwargs = {'buffer': {'buffer_size': 0}, 'policy': {'dataset_policy': 'bad'},
              'float_buffer': {'buffer_size': 1.5}, 'none_buffer': {'buffer_size': None}}.get(case, {})
    if case == 'missing': source = tmp_path / 'missing.nq'
    error = FileNotFoundError if case == 'missing' else TypeError if case in ('float_buffer', 'none_buffer') else ValueError
    with pytest.raises(error):
        convert(source, destination, input_format='nquads', output_format='nt', **kwargs)
    assert destination.read_bytes() == b'previous data'


class ShortWriter:
    def __init__(self): self.data = bytearray()
    def write(self, data):
        self.data.extend(data[:2])
        return min(2, len(data))
    def flush(self): pass


def test_bounded_write_retries_partial_chunks():
    sink = ShortWriter()
    assert BoundedWriteStream(sink, chunk_size=5).write(b'abcdefghij') == 10
    assert sink.data == b'abcdefghij'


@pytest.mark.parametrize('result', [0, None, -1, 100, 'wrong'])
def test_bounded_write_rejects_invalid_progress(result):
    class Sink:
        def write(self, data): return result
    with pytest.raises((OSError, TypeError)):
        BoundedWriteStream(Sink()).write(b'abc')


@pytest.mark.parametrize('format', ['nt', 'nt12', 'nquads', 'nq12'])
def test_convert_completes_partial_writes(format):
    sink = ShortWriter()
    convert(BytesIO(DATA), sink, input_format='nt', output_format=format)
    assert bytes(sink.data) == (b'VERSION "1.2"\n' if format.endswith('12') else b'') + DATA


@pytest.mark.parametrize('compression', ['gz', 'bz2', 'xz'])
def test_compression_also_completes_partial_underlying_writes(compression):
    import bz2, gzip, lzma
    sink = ShortWriter()
    convert(BytesIO(DATA), sink, input_format='nt', output_format='nt', output_compression=compression)
    codec = {'gz': gzip, 'bz2': bz2, 'xz': lzma}[compression]
    assert codec.decompress(sink.data) == DATA


def test_same_file_detection_includes_open_handles(tmp_path):
    path = tmp_path / 'data.nt'
    path.write_bytes(DATA)
    with path.open('r+b') as stream:
        with pytest.raises(ValueError, match='same file'):
            convert(stream, path, input_format='nt', output_format='nt')
    assert path.read_bytes() == DATA


def test_custom_sink_cleanup_still_precedes_owned_input_close(monkeypatch):
    from rdfcore import pipeline
    source = BytesIO(DATA)
    monkeypatch.setattr(pipeline, 'open_input', lambda *args, **kwargs: (source, True))
    class Sink:
        def add(self, statement): pass
        def close(self): assert not source.closed
    convert(source, input_format='nt', output_format='nt', sink=Sink())
    assert source.closed


@pytest.mark.parametrize('source', [None, '-'])
def test_redirected_stdin_cannot_be_truncated(tmp_path, monkeypatch, source):
    import sys
    path = tmp_path / 'input.nt'
    path.write_bytes(DATA)
    with path.open('rb') as stream:
        monkeypatch.setattr(sys, 'stdin', stream)
        with pytest.raises(ValueError, match='same file'):
            convert(source, path, input_format='nt', output_format='nt')
    assert path.read_bytes() == DATA
