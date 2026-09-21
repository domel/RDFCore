from rdfcore import Collection, Graph, Literal, RDF, Resource, URIRef


def test_collection_supports_common_list_operations():
    graph = Graph()
    collection = Collection(graph, URIRef("urn:list"), [Literal("a"), Literal("b")])
    assert list(collection) == [Literal("a"), Literal("b")]
    collection.append(Literal("c"))
    assert collection.index(Literal("b")) == 1
    collection[1] = Literal("changed")
    assert collection[1] == Literal("changed")
    del collection[0]
    assert list(collection) == [Literal("changed"), Literal("c")]
    collection += [Literal("d")]
    assert list(collection)[-1] == Literal("d")
    assert collection.clear() is collection
    assert list(collection) == []


def test_resource_wraps_graph_operations():
    graph = Graph()
    subject = URIRef("urn:s")
    resource = graph.resource(subject)
    resource.add(URIRef("urn:p"), Literal("value"))
    assert list(resource.objects(URIRef("urn:p"))) == [Literal("value")]
    assert resource.value(URIRef("urn:p")) == Literal("value")
    assert resource.identifier == subject


def test_resource_matches_mutation_and_index_protocol():
    graph = Graph()
    resource = graph.resource(URIRef("urn:s"))
    predicate = URIRef("urn:p")
    assert resource.add(predicate, Literal("one")) is None
    resource[predicate] = Literal("two")
    assert list(resource[predicate]) == [Literal("two")]
    assert str(resource) == "Resource(urn:s)"
    with __import__("pytest").raises(TypeError):
        resource[1]
