from pathlib import Path

from tests.w3c.semantic_audit import audit_report
from tests.w3c.semantic_coverage import coverage_report


def test_each_reviewed_obligation_has_a_reference_and_existing_evidence():
    report = audit_report()
    root = Path(__file__).resolve().parents[2]
    rows = report['obligations']
    assert len({r['id'] for r in rows}) == len(rows)
    for row in rows:
        assert row['reference'].startswith('https://www.w3.org/TR/2026/CRD-rdf12-semantics-20260924/#')
        assert (root / row['evidence']).is_file(), row
        assert row['requirement'] and row['reason'] and row['implementation']


def test_review_completion_does_not_hide_incomplete_implementation():
    report = audit_report()
    assert report['implementation_complete'] is False
    assert {'injective-it', 'proposition-image', 'rdfs-entailment'} <= {
        r['id'] for r in report['obligations'] if r['status'] == 'partial'}
    assert coverage_report([])['normative_audit'] == report


def test_recognition_strengthens_entailment():
    from rdfcore import Literal, URIRef, XSD
    from rdfcore.semantics import entails
    s, p = URIRef('urn:s'), URIRef('urn:p')
    source = [(s, p, Literal('01', datatype=XSD.integer, normalize=False))]
    target = [(s, p, Literal('1', datatype=XSD.integer, normalize=False))]
    assert entails(source, target, mode='decide', datatypes=()) is False
    assert entails(source, target, mode='decide', datatypes=(XSD.integer,)) is True


def test_rdfs_strengthens_rdf_entailment():
    from rdfcore import RDF, RDFS, URIRef
    from rdfcore.semantics import entails
    target = [(URIRef('urn:s'), RDF.type, RDFS.Resource)]
    assert entails([], target, regime='rdf', mode='decide') is False
    assert entails([], target, regime='rdfs', mode='decide') is True
