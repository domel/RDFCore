"""Evidence accounting must not turn old failures into successes."""

from copy import deepcopy
from hashlib import sha256

import pytest

from tests.w3c import official


def sample(*statuses, profile='default'):
    counts = dict.fromkeys(('passed', 'failed', 'unsupported', 'error'), 0)
    tests = []
    for status in statuses:
        counts[status] += 1
        tests.append({'id': 'urn:test', 'status': status, 'reason': 'observed ' + status,
                      'manifest': 'rdf/manifest.ttl'})
    return {'snapshot': 'a' * 40, 'execution_profile': profile,
            'suites': [{'rdf_version': 'rdf12', 'format': 'nt12', 'category': 'syntax',
                        'total': len(tests), 'counts': counts, 'tests': tests}]}


def test_empty_manifest_is_not_a_successful_suite(tmp_path):
    path = tmp_path / 'manifest.ttl'
    path.write_text('''@prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
<> a mf:Manifest; mf:entries () .''')
    result = official.report_suite(path, 'nt')
    assert 'no test entries' in result['suite_error']
    assert result['total'] == 0 and result['counts']['passed'] == 0


def test_compare_preserves_repeated_executions_and_input():
    from tests.w3c.audit import compare_reports
    before, after = sample('passed', 'failed'), sample('passed', 'passed', 'unsupported')
    original = deepcopy((before, after))
    delta = compare_reports(before, after)
    assert delta['unchanged'] == 1
    assert len(delta['changed']) == len(delta['added']) == 1
    assert delta['removed'] == []
    assert delta['changed'][0]['before']['status'] == 'failed'
    assert delta['changed'][0]['after']['status'] == 'passed'
    assert (before, after) == original


def test_compare_keeps_rdf11_and_rdf12_runs_distinct():
    from tests.w3c.audit import compare_reports
    before, after = sample('passed'), sample('passed')
    after['suites'][0]['rdf_version'] = 'rdf11'
    delta = compare_reports(before, after)
    assert delta['unchanged'] == 0
    assert len(delta['removed']) == len(delta['added']) == 1


def test_compare_handles_an_explicitly_unavailable_format():
    from tests.w3c.audit import compare_reports
    before, after = sample('passed'), sample('unsupported')
    after['suites'][0]['format'] = None
    delta = compare_reports(before, after)
    assert len(delta['removed']) == len(delta['added']) == 1


def test_cli_does_not_hide_removed_executions(tmp_path):
    import json
    from tests.w3c.audit import main
    before, after = sample('passed', 'passed'), sample('passed')
    previous, current = tmp_path / 'before.json', tmp_path / 'after.json'
    previous.write_text(json.dumps(before))
    current.write_text(json.dumps(after))
    output = tmp_path / 'audit.json'
    assert main(['--before', str(previous), '--current', str(current), '--output', str(output)]) == 1
    result = json.loads(output.read_text())
    assert result['audit']['issues'] == []
    assert len(result['comparison']['removed']) == 1


def test_compare_does_not_mix_default_and_recovery():
    from tests.w3c.audit import compare_reports
    with pytest.raises(ValueError, match='profile'):
        compare_reports(sample('failed'), sample('passed', profile='legacy-w3c-xml'))


@pytest.mark.parametrize('field,value', [('total', 2), ('counts', {'passed': 99}), ('tests', [])])
def test_compare_rejects_inconsistent_accounting(field, value):
    from tests.w3c.audit import compare_reports
    invalid = sample('passed')
    invalid['suites'][0][field] = value
    with pytest.raises(ValueError, match='accounting'):
        compare_reports(sample('passed'), invalid)


def test_compare_reports_suite_errors_separately():
    from tests.w3c.audit import compare_reports
    before, after = sample('passed'), sample('passed')
    after['suites'][0]['suite_error'] = 'missing manifest'
    delta = compare_reports(before, after)
    assert delta['suite_errors']['after'][0]['reason'] == 'missing manifest'


@pytest.mark.parametrize('kind', ['no-suites', 'empty-suite', 'boolean-count'])
def test_empty_or_malformed_report_cannot_look_green(kind):
    from tests.w3c.audit import audit_report
    report = sample('passed')
    if kind == 'no-suites':
        report['suites'] = []
    elif kind == 'empty-suite':
        report = sample()
    else:
        report['suites'][0]['counts']['passed'] = True
    with pytest.raises(ValueError, match='accounting'):
        audit_report(report)


@pytest.mark.parametrize('field,value', [('test_executions', 99), ('unique_test_ids', 99),
                                       ('totals', {'passed': 99, 'failed': 0, 'unsupported': 0, 'error': 0})])
def test_global_accounting_cannot_disagree_with_executed_cases(field, value):
    from tests.w3c.audit import audit_report
    report = sample('passed')
    report[field] = value
    with pytest.raises(ValueError, match='accounting'):
        audit_report(report)


def test_unknown_failure_is_not_given_a_reviewed_explanation():
    from tests.w3c.audit import audit_report
    report = sample('failed')
    report['snapshot'] = 'f' * 40
    original = deepcopy(report)
    result = audit_report(report)
    assert result['issues'][0]['classification'] == 'unreviewed'
    assert result['issues'][0]['status'] == 'failed'
    assert result['unreviewed'] == 1
    assert report == original


