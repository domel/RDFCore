"""Executable namespace comparisons against the pinned RDFLib oracle."""

import itertools

import pytest
import rdflib
import rdfcore


def manager(module):
    return module.Graph(bind_namespaces="none").namespace_manager


def bindings(nm, module):
    rows = list(nm.namespaces())
    assert all(type(uri) is module.URIRef for _, uri in rows)
    return [(prefix, str(uri)) for prefix, uri in rows]


@pytest.mark.parametrize("override,replace", itertools.product([False, True], repeat=2))
@pytest.mark.parametrize("initial,prefix,uri", [
    ([], "ex", "urn:a:"),
    ([("ex", "urn:a:")], "ex", "urn:a:"),
    ([("ex", "urn:a:")], "ex", "urn:b:"),
    ([("ex", "urn:a:")], "other", "urn:a:"),
    ([("ex", "urn:a:"), ("other", "urn:b:")], "ex", "urn:b:"),
    ([("ex", "urn:a:"), ("ex1", "urn:c:")], "ex", "urn:b:"),
    ([("", "urn:a:")], "", "urn:b:"),
    ([("_auto", "urn:a:")], "ex", "urn:a:"),
    ([], None, "urn:a:"),
])
def test_bind_matrix(initial, prefix, uri, override, replace):
    def observe(module):
        nm = manager(module)
        for p, ns in initial:
            nm.bind(p, ns)
        for _ in range(2):
            assert nm.bind(prefix, module.URIRef(uri), override=override, replace=replace) is None
        return bindings(nm, module)
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize("prefix", ["a b", " "])
def test_invalid_prefix(prefix):
    for module in (rdflib, rdfcore):
        nm = manager(module)
        with pytest.raises(KeyError, match="Prefixes may not contain spaces"):
            nm.bind(prefix, "urn:a:")
        assert bindings(nm, module) == []


@pytest.mark.parametrize("uri", [
    "https://e/a", "urn:example:thing", "https://e/123", "https://e/é",
    "https://e/a-b", "https://e/a%20b", "https://e/_a", "https://e/a:b",
    "https://e/", "", "relative", "https://e/bad iri", "https://e/a?x=1",
])
@pytest.mark.parametrize("generate", [False, True])
def test_compute_qname_matrix(uri, generate):
    def observe(module):
        nm = manager(module)
        try:
            prefix, namespace, local = nm.compute_qname(module.URIRef(uri), generate=generate)
        except Exception as error:
            return type(error).__name__, bindings(nm, module)
        assert type(namespace) is module.URIRef
        assert nm.compute_qname(uri, generate=False) == (prefix, namespace, local)
        return (prefix, str(namespace), local), bindings(nm, module)
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize("prefix", ["ex", ""])
@pytest.mark.parametrize("uri", ["https://e/a", "https://e/123", "https://e/", "https://e/sub/a"])
def test_bound_qnames(prefix, uri):
    def observe(module):
        nm = manager(module)
        nm.bind(prefix, "https://e/")
        try:
            return nm.qname(uri), nm.normalizeUri(module.URIRef(uri)), bindings(nm, module)
        except Exception as error:
            return type(error).__name__, bindings(nm, module)
    assert observe(rdfcore) == observe(rdflib)


def test_qname_generation_collision_and_cache():
    def observe(module):
        nm = manager(module)
        nm.bind("ns1", "urn:occupied:")
        first = nm.qname("https://e/a")
        nm.bind("renamed", "https://e/")
        return first, nm.qname("https://e/a"), nm.qname("https://e/b"), bindings(nm, module)
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize("variable", [False, True])
@pytest.mark.parametrize("value", ["x", "https://e/a", "https://e/123", "https://e/", "urn:a:b"])
@pytest.mark.parametrize("bound", [False, True])
def test_normalize_uri(variable, value, bound):
    def observe(module):
        nm = manager(module)
        if bound:
            nm.bind("ex", "https://e/")
        term = (module.Variable if variable else module.URIRef)(value)
        return nm.normalizeUri(rdfTerm=term), bindings(nm, module)
    assert observe(rdfcore) == observe(rdflib)


def test_longest_bound_namespace():
    def observe(module):
        nm = manager(module)
        nm.bind("ex", "https://e/")
        nm.bind("long", "https://e/abc")
        return nm.compute_qname("https://e/abcdef")[::2], nm.qname("https://e/abc")
    assert observe(rdfcore) == observe(rdflib)


@pytest.mark.parametrize("value", [None, 1, [], {}])
def test_qname_wrong_types(value):
    def observe(module):
        nm = manager(module)
        with pytest.raises(Exception) as error:
            nm.compute_qname(value)
        return type(error.value).__name__, nm.normalizeUri(value)
    assert observe(rdfcore) == observe(rdflib)


def test_qname_cache_preserves_input_term_identity():
    def observe(module):
        nm = manager(module)
        nm.bind("ex", "https://e/")
        first = nm.qname(module.URIRef("https://e/a"))
        nm.bind("other", "https://e/")
        return first, nm.qname("https://e/a"), nm.qname(module.URIRef("https://e/a"))
    assert observe(rdfcore) == observe(rdflib)
