from io import StringIO

from rdfcore import DATASET_DEFAULT_GRAPH_ID, Dataset, Literal, NQuadsSerializer, URIRef


def test_nquads_serializer_omits_default_graph_label_and_round_trips():
    dataset = Dataset()
    subject = URIRef("http://e/s")
    predicate = URIRef("http://e/p")
    dataset.add((subject, predicate, Literal("default")))
    dataset.add((subject, predicate, Literal("named"), URIRef("http://e/g")))
    output = dataset.serialize(format="nquads")
    assert '<http://e/g>' in output
    assert f'<{DATASET_DEFAULT_GRAPH_ID}>' not in output
    reparsed = Dataset().parse(data=output, format="nquads")
    assert set(reparsed.quads()) == set(dataset.quads())


def test_nquads_serializer_is_deterministic_and_supports_destination():
    dataset = Dataset()
    dataset.add((URIRef("http://e/z"), URIRef("http://e/p"), Literal("z")))
    dataset.add((URIRef("http://e/a"), URIRef("http://e/p"), Literal("a")))
    first = dataset.serialize(format="nquads", canonical=True)
    second = dataset.serialize(format="nquads", canonical=True)
    assert first == second
    stream = StringIO()
    assert dataset.serialize(stream, format="nquads") is dataset
    assert stream.getvalue() == first
