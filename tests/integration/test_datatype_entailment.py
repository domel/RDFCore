"""T38: Semantics CRD 2026-09-24 §§7–9; Concepts CR 2026-04-07 §5/A.

These section-derived cases supplement, not replace, the official manifests.
"""

import pytest

from rdfcore import BNode, Literal, RDF, RDFS, TripleTerm, URIRef, XSD
from rdfcore.semantics import EntailmentResourceLimit, UnsupportedEntailment, entails

S, P, O, Q, V = map(URIRef, ('urn:s', 'urn:p', 'urn:o', 'urn:q', 'urn:v'))


def lit(text, datatype):
    return Literal(text, datatype=datatype, normalize=False)


def decide(source, target, *, regime='rdfs', datatypes=()):
    return entails(source, target, regime=regime, datatypes=set(datatypes), mode='decide')


@pytest.mark.parametrize('source_type,target_type,text,expected', [
    (XSD.integer, XSD.decimal, '25', True),
    (XSD.integer, XSD.byte, '127', True),
    (XSD.integer, XSD.byte, '128', False),
    (XSD.decimal, XSD.integer, '1.5', False),
    (XSD.boolean, XSD.integer, 'true', False),
    (XSD.float, XSD.double, '1', False),
    (XSD.double, RDF.JSON, 'NaN', True),
    (RDF.JSON, XSD.string, '"text"', True),
    (RDF.JSON, XSD.boolean, 'true', True),
    (RDF.JSON, XSD.double, '1', True),
    (RDF.JSON, XSD.integer, '1', False),
    (RDF.JSON, XSD.string, '[]', False),
    (RDF.JSON, XSD.string, '"\\u0000"', False),
    (RDF.HTML, RDF.XMLLiteral, 'text', True),
    (RDF.XMLLiteral, RDF.HTML, '<a/>', True),
    (XSD.string, RDF.HTML, 'text', False),
    (XSD.string, XSD.token, 'a b', True),
    (XSD.string, XSD.token, ' a ', False),
    (XSD.dateTime, XSD.dateTimeStamp, '2026-10-22T12:00:00Z', True),
    (XSD.dateTime, XSD.dateTimeStamp, '2026-10-22T12:00:00', False),
    (XSD.duration, XSD.dayTimeDuration, 'PT1S', True),
    (XSD.duration, XSD.yearMonthDuration, 'P1DT1S', False),
])
def test_recognized_value_space_membership(source_type, target_type, text, expected):
    value = lit(text, source_type)
    source = [(S, P, value)]
    x = BNode('value')
    target = [(S, P, x), (x, RDF.type, target_type)]
    assert decide(source, target, regime='rdf', datatypes={source_type, target_type}) is expected


@pytest.mark.parametrize('left,right', [
    (XSD.decimal, XSD.integer), (XSD.positiveInteger, XSD.byte),
    (XSD.string, XSD.token), (XSD.normalizedString, XSD.token),
    (XSD.NCName, XSD.language), (XSD.dateTime, XSD.dateTimeStamp),
])
def test_type_negatives_use_distinguishing_values_not_only_default_samples(left, right):
    assert decide([(V, RDF.type, left)], [(V, RDF.type, right)], regime='rdf',
                  datatypes={left, right}) is False


def test_nested_simple_d_terms_have_value_aware_negative_decisions():
    left = TripleTerm(S, P, TripleTerm(O, Q, lit('01', XSD.integer)))
    right = TripleTerm(S, P, TripleTerm(O, Q, lit('2', XSD.integer)))
    assert decide([(S, P, left)], [(S, P, right)], regime='simple', datatypes={XSD.integer}) is False
    assert decide([(S, P, left)], [(O, Q, lit('1', XSD.integer))],
                  regime='simple', datatypes={XSD.integer}) is False


@pytest.mark.parametrize('value', [
    lit('v', RDF.langString), lit('v', RDF.dirLangString),
    Literal('v', lang='en-abcdefghi'), Literal('\ud800'),
])
def test_malformed_rdf_literal_is_not_a_datatype_inconsistency(value):
    with pytest.raises(TypeError, match='literal|language|scalar'):
        decide([(S, P, value)], False)
    # The RDFLib-compatible constructor and legacy proof path are unchanged.
    assert entails([(S, P, value)], []) is True


def test_legal_language_literals_have_no_ill_typed_lexical_forms():
    assert decide([(S, P, Literal('\0', lang='en'))], False) is False
    assert decide([(S, P, Literal('\0', lang='en', direction='rtl'))], False) is False


