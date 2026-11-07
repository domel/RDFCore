"""ConjunctiveGraph parsing and output semantics against the pinned oracle."""

import io

import pytest
import rdflib
import rdfcore

from .test_conjunctive_graph import normalized


FORMATS = [
    ("nt", "nt11"),
    ("turtle", "turtle11"),
    ("trig", "trig11"),
    ("nquads", "nq11"),
    ("xml", "xml"),
]


@pytest.mark.parametrize("reference,core", FORMATS)
@pytest.mark.parametrize("encoding", [None, "utf-8"])
def test_serialize_and_parse(reference, core, encoding):
    outcomes = []
    for module, fmt in [(rdflib, reference), (rdfcore, core)]:
        graph = module.ConjunctiveGraph(identifier=module.URIRef("urn:default"))
        triple = tuple(module.URIRef("urn:" + x) for x in "spo")
        graph.add(triple)
        graph.get_context(module.URIRef("urn:named")).add(
            (triple[2], triple[1], triple[0])
        )
        value = graph.serialize(format=fmt, encoding=encoding)
        assert isinstance(value, bytes if encoding else str)
        # Parse independently with the oracle, so a shared reader/writer bug
        # cannot conceal a change of graph boundaries.
        parsed = rdflib.ConjunctiveGraph(identifier=rdflib.URIRef("urn:default"))
        parsed.parse(data=value, format=reference)
        outcomes.append(normalized(parsed.quads()))
        destination = io.BytesIO()
        assert graph.serialize(destination, format=fmt, encoding="utf-8") is graph
        assert not destination.closed
        assert destination.getvalue()
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("reference,core", FORMATS)
def test_parse_return_default_and_public_id(reference, core):
    source = rdflib.ConjunctiveGraph(identifier=rdflib.URIRef("urn:default"))
    source.add((rdflib.URIRef("urn:s"), rdflib.URIRef("urn:p"), rdflib.Literal("v")))
    source.get_context(rdflib.URIRef("urn:named")).add(
        (rdflib.URIRef("urn:n"), rdflib.URIRef("urn:p"), rdflib.Literal("v"))
    )
    data = source.serialize(format=reference)
    outcomes = []
    for module, fmt in [(rdflib, reference), (rdfcore, core)]:
        graph = module.ConjunctiveGraph(identifier=module.URIRef("urn:default"))
        assert (
            graph.parse(data=data, format=fmt, publicID="https://example.org/base/")
            is graph
        )
        outcomes.append(normalized(graph.quads()))
        assert module.URIRef("https://example.org/base/") not in {
            g.identifier for g in graph.contexts()
        }
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("reference,core", [("turtle", "turtle11"), ("xml", "xml")])
def test_relative_base_and_input_ownership(reference, core):
    text = (
        "<s> <p> <o> ."
        if reference == "turtle"
        else '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:e="https://example.org/">'
        '<rdf:Description rdf:about="s"><e:p rdf:resource="o"/></rdf:Description></rdf:RDF>'
    )
    outcomes = []
    for module, fmt in [(rdflib, reference), (rdfcore, core)]:
        graph = module.ConjunctiveGraph(
            identifier=module.URIRef("urn:default"),
            default_graph_base="https://default.example/",
        )
        stream = io.BytesIO(text.encode())
        stream.name = "input.rdf"
        graph.parse(file=stream, publicID="https://document.example/", format=fmt)
        outcomes.append((normalized(graph.quads()), stream.closed))
    assert outcomes[0] == outcomes[1]


def test_replaced_default_context_parses_into_its_own_store():
    for module, fmt in [(rdflib, "turtle"), (rdfcore, "turtle11")]:
        graph = module.ConjunctiveGraph()
        foreign = module.Graph(identifier=module.URIRef("urn:foreign"))
        graph.default_context = foreign
        assert graph.parse(data="<urn:s> <urn:p> <urn:o> .", format=fmt) is graph
        assert len(foreign) == 1
        assert len(graph) == 0
