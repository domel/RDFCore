from io import BytesIO

import pytest

from rdfcore import Dataset, Graph, URIRef, benchmark_parse
from rdfcore.io import open_input, open_output
from rdfcore.streaming import BoundedReadStream, parse_stream


DATA = b'<urn:s> <urn:p> "o" .\n'


class NoUnboundedRead:
    def __init__(self, data):
        self._stream = BytesIO(data)
        self.calls = []

    def read(self, size=-1):
        self.calls.append(size)
        if size < 0 or size > 1:
            raise AssertionError("unbounded read")
        return self._stream.read(size)


@pytest.mark.parametrize("format", ["nt", "nquads", "turtle", "trig"])
def test_all_streaming_parsers_accept_bounded_reads(format):
    source = DATA if format in ("nt", "nquads") else b'<urn:s> <urn:p> "o" .\n'
    sink = type("Sink", (), {"add": lambda self, statement: None})()
    guarded = NoUnboundedRead(source)
    parse_stream(BoundedReadStream(guarded, chunk_size=1), format, sink)
    assert guarded.calls and all(0 <= size <= 1 for size in guarded.calls)


@pytest.mark.parametrize("compression", ["gz", "bz2", "xz"])
def test_streaming_compression_round_trip(compression):
    import io

    output = io.BytesIO()
    writer, owned = open_output(output, compression=compression, buffer_size=2)
    writer.write(DATA)
    writer.close()
    reader, _ = open_input(io.BytesIO(output.getvalue()), compression=compression, buffer_size=2)
    assert reader.read() == DATA


def test_convert_path_does_not_construct_graph_or_dataset(monkeypatch):
    from rdfcore import pipeline

    monkeypatch.setattr(pipeline, "Graph", None, raising=False)
    monkeypatch.setattr(pipeline, "Dataset", None, raising=False)
    output = BytesIO()
    pipeline.convert(BytesIO(DATA), output, input_format="nt", output_format="nt")
    assert output.getvalue() == DATA


def test_benchmark_reports_streaming_metrics():
    result = benchmark_parse(BytesIO(DATA), "nt", buffer_size=1)
    assert result["statements"] == 1
    assert result["statements_per_second"] > 0
    assert "peak_rss_bytes" in result


@pytest.mark.parametrize('format', ['nt', 'nquads'])
def test_short_record_streaming_rss_does_not_scale_with_input(tmp_path, format):
    import json
    import subprocess
    import sys
    pytest.importorskip('resource')
    records = []
    line = DATA if format == 'nt' else b'<urn:s> <urn:p> "o" <urn:g> .\n'
    for size in (10000, 100000):
        path = tmp_path / f'{size}.rdf'
        with path.open('wb') as handle:
            for _ in range(size):
                handle.write(line)
        result = subprocess.run([sys.executable, '-m', 'tests.streaming.memory_probe', str(path), format],
                                check=True, capture_output=True, text=True, timeout=30)
        record = json.loads(result.stdout)
        assert record['statements'] == size
        assert record['unit'] == 'bytes'
        assert record['peak_rss_bytes'] > 0
        records.append(record)
    # Fresh interpreters have different startup peaks. 16 MiB allows that
    # noise but rejects retaining 100k newly parsed statements in a list.
    assert records[1]['peak_rss_bytes'] - records[0]['peak_rss_bytes'] < 16 * 1024 * 1024, records
