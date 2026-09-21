from rdfcore import Literal


def test_ill_typed_matches_rdflib_states():
    assert Literal("text", lang="en").ill_typed is None
    assert Literal("text", datatype="urn:unknown").ill_typed is None
    invalid = Literal("not-an-integer", datatype="http://www.w3.org/2001/XMLSchema#integer")
    assert invalid.ill_typed is True
    assert invalid.value is None


def test_well_typed_explicit_literal_is_not_ill_typed():
    literal = Literal("42", datatype="http://www.w3.org/2001/XMLSchema#integer")
    assert literal.ill_typed is False
    assert literal.value == 42


def test_ill_typed_covers_derived_xsd_types():
    assert Literal("text", datatype="http://www.w3.org/2001/XMLSchema#string").ill_typed is False
    valid = Literal("7", datatype="http://www.w3.org/2001/XMLSchema#nonNegativeInteger")
    invalid = Literal("-1", datatype="http://www.w3.org/2001/XMLSchema#nonNegativeInteger")
    assert (valid.value, valid.ill_typed) == (7, False)
    assert (invalid.value, invalid.ill_typed) == (None, True)
