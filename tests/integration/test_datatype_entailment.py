"""T38: Semantics CRD 2026-09-24 §§7–9; Concepts CR 2026-04-07 §5/A.

These section-derived cases supplement, not replace, the official manifests.
"""

import pytest

from rdfcore import BNode, Literal, RDF, RDFS, TripleTerm, URIRef, XSD
from rdfcore.semantics import EntailmentResourceLimit, entails

S, P, O, Q, V = map(URIRef, ("urn:s", "urn:p", "urn:o", "urn:q", "urn:v"))


def lit(text, datatype):
    return Literal(text, datatype=datatype, normalize=False)


def decide(source, target, *, regime="rdfs", datatypes=()):
    return entails(
        source, target, regime=regime, datatypes=set(datatypes), mode="decide"
    )


@pytest.mark.parametrize(
    "source_type,target_type,text,expected",
    [
        (XSD.integer, XSD.decimal, "25", True),
        (XSD.integer, XSD.byte, "127", True),
        (XSD.integer, XSD.byte, "128", False),
        (XSD.decimal, XSD.integer, "1.5", False),
        (XSD.boolean, XSD.integer, "true", False),
        (XSD.float, XSD.double, "1", False),
        (XSD.double, RDF.JSON, "NaN", True),
        (RDF.JSON, XSD.string, '"text"', True),
        (RDF.JSON, XSD.boolean, "true", True),
        (RDF.JSON, XSD.double, "1", True),
        (RDF.JSON, XSD.integer, "1", False),
        (RDF.JSON, XSD.string, "[]", False),
        (RDF.JSON, XSD.string, '"\\u0000"', False),
        (RDF.HTML, RDF.XMLLiteral, "text", True),
        (RDF.XMLLiteral, RDF.HTML, "<a/>", True),
        (XSD.string, RDF.HTML, "text", False),
        (XSD.string, XSD.token, "a b", True),
        (XSD.string, XSD.token, " a ", False),
        (XSD.dateTime, XSD.dateTimeStamp, "2026-10-22T12:00:00Z", True),
        (XSD.dateTime, XSD.dateTimeStamp, "2026-10-22T12:00:00", False),
        (XSD.duration, XSD.dayTimeDuration, "PT1S", True),
        (XSD.duration, XSD.yearMonthDuration, "P1DT1S", False),
    ],
)
def test_recognized_value_space_membership(source_type, target_type, text, expected):
    value = lit(text, source_type)
    source = [(S, P, value)]
    x = BNode("value")
    target = [(S, P, x), (x, RDF.type, target_type)]
    assert (
        decide(source, target, regime="rdf", datatypes={source_type, target_type})
        is expected
    )


@pytest.mark.parametrize(
    "left,right",
    [
        (XSD.decimal, XSD.integer),
        (XSD.positiveInteger, XSD.byte),
        (XSD.string, XSD.token),
        (XSD.normalizedString, XSD.token),
        (XSD.NCName, XSD.language),
        (XSD.dateTime, XSD.dateTimeStamp),
    ],
)
def test_type_negatives_use_distinguishing_values_not_only_default_samples(left, right):
    assert (
        decide(
            [(V, RDF.type, left)],
            [(V, RDF.type, right)],
            regime="rdf",
            datatypes={left, right},
        )
        is False
    )


def test_nested_simple_d_terms_have_value_aware_negative_decisions():
    left = TripleTerm(S, P, TripleTerm(O, Q, lit("01", XSD.integer)))
    right = TripleTerm(S, P, TripleTerm(O, Q, lit("2", XSD.integer)))
    assert (
        decide(
            [(S, P, left)], [(S, P, right)], regime="simple", datatypes={XSD.integer}
        )
        is False
    )
    assert (
        decide(
            [(S, P, left)],
            [(O, Q, lit("1", XSD.integer))],
            regime="simple",
            datatypes={XSD.integer},
        )
        is False
    )


def test_unrecognized_range_and_explicit_d_set_do_not_guess_inconsistency():
    source = [
        (S, P, lit("flargh", XSD.integer)),
        (P, RDFS.range, URIRef("urn:datatype")),
    ]
    assert decide(source, []) is True
    # T39's free-extension model can certify consistency without recognizing
    # either the opaque literal's datatype or the custom range class.
    assert decide(source, False) is False
    # An unrecognized literal can denote a string even if its lexical form
    # would be invalid were its datatype recognized.
    source = [(S, P, lit("flargh", XSD.integer)), (P, RDFS.range, XSD.string)]
    assert decide(source, False) is False


def test_typing_axioms_and_intersection_witnesses_do_not_assert_embedded_triples():
    x = BNode("x")
    assert (
        decide(
            [],
            [(x, RDF.type, XSD.positiveInteger), (x, RDF.type, XSD.byte)],
            regime="rdf",
            datatypes={XSD.positiveInteger, XSD.byte},
        )
        is True
    )
    source = [(S, P, TripleTerm(O, Q, lit("01", XSD.integer)))]
    assert (
        decide(
            source,
            [(x, RDF.type, XSD.decimal)],
            regime="rdf",
            datatypes={XSD.integer, XSD.decimal},
        )
        is True
    )
    assert (
        decide(
            source,
            [(O, Q, lit("1", XSD.integer))],
            regime="rdf",
            datatypes={XSD.integer},
        )
        is False
    )


def test_work_limit_is_not_a_datatype_verdict():
    with pytest.raises(EntailmentResourceLimit):
        entails(
            [(V, RDF.type, XSD.boolean)],
            False,
            regime="rdf",
            datatypes={XSD.boolean},
            mode="decide",
            max_steps=2,
        )


def test_typed_names_inside_propositions_keep_semantic_value_assignments():
    source = [(V, RDF.type, XSD.boolean)]
    assert (
        decide(
            source, [(S, P, TripleTerm(V, Q, O))], regime="rdf", datatypes={XSD.boolean}
        )
        is False
    )


def test_fixed_vocabulary_aliasing_has_a_checked_candidate_model():
    assert (
        decide(
            [(RDF.type, RDF.type, XSD.boolean)],
            False,
            regime="rdf",
            datatypes={XSD.boolean},
        )
        is False
    )
