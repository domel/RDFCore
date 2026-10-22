from pathlib import Path

import pytest

from tests.w3c.official import inventory, report_suite, verify_checkout


def manifest(tmp_path, entries, declarations, include=""):
    path = tmp_path / "manifest.ttl"
    path.write_text('''@prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
@prefix rt: <http://www.w3.org/ns/rdftest#> .
<> a mf:Manifest ; mf:entries (''' + entries + ") " + include + " .\n" + declarations)
    return path


def test_unknown_type_and_missing_action_are_not_success(tmp_path):
    path = manifest(tmp_path, "<#u> <#m>", '''
<#u> a rt:FutureTest ; mf:name "unknown" ; mf:action <x.nt> .
<#m> a rt:TestNTriplesPositiveSyntax ; mf:name "missing" .''')
    (tmp_path / 'x.nt').write_text('<urn:s> <urn:p> <urn:o> .')
    report = report_suite(path, "nt")
    assert report["counts"] == {"passed": 0, "failed": 0, "unsupported": 2, "error": 0}
    assert report["total"] == 2


def test_semantic_resource_limit_is_reported_distinctly(tmp_path, monkeypatch):
    from rdfcore import semantics

    path = manifest(tmp_path, '<#p>', '''
<#p> a mf:PositiveEntailmentTest ; mf:action <x.nt> ; mf:result <x.nt> .''')
    (tmp_path / 'x.nt').write_text('<urn:s> <urn:p> <urn:o> .')

    def exhausted(*args, **kwargs):
        raise semantics.EntailmentResourceLimit('test work limit')

    monkeypatch.setattr(semantics, 'entails', exhausted)
    report = report_suite(path, 'semantics')
    assert report['counts'] == {'passed': 0, 'failed': 0, 'unsupported': 1, 'error': 0}
    assert report['tests'][0]['reason'] == 'EntailmentResourceLimit: test work limit'


def test_duplicate_names_are_executed_independently(tmp_path):
    path = manifest(tmp_path, "<#a> <#b>", '''
<#a> a rt:TestNTriplesPositiveSyntax ; mf:name "same" ; mf:action <x.nt> .
<#b> a rt:TestNTriplesPositiveSyntax ; mf:name "same" ; mf:action <bad.nt> .''')
    (tmp_path / "x.nt").write_text('<urn:s> <urn:p> <urn:o> .')
    (tmp_path / "bad.nt").write_text('not RDF')
    report = report_suite(path, "nt")
    assert report["counts"] == {"passed": 1, "failed": 1, "unsupported": 0, "error": 0}
    assert len({test['id'] for test in report['tests']}) == 2
    failure, = [test for test in report['tests'] if test['status'] == 'failed']
    assert 'ParserError' in failure['reason']


def test_include_lists_and_direct_includes_are_inventoried(tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    manifest(child, "<#p>", '<#p> a rt:TestNTriplesPositiveSyntax ; mf:action <x.nt> .')
    (child / "x.nt").write_text('<urn:s> <urn:p> <urn:o> .')
    for include in ('; mf:include ( <child/manifest.ttl> )', '; mf:include <child/manifest.ttl>'):
        path = manifest(tmp_path, "", "", include)
        assert len(inventory(path)) == 1
        assert report_suite(path, "nt")["counts"]["passed"] == 1


def test_unavailable_format_never_passes_negative_tests(tmp_path):
    path = manifest(tmp_path, "<#n>", '<#n> a rt:TestXMLNegativeSyntax ; mf:action <x.rdf> .')
    (tmp_path / 'x.rdf').write_text('not XML')
    assert report_suite(path, None)["counts"]["unsupported"] == 1


def test_checkout_pin_mismatch_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="checkout"):
        verify_checkout(tmp_path)


def test_include_cycle_is_reported_as_error(tmp_path):
    path = manifest(tmp_path, "", "", '; mf:include ( <manifest.ttl> )')
    report = report_suite(path, "nt")
    assert report["suite_error"]
    assert report["counts"]["passed"] == 0


def test_missing_action_file_is_error_not_negative_success(tmp_path):
    path = manifest(tmp_path, '<#n>', '<#n> a rt:TestNTriplesNegativeSyntax ; mf:action <absent.nt> .')
    report = report_suite(path, 'nt')
    assert report['counts'] == {'passed': 0, 'failed': 0, 'unsupported': 0, 'error': 1}


def test_missing_manifest_is_suite_error(tmp_path):
    report = report_suite(tmp_path / 'absent.ttl', 'nt')
    assert report['suite_error']
    assert not report['total']


def test_staged_changes_are_in_report_fingerprint(tmp_path, monkeypatch):
    from tests.w3c import official
    import hashlib
    import subprocess
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args])
    git('init', '-q')
    git('-c', 'user.name=domel', '-c', 'user.email=ddooss@wp.pl', 'commit', '--allow-empty', '-qm', 'Baseline')
    (tmp_path / 'changed.py').write_text('changed = True\n')
    git('add', 'changed.py')
    monkeypatch.setattr(official, 'ROOT', tmp_path)
    monkeypatch.setattr(official, 'verify_checkout', lambda path: 'a' * 40)
    monkeypatch.setattr(official, 'report_suite', lambda *args, **kwargs: {'counts': {}, 'tests': []})
    report = official.build_report(tmp_path)
    expected = hashlib.sha256(git('diff', '--binary', 'HEAD')).hexdigest()
    assert report['tracked_diff_sha256'] == expected
    assert expected != hashlib.sha256(b'').hexdigest()
    assert len(report['suites']) == 12
    assert all(suite['reference_document'].startswith('https://www.w3.org/TR/') for suite in report['suites'])
    assert {suite['category'] for suite in report['suites']} == {'syntax', 'entailment'}
    assert report['execution_profile'] == 'default'
    assert report['parser_options'] == {}
    legacy = official.build_report(tmp_path, legacy_w3c=True)
    assert legacy['execution_profile'] == 'legacy-w3c-xml'
    assert legacy['parser_options'] == {'legacy_w3c': True}


def test_xml_recovery_report_does_not_rewrite_expected_results(tmp_path):
    path = manifest(tmp_path, '<#x>', '<#x> a rt:TestXMLEval ; mf:action <x.rdf> ; mf:result <x.nt> .')
    (tmp_path / 'x.rdf').write_text('''<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:e="urn:e:">
    <rdf:Description rdf:about="urn:s"><e:p rdf:parseType="Literal"><br/></e:p></rdf:Description></rdf:RDF>''')
    expected = '<urn:s> <urn:e:p> "<br></br>"^^<http://www.w3.org/1999/02/22-rdf-syntax-ns#XMLLiteral> .'
    (tmp_path / 'x.nt').write_text(expected)
    assert report_suite(path, 'xml')['counts']['failed'] == 1
    assert report_suite(path, 'xml', legacy_w3c=True)['counts']['passed'] == 1
    assert (tmp_path / 'x.nt').read_text() == expected
    (tmp_path / 'x.nt').write_text('')
    assert report_suite(path, 'xml', legacy_w3c=True)['counts']['failed'] == 1


def test_invalid_pin_has_explicit_error(tmp_path, monkeypatch):
    from tests.w3c import official
    lock = tmp_path / 'manifest.lock'
    lock.write_text('commit = "not-a-revision"\n')
    monkeypatch.setattr(official, 'LOCK', lock)
    with pytest.raises(ValueError, match='hexadecimal'):
        official.verify_checkout(tmp_path)
