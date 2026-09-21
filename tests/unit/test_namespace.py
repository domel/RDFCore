from rdfcore import Namespace, NamespaceManager, RDF, RDFS, XSD


def test_namespace_terms():
    ex = Namespace("http://example.org/")
    assert isinstance(ex, str)
    assert str(ex.person) == "http://example.org/person"
    assert ex["item"] == ex.item
    assert RDF.type.n3() == "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"
    assert str(RDFS.label).endswith("#label")
    assert str(XSD.integer).endswith("#integer")


def test_namespace_manager_qnames():
    manager = NamespaceManager()
    manager.bind("ex", Namespace("http://example.org/"))
    assert manager.qname("http://example.org/person") == "ex:person"
    assert manager.normalizeUri("http://other.example/item") == "<http://other.example/item>"
    assert manager.compute_qname("http://example.org/person") == ("ex", "http://example.org/", "person")


def test_rebinding_prefix_removes_stale_reverse_mapping():
    manager = NamespaceManager()
    manager.bind("ex", "http://old.example/")
    manager.bind("ex", "http://new.example/")
    assert manager.qname("http://new.example/item") == "ex:item"
    assert manager.normalizeUri("http://old.example/item") == "<http://old.example/item>"
