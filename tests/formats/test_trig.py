from rdfcore import Dataset, Literal, RDF, URIRef


def test_trig_parser_default_and_named_graphs():
    dataset = Dataset().parse(data='''
        @prefix ex: <http://example.org/> .
        { ex:s ex:p "default" . }
        GRAPH ex:g { ex:s ex:p "named" . }
        ex:h { ex:s ex:p ( ex:a ex:b ) . }
    ''', format="trig")
    assert list(dataset.default_graph.objects(URIRef("http://example.org/s"), URIRef("http://example.org/p"))) == [Literal("default")]
    assert list(dataset.graph(URIRef("http://example.org/g")))
    head = dataset.graph(URIRef("http://example.org/h")).value(URIRef("http://example.org/s"), URIRef("http://example.org/p"))
    assert dataset.graph(URIRef("http://example.org/h")).value(head, RDF.first) == URIRef("http://example.org/a")
