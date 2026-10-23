"""Finite witnesses do not constitute arbitrary value-space inclusion proofs."""

import pytest

from rdfcore import Literal, RDF, URIRef, XSD
from rdfcore.datatypes import datatype_value, SUPPORTED_DATATYPES
from rdfcore._datatype_spaces import contains, subset, witnesses
from tests.integration.test_datatype_coverage import CASES


@pytest.mark.parametrize('datatype', sorted(SUPPORTED_DATATYPES))
def test_every_supported_space_has_valid_recognized_witnesses(datatype):
    samples, complete = witnesses({datatype})
    assert samples
    assert type(complete) is bool
    for sample in samples:
        if datatype in {str(RDF.langString), str(RDF.dirLangString)}:
            # Shared Literal API keeps datatype=None for language literals.
            assert sample.datatype is None and sample.language == 'en'
            assert sample.direction == ('ltr' if datatype == str(RDF.dirLangString) else None)
        else:
            assert sample.datatype == URIRef(datatype)
        assert contains(datatype_value(sample), datatype)


@pytest.mark.parametrize('datatype', sorted(CASES, key=str))
def test_each_independent_lexical_fixture_is_in_its_own_space(datatype):
    assert contains(datatype_value(Literal(CASES[datatype][0], datatype=datatype, normalize=False)), datatype)


@pytest.mark.parametrize('left,right,expected', [
    (XSD.integer, XSD.decimal, True), (XSD.decimal, XSD.integer, False),
    (XSD.byte, XSD.short, True), (XSD.unsignedByte, XSD.byte, False),
    (XSD.negativeInteger, XSD.nonPositiveInteger, True),
    (XSD.nonNegativeInteger, XSD.nonPositiveInteger, False),
    (XSD.NCName, XSD.Name, True), (XSD.Name, XSD.NCName, False),
    (XSD.language, XSD.NCName, True), (XSD.token, XSD.NMTOKEN, False),
    (XSD.dateTimeStamp, XSD.dateTime, True), (XSD.dateTime, XSD.dateTimeStamp, False),
    (XSD.yearMonthDuration, XSD.duration, True),
    (XSD.yearMonthDuration, XSD.dayTimeDuration, False),
    (RDF.HTML, RDF.XMLLiteral, True), (RDF.XMLLiteral, RDF.HTML, True),
    (XSD.double, RDF.JSON, True), (RDF.JSON, XSD.double, False),
    (XSD.float, RDF.JSON, False), (XSD.string, RDF.JSON, True),
    (RDF.langString, RDF.JSON, False), (XSD.boolean, XSD.integer, False),
])
def test_value_space_inclusion(left, right, expected):
    assert subset(left, right) is expected


@pytest.mark.parametrize('types,empty,complete', [
    ({XSD.boolean, XSD.integer}, True, True),
    ({XSD.positiveInteger, XSD.nonPositiveInteger}, True, True),
    ({XSD.nonPositiveInteger, XSD.nonNegativeInteger}, False, True),
    ({XSD.positiveInteger, XSD.byte}, False, False),
    ({RDF.JSON, XSD.boolean}, False, True),
    ({RDF.JSON, XSD.integer}, True, True),
    ({XSD.yearMonthDuration, XSD.dayTimeDuration}, False, True),
    ({XSD.dateTimeStamp, XSD.date}, True, True),
])
def test_intersection_witnesses(types, empty, complete):
    samples, exhaustive = witnesses(types)
    assert (not samples) is empty
    assert exhaustive is complete
    assert all(contains(datatype_value(sample), datatype) for sample in samples for datatype in types)


def test_empty_constraint_set_is_not_misreported_as_an_empty_space():
    with pytest.raises(ValueError, match='at least one'):
        witnesses(set())


def test_membership_partition_covers_independent_boundaries_and_lexical_profiles():
    from rdfcore._datatype_spaces import membership_regions
    recognized = set(SUPPORTED_DATATYPES)
    regions = dict(membership_regions(recognized, step=lambda: None))
    candidates = [Literal(str(n), datatype=XSD.integer, normalize=False)
                  for n in (-10**50, -32769, -32768, -129, -128, -1, 0, 1, 127, 128,
                            255, 256, 32767, 32768, 2**64-1, 2**64, 10**50)]
    candidates += [Literal(s, datatype=XSD.string, normalize=False)
                   for s in ('', 'two words', ' leading', 'trailing ', '\n', '\u0085',
                             ':', '1name', '\u0300', 'é', 'en-123', 'a_b')]
    candidates += [Literal('0.125', datatype=XSD.decimal),
                   Literal('P2YT3S', datatype=XSD.duration),
                   Literal('2000-02-29T12:00:00', datatype=XSD.dateTime),
                   Literal('2000-02-29T12:00:00Z', datatype=XSD.dateTime),
                   Literal('"\\u0000"', datatype=RDF.JSON)]
    for sample in candidates:
        profile = frozenset(d for d in recognized if contains(datatype_value(sample), d))
        assert profile in regions, repr(sample)
    for profile, witness in regions.items():
        assert profile == frozenset(d for d in recognized if contains(datatype_value(witness), d))
