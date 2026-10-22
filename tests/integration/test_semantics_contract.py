"""T37: decisions, missing facilities and exhaustion are different outcomes.

Normative baseline: Semantics CRD 2026-09-24 §§5, 7.1–7.2, 8 and 9.
The explicit decision mode is not a complete RDF/RDFS reasoner.
"""

import pytest

from rdfcore import BNode, ConjunctiveGraph, Dataset, Literal, RDF, TripleTerm, URIRef, XSD
from rdfcore.datatypes import DatatypeResourceLimit, UnsupportedDatatype
from rdfcore import semantics

S, P, O, Q = map(URIRef, ('urn:s', 'urn:p', 'urn:o', 'urn:q'))


def typed(value, datatype=XSD.integer):
    return Literal(value, datatype=datatype, normalize=False)


@pytest.mark.parametrize('regime', ['simple', 'rdf', 'rdfs'])
def test_positive_negative_and_legacy_contract(regime):
    assert semantics.entails([(S, P, O)], [(S, P, O)], regime=regime, mode='decide') is True
    assert semantics.entails([(S, P, O)], [(S, Q, O)], regime=regime, mode='decide') is False
    if regime != 'simple':
        with pytest.raises(semantics.UnsupportedEntailment):
            semantics.entails([(S, P, O)], [(S, Q, O)], regime=regime)


@pytest.mark.parametrize('regime', ['simple', 'rdf', 'rdfs'])
def test_ill_typed_recognized_literal_explodes_even_inside_unasserted_term(regime):
    value = typed('invalid')
    premise = [(S, P, TripleTerm(S, Q, value))]
    for target in (False, [], [(O, Q, S)]):
        assert semantics.entails(premise, target, regime=regime,
                                datatypes={XSD.integer}, mode='decide') is True
    assert semantics.entails(premise, False, mode='decide') is False


@pytest.mark.parametrize('left,right,recognized,expected', [
    (typed('010'), typed('10'), {XSD.integer}, True),
    (typed('10'), typed('10.0', XSD.decimal), {XSD.integer, XSD.decimal}, True),
    (typed('10'), typed('10.0', XSD.decimal), {XSD.integer}, False),
    (typed('010'), typed('10'), set(), False),
    (typed('0', XSD.double), typed('-0', XSD.double), {XSD.double}, False),
    (typed('{"a":0,"b":1}', RDF.JSON), typed('{"b":1,"a":0}', RDF.JSON), {RDF.JSON}, True),
    (typed('[0]', RDF.JSON), typed('[-0]', RDF.JSON), {RDF.JSON}, False),
    (Literal('v', lang='en'), Literal('v', lang='EN'), {RDF.langString}, True),
    (Literal('v', lang='en', direction='ltr'), Literal('v', lang='en', direction='rtl'),
     {RDF.dirLangString}, False),
])
def test_explicit_simple_datatype_value_decisions(left, right, recognized, expected):
    assert semantics.entails([(S, P, left)], [(S, P, right)],
                            datatypes=recognized, mode='decide') is expected


def test_transparent_values_do_not_assert_inner_triples():
    left, right = TripleTerm(S, Q, typed('042')), TripleTerm(S, Q, typed('42'))
    assert semantics.entails([(S, P, left)], [(S, P, right)],
                            datatypes={XSD.integer}, mode='decide') is True
    with pytest.raises(semantics.UnsupportedEntailment):
        semantics.entails([(S, P, left)], [(S, Q, typed('42'))],
                         regime='rdf', datatypes={XSD.integer}, mode='decide')


def test_negative_certificate_is_not_assumed_for_full_rdfs_or_rdf():
    # Proposition constraints still need T39; finite booleans are covered by T38.
    from rdfcore import RDFS
    premise = [(S, RDF.type, RDFS.Proposition)]
    for regime in ('rdf', 'rdfs'):
        with pytest.raises(semantics.UnsupportedEntailment):
            semantics.entails(premise, [(S, P, O)], regime=regime,
                             datatypes={XSD.boolean}, mode='decide')
        with pytest.raises(semantics.UnsupportedEntailment):
            semantics.entails(premise, False, regime=regime,
                             datatypes={XSD.boolean}, mode='decide')


def test_invalid_conclusion_is_false_only_if_premise_consistency_is_known():
    target = [(S, P, typed('invalid'))]
    assert semantics.entails([], target, datatypes={XSD.integer}, mode='decide') is False
    with pytest.raises(semantics.UnsupportedEntailment):
        semantics.entails([(S, RDF.type, XSD.boolean)], target,
                         regime='rdf', datatypes={XSD.integer}, mode='decide')


