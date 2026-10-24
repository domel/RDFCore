"""Semantics CRD 2026-09-24 §§7–9, beyond the official manifest."""
import pytest

from rdfcore import BNode, Literal, RDF, RDFS, TripleTerm, URIRef, XSD
from rdfcore.semantics import entails
from rdfcore.datatypes import SUPPORTED_DATATYPES

S, P, O, C = map(URIRef, ('urn:s', 'urn:p', 'urn:o', 'urn:C'))


def decide(source, target, **kw):
    return entails(source, target, mode='decide', regime=kw.pop('regime', 'rdfs'), **kw)


@pytest.mark.parametrize('name', [RDF.type, RDF.reifies, RDFS.domain,
                                 RDFS.Class, RDFS.Resource, RDFS.Proposition])
def test_vocabulary_names_can_denote_boolean_values_without_changing_their_roles(name):
    assert decide([(name, RDF.type, XSD.boolean)], False, datatypes={XSD.boolean}) is False


@pytest.mark.parametrize('regime', ['rdf', 'rdfs'])
def test_alias_case_analysis_preserves_predicate_meaning_and_value_identity(regime):
    source = [(RDF.type, RDF.type, XSD.boolean),
              (S, P, Literal('true', datatype=XSD.boolean)),
              (S, P, Literal('false', datatype=XSD.boolean))]
    assert decide(source, [(S, P, RDF.type)], regime=regime, datatypes={XSD.boolean}) is True
    assert decide(source, [(S, P, O)], regime=regime, datatypes={XSD.boolean}) is False


def test_aliases_do_not_capture_target_blank_nodes_with_the_same_label():
    x = BNode('value')
    source = [(x, RDF.type, XSD.boolean), (RDF.type, RDF.type, XSD.boolean), (S, P, x)]
    assert decide(source, [(x, P, O)], datatypes={XSD.boolean}) is False


@pytest.mark.parametrize('datatype', [XSD.token, XSD.integer, XSD.decimal, RDF.JSON, RDF.HTML])
def test_individual_propositions_can_belong_to_overlapping_value_spaces(datatype):
    source = [(S, RDF.type, RDFS.Proposition), (S, RDF.type, datatype)]
    assert decide(source, False, datatypes={datatype}) is False


def test_universal_string_constraint_checks_profiles_not_just_alphabetic_samples():
    source = [(RDF.type, RDFS.domain, C), (C, RDFS.subClassOf, XSD.token)]
    assert decide(source, False, datatypes={XSD.token}) is True


def test_profile_intersection_does_not_create_an_asserted_subclass_link():
    source = [(S, RDF.type, XSD.language)]
    assert decide(source, [(S, RDF.type, XSD.token)], datatypes={XSD.language, XSD.token})
    assert decide(source, [(XSD.language, RDFS.subClassOf, XSD.token)],
                  datatypes={XSD.language, XSD.token}) is False


@pytest.mark.parametrize('parent', [RDFS.Class, RDF.Property, RDFS.Literal, RDFS.Proposition])
def test_universal_resource_classes_have_a_consistent_infinite_extension(parent):
    source = [(RDFS.Resource, RDFS.subClassOf, parent)]
    assert decide(source, False) is False
    assert decide(source, [(S, RDF.type, parent)]) is True


def test_schema_properties_can_extend_the_meaning_of_type_without_reversing_it():
    source = [(RDF.type, RDFS.subPropertyOf, P)]
    assert decide(source, [(S, P, RDFS.Resource)]) is True
    assert decide(source, [(S, P, O)]) is False


def test_all_resource_classes_cannot_be_a_finite_recognized_space():
    assert decide([(RDFS.Resource, RDFS.subClassOf, XSD.boolean)], False,
                  datatypes={XSD.boolean}) is True


@pytest.mark.parametrize('datatype', sorted(SUPPORTED_DATATYPES))
def test_constructor_image_has_the_required_cardinality_in_each_supported_datatype(datatype):
    finite = {XSD.boolean, XSD.float, XSD.double, XSD.byte, XSD.short, XSD.int, XSD.long,
              XSD.unsignedByte, XSD.unsignedShort, XSD.unsignedInt, XSD.unsignedLong,
              XSD.gMonth, XSD.gDay, XSD.gMonthDay}
    datatype = URIRef(datatype)
    assert decide([(RDFS.Proposition, RDFS.subClassOf, datatype)], False,
                  datatypes={datatype}) is (datatype in finite)


def test_an_infinite_image_does_not_select_a_particular_literal_as_a_proposition():
    x = BNode('x')
    source = [(S, P, Literal('a')), (RDFS.Proposition, RDFS.subClassOf, XSD.string)]
    assert decide(source, [(S, P, x), (x, RDF.type, RDFS.Proposition)]) is False


def test_infinite_numeric_image_is_not_replaced_by_a_finite_facet_region():
    source = [(RDFS.Proposition, RDFS.subClassOf, XSD.decimal)]
    assert decide(source, False, datatypes={XSD.decimal, XSD.integer, XSD.byte}) is False


@pytest.mark.parametrize('datatype', sorted(SUPPORTED_DATATYPES))
def test_recognized_datatype_objects_are_not_string_values(datatype):
    datatype = URIRef(datatype)
    assert decide([(datatype, RDF.type, XSD.string)], False, datatypes={datatype}) is True


def test_an_unrecognized_datatype_name_can_still_denote_an_ordinary_value():
    assert decide([(RDF.XMLLiteral, RDF.type, XSD.string)], False) is False


