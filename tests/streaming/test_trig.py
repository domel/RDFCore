from io import BytesIO

from rdfcore import BoundedReadStream, Literal, URIRef
from rdfcore.streaming import parse_stream


class Sink:
    def __init__(self):
        self.statements = []

    def add(self, statement):
        self.statements.append(statement)


def test_trig_streaming_parser_preserves_default_and_named_graphs():
    data = b'''@prefix : <urn:> .
        { :s :p "default" . }
        :g { :s :p "named" . }
    '''
    sink = Sink()
    parse_stream(BoundedReadStream(BytesIO(data), chunk_size=1), "trig", sink)
    assert (URIRef("urn:s"), URIRef("urn:p"), Literal("default", normalize=False)) in sink.statements
    named = [statement for statement in sink.statements if len(statement) == 4]
    assert named[0][3] == URIRef("urn:g")
    assert named[0][2] == Literal("named", normalize=False)