@pytest.mark.parametrize('regime', ['rdf', 'rdfs'])
def test_mandatory_datatypes_and_explicit_recognition(regime):
    assert semantics.entails([(S, P, typed('\0', XSD.string))], False,
                            regime=regime, datatypes=set(), mode='decide') is True
    # An unrecognized datatype is opaque, not automatically ill-typed.
    assert semantics.entails([(S, P, typed('bad', URIRef('urn:unknown')))], [],
                            regime=regime, mode='decide') is True


@pytest.mark.parametrize('datatypes', [XSD.integer, 'integer', [str(XSD.integer)], [None]])
def test_recognition_requires_an_iterable_of_iris(datatypes):
    with pytest.raises(TypeError):
        semantics.entails([], [], datatypes=datatypes, mode='decide')


def test_unknown_recognition_is_unsupported_and_legacy_does_not_silently_opt_in():
    with pytest.raises(semantics.UnsupportedEntailment):
        semantics.entails([], [], datatypes={URIRef('urn:unknown')}, mode='decide')
    with pytest.raises(semantics.UnsupportedEntailment):
        semantics.entails([], [], datatypes={XSD.integer})
    with pytest.raises(TypeError):
        semantics.entails([], False)
    with pytest.raises(ValueError):
        semantics.entails([], [], mode='complete')


@pytest.mark.parametrize('factory', [Dataset, ConjunctiveGraph])
def test_dataset_is_never_implicitly_unioned(factory):
    dataset = factory()
    dataset.get_context(URIRef('urn:g')).add((S, P, O))
    with pytest.raises(semantics.UnsupportedEntailment, match='graph'):
        semantics.entails(dataset, [], mode='decide')
    with pytest.raises(semantics.UnsupportedEntailment, match='graph'):
        semantics.entails([], dataset, mode='decide')


@pytest.mark.parametrize('exception', [DatatypeResourceLimit, UnsupportedDatatype])
def test_datatype_facility_failure_is_not_inconsistency(monkeypatch, exception):
    from rdfcore import datatypes

    def unavailable(literal):
        raise exception('controlled failure')

    monkeypatch.setattr(datatypes, 'datatype_value', unavailable)
    expected = (semantics.EntailmentResourceLimit if exception is DatatypeResourceLimit
                else semantics.UnsupportedEntailment)
    with pytest.raises(expected):
        semantics.entails([(S, P, typed('1'))], False,
                         datatypes={XSD.integer}, mode='decide')


def test_budget_and_recognition_are_restored_after_decision():
    with pytest.raises(semantics.EntailmentResourceLimit):
        semantics.entails([(S, P, typed('1'))], False, max_steps=0,
                         datatypes={XSD.integer}, mode='decide')
    assert not semantics.entails([(S, P, typed('01'))], [(S, P, typed('1'))])


def test_shared_existential_mapping_uses_value_identity():
    x = BNode('x')
    premise = [(S, P, typed('01')), (O, P, typed('1'))]
    assert semantics.entails(premise, [(S, P, x), (O, P, x)],
                            datatypes={XSD.integer}, mode='decide') is True


@pytest.mark.parametrize('regime', ['rdf', 'rdfs'])
def test_iri_identity_is_not_percent_decoded(regime):
    a, b = URIRef('http://example.org/#André'), URIRef('http://example.org/#Andr%C3%A9')
    for left, right in ((a, b), (b, a)):
        assert semantics.entails([(left, P, Literal('2000'))], [(right, P, Literal('2000'))],
                                regime=regime, mode='decide') is False


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
def test_decisions_preserve_store_and_graph_contexts(tmp_path, backend):
    from rdfcore import Memory, SQLiteStore

    store = Memory() if backend == 'memory' else SQLiteStore(tmp_path / 'semantics.sqlite')
    dataset = Dataset(store=store)
    graph = dataset.graph(URIRef('urn:g'))
    graph.add((S, P, typed('01')))
    dataset.default_graph.add((S, Q, O))
    before = set(dataset.quads())
    assert semantics.entails(graph, [(S, P, typed('1'))],
                            mode='decide', datatypes={XSD.integer}) is True
    assert semantics.entails(dataset.default_graph, [(S, P, typed('1'))],
                            mode='decide', datatypes={XSD.integer}) is False
    assert set(dataset.quads()) == before
    dataset.close()
    if backend == 'sqlite':
        reopened = Dataset(store=SQLiteStore(tmp_path / 'semantics.sqlite'))
        assert set(reopened.quads()) == before
        reopened.close()


def test_parallel_calls_do_not_share_recognition():
    from concurrent.futures import ThreadPoolExecutor

    def compare(recognized):
        return semantics.entails([(S, P, typed('01'))], [(S, P, typed('1'))],
                                 mode='decide', datatypes={XSD.integer} if recognized else set())

    options = [True, False] * 10
    with ThreadPoolExecutor(max_workers=4) as executor:
        assert list(executor.map(compare, options)) == options
