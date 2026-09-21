import pytest

from rdfcore import BNode, Literal, TripleTerm, URIRef, RDF, RDFS


def test_directional_literal_is_distinct_and_hashable():
    literal = Literal("hello", lang="en", direction="ltr")
    assert literal.language == "en"
    assert literal.direction == "ltr"
    assert literal.datatype is None
    assert literal.n3() == '"hello"@en--ltr'
    assert literal != Literal("hello", lang="en", direction="rtl")
    assert hash(literal) == hash(Literal("hello", lang="EN", direction="ltr"))


def test_directional_literal_validates_constructor_arguments():
    with pytest.raises(TypeError):
        Literal("hello", direction="ltr")
    with pytest.raises(ValueError):
        Literal("hello", lang="en", direction="sideways")
    with pytest.raises(TypeError):
        Literal("hello", "en", None, None, "ltr")
    with pytest.raises(TypeError):
        Literal("hello", lang="", direction="ltr")


def test_triple_term_is_immutable_structural_and_hashable():
    triple = TripleTerm(URIRef("http://e/s"), URIRef("http://e/p"), BNode("o"))
    same = TripleTerm(URIRef("http://e/s"), URIRef("http://e/p"), BNode("o"))
    assert not isinstance(triple, str)
    assert tuple(triple) == tuple(same)
    assert triple == same
    assert hash(triple) == hash(same)
    assert triple.n3() == '<<( <http://e/s> <http://e/p> _:o )>>'
    with pytest.raises(AttributeError):
        triple.subject = URIRef("http://e/changed")


@pytest.mark.parametrize("subject,predicate,obj", [
    (Literal("bad"), URIRef("http://e/p"), URIRef("http://e/o")),
    (URIRef("http://e/s"), BNode("bad"), URIRef("http://e/o")),
    (URIRef("http://e/s"), URIRef("http://e/p"), object()),
])
def test_triple_term_rejects_invalid_rdf_positions(subject, predicate, obj):
    with pytest.raises(TypeError):
        TripleTerm(subject, predicate, obj)


def test_rdf_12_namespace_terms_are_exposed():
    assert str(RDF.dirLangString).endswith("#dirLangString")
    assert str(RDF.reifies).endswith("#reifies")
    assert str(RDF.PropositionForm).endswith("#PropositionForm")
    assert str(RDF.propositionFormSubject).endswith("#propositionFormSubject")
    assert str(RDF.propositionFormPredicate).endswith("#propositionFormPredicate")
    assert str(RDF.propositionFormObject).endswith("#propositionFormObject")
    assert str(RDFS.Proposition).endswith("#Proposition")
