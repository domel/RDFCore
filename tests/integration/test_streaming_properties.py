"""Generated RDF model invariants; not a substitute for W3C conformance.

Concepts CR 2026-04-07 §§3.1,3.6; Interop DNOTE 2026-07-23 §§3.1–3.3.
Seeds are deterministic; Hypothesis prints a replay blob and shrinks failures.
"""

import pytest
import rdflib
import rdfcore
from hypothesis import given, settings, strategies as st
from rdfcore.compare import isomorphic
from rdfcore.interop import basic_encode, basic_decode
from rdfcore.exceptions import ParserError

settings.register_profile(
    "rdfcore_bounded", max_examples=25, deadline=None, derandomize=True, print_blob=True
)
PROPERTY = settings.get_profile("rdfcore_bounded")
IRI = st.tuples(st.just("u"), st.integers(0, 4))
BNODE = st.tuples(st.just("b"), st.integers(0, 3))
SUBJECT = st.one_of(IRI, BNODE)
TEXT = st.text(alphabet='abc ż🙂\t\n\r"\\', max_size=12)
PLAIN = st.tuples(st.just("l"), TEXT, st.sampled_from([None, "en", "EN"]))
DIRECTION = st.tuples(st.just("d"), TEXT, st.sampled_from(["ltr", "rtl"]))
LEGACY_OBJECT = st.one_of(SUBJECT, PLAIN)
OBJECT = st.recursive(
    st.one_of(LEGACY_OBJECT, DIRECTION),
    lambda child: st.tuples(st.just("t"), SUBJECT, st.integers(0, 2), child),
    max_leaves=6,
)
ROWS = st.lists(st.tuples(SUBJECT, st.integers(0, 2), OBJECT), max_size=10)
LEGACY_ROWS = st.lists(
    st.tuples(SUBJECT, st.integers(0, 2), LEGACY_OBJECT), max_size=10
)


def term(module, descriptor):
    kind, *values = descriptor
    if kind == "u":
        return module.URIRef(f"urn:n{values[0]}")
    if kind == "b":
        return module.BNode(f"b{values[0]}")
    if kind == "l":
        return module.Literal(values[0], lang=values[1])
    if kind == "d":
        return module.Literal(values[0], lang="en", direction=values[1])
    return module.TripleTerm(
        term(module, values[0]),
        module.URIRef(f"urn:p{values[1]}"),
        term(module, values[2]),
    )


def triples(module, rows):
    return [
        (term(module, s), module.URIRef(f"urn:p{p}"), term(module, o))
        for s, p, o in rows
    ]


@pytest.mark.parametrize("format", ["nt12", "turtle12", "xml12"])
@pytest.mark.parametrize("sqlite", [False, True])
@PROPERTY
@given(rows=ROWS)
def test_generated_graph_roundtrip(rows, format, sqlite):
    store = rdfcore.SQLiteStore() if sqlite else rdfcore.Memory()
    graph = rdfcore.Graph(store=store)
    try:
        for row in triples(rdfcore, rows):
            graph.add(row)
        parsed = rdfcore.Graph().parse(
            data=graph.serialize(format=format), format=format
        )
        assert isomorphic(graph, parsed)
    finally:
        store.close()


@pytest.mark.parametrize("sqlite", [False, True])
@PROPERTY
@given(
    rows=ROWS,
    names=st.lists(
        st.sampled_from([None, "urn:g0", "urn:g1"]), min_size=10, max_size=10
    ),
)
def test_generated_dataset_roundtrip_and_interop(rows, names, sqlite):
    store = rdfcore.SQLiteStore() if sqlite else rdfcore.Memory()
    dataset = rdfcore.Dataset(store=store)
    try:
        dataset.graph(rdfcore.URIRef("urn:empty"))
        for triple, name in zip(triples(rdfcore, rows), names):
            graph = (
                dataset.default_graph
                if name is None
                else dataset.graph(term(rdfcore, name))
            )
            graph.add(triple)
        parsed = rdfcore.Dataset().parse(
            data=dataset.serialize(format="trig12"), format="trig12"
        )
        assert isomorphic(dataset, parsed)
        assert isomorphic(dataset, basic_decode(basic_encode(dataset)))
    finally:
        store.close()


def snapshot(graph):
    def node(value):
        return (
            type(value).__name__,
            str(value),
            getattr(value, "language", None),
            str(value.datatype)
            if getattr(value, "datatype", None) is not None
            else None,
        )

    return {tuple(node(item) for item in triple) for triple in graph}


