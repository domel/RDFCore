"""Contract regressions are not substitutes for official entailment verdicts."""

import pytest

from rdfcore.semantics import UnsupportedEntailment, entails
from tests.w3c.semantic_contract import CASES, semantic_plan
from tests.w3c.known_issues import BASE, SEMANTIC_11, SEMANTIC_12
from tests.w3c.test_known_issues import SEMANTIC_IDS, NEW_SEMANTIC_IDS


@pytest.mark.parametrize('name', sorted(CASES))
def test_case(name):
    case = CASES[name]
    options = dict(regime=case.regime, datatypes=case.datatypes, mode='decide')
    if case.supported:
        assert entails(case.premise, case.conclusion, **options) is case.expected
    else:
        # A missing countermodel or consistency procedure is still a blocker,
        # not a successful negative entailment or a conformance pass.
        with pytest.raises(UnsupportedEntailment, match='consistency|certificate'):
            entails(case.premise, case.conclusion, **options)


def test_every_historical_execution_has_requirement_regression_and_route():
    assert set(CASES) == set(SEMANTIC_IDS + NEW_SEMANTIC_IDS)
    assert set(SEMANTIC_11) == set(SEMANTIC_IDS)
    assert set(SEMANTIC_12) == set(NEW_SEMANTIC_IDS)
    executions = []
    # RDF12 includes the RDF11 manifest: inherited IDs remain RDF11 IDs, but
    # each suite execution still has its own published reference and outcome.
    for version in ('rdf11', 'rdf12'):
        document = ('https://www.w3.org/TR/2014/REC-rdf11-mt-20140225/' if version == 'rdf11'
                    else 'https://www.w3.org/TR/2026/CRD-rdf12-semantics-20260924/')
        for name in SEMANTIC_IDS:
            executions.append(semantic_plan(BASE+'rdf11/rdf-mt/manifest.ttl#'+name, document))
    for name in NEW_SEMANTIC_IDS:
        executions.append(semantic_plan(BASE+'rdf12/rdf-semantics#'+name))
    assert len(executions) == 79
    for plan in executions:
        assert plan and all(plan.values())
        assert plan['reference'].startswith('https://www.w3.org/TR/') and '#' in plan['reference']
        assert plan['regression'].startswith('tests/w3c/test_semantics_contract.py::test_case[')
    assert semantic_plan('urn:unreviewed') is None


def test_t38_backlog_has_decisions_not_unsupported_boundary_expectations():
    catalogue = {**SEMANTIC_11, **SEMANTIC_12}
    names = [name for name, requirement in catalogue.items() if requirement[0] == 'S11 T38']
    assert names
    for name in names:
        case = CASES[name]
        assert case.supported, name
        assert entails(case.premise, case.conclusion, regime=case.regime,
                       datatypes=case.datatypes, mode='decide') is case.expected
