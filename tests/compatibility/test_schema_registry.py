"""Pinned RDFLib names and additive Schema WD 2026-10-22 registry entries."""
import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('name', ['CompoundLiteral', 'direction', 'language', 'PlainLiteral'])
def test_shared_registry_attributes_match_pinned_reference(name):
    assert rdflib.__version__ == '7.6.0'
    assert str(getattr(rdfcore.RDF, name)) == str(getattr(rdflib.RDF, name))
    assert getattr(rdfcore.RDF, name) == rdfcore.RDF[name]


def test_rdf12_registry_addition_does_not_claim_reference_support():
    with pytest.raises(AttributeError):
        getattr(rdflib.RDF, 'langRange')
    assert rdfcore.RDF.langRange == rdfcore.URIRef(str(rdfcore.RDF)+'langRange')


def test_registry_presence_does_not_add_external_reasoning_rules():
    from rdfcore.semantics import entails
    assert entails([], [(rdfcore.RDF.CompoundLiteral, rdfcore.RDF.type, rdfcore.RDFS.Class)],
                   regime='rdfs', mode='decide') is False
