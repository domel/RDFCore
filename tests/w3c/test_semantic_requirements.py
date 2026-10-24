"""Execute clause consequences independently of the official snapshot."""
import pytest

from tests.w3c.semantic_requirements import ALL_PROBES, run_probe


@pytest.mark.parametrize('probe', ALL_PROBES, ids=lambda p: p.id)
def test_semantic_requirement_consequence(probe):
    result = run_probe(probe)
    assert result['status'] == 'passed', result
    assert result['actual'] is probe.expected


def test_requirement_ids_are_unique_and_include_negative_cases():
    assert len({p.id for p in ALL_PROBES}) == len(ALL_PROBES)
    assert any(p.expected is False for p in ALL_PROBES)
