import pytest

from rdfcore import Dataset, Graph, Parser, Serializer, PluginException, URIRef
from rdfcore.plugin import plugins


def test_all_supported_aliases_are_registered_for_parser_and_serializer():
    parser_names = {plugin.name for plugin in plugins(Parser)}
    serializer_names = {plugin.name for plugin in plugins(Serializer)}
    expected = {
        "nt", "ntriples", "nt11", "application/n-triples",
        "nquads", "application/n-quads",
        "turtle", "ttl", "text/turtle",
        "trig", "application/trig",
    }
    assert expected <= parser_names
    assert expected <= serializer_names
    assert not parser_names.intersection({"nq", "n-triples", "n-quads"})
    assert not serializer_names.intersection({"nq", "n-triples", "n-quads"})


def test_dataset_parse_and_serialize_are_integrated_for_nquads_and_trig():
    source = '<http://e/s> <http://e/p> <http://e/o> <http://e/g> .\n'
    dataset = Dataset().parse(data=source, format="application/n-quads")
    assert dataset.serialize(format="application/n-quads")
    trig = dataset.serialize(format="application/trig")
    reparsed = Dataset().parse(data=trig, format="trig")
    assert set(reparsed.quads()) == set(dataset.quads())


def test_graph_parse_and_serialize_are_integrated_for_mime_aliases():
    source = '<http://e/s> <http://e/p> "x" .\n'
    graph = Graph().parse(data=source, format="application/n-triples")
    assert graph.serialize(format="nt11")


def test_integration_preserves_public_exception_types():
    with pytest.raises(PluginException):
        Graph().parse(data="", format="xml")
    with pytest.raises(PluginException):
        Graph().serialize(format="json-ld")
