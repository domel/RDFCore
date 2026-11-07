from rdfcore import Literal, RDF


def test_json_value_equality_is_independent_of_mutable_python_helper():
    literal = Literal('{"items":[1]}', datatype=RDF.JSON)
    equivalent = Literal('{"items":[1.0]}', datatype=RDF.JSON)
    original_hash = hash(literal)
    literal.toPython()["items"].append(2)
    assert literal.eq(equivalent) is True
    assert hash(literal) == original_hash
    assert str(literal) == '{"items":[1]}'
