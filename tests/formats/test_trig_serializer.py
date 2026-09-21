from io import StringIO

from rdfcore import Dataset, Literal, TriGSerializer, URIRef


def test_trig_serializer_round_trip_default_and_named_graphs():
    dataset = Dataset()
    subject = URIRef("http://e/s")
    predicate = URIRef("http://e/p")
    dataset.add((subject, predicate, Literal("default")))
    dataset.add((subject, predicate, Literal("named"), URIRef("http://e/g")))
    output = dataset.serialize(format="trig")
    assert "{" in output and "<http://e/g> {" in output
    reparsed = Dataset().parse(data=output, format="trig")
    assert set(reparsed.quads()) == set(dataset.quads())


def test_trig_serializer_destination_is_supported():
    dataset = Dataset()
    dataset.add((URIRef("http://e/s"), URIRef("http://e/p"), Literal("x")))
    stream = StringIO()
    assert dataset.serialize(stream, format="trig") is dataset
    assert stream.getvalue().startswith("@prefix")
