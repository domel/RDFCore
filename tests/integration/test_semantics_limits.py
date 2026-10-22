"""Resource exhaustion is not a negative entailment decision."""

import pytest

from rdfcore import URIRef
from rdfcore import semantics


TRIPLE = tuple(URIRef('urn:' + name) for name in ('s', 'p', 'o'))


@pytest.mark.parametrize('operation', [semantics.entails, semantics.entailment_closure])
def test_limit_is_distinct_from_unsupported(operation):
    args = ([TRIPLE], [TRIPLE]) if operation is semantics.entails else ([TRIPLE],)
    with pytest.raises(semantics.EntailmentResourceLimit):
        operation(*args, max_steps=0)
    assert issubclass(semantics.EntailmentResourceLimit, semantics.UnsupportedEntailment)


@pytest.mark.parametrize('limit', [True, 1.5, '1'])
def test_limit_type(limit):
    with pytest.raises(TypeError):
        semantics.entails([], [], max_steps=limit)


def test_negative_limit():
    with pytest.raises(ValueError):
        semantics.entailment_closure([], max_steps=-1)


def test_budget_applies_to_consumption_and_does_not_leak_between_calls():
    consumed = []

    def source():
        while True:
            consumed.append(True)
            yield TRIPLE

    with pytest.raises(semantics.EntailmentResourceLimit):
        semantics.entails(source(), [], max_steps=3)
    assert len(consumed) == 4
    assert semantics.entails([TRIPLE], [TRIPLE], max_steps=1000) is True
    assert semantics.entails([TRIPLE], [], max_steps=1000) is True
    assert semantics.entails([], [TRIPLE], max_steps=1000) is False


@pytest.mark.parametrize('regime', ['rdf', 'rdfs'])
def test_unknown_remains_unknown_with_sufficient_budget(regime):
    with pytest.raises(semantics.UnsupportedEntailment) as caught:
        semantics.entails([], [TRIPLE], regime=regime, max_steps=100000)
    assert not isinstance(caught.value, semantics.EntailmentResourceLimit)


def test_closure_work_is_limited_after_snapshot():
    with pytest.raises(semantics.EntailmentResourceLimit):
        semantics.entailment_closure([TRIPLE], max_steps=2)


def test_recursion_exhaustion_is_resource_failure(monkeypatch):
    def exhausted(*args, **kwargs):
        raise RecursionError('controlled test')

    monkeypatch.setattr(semantics, '_homomorphism', exhausted)
    with pytest.raises(semantics.EntailmentResourceLimit):
        semantics.entails([], [])


def test_nested_calls_restore_outer_budget():
    def source():
        assert semantics.entails([], [], max_steps=10) is True
        yield TRIPLE

    with pytest.raises(semantics.EntailmentResourceLimit):
        semantics.entails(source(), [], max_steps=0)
    assert semantics.entails([TRIPLE], [TRIPLE]) is True


def test_closure_recursion_exhaustion_is_resource_failure(monkeypatch):
    def exhausted(*args, **kwargs):
        raise RecursionError('controlled test')

    monkeypatch.setattr(semantics, '_closure', exhausted)
    with pytest.raises(semantics.EntailmentResourceLimit):
        semantics.entailment_closure([])
