from pathlib import Path

from rdfcore import Graph, URIRef
from tests.w3c.runner import run_manifest


def test_official_public_id_does_not_depend_on_checkout_name(tmp_path):
    from tests.w3c.runner import _canonical_public_id
    suffix = 'rdf/rdf11/rdf-xml/xmlbase/test014.rdf'
    expected = 'https://w3c.github.io/rdf-tests/' + suffix
    assert _canonical_public_id(tmp_path / 'arbitrary-clone' / suffix) == expected
    assert _canonical_public_id(tmp_path / 'rdf-tests' / suffix) == expected


def test_runner_dispatches_local_positive_and_negative_ntriples(tmp_path: Path):
    positive = tmp_path / "positive.nt"
    negative = tmp_path / "negative.nt"
    positive.write_text('<http://e/s> <http://e/p> "ok" .\n', encoding="utf-8")
    negative.write_text('<http://e/s> <http://e/p> "unterminated .\n', encoding="utf-8")
    manifest = tmp_path / "manifest.ttl"
    manifest.write_text('''
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
        @prefix rdft: <http://www.w3.org/ns/rdftest#> .
        <> a mf:Manifest ; mf:entries ( <#p> <#n> ) .
        <#p> a rdft:TestNTriplesPositiveSyntax ; mf:name "p" ; mf:action <positive.nt> .
        <#n> a rdft:TestNTriplesNegativeSyntax ; mf:name "n" ; mf:action <negative.nt> .
    ''', encoding="utf-8")
    assert run_manifest(manifest, "nt") == {"p": True, "n": True}
