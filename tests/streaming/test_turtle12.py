from io import BytesIO

from rdfcore import BNode, Literal, RDF, TripleTerm, URIRef
from rdfcore.streaming import BoundedReadStream, parse_stream


class Sink:
    def __init__(self):
        self.statements = []

    def add(self, statement):
        self.statements.append(statement)


def test_turtle12_features_survive_one_byte_chunks():
    data = b'''VERSION "1.2"\n
        @prefix : <urn:> .
        :s :p "hello"@en--ltr .
        :s :q <<( :a :b <<( :c :d :e )>> )>> .
        :s :r :o ~ :statement {| :source :doc |} .
    '''
    sink = Sink()
    parse_stream(BoundedReadStream(BytesIO(data), chunk_size=1), "turtle12", sink)
    directional = [statement for statement in sink.statements if isinstance(statement[2], Literal) and statement[2].direction]
    nested = [statement for statement in sink.statements if isinstance(statement[2], TripleTerm)]
    assert directional[0][2].direction == "ltr"
    assert nested[0][2].object.object == URIRef("urn:e")
    assert any(statement[1] == RDF.reifies for statement in sink.statements)
    assert any(statement[0] == URIRef("urn:statement") for statement in sink.statements)


def test_turtle12_streaming_preserves_reifier_blank_node():
    sink = Sink()
    parse_stream(
        BoundedReadStream(BytesIO(b'@prefix : <urn:> . :s :p :o ~ {| :source :doc |} .'), chunk_size=2),
        "turtle12",
        sink,
    )
    assert any(isinstance(subject, BNode) and predicate == RDF.reifies for subject, predicate, _ in sink.statements)