def test_source_hashes_record_original_fixture_bytes(tmp_path):
    from tests.w3c.test_official_reporting import manifest
    path = manifest(tmp_path, '<#p>', '<#p> a rt:TestNTriplesPositiveSyntax ; mf:action <x.nt> .')
    data = b'<urn:s> <urn:p> <urn:o> .\n'
    (tmp_path / 'x.nt').write_bytes(data)
    result = official.report_suite(path, 'nt')
    assert result['tests'][0]['action_sha256'] == sha256(data).hexdigest()
    assert result['tests'][0]['result_sha256'] is None


def test_fixture_checkout_with_spaces_is_not_a_false_failure(tmp_path):
    from tests.w3c.test_official_reporting import manifest
    root = tmp_path / 'checkout with spaces'
    root.mkdir()
    path = manifest(root, '<#p>', '<#p> a rt:TestNTriplesPositiveSyntax ; mf:action <x.nt> .')
    (root / 'x.nt').write_text('<urn:s> <urn:p> <urn:o> .')
    result = official.report_suite(path, 'nt')
    assert result['counts'] == {'passed': 1, 'failed': 0, 'unsupported': 0, 'error': 0}


def test_nonlocal_file_authority_is_an_accounted_error(tmp_path):
    from tests.w3c.test_official_reporting import manifest
    path = manifest(tmp_path, '<#p>',
                    '<#p> a rt:TestNTriplesPositiveSyntax ; mf:action <file://remote/x.nt> .')
    result = official.report_suite(path, 'nt')
    assert result['counts'] == {'passed': 0, 'failed': 0, 'unsupported': 0, 'error': 1}
    assert 'only local manifest paths' in result['tests'][0]['reason']


def test_missing_file_is_error_even_if_the_format_is_unsupported(tmp_path):
    from tests.w3c.test_official_reporting import manifest
    path = manifest(tmp_path, '<#p>', '<#p> a rt:FutureTest ; mf:action <absent.nt> .')
    result = official.report_suite(path, None)
    assert result['counts'] == {'passed': 0, 'failed': 0, 'unsupported': 0, 'error': 1}
    assert 'FileNotFoundError' in result['tests'][0]['reason']


def test_untracked_sources_are_part_of_evidence(tmp_path, monkeypatch):
    import subprocess
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args])
    git('init', '-q')
    git('-c', 'user.name=domel', '-c', 'user.email=ddooss@wp.pl',
        'commit', '--allow-empty', '-qm', 'Baseline')
    data = b'value = 42\n'
    (tmp_path / 'new.py').write_bytes(data)
    (tmp_path / 'alias.py').symlink_to('new.py')
    monkeypatch.setattr(official, 'ROOT', tmp_path)
    monkeypatch.setattr(official, 'verify_checkout', lambda path: 'a' * 40)
    monkeypatch.setattr(official, 'report_suite', lambda *a, **kw: {'counts': {}, 'tests': []})
    result = official.build_report(tmp_path)
    assert result['untracked_file_sha256'] == {
        'new.py': sha256(data).hexdigest(), 'alias.py': sha256(b'new.py').hexdigest()}


def test_archived_checkout_requires_an_explicit_lock(tmp_path):
    import subprocess
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args], text=True).strip()
    git('init', '-q')
    git('-c', 'user.name=domel', '-c', 'user.email=ddooss@wp.pl',
        'commit', '--allow-empty', '-qm', 'Baseline')
    revision = git('rev-parse', 'HEAD')
    # Keep the alternate lock outside this checkout to preserve a clean tree.
    lock = tmp_path.parent / (tmp_path.name + '.lock')
    lock.write_text(f'commit = "{revision}"\n')
    assert official.verify_checkout(tmp_path, lock=lock) == revision
    with pytest.raises(ValueError, match='locked revision|clean at'):
        official.verify_checkout(tmp_path)


@pytest.mark.parametrize('field,before_value,after_value', [
    ('regime', 'simple', 'rdfs'),
    ('recognized_datatypes', [], ['urn:datatype']),
    ('types', ['urn:PositiveEntailmentTest'], ['urn:NegativeEntailmentTest']),
    ('action', 'urn:old-input', 'urn:new-input'),
    ('result', 'urn:old-result', 'false'),
])
def test_compare_records_changed_execution_meaning_even_when_hashes_and_status_match(
        field, before_value, after_value):
    from tests.w3c.audit import compare_reports
    before, after = sample('passed', 'passed'), sample('passed', 'passed')
    before['suites'][0]['tests'][1][field] = before_value
    after['suites'][0]['tests'][1][field] = after_value
    original = deepcopy((before, after))
    delta = compare_reports(before, after)
    assert len(delta['changed']) == 1 and delta['unchanged'] == 1
    assert delta['changed'][0]['execution'][-1] == 1
    assert not delta['added'] and not delta['removed']
    assert (before, after) == original


@pytest.mark.parametrize('field', ['types', 'recognized_datatypes'])
def test_comparison_ignores_only_set_order_not_datatype_or_test_type_changes(field):
    from tests.w3c.audit import compare_reports
    before, after = sample('passed'), sample('passed')
    before['suites'][0]['tests'][0][field] = ['urn:a', 'urn:b']
    after['suites'][0]['tests'][0][field] = ['urn:b', 'urn:a']
    delta = compare_reports(before, after)
    assert delta['unchanged'] == 1 and not delta['changed']
