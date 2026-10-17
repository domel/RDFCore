"""Executable Collection oracle: RDFLib 7.6.0, including upstream quirks."""

from itertools import count
import inspect
from unittest.mock import patch

import pytest
import rdflib
import rdflib.collection
import rdfcore
import rdfcore.collection


def observe(module, size, operation, key=0, shape="normal"):
    graph = module.Graph()
    head = module.URIRef("urn:list") if shape != "nil" else module.RDF.nil
    serial = count()
    factory = lambda: module.BNode("cell%d" % next(serial))
    with patch.object(module.collection, "BNode", factory):
        collection = module.collection.Collection(
            graph, head, [module.Literal(str(i)) for i in range(size)]
        )
        if shape == "unterminated":
            graph.remove((collection._end(), module.RDF.rest, None))
        elif shape == "missing-first":
            graph.remove((head, module.RDF.first, None))
        elif shape == "false-first":
            graph.set((head, module.RDF.first, module.Literal("")))
        elif shape == "metadata":
            graph.add((head, module.URIRef("urn:label"), module.Literal("keep")))
        def run():
            if operation == "get":
                return collection[key]
            if operation == "set":
                return collection.__setitem__(key, module.Literal("new"))
            if operation == "delete":
                return collection.__delitem__(key)
            if operation == "container":
                return collection._get_container(key)
            if operation == "index":
                return collection.index(module.Literal(str(key)))
            if operation == "append":
                return collection.append(module.Literal("new"))
            if operation == "iadd":
                return collection.__iadd__([module.Literal("new"), module.Literal("new")])
            if operation == "empty-iadd":
                return collection.__iadd__([])
            if operation == "invalid-iadd":
                return collection.__iadd__(None)
            if operation == "clear":
                collection.clear()
                return collection.clear()
            if operation == "n3":
                return collection.n3()
            if operation == "iterate":
                return tuple(collection)
            return collection._end()
        def encode(value):
            if value is collection:
                return "self"
            if isinstance(value, tuple):
                return tuple(encode(item) for item in value)
            if isinstance(value, (module.URIRef, module.BNode, module.Literal)):
                return (type(value).__name__, value.n3())
            return (type(value).__name__, value)
        try:
            outcome = ("return", encode(run()))
        except Exception as error:
            outcome = ("error", type(error).__name__, str(error))
        triples = sorted(tuple(encode(term) for term in triple) for triple in graph)
        return outcome, triples


@pytest.mark.parametrize("size", [0, 1, 3])
@pytest.mark.parametrize("key", [-4, -1, 0, 1, 2, 3, 4, True, "0", None, slice(0, 1)])
@pytest.mark.parametrize("operation", ["get", "set", "delete", "container", "index"])
def test_index_matrix(size, key, operation):
    assert observe(rdfcore, size, operation, key) == observe(rdflib, size, operation, key)


@pytest.mark.parametrize("size", [0, 1, 3])
@pytest.mark.parametrize("shape", ["normal", "unterminated", "missing-first", "false-first", "metadata"])
@pytest.mark.parametrize("operation", ["append", "iadd", "empty-iadd", "invalid-iadd", "clear", "n3", "iterate", "end"])
def test_mutation_matrix(size, shape, operation):
    assert observe(rdfcore, size, operation, shape=shape) == observe(rdflib, size, operation, shape=shape)


@pytest.mark.parametrize("operation", ["append", "iadd", "empty-iadd", "invalid-iadd", "get", "set", "delete", "clear", "iterate"])
def test_nil_matrix(operation):
    assert observe(rdfcore, 0, operation, shape="nil") == observe(rdflib, 0, operation, shape="nil")


def test_constructor_requires_uri_and_pinned_oracle():
    assert rdflib.__version__ == "7.6.0"
    for module in (rdfcore, rdflib):
        with pytest.raises(TypeError):
            module.collection.Collection(module.Graph())


