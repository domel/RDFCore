from io import BytesIO

import pytest

from rdfcore.tokenizer import ChunkReader, TokenReader


class NoUnboundedRead:
    def __init__(self, data):
        self.stream = BytesIO(data)
        self.calls = []

    def read(self, size=-1):
        self.calls.append(size)
        if size < 0 or size > 3:
            raise AssertionError("unbounded read")
        return self.stream.read(size)


def test_chunk_reader_decodes_utf8_split_between_chunks():
    source = NoUnboundedRead("<urn:ą>".encode())
    assert "".join(ChunkReader(source, chunk_size=3)) == "<urn:ą>"
    assert all(size == 3 for size in source.calls)


@pytest.mark.parametrize("text", [
    "<urn:subject> ex:p \"short\" .",
    "<urn:subject> ex:p \"\"\"long literal\"\"\" .",
    "<urn:subject> ex:p \"escaped \\\" value\" .",
    "@prefix ex: <urn:> . # comment",
    "ex:name.with.dots ex:p 'single' .",
    "ex:s ex:p '''long single literal''' .",
])
def test_tokens_survive_one_character_chunks(text):
    tokens = list(TokenReader(NoUnboundedRead(text.encode()), chunk_size=1))
    values = [token.value for token in tokens if token.kind not in ("whitespace", "comment")]
    assert values
    assert all(token.line >= 1 and token.column >= 1 for token in tokens)


def test_token_reader_reports_unterminated_iri():
    with pytest.raises(ValueError, match="unterminated IRI"):
        list(TokenReader(NoUnboundedRead(b"<urn:x"), chunk_size=2))