def test_equal_domain_and_range_names_keep_both_semantic_conditions():
    types = {XSD.nonNegativeInteger, XSD.nonPositiveInteger}
    source = [(name, RDF.type, datatype) for name in (RDFS.domain, RDFS.range) for datatype in types]
    source += [(P, RDFS.domain, C), (S, P, O)]
    assert decide(source, False, datatypes=types) is False
    assert decide(source, [(S, RDF.type, C), (O, RDF.type, C)], datatypes=types) is True


@pytest.mark.parametrize('node', [O, RDF.type])
def test_value_assignments_inside_nested_terms_do_not_change_public_grammar(node):
    x = BNode('value')
    source = [(node, RDF.type, XSD.boolean), (S, P, TripleTerm(node, P, TripleTerm(S, node, O)))]
    target = [(S, P, TripleTerm(x, P, TripleTerm(S, node, O))), (x, RDF.type, XSD.boolean)]
    assert decide(source, target, datatypes={XSD.boolean}) is True
    assert decide(source, [(node, P, O)], datatypes={XSD.boolean}) is False
    with pytest.raises(TypeError):
        TripleTerm(Literal(True), P, O)


def test_injective_constructor_values_cannot_merge_different_string_arguments():
    types = {XSD.nonNegativeInteger, XSD.nonPositiveInteger}
    source = [(P, RDFS.range, d) for d in types]
    source += [(S, P, TripleTerm(S, C, Literal(text))) for text in ('a', 'b')]
    assert decide(source, False, datatypes=types) is True


def test_injectivity_can_force_names_equal_instead_of_assuming_distinct_names():
    types = {XSD.nonNegativeInteger, XSD.nonPositiveInteger}
    source = [(P, RDFS.range, d) for d in types]
    source += [(S, P, TripleTerm(S, P, node)) for node in (O, C)]
    source += [(O, C, Literal('value'))]
    assert decide(source, False, datatypes=types) is False
    assert decide(source, [(C, C, Literal('value'))], datatypes=types) is True


def test_existential_constructor_patterns_use_the_assigned_values_unique_preimage():
    x = BNode('argument')
    source = [(P, RDFS.range, XSD.boolean), (S, P, TripleTerm(C, P, O)), (C, RDF.type, RDFS.Class)]
    assert decide(source, [(S, P, TripleTerm(x, P, O)), (x, RDF.type, RDFS.Class)],
                  datatypes={XSD.boolean}) is True
    assert decide(source, [(S, P, Literal(True))], datatypes={XSD.boolean}) is False


def test_self_referential_constructor_values_do_not_trigger_an_occurs_check():
    types = {XSD.nonNegativeInteger, XSD.nonPositiveInteger}
    source = [(P, RDFS.range, d) for d in types] + [(S, RDF.type, d) for d in types]
    source += [(S, P, TripleTerm(S, P, S))]
    assert decide(source, False, datatypes=types) is False


def test_constructor_interpretations_do_not_leak_into_a_later_proof_call():
    term = TripleTerm(S, C, O)
    assert decide([(P, RDFS.range, XSD.boolean), (S, P, term)], False,
                  datatypes={XSD.boolean}) is False
    assert entails([(S, P, term)], [(S, P, Literal(True))]) is False


def test_nested_public_calls_do_not_inherit_a_callers_constructor_interpretation():
    from rdfcore import semantics
    term = TripleTerm(S, C, O)
    with semantics._interpreted_applications([(Literal(True), (S, C, O))]):
        assert entails([(S, P, term)], [(S, P, Literal(True))]) is False


def test_known_ground_constructor_results_are_constants_not_existential_variables():
    first, second = TripleTerm(S, C, Literal('a')), TripleTerm(S, C, Literal('b'))
    source = [(RDF.type, RDF.type, XSD.boolean), (S, P, first), (O, P, second)]
    assert decide(source, [(S, P, second)], datatypes={XSD.boolean}) is False


@pytest.mark.parametrize('alias_type', [False, True])
@pytest.mark.parametrize('depth', [1, 2])
def test_constructor_witness_uses_interpreted_schema_vocabulary(alias_type, depth):
    # Each constrained name must denote integer zero. P therefore has exactly
    # subClassOf's meaning, even though the asserted predicate is ordinary.
    types = {XSD.nonNegativeInteger, XSD.nonPositiveInteger}
    names = [P, RDFS.subClassOf] + ([RDF.type] if alias_type else [])
    source = [(name, RDF.type, datatype) for name in names for datatype in types]
    source.append((RDFS.Resource, P, RDFS.Class))
    term = O
    for _ in range(depth):
        term = TripleTerm(S, RDF.type, term)
    assert decide(source, [(BNode('class'), RDFS.subClassOf, term)],
                  datatypes=types, max_steps=1000000) is True


def test_aliased_infinite_superproperty_is_not_a_finite_countermodel():
    from rdfcore.semantics import UnsupportedEntailment
    types = {XSD.nonNegativeInteger, XSD.nonPositiveInteger}
    q = URIRef('urn:superproperty')
    source = [(name, RDF.type, datatype) for name in (P, RDFS.subClassOf) for datatype in types]
    source += [(RDFS.Resource, P, RDFS.Class), (RDFS.subClassOf, RDFS.subPropertyOf, q)]
    # Constructor totality plus reflexive subclass edges makes this true.
    # Until superproperty witnesses are supported, it must stay unknown,
    # rather than claiming the finite sample is a negative certificate.
    with pytest.raises(UnsupportedEntailment):
        decide(source, [(BNode('class'), q, TripleTerm(S, RDF.type, O))],
               datatypes=types, max_steps=1000000)
