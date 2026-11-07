"""Registry IRIs: RDFLib 7.6.0 and Schema WD 2026-10-23 §§A.1/A.2.

The registries are informative; this does not test entailment completeness.
"""

from inspect import get_annotations

import rdfcore
import rdflib


def test_registry_presence_does_not_add_external_reasoning_rules():
    from rdfcore.semantics import entails

    assert (
        entails(
            [],
            [(rdfcore.RDF.CompoundLiteral, rdfcore.RDF.type, rdfcore.RDFS.Class)],
            regime="rdfs",
            mode="decide",
        )
        is False
    )


def test_registry_names_and_iris_match_reference_and_rdf12():
    assert rdflib.__version__ == "7.6.0"
    additions = {
        "RDF": {
            "dirLangString",
            "reifies",
            "langRange",
            "PropositionForm",
            "propositionFormSubject",
            "propositionFormPredicate",
            "propositionFormObject",
        },
        "RDFS": {"Proposition"},
    }
    for namespace, base in (
        ("RDF", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
        ("RDFS", "http://www.w3.org/2000/01/rdf-schema#"),
    ):
        reference, core = getattr(rdflib, namespace), getattr(rdfcore, namespace)
        shared = set(get_annotations(reference))
        assert str(core) == str(reference) == base
        assert core._TERMS == shared | additions[namespace]
        for name in shared:
            assert (
                str(getattr(core, name)) == str(getattr(reference, name)) == base + name
            )
        for name in shared | additions[namespace]:
            actual = getattr(core, name)
            assert isinstance(actual, rdfcore.URIRef)
            assert str(actual) == base + name
            assert actual == core[name]
