"""Semantics CRD 2026-09-24 §§5/8/9; Schema WD 2026-10-22.

These tests do not turn a finite rule closure into a general decision procedure.
"""
import pytest

from rdfcore import BNode, Literal, RDF, RDFS, TripleTerm, URIRef, XSD
from rdfcore.semantics import EntailmentResourceLimit, UnsupportedEntailment, entails

S, P, O, Q, C, D = map(URIRef, ('urn:s', 'urn:p', 'urn:o', 'urn:q', 'urn:C', 'urn:D'))


def decide(source, target, regime='rdfs', **kwargs):
    return entails(source, target, regime=regime, mode='decide', **kwargs)


@pytest.mark.parametrize('name', [
    'horst-01-subClassOf-intensional',
    'rdfs-container-membership-superProperty-test001',
    'rdfs-domain-and-range-intensionality-range',
    'rdfs-domain-and-range-intensionality-domain',
    'rdfs-subClassOf-a-Property-test001',
    *(f'statement-entailment-test{n:03}' for n in range(1, 5)),
])
def test_remaining_historical_semantic_cases_have_actual_decisions(name):
    from tests.w3c.semantic_contract import CASES
    case = CASES[name]
    assert decide(case.premise, case.conclusion, case.regime, datatypes=case.datatypes) is case.expected


@pytest.mark.parametrize('regime', ['rdf', 'rdfs'])
def test_nested_term_predicates_are_properties_without_inner_assertions(regime):
    term = TripleTerm(S, P, TripleTerm(O, Q, Literal('v')))
    source = [(S, RDF.reifies, term)]
    assert decide(source, [(P, RDF.type, RDF.Property), (Q, RDF.type, RDF.Property)], regime)
    assert decide(source, [(S, P, TripleTerm(O, Q, Literal('v')))], regime) is False
    assert decide(source, [(O, Q, Literal('v'))], regime) is False


def test_proposition_exists_even_in_the_empty_graph_but_is_not_asserted():
    x = BNode('x')
    assert decide([], [(x, RDF.type, RDFS.Proposition)]) is True
    assert decide([], [(S, RDF.type, RDFS.Proposition)]) is False
    assert decide([], [(S, P, O)]) is False
    # Proposition has no special semantics in RDF entailment.
    assert decide([], [(x, RDF.type, RDFS.Proposition)], 'rdf') is False


def test_constructor_existence_is_not_limited_to_terms_already_in_the_premise():
    source = [(RDFS.Resource, RDFS.subClassOf, RDFS.Class)]
    term = TripleTerm(S, RDF.type, O)
    x = BNode('class')
    assert decide(source, [(x, RDFS.subClassOf, term)]) is True
    prop = BNode('property')
    nested = TripleTerm(prop, RDF.type, TripleTerm(prop, RDF.type, O))
    assert decide(source, [(prop, RDF.type, RDF.Property), (x, RDFS.subClassOf, nested)]) is True


def test_constructor_witness_does_not_invent_its_predicate_property():
    source = [(RDFS.Resource, RDFS.subClassOf, RDFS.Class)]
    with pytest.raises(UnsupportedEntailment):
        decide(source, [(BNode('class'), RDFS.subClassOf, TripleTerm(S, P, O))])


def test_named_propositions_and_literal_reifiers_are_not_automatically_inconsistent():
    assert decide([(S, RDF.type, RDFS.Proposition)], False) is False
    assert decide([(S, RDF.reifies, Literal('value'))], False) is False
    assert decide([(S, RDF.reifies, O)], [(O, RDF.type, RDFS.Proposition)]) is True
    assert decide([(S, RDF.reifies, O)], [(S, P, O)]) is False


def test_resources_and_container_axioms_are_query_targeted_not_source_assertions():
    assert decide([], [(S, RDF.type, RDFS.Resource)]) is True
    assert decide([], [(RDF['_99999'], RDF.type, RDFS.ContainerMembershipProperty)]) is True
    assert decide([], [(RDF['_99999'], RDFS.subPropertyOf, RDFS.member)]) is True
    assert decide([], [(RDF['_01'], RDF.type, RDF.Property)]) is False
    assert decide([], [(P, RDF.type, RDF.Property)]) is False