@pytest.mark.parametrize('value,datatype', [
    (lit('25', XSD.integer), XSD.string),
    (Literal('25'), XSD.integer),
    (Literal('v'), RDF.langString),
    (Literal('v', lang='en'), RDF.dirLangString),
    (Literal('v', lang='en', direction='rtl'), RDF.langString),
    (lit('[]', RDF.JSON), XSD.string),
    (lit('<a/>', RDF.XMLLiteral), XSD.string),
    (lit('<a>', RDF.HTML), XSD.string),
])
def test_range_clash_is_inconsistency_not_literal_conversion(value, datatype):
    recognized = {datatype, value.datatype or XSD.string}
    source = [(S, P, value), (P, RDFS.range, datatype)]
    assert decide(source, False, datatypes=recognized) is True
    assert decide(source, [(O, Q, S)], datatypes=recognized) is True
    # domain/range have no built-in meaning in RDF or simple entailment.
    assert decide(source, False, regime='simple', datatypes=recognized) is False


def test_compatible_datatype_subclass_is_consistent_but_not_automatically_asserted():
    source = [(XSD.integer, RDFS.subClassOf, XSD.decimal)]
    assert decide(source, False, datatypes={XSD.integer, XSD.decimal}) is False
    assert decide([(XSD.string, RDFS.subClassOf, XSD.integer)], False,
                  datatypes={XSD.string, XSD.integer}) is True
    assert decide([], source, datatypes={XSD.integer, XSD.decimal}) is False


def test_disjoint_ranges_force_empty_property_not_subproperty_assertion():
    source = [(P, RDF.type, RDF.Property), (Q, RDF.type, RDF.Property),
              (P, RDFS.range, XSD.integer), (P, RDFS.range, XSD.string)]
    assert decide(source, False, datatypes={XSD.integer, XSD.string}) is False
    assert decide(source, [(P, RDFS.subPropertyOf, Q)], datatypes={XSD.integer, XSD.string}) is False
    assert decide(source + [(S, P, O)], False, datatypes={XSD.integer, XSD.string}) is True


@pytest.mark.parametrize('regime', ['rdf', 'rdfs'])
def test_boolean_finite_space_requires_every_possible_assignment(regime):
    source = [(S, P, lit('true', XSD.boolean)), (S, P, lit('false', XSD.boolean)),
              (V, RDF.type, XSD.boolean)]
    assert decide(source, [(S, P, V)], regime=regime, datatypes={XSD.boolean}) is True
    assert decide(source[1:], [(S, P, V)], regime=regime, datatypes={XSD.boolean}) is False
    source += [(V, RDF.type, XSD.integer)]
    assert decide(source, False, regime=regime, datatypes={XSD.boolean, XSD.integer}) is True


def test_intersection_checks_integer_bounds_and_domain_propagation():
    source = [(V, RDF.type, XSD.positiveInteger), (V, RDF.type, XSD.nonPositiveInteger)]
    assert decide(source, False, regime='rdf', datatypes={XSD.positiveInteger, XSD.nonPositiveInteger}) is True
    source = [(P, RDFS.domain, XSD.boolean), (S, RDF.type, XSD.integer), (S, P, O)]
    assert decide(source, False, datatypes={XSD.boolean, XSD.integer}) is True


def test_unrecognized_range_and_explicit_d_set_do_not_guess_inconsistency():
    source = [(S, P, lit('flargh', XSD.integer)), (P, RDFS.range, URIRef('urn:datatype'))]
    assert decide(source, []) is True
    # T39's free-extension model can certify consistency without recognizing
    # either the opaque literal's datatype or the custom range class.
    assert decide(source, False) is False
    # An unrecognized literal can denote a string even if its lexical form
    # would be invalid were its datatype recognized.
    source = [(S, P, lit('flargh', XSD.integer)), (P, RDFS.range, XSD.string)]
    assert decide(source, False) is False


@pytest.mark.parametrize('value', [
    lit('0', XSD.integer), Literal('a'), Literal('value', lang='en'),
    Literal('value', lang='en', direction='ltr'), lit('--10Z', XSD.gMonth),
    lit('---22Z', XSD.gDay), lit('--10-22Z', XSD.gMonthDay),
])
def test_one_observed_value_does_not_cover_a_datatype_space(value):
    datatype = value.datatype or (RDF.dirLangString if value.direction else
                                  RDF.langString if value.language else XSD.string)
    source = [(S, P, value), (V, RDF.type, datatype)]
    assert decide(source, [(S, P, V)], regime='rdf', datatypes={datatype}) is False


