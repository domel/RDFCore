from rdfcore import Graph, URIRef


def test_graph_basic_api():
    graph = Graph()
    assert graph.qname("http://www.w3.org/1999/02/22-rdf-syntax-ns#type") == "rdf:type"
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/p")
    o = URIRef("http://example.org/o")
    graph.add((s, p, o)).add((s, p, o))
    assert len(graph) == 1
    assert (s, p, o) in graph
    assert list(graph.objects(s, p)) == [o]
    assert graph.value(s, p) == o
    assert list(graph.subjects(p, o)) == [s]


def test_graph_namespaces_and_set():
    graph = Graph()
    graph.bind("ex", "http://example.org/")
    assert graph.qname("http://example.org/item") == "ex:item"
    s, p = URIRef("http://example.org/s"), URIRef("http://example.org/p")
    old, new = URIRef("http://example.org/old"), URIRef("http://example.org/new")
    graph.add((s, p, old)).set((s, p, new))
    assert list(graph.objects(s, p)) == [new]


def test_graph_addn_uses_only_its_own_context():
    graph = Graph()
    other = Graph(store=graph.store)
    triple = (URIRef("http://example.org/s"), URIRef("http://example.org/p"), URIRef("http://example.org/o"))
    graph.addN([(*triple, other), (*triple, graph)])
    assert list(graph) == [triple]
    assert list(other) == []
