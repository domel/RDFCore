from io import StringIO

from rdfcore import Graph, Parser, Serializer, URIRef, Literal, plugin
from rdfcore.exceptions import PluginException


class DemoParser(Parser):
    def parse(self, source, sink, **kwargs):
        sink.add((URIRef("http://example.org/s"), URIRef("http://example.org/p"), Literal("ok")))
        return sink


class DemoSerializer(Serializer):
    def serialize(self, stream=None, **kwargs):
        result = "demo"
        if stream is not None:
            stream.write(result)
            return stream
        return result


def test_plugin_registry_and_graph_plumbing():
    plugin.register("demo", Parser, DemoParser)
    plugin.register("demo", Serializer, DemoSerializer)
    graph = Graph().parse(data="ignored", format="demo")
    assert len(graph) == 1
    assert graph.serialize(format="demo") == "demo"
    output = StringIO()
    assert graph.serialize(output, format="demo") is graph


def test_missing_plugin_is_explicit():
    try:
        plugin.get("missing", Parser)
    except PluginException:
        pass
    else:
        raise AssertionError("missing plugin did not raise PluginException")
