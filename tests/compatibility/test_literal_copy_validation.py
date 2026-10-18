"""Literal copies retain the reference constructor's validation contract."""
import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize("lexical", ["true", "false", "1", "0", "invalid"])
@pytest.mark.parametrize("normalize", [True, False])
def test_boolean_copy_validation_matches_reference(lexical, normalize):
    results = []
    for module in (rdflib, rdfcore):
        original = module.Literal(lexical, datatype=module.XSD.boolean,
                                  normalize=normalize)
        copied = module.Literal(original)
        results.append((str(copied), copied.value, copied.ill_typed,
                        copied == original, hash(copied) == hash(original)))
    assert results[1] == results[0]


@pytest.mark.parametrize('datatype', ['byte', 'unsignedByte', 'positiveInteger', 'nonPositiveInteger'])
@pytest.mark.parametrize('lexical', ['-1', '0', '1', '256', 'invalid'])
def test_bounded_integer_copy_validation_matches_reference(datatype, lexical):
    observations = []
    for module in (rdflib, rdfcore):
        original = module.Literal(lexical, datatype=module.XSD[datatype], normalize=False)
        copied = module.Literal(original)
        observations.append((str(copied), copied.value, copied.ill_typed,
                             copied == original, hash(copied) == hash(original)))
    assert observations[0] == observations[1]


@pytest.mark.parametrize('datatype,lexical', [
    ('date', '2020-02-29Z'), ('date', '2020-02-29z'),
    ('date', '2020-02-29+02:00'), ('date', '2020-02-29-09:00'),
    ('date', '2020-02-29T12:30:00Z'), ('date', '2020-02-30'),
    ('dateTime', '2020-02-29'), ('dateTime', '2020-02-29T12:30:00+02:00'),
    ('dateTime', '2020-02-29T12:30:00Z'),
    ('time', '12:30:00Z'), ('time', '12:30:00-09:00'),
])
@pytest.mark.parametrize('normalize', [True, False])
def test_temporal_constructor_and_copy_match_reference(datatype, lexical, normalize):
    observations = []
    for module in (rdflib, rdfcore):
        original = module.Literal(lexical, datatype=module.XSD[datatype], normalize=normalize)
        copied = module.Literal(original)
        observations.append((str(original), original.ill_typed, type(original.value).__name__,
                             str(original.value), str(copied), copied.ill_typed,
                             original == copied, hash(original) == hash(copied)))
    assert observations[0] == observations[1]
