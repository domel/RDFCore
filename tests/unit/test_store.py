from rdfcore import Memory, URIRef


def test_memory_store_indexes_and_contexts():
    store = Memory()
    alice = URIRef("http://example.org/alice")
    knows = URIRef("http://example.org/knows")
    bob = URIRef("http://example.org/bob")
    context = URIRef("http://example.org/graph")
    triple = (alice, knows, bob)

    store.add(triple, context)
    assert len(store) == 1
    assert list(store.triples((alice, None, None), context))[0][0] == triple
    assert list(store.contexts(triple)) == [context]

    store.remove(triple, context)
    assert len(store) == 0
    assert list(store.contexts()) == []
