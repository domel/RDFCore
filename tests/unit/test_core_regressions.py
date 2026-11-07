import pytest

from rdfcore import ClosedNamespace, URIRef
from rdfcore.namespace import NamespaceManager


def test_closed_namespace_and_invalid_qname_local_name():
    ns = ClosedNamespace("http://example.org/", ["allowed"])
    assert str(ns.allowed) == "http://example.org/allowed"
    with pytest.raises(AttributeError):
        ns.other
    manager = NamespaceManager()
    manager.bind("ex", "http://example.org/")
    with pytest.raises(ValueError):
        manager.qname("http://example.org/_ contains-space")
    assert NamespaceManager().compute_qname("http://example.org/0invalid") == (
        "ns1",
        URIRef("http://example.org/"),
        "0invalid",
    )


def test_python_compatibility_helpers():
    from rdfcore.compat import binary_type, is_py3, iteritems, string_types, text_type

    assert is_py3()
    assert text_type is str
    assert binary_type is bytes
    assert isinstance("x", string_types)
    assert list(iteritems({"x": 1})) == [("x", 1)]
