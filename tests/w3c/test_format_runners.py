from pathlib import Path

from tests.w3c.runner import run_manifest


def test_runner_dispatches_turtle_and_trig_manifest_classes(tmp_path: Path):
    # The full W3C snapshot is exercised by the external conformance command;
    # this local fixture verifies both syntax and eval dispatch paths.
    (tmp_path / "input.ttl").write_text('@prefix ex: <http://e/> . ex:s ex:p "x" .', encoding="utf-8")
    (tmp_path / "expected.nt").write_text('<http://e/s> <http://e/p> "x" .\n', encoding="utf-8")
    (tmp_path / "bad.ttl").write_text('ex:s ex:p .', encoding="utf-8")
    (tmp_path / "manifest.ttl").write_text('''
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
        @prefix rdft: <http://www.w3.org/ns/rdftest#> .
        <> a mf:Manifest ; mf:entries ( <#p> <#n> <#e> ) .
        <#p> a rdft:TestTurtlePositiveSyntax ; mf:name "p" ; mf:action <input.ttl> .
        <#n> a rdft:TestTurtleNegativeSyntax ; mf:name "n" ; mf:action <bad.ttl> .
        <#e> a rdft:TestTurtleEval ; mf:name "e" ; mf:action <input.ttl> ; mf:result <expected.nt> .
    ''', encoding="utf-8")
    assert run_manifest(tmp_path / "manifest.ttl", "turtle") == {"p": True, "n": True, "e": True}


def test_runner_follows_mf_include_and_c14n(tmp_path: Path):
    (tmp_path / "input.nt").write_text('<http://e/s> <http://e/p> "x" .\n', encoding="utf-8")
    (tmp_path / "expected.nt").write_text('<http://e/s> <http://e/p> "x" .\n', encoding="utf-8")
    (tmp_path / "included.ttl").write_text('''
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
        @prefix rdft: <http://www.w3.org/ns/rdftest#> .
        <> a mf:Manifest ; mf:entries ( <#c> ) .
        <#c> a rdft:TestNTriplesC14N ; mf:name "c" ; mf:action <input.nt> ; mf:result <expected.nt> .
    ''', encoding="utf-8")
    (tmp_path / "manifest.ttl").write_text('''
        @prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
        <> a mf:Manifest ; mf:include <included.ttl> .
    ''', encoding="utf-8")
    assert run_manifest(tmp_path / "manifest.ttl", "nt") == {"c": True}


def test_runner_uses_rdf12_parser_for_versioned_format(tmp_path: Path):
    (tmp_path / "input.nt").write_text(
        '<http://e/s> <http://e/p> <<( <http://e/a> <http://e/b> <http://e/c> )>> .\n',
        encoding="utf-8",
    )
    (tmp_path / "manifest.ttl").write_text('''
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> .
        @prefix rdft: <http://www.w3.org/ns/rdftest#> .
        <> a mf:Manifest ; mf:entries ( <#p> ) .
        <#p> a rdft:TestNTriplesPositiveSyntax ; mf:name "rdf12" ; mf:action <input.nt> .
    ''', encoding="utf-8")
    assert run_manifest(tmp_path / "manifest.ttl", "nt12") == {"rdf12": True}
