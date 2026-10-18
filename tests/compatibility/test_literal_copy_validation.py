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