@PROPERTY
@given(rows=LEGACY_ROWS)
def test_generated_store_parity_and_shared_api(rows):
    graphs = [
        rdflib.Graph(),
        rdfcore.Graph(),
        rdfcore.Graph(store=rdfcore.SQLiteStore()),
    ]
    try:
        for module, graph in zip([rdflib, rdfcore, rdfcore], graphs):
            for row in triples(module, rows) * 2:
                assert graph.add(row) is graph
        expected = snapshot(graphs[0])
        assert all(snapshot(graph) == expected for graph in graphs)
        for module, graph in zip([rdflib, rdfcore, rdfcore], graphs):
            assert graph.remove((module.BNode("b0"), None, None)) is graph
        assert snapshot(graphs[0]) == snapshot(graphs[1]) == snapshot(graphs[2])
    finally:
        for graph in graphs:
            graph.close()


@pytest.mark.parametrize("format", ["nt", "turtle", "nt12", "turtle12"])
@PROPERTY
@given(predicate=st.sampled_from(['"literal"', "<<( <urn:s> <urn:p> <urn:o> )>>"]))
def test_generated_invalid_predicate_is_rejected(predicate, format):
    error = rdfcore.BadSyntax if format.startswith("turtle") else ParserError
    with pytest.raises(error):
        rdfcore.Graph().parse(
            data=f"<urn:s> {predicate} <urn:o> .", format=format, strict=True
        )


@pytest.mark.parametrize("mode", ["pretty", "stream"])
@PROPERTY
@given(rows=ROWS)
def test_graph_trig12_preserves_named_graph(rows, mode):
    graph = rdfcore.Graph(identifier=rdfcore.URIRef("urn:graph"))
    expected = rdfcore.Dataset()
    named = expected.graph(graph.identifier)
    for row in triples(rdfcore, rows):
        graph.add(row)
        named.add(row)
    actual = rdfcore.Dataset().parse(
        data=graph.serialize(format="trig12", mode=mode), format="trig12"
    )
    assert isomorphic(actual, expected)


@pytest.mark.parametrize("format", ["nt", "turtle", "xml"])
@PROPERTY
@given(rows=LEGACY_ROWS)
def test_generated_legacy_graph_roundtrip(rows, format):
    graph = rdfcore.Graph()
    for row in triples(rdfcore, rows):
        graph.add(row)
    assert isomorphic(
        graph, rdfcore.Graph().parse(data=graph.serialize(format=format), format=format)
    )


@pytest.mark.parametrize("format", ["nquads", "nq12"])
@PROPERTY
@given(
    rows=LEGACY_ROWS,
    names=st.lists(st.one_of(st.none(), SUBJECT), min_size=10, max_size=10),
)
def test_generated_nquads_roundtrip(rows, names, format):
    dataset = rdfcore.Dataset()
    for row, name in zip(triples(rdfcore, rows), names):
        graph = (
            dataset.default_graph
            if name is None
            else dataset.graph(term(rdfcore, name))
        )
        graph.add(row)
    # N-Quads cannot encode empty named graphs; none are created in this strategy.
    restored = rdfcore.Dataset().parse(
        data=dataset.serialize(format=format), format=format
    )
    assert isomorphic(dataset, restored)


@PROPERTY
@given(predicate=st.sampled_from(['"literal"', "<<( <urn:s> <urn:p> <urn:o> )>>"]))
def test_legacy_permissive_predicates_match_oracle(predicate):
    outcomes = []
    for module in (rdflib, rdfcore):
        try:
            graph = module.Graph().parse(
                data=f"<urn:s> {predicate} <urn:o> .", format="turtle"
            )
            outcomes.append(("accepted", snapshot(graph)))
        except (rdflib.plugins.parsers.notation3.BadSyntax, rdfcore.BadSyntax) as error:
            outcomes.append(("error", type(error).__name__))
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("mode", ["pretty", "stream"])
@pytest.mark.parametrize("identifier", ["urn:graph", "urn:x-rdflib:default"])
def test_single_graph_trig12_matches_reference_named_graph(mode, identifier):
    observations = []
    for module in (rdflib, rdfcore):
        graph = module.Graph(identifier=module.URIRef(identifier))
        graph.add((module.URIRef("urn:s"), module.URIRef("urn:p"), module.Literal("v")))
        data = graph.serialize(
            format="trig" if module is rdflib else "trig12",
            **({"mode": mode} if module is rdfcore else {}),
        )
        parsed = module.Dataset().parse(
            data=data, format="trig" if module is rdflib else "trig12"
        )
        observations.append(
            {tuple(str(term) for term in row) for row in parsed.quads()}
        )
    assert observations[0] == observations[1] == {("urn:s", "urn:p", "v", identifier)}
