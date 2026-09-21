from datetime import date

from rdfcore import BNode, Literal, URIRef, Variable, XSD


def test_terms_are_string_subclasses():
    assert isinstance(URIRef("http://example.org/"), str)
    assert isinstance(BNode("b1"), str)
    assert isinstance(Literal("x"), str)
    assert isinstance(Variable("x"), str)


def test_term_n3():
    assert URIRef("http://example.org/").n3() == "<http://example.org/>"
    assert BNode("b1").n3() == "_:b1"
    assert Variable("?x").n3() == "?x"
    assert Literal("hello").n3() == '"hello"'


def test_literal_python_mapping_and_normalization():
    assert Literal(3).datatype == URIRef("http://www.w3.org/2001/XMLSchema#integer")
    assert Literal("01", datatype="http://www.w3.org/2001/XMLSchema#integer") == Literal("1", datatype="http://www.w3.org/2001/XMLSchema#integer")
    assert str(Literal("01", datatype="http://www.w3.org/2001/XMLSchema#integer", normalize=False)) == "01"
    assert Literal(True).toPython() is True


def test_language_tag_is_case_insensitive_for_equality():
    left = Literal("colour", lang="EN")
    right = Literal("colour", lang="en")
    assert left.language == "EN"
    assert left == right
    assert hash(left) == hash(right)


def test_non_normalized_typed_literal_keeps_lexical_form_but_parses_value():
    literal = Literal("01", datatype=XSD.integer, normalize=False)
    assert str(literal) == "01"
    assert literal.toPython() == 1
    assert not literal.ill_typed
    assert Literal("invalid", datatype=XSD.boolean, normalize=False).ill_typed
    assert Literal("2026-09-21", datatype=XSD.date, normalize=False).toPython() == date(2026, 9, 21)
