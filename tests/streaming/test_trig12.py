from io import BytesIO

from rdfcore import Literal, RDF, TripleTerm, URIRef
from rdfcore.streaming import BoundedReadStream, parse_stream


class Sink:
    def __init__(self):
        self.statements = []

    def add(self, statement):
        self.statements.append(statement)


def test_trig12_rdf12_features_survive_one_byte_chunks_and_graph_scope():
    data = b'''VERSION "1.2"\n
        @prefix : <urn:> .
        { :default :p "d" . }
        :g {
          :s :p "x"@en--rtl .
          :s :q <<( :a :b <<( :c :d :e )>> )>> .
          :s :r :o ~ :statement {| :source :doc |} .
        }
    '''
    sink = Sink()
    parse_stream(BoundedReadStream(BytesIO(data), chunk_size=1), "trig12", sink)
    default = [statement for statement in sink.statements if len(statement) == 3]
    named = [statement for statement in sink.statements if len(statement) == 4]
    assert default[0][0] == URIRef("urn:default")
    assert len(named) == 5
    assert named[0][3] == URIRef("urn:g")
    assert any(isinstance(statement[2], Literal) and statement[2].direction == "rtl" for statement in named)
    assert any(isinstance(statement[2], TripleTerm) and isinstance(statement[2].object, TripleTerm) for statement in named)
    assert any(statement[1] == RDF.reifies and statement[0] == URIRef("urn:statement") for statement in named)