def test_typing_axioms_and_intersection_witnesses_do_not_assert_embedded_triples():
    x = BNode('x')
    assert decide([], [(x, RDF.type, XSD.positiveInteger), (x, RDF.type, XSD.byte)],
                  regime='rdf', datatypes={XSD.positiveInteger, XSD.byte}) is True
    source = [(S, P, TripleTerm(O, Q, lit('01', XSD.integer)))]
    assert decide(source, [(x, RDF.type, XSD.decimal)], regime='rdf',
                  datatypes={XSD.integer, XSD.decimal}) is True
    assert decide(source, [(O, Q, lit('1', XSD.integer))],
                  regime='rdf', datatypes={XSD.integer}) is False


def test_work_limit_is_not_a_datatype_verdict():
    with pytest.raises(EntailmentResourceLimit):
        entails([(V, RDF.type, XSD.boolean)], False, regime='rdf', datatypes={XSD.boolean},
                mode='decide', max_steps=2)


def test_assignment_limit_reports_exhaustion_instead_of_false(monkeypatch):
    from rdfcore import _datatype_reasoning
    monkeypatch.setattr(_datatype_reasoning, '_MAX_ASSIGNMENTS', 2)
    source = [(S, P, lit('true', XSD.boolean)), (S, P, lit('false', XSD.boolean)),
              (V, RDF.type, XSD.boolean), (O, RDF.type, XSD.boolean)]
    with pytest.raises(EntailmentResourceLimit, match='assignment limit'):
        decide(source, [(S, P, V)], regime='rdf', datatypes={XSD.boolean})


def test_bounded_integer_domain_is_not_reduced_to_three_sample_values():
    source = [(S, P, lit(str(n), XSD.byte)) for n in range(-128, 128)]
    source.append((V, RDF.type, XSD.byte))
    assert decide(source, [(S, P, V)], regime='rdf', datatypes={XSD.byte}) is True
    # Remove a value that is not one of the default 0/1/-1 existence samples.
    source.remove((S, P, lit('27', XSD.byte)))
    assert decide(source, [(S, P, V)], regime='rdf', datatypes={XSD.byte}) is False


def test_new_assignment_values_receive_all_recognized_memberships():
    assert decide([(V, RDF.type, XSD.byte)], [(V, RDF.type, XSD.integer)],
                  regime='rdf', datatypes={XSD.byte, XSD.integer}) is True


def test_typed_names_inside_propositions_keep_semantic_value_assignments():
    source = [(V, RDF.type, XSD.boolean)]
    assert decide(source, [(S, P, TripleTerm(V, Q, O))], regime='rdf', datatypes={XSD.boolean}) is False


def test_fixed_vocabulary_aliasing_has_a_checked_candidate_model():
    assert decide([(RDF.type, RDF.type, XSD.boolean)], False, regime='rdf', datatypes={XSD.boolean}) is False


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
def test_inconsistency_decision_does_not_mutate_or_repair_stored_data(tmp_path, backend):
    from rdfcore import Dataset, Memory, SQLiteStore

    path = tmp_path / 'datatype.sqlite'
    store = Memory() if backend == 'memory' else SQLiteStore(path)
    dataset = Dataset(store=store)
    graph = dataset.graph(URIRef('urn:graph'))
    graph.add((S, P, lit('25', XSD.integer)))
    graph.add((P, RDFS.range, XSD.string))
    before = set(dataset.quads())
    assert decide(graph, False, datatypes={XSD.integer}) is True
    assert set(dataset.quads()) == before
    assert len(dataset.default_graph) == 0
    with pytest.raises(UnsupportedEntailment):
        entails(graph, [(O, Q, V)], regime='rdfs')
    dataset.close()
    if backend == 'sqlite':
        reopened = Dataset(store=SQLiteStore(path))
        assert set(reopened.quads()) == before
        reopened.close()


def test_aliased_properties_cannot_certify_a_branch_with_unassigned_new_constraints():
    # Picking P=Q as a boolean value can activate Q's integer range on P's
    # ordinary edge. That branch needs a value assignment for O as well.
    source = [(P, RDF.type, XSD.boolean), (Q, RDF.type, XSD.boolean),
              (Q, RDFS.range, XSD.integer), (S, P, O)]
    # A different boolean assignment keeps the graph consistent.
    assert decide(source, False, datatypes={XSD.boolean, XSD.integer}) is False


def test_missing_html_mapping_and_xml_entities_are_not_silent_consistency_results(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, 'html5rdf', None)
    with pytest.raises(UnsupportedEntailment):
        decide([(S, P, lit('<p>text', RDF.HTML))], False, datatypes={RDF.HTML})
    # The XML path rejects a DTD; it does not read the external resource.
    xml = '<!DOCTYPE a SYSTEM "file:///does-not-exist"><a/>'
    assert decide([(S, P, lit(xml, RDF.XMLLiteral))], False,
                  datatypes={RDF.XMLLiteral}) is True
