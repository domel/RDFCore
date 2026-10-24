import pytest

from tests.w3c.semantic_coverage import SCHEMA_CHECKS, SCHEMA_SECTIONS, coverage_report


@pytest.mark.parametrize('versions', [(), ('rdf11',), ('rdf12',), ('rdf11', 'rdf12')])
def test_empty_or_missing_suites_cannot_pass_acceptance(versions):
    suites = [dict(category='entailment', rdf_version=v, tests=[], counts={}) for v in versions]
    report = coverage_report(suites)
    assert report['official_semantics_passed'] is False
    assert report['full_profile_verified'] is False


def test_all_green_fixtures_do_not_prove_full_profile():
    suites = [dict(category='entailment', rdf_version=v,
                   total=1, tests=[{'status': 'passed'}], counts={'passed': 1}) for v in ('rdf11', 'rdf12')]
    report = coverage_report(suites)
    assert report['official_semantics_passed'] is True
    assert report['full_profile_verified'] is False
    assert [p['status'] for p in report['additional_probes'][:3]] == ['passed'] * 3
    assert report['additional_probes'][3]['status'] == 'passed'
    assert report['additional_probes'][4]['status'] == 'passed'
    assert all(p['status'] == 'passed' for p in report['semantic_conditions'])
    assert all(p['reference'].startswith(report['semantics_reference'] + '#')
               for p in report['semantic_conditions'])
    assert len(report['schema_sections']) == len(SCHEMA_SECTIONS) == 41
    assert all(r['status'] == 'partial' and r['evidence'] and r['limitation']
               for r in report['schema_sections'])
    assert all('#' in r['reference'] for r in report['schema_sections'])


def test_schema_checks_reference_executable_requirements():
    from tests.w3c.semantic_requirements import ALL_PROBES
    ids = {p.id for p in ALL_PROBES}
    assert set(SCHEMA_CHECKS) == set(SCHEMA_SECTIONS)
    for section, checks in SCHEMA_CHECKS.items():
        if section not in {'A.1', 'A.2'}:
            assert checks, section
        assert set(checks) <= ids, section


def test_suite_error_cannot_be_hidden_by_passing_entries(monkeypatch):
    from tests.w3c import semantic_coverage
    monkeypatch.setattr(semantic_coverage, '_probe', lambda *a: {'status': 'unsupported'})
    suites = [dict(category='entailment', rdf_version=v, total=1,
                   tests=[{'status': 'passed'}], counts={'passed': 1},
                   suite_error='incomplete manifest') for v in ('rdf11', 'rdf12')]
    assert coverage_report(suites)['official_semantics_passed'] is False


@pytest.mark.parametrize('status', ['failed', 'unsupported', 'error'])
def test_nonpassing_manifest_result_keeps_gate_closed(status):
    suites = [dict(category='entailment', rdf_version=v,
                   tests=[{'status': status}], counts={status: 1}) for v in ('rdf11', 'rdf12')]
    assert coverage_report(suites)['official_semantics_passed'] is False