@pytest.mark.parametrize("kind", ["none", "empty", "false", "generator", "failing-generator"])
def test_constructor_inputs_and_partial_generator_failure(kind):
    def run(module):
        graph = module.Graph()
        head = module.URIRef("urn:list")
        def values():
            yield module.Literal("one")
            if kind == "failing-generator":
                raise RuntimeError("source failed")
        seq = {"none": None, "empty": [], "false": False}.get(kind)
        if "generator" in kind:
            seq = values()
        try:
            collection = module.collection.Collection(graph, head, seq)
            result = ("ok", [str(item) for item in collection])
        except Exception as error:
            result = (type(error).__name__, str(error))
        return result, sorted(tuple(term.n3() for term in triple) for triple in graph)
    assert run(rdfcore) == run(rdflib)


@pytest.mark.parametrize("operation", ["append", "iadd", "clear", "delete"])
def test_named_graph_isolation(operation):
    def run(module):
        dataset = module.Dataset()
        graph = dataset.graph(module.URIRef("urn:selected"))
        other = dataset.graph(module.URIRef("urn:other"))
        head = module.URIRef("urn:list")
        collection = module.collection.Collection(graph, head, [module.Literal("one")])
        module.collection.Collection(other, head, [module.Literal("untouched")])
        if operation == "append":
            collection.append(module.Literal("two"))
        elif operation == "iadd":
            collection += [module.Literal("two")]
        elif operation == "clear":
            collection.clear()
        else:
            del collection[0]
        return [str(item) for item in collection], [str(item) for item in other.items(head)], len(graph), len(other)
    assert run(rdfcore) == run(rdflib)


@pytest.mark.parametrize("operation", ["index", "iterate", "clear"])
def test_malformed_collection(operation):
    def run(module):
        graph = module.Graph()
        head = module.URIRef("urn:list")
        collection = module.collection.Collection(graph, head)
        graph.add((head, module.RDF.first, module.Literal("one")))
        # Two rest links are malformed for index(), but clear() must remove both.
        graph.add((head, module.RDF.rest, module.RDF.nil))
        graph.add((head, module.RDF.rest, module.URIRef("urn:tail")))
        try:
            if operation == "index":
                collection.index(module.Literal("missing"))
            elif operation == "iterate":
                # Multiple links have no defined traversal order: test separately below.
                graph.remove((head, module.RDF.rest, module.RDF.nil))
                graph.set((head, module.RDF.rest, head))
                list(collection)
            else:
                collection.clear()
            outcome = None
        except Exception as error:
            outcome = type(error).__name__, str(error)
        return outcome, len(graph)
    assert run(rdfcore) == run(rdflib)


def test_clear_recursive_chain_terminates_and_preserves_metadata():
    for module in (rdfcore, rdflib):
        graph = module.Graph()
        head = module.URIRef("urn:list")
        graph.add((head, module.RDF.first, module.Literal("one")))
        graph.add((head, module.RDF.rest, head))
        graph.add((head, module.URIRef("urn:label"), module.Literal("keep")))
        collection = module.collection.Collection(graph, head)
        assert collection.clear() is collection
        assert list(graph) == [(head, module.URIRef("urn:label"), module.Literal("keep"))]


@pytest.mark.parametrize("name", ["__init__", "__getitem__", "__setitem__", "__delitem__", "__iadd__", "append", "index", "_get_container", "_end", "clear", "n3"])
def test_call_signatures(name):
    def signature(cls):
        return [(p.name, p.kind, p.default) for p in inspect.signature(getattr(cls, name)).parameters.values()]
    assert signature(rdfcore.Collection) == signature(rdflib.collection.Collection)


@pytest.mark.parametrize("value", [None, "plain string", 123])
@pytest.mark.parametrize("operation", ["append", "set", "iadd"])
def test_invalid_value_side_effects(value, operation):
    def run(module):
        graph = module.Graph()
        head = module.URIRef("urn:list")
        collection = module.collection.Collection(graph, head, [module.Literal("one")])
        serial = count()
        with patch.object(module.collection, "BNode", lambda: module.BNode("invalid%d" % next(serial))):
            try:
                if operation == "append":
                    collection.append(value)
                elif operation == "set":
                    collection[0] = value
                else:
                    collection += [value]
                error = None
            except Exception as exc:
                # Graph.add's assertion prose is outside Collection's contract.
                error = type(exc).__name__
        return error, sorted(tuple(term.n3() for term in triple) for triple in graph)
    assert run(rdfcore) == run(rdflib)
