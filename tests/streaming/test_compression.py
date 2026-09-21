import gzip
from io import BytesIO

from rdfcore.io import BoundedWriteStream, open_input, open_output


def test_gzip_input_and_output_are_streaming_file_like_objects():
    payload = b'<urn:s> <urn:p> "o" .\n'
    compressed = gzip.compress(payload)
    reader, owns_reader = open_input(BytesIO(compressed), compression="gz", buffer_size=3)
    assert reader.read() == payload
    assert not owns_reader
    reader.close()

    output = BytesIO()
    writer, owns_writer = open_output(output, compression="gz", buffer_size=2)
    writer.write(payload)
    writer.close()
    assert gzip.decompress(output.getvalue()) == payload
    assert not owns_writer


def test_bounded_writer_limits_each_underlying_write():
    class Sink:
        def __init__(self):
            self.writes = []
        def write(self, data):
            self.writes.append(data)
            return len(data)

    target = Sink()
    writer = BoundedWriteStream(target, chunk_size=2)
    writer.write(b"abcdef")
    assert target.writes == [b"ab", b"cd", b"ef"]