def test_intensional_schema_does_not_follow_from_coinciding_extensions():
    source = [(P, RDFS.range, C), (C, RDFS.subClassOf, D)]
    assert decide(source, [(P, RDFS.range, D)]) is False
    assert decide(source + [(S, P, O)], [(O, RDF.type, D)]) is True
    assert decide([(C, RDF.type, RDFS.Class), (RDF.type, RDFS.domain, D)],
                  [(C, RDFS.subClassOf, D)]) is False


def test_one_mapping_correlates_blank_nodes_across_all_conclusions():
    x = BNode('x')
    source = [(S, P, O), (O, Q, S)]
    assert decide(source, [(x, P, O), (x, Q, S)]) is False
    assert decide(source, [(x, P, O), (O, Q, x)]) is True


def test_multiple_reifiers_and_multiple_targets_are_not_functional():
    a, b = TripleTerm(S, P, O), TripleTerm(O, Q, S)
    source = [(S, RDF.reifies, a), (S, RDF.reifies, b), (O, RDF.reifies, a)]
    assert decide(source, False) is False
    assert decide(source, [(O, RDF.reifies, b)]) is False
    assert decide(source, [(S, P, O)]) is False


def test_collection_and_container_conventions_do_not_add_semantic_restrictions():
    source = [(S, RDF.first, O), (S, RDF.first, C), (S, RDF.rest, S),
              (S, RDF.type, RDF.Bag), (S, RDF.type, RDF.Seq), (S, RDF['_3'], O)]
    assert decide(source, False) is False
    assert decide(source, [(S, RDFS.member, O)]) is True
    assert decide(source, [(S, RDF['_1'], O)]) is False
    assert decide(source, [(S, RDF['_2'], O)]) is False


def test_literal_range_clash_can_be_found_through_a_custom_class():
    source = [(P, RDFS.range, C), (C, RDFS.subClassOf, XSD.string),
              (S, P, Literal('v', lang='en'))]
    assert decide(source, False) is True
    assert decide(source, [(S, Q, O)]) is True


def test_propositions_can_overlap_literal_values_but_cannot_fit_a_finite_space():
    # A proposition is an element of the IT image, not a disjoint fourth
    # semantic value family. Do not declare these inputs inconsistent.
    source = [(S, RDF.type, RDFS.Proposition), (S, RDF.type, XSD.boolean)]
    assert decide(source, False, datatypes={XSD.boolean}) is False
    # Every proposition is forced into a finite space. Neither sampling nor
    # a finite Horn closure is a completeness proof for this requirement.
    assert decide([(RDFS.Proposition, RDFS.subClassOf, XSD.boolean)], False,
                  datatypes={XSD.boolean}) is True


@pytest.mark.parametrize('datatype', [XSD.boolean, XSD.byte, XSD.float, XSD.double, XSD.gMonth])
def test_an_infinite_proposition_image_cannot_be_a_finite_datatype_class(datatype):
    assert decide([(RDFS.Proposition, RDFS.subClassOf, datatype)], False,
                  datatypes={datatype}) is True


def test_genuinely_unresolved_fixed_datatype_and_constructor_queries_stay_unknown():
    with pytest.raises(UnsupportedEntailment):
        decide([(RDF.type, RDF.type, XSD.boolean)], False, datatypes={XSD.boolean})
    with pytest.raises(UnsupportedEntailment):
        decide([(RDFS.Resource, RDFS.subClassOf, RDFS.Class)],
               [(BNode('c'), RDFS.subClassOf, TripleTerm(BNode('s'), P, O))])


def test_exhaustion_is_not_non_entailment():
    with pytest.raises(EntailmentResourceLimit):
        decide([(C, RDF.type, RDFS.Class)], False, max_steps=10)


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
def test_schema_decisions_preserve_graph_state(tmp_path, backend):
    from rdfcore import Dataset, SQLiteStore
    store = SQLiteStore(tmp_path / 'schema.db') if backend == 'sqlite' else 'default'
    dataset = Dataset(store=store)
    try:
        graph = dataset.graph(URIRef('urn:g'))
        graph.add((C, RDF.type, RDFS.Class))
        graph.add((D, RDFS.subClassOf, C))
        before = set(dataset.quads())
        assert decide(graph, False) is False
        assert decide(graph, [(C, RDFS.subClassOf, D)]) is False
        assert set(dataset.quads()) == before
        assert len(dataset.default_graph) == 0
    finally:
        dataset.close()
