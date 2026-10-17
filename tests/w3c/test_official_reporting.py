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
    report = report_suite(path, "nt")
    assert report["counts"] == {"passed": 0, "failed": 0, "unsupported": 2, "error": 0}
    assert report["total"] == 2


def test_duplicate_names_are_executed_independently(tmp_path):
    path = manifest(tmp_path, "<#a> <#b>", '''
<#a> a rt:TestNTriplesPositiveSyntax ; mf:name "same" ; mf:action <x.nt> .
<#b> a rt:TestNTriplesPositiveSyntax ; mf:name "same" ; mf:action <bad.nt> .''')
    (tmp_path / "x.nt").write_text('<urn:s> <urn:p> <urn:o> .')
    (tmp_path / "bad.nt").write_text('not RDF')
    report = report_suite(path, "nt")
    assert report["counts"] == {"passed": 1, "failed": 1, "unsupported": 0, "error": 0}
    assert len({test['id'] for test in report['tests']}) == 2


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
    assert report_suite(path, None)["counts"]["unsupported"] == 1


def test_checkout_pin_mismatch_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="checkout"):
        verify_checkout(tmp_path)


def test_include_cycle_is_reported_as_error(tmp_path):
    path = manifest(tmp_path, "", "", '; mf:include ( <manifest.ttl> )')
    report = report_suite(path, "nt")
    assert report["suite_error"]
    assert report["counts"]["passed"] == 0
