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
    ('null', '"null"', False), ('0', '-0', False),
    ('[0]', '[-0]', False), ('{"a":0}', '{"a":-0}', False),
    ('[-0,0]', '[0,-0]', False), ('-0', '-1e-9999', True),
    ('{"a":1,"b":2}', '{"b":2,"a":1}', True),
    ('[1,2]', '[2,1]', False), ('1e400', '10e399', True),
])
def test_json_value_equality(left, right, expected):
    assert Literal(left, datatype=RDF.JSON).eq(Literal(right, datatype=RDF.JSON)) is expected


def test_json_copy_rebuilds_value_from_lexical_form():
    original = Literal('{"items":[1]}', datatype=RDF.JSON)
    original.value['items'].append(2)
    copied = Literal(original)
    assert copied.value == {'items': [1.0]}
    assert copied.value is not original.value
    assert copied == original


@pytest.mark.parametrize('lexical', [
    '{"a":0,"\\u0061":1}', '{"a":{"x":1,"x":2}}',
    '"\\udfff"', '"\\ud800x"', 'Infinity', '-Infinity', '01', '+1', '.1', '1.',
])
def test_json_lexical_space_edge_cases(lexical):
    literal = Literal(lexical, datatype=RDF.JSON, normalize=False)
    assert literal.ill_typed is True
    assert literal.value is None
    assert str(literal) == lexical


@pytest.mark.parametrize('left,right', [
    ('"\\ud83d\\ude00"', '"😀"'), ('"\\u0061"', '"a"'),
    ('9007199254740992.5', '9007199254740991.5'),
    ('1e400', '1e401'), ('0', '1e-9999'),
])
def test_json_mapping_equivalent_lexical_forms_keep_distinct_term_identity(left, right):
    a, b = Literal(left, datatype=RDF.JSON), Literal(right, datatype=RDF.JSON)
    assert a.ill_typed is False and b.ill_typed is False
    assert a.eq(b) is True
    assert a != b
    assert len({a, b}) == 2


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
@pytest.mark.parametrize('format', ['nt12', 'turtle12', 'xml12'])
def test_json_lexical_identity_survives_storage_and_serialization(tmp_path, backend, format):
    from rdfcore import Memory, SQLiteStore
    path = tmp_path / 'json.sqlite'
    graph = Graph(store=Memory() if backend == 'memory' else SQLiteStore(path), identifier=URIRef('urn:g'))
    lexicals = ['0', '-0', '{"a":1,"b":2}', '{"b":2,"a":1}', 'null', '1e400']
    for lexical in lexicals:
        graph.add((URIRef('urn:s'), URIRef('urn:p'), Literal(lexical, datatype=RDF.JSON)))
    if backend == 'sqlite':
        graph.close()
        graph = Graph(store=SQLiteStore(path), identifier=URIRef('urn:g'))
    assert len(graph) == len(lexicals)
    restored = Graph().parse(data=graph.serialize(format=format), format=format)
    assert {str(o) for o in restored.objects()} == set(lexicals)
    assert Literal('0', datatype=RDF.JSON).eq(Literal('-0', datatype=RDF.JSON)) is False
    graph.close()
