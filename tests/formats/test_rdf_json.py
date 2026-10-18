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


def test_json_value_equality_is_independent_of_mutable_python_helper():
    literal = Literal('{"items":[1]}', datatype=RDF.JSON)
    equivalent = Literal('{"items":[1.0]}', datatype=RDF.JSON)
    original_hash = hash(literal)
    literal.toPython()["items"].append(2)
    assert literal.eq(equivalent) is True
    assert hash(literal) == original_hash
    assert str(literal) == '{"items":[1]}'


@pytest.mark.parametrize('codepoint', [0xFDD0, 0xFDEF, 0xFFFE, 0xFFFF, 0x1FFFE, 0x10FFFF])
@pytest.mark.parametrize('template', ['"{}"', '["{}"]', '{{"{}":0}}', '{{"key":"{}"}}'])
def test_json_rejects_noncharacters(codepoint, template):
    import json
    character = chr(codepoint)
    for encoded in (character, json.dumps(character)[1:-1]):
        literal = Literal(template.format(encoded), datatype=RDF.JSON)
        assert literal.ill_typed is True
        assert literal.value is None


@pytest.mark.parametrize('left,right,expected', [
    ('true', '1', False), ('false', '0', False), ('[true]', '[1]', False),
    ('{"a":true}', '{"a":1}', False), ('null', 'null', True),
    ('null', '"null"', False), ('0', '-0', True),
    ('{"a":1,"b":2}', '{"b":2,"a":1}', True),
    ('[1,2]', '[2,1]', False), ('1e400', '10e399', True),
])
def test_json_value_equality(left, right, expected):
    assert Literal(left, datatype=RDF.JSON).eq(Literal(right, datatype=RDF.JSON)) is expected
