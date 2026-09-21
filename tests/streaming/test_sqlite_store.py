from rdfcore import Dataset, Graph, Literal, SQLiteStore, URIRef


def test_sqlite_store_round_trips_graph_and_reopens(tmp_path):
    path = tmp_path / "data.sqlite"
    store = SQLiteStore(path)
    graph = Graph(store=store, identifier=URIRef("urn:g"))
    triple = (URIRef("urn:s"), URIRef("urn:p"), Literal("o"))
    graph.add(triple)
    assert list(graph) == [triple]
    graph.close()

    reopened = Graph(store=SQLiteStore(path), identifier=URIRef("urn:g"))
    assert list(reopened) == [triple]
    reopened.close()


def test_sqlite_store_keeps_named_graphs_separate(tmp_path):
    store = SQLiteStore(tmp_path / "dataset.sqlite")
    dataset = Dataset(store=store)
    triple = (URIRef("urn:s"), URIRef("urn:p"), Literal("o"))
    dataset.add((*triple, URIRef("urn:g")))
    dataset.add(triple)
    assert set(dataset.quads()) == {(*triple, URIRef("urn:g")), (*triple, dataset.identifier)}
    dataset.remove_graph(URIRef("urn:g"))
    assert list(dataset.quads()) == [(*triple, dataset.identifier)]
    dataset.close()


def test_sqlite_dataset_discovers_persisted_named_graphs(tmp_path):
    path = tmp_path / "persistent-dataset.sqlite"
    graph_id = URIRef("urn:g")
    triple = (URIRef("urn:s"), URIRef("urn:p"), Literal("o"))
    dataset = Dataset(store=SQLiteStore(path))
    dataset.add((*triple, graph_id))
    dataset.close()

    reopened = Dataset(store=SQLiteStore(path))
    assert list(reopened.quads()) == [(*triple, graph_id)]
    reopened.remove((None, None, None, None))
    assert list(reopened.quads()) == []
    reopened.close()


def test_sqlite_union_matches_memory_deduplication(tmp_path):
    store = SQLiteStore(tmp_path / "union.sqlite")
    triple = (URIRef("urn:s"), URIRef("urn:p"), Literal("o"))
    store.add(triple, URIRef("urn:g1"))
    store.add(triple, URIRef("urn:g2"))
    assert len(store) == 1
    assert [item for item, contexts in store.triples((None, None, None))] == [triple]
    store.close()
