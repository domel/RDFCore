import pytest

from rdfcore import Graph, Literal, RDF, URIRef


def test_rdf_json_is_exposed_and_parsed():
    assert RDF.JSON == URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#JSON")
    literal = Literal('{"name":"RDFCore","values":[1,true,null]}', datatype=RDF.JSON)
    assert literal.ill_typed is False
    assert literal.value == {"name": "RDFCore", "values": [1.0, True, None]}
    assert isinstance(literal.value["values"][0], float)


@pytest.mark.parametrize(
    "lexical",
    ["not json", "NaN", '{"x":"\\ud800"}', '{"duplicate":1,"duplicate":2}'],
)
def test_rdf_json_rejects_invalid_json_values(lexical):
    literal = Literal(lexical, datatype=RDF.JSON)
    assert literal.ill_typed is True
    assert literal.value is None


def test_rdf_json_round_trips_through_turtle12():
    graph = Graph().add((URIRef("urn:s"), URIRef("urn:p"), Literal('{"a":1}', datatype=RDF.JSON)))
    text = graph.serialize(format="turtle12")
    parsed = Graph().parse(data=text, format="turtle12")
    assert list(parsed)[0][2].value == {"a": 1.0}


def test_rdf_json_scalar_values_and_literal_copy():
    assert Literal("true", datatype=RDF.JSON).value is True
    assert Literal("null", datatype=RDF.JSON).value is None
    number = Literal("1", datatype=RDF.JSON)
    assert number.value == 1.0
    assert isinstance(number.value, float)
    copied = Literal(number)
    assert copied.value == 1.0
    assert copied.ill_typed is False
